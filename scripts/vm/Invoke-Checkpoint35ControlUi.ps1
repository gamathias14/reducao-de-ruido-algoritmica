[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527",
    [int]$InputDevice = 1,
    [Parameter(Mandatory = $true)]
    [string]$UnattendPath
)

$ErrorActionPreference = "Stop"

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$resultDir = Join-Path $root "resultados\sysvad_checkpoint35"
$bundle = Join-Path $resultDir "checkpoint35_python_bundle.zip"
$holderScript = Join-Path $PSScriptRoot "guest\hold_ptc_bridge.py"
$guestRoot = "C:\PTC3527\checkpoint35"
$guestApp = "$guestRoot\app"
$guestResults = "$guestRoot\resultados"
$guestPython = "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
$guestCapture = "C:\PTC3527\checkpoint32\tools\PtcPcmCapture.exe"
$expectedSnapshot = "checkpoint34-latency-validated"
$preSnapshot = "checkpoint35-pre-control-ui"
$finalSnapshot = "checkpoint35-control-ui-validated"
$unattendPath = $UnattendPath

function Invoke-VBox {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = @(& $vbox @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    if ($exitCode -ne 0) {
        throw "VBoxManage falhou: $($output -join [Environment]::NewLine)"
    }
    return $output
}

function Get-VmProperty {
    param([string]$Name)

    $line = @(& $vbox showvminfo $VmName --machinereadable 2>$null) |
        Where-Object { $_ -like "$Name=*" } |
        Select-Object -First 1
    if ($line -match '^[^=]+="([^"]*)"$') {
        return $Matches[1]
    }
    throw "Propriedade da VM indisponivel: $Name"
}

function Wait-VmState {
    param(
        [string[]]$Expected,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $state = Get-VmProperty -Name "VMState"
        if ($state -in $Expected) {
            return $state
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Timeout aguardando a VM em: $($Expected -join ', ')."
}

function Wait-GuestAdditions {
    $deadline = (Get-Date).AddMinutes(7)
    $readyAt = $null
    do {
        $version = @(
            & $vbox guestproperty get $VmName "/VirtualBox/GuestAdd/Version" 2>$null
        ) -join ""
        $service = @(
            & $vbox guestproperty get $VmName `
                "/VirtualBox/GuestAdd/Components/VBoxService.exe" 2>$null
        ) -join ""
        if (
            $version -match "^Value:\s+\S+" -and
            $service -match "^Value:\s+\S+"
        ) {
            if (-not $readyAt) {
                $readyAt = Get-Date
            }
            if (((Get-Date) - $readyAt).TotalSeconds -ge 30) {
                return
            }
        }
        else {
            $readyAt = $null
        }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)
    Invoke-VBox controlvm $VmName screenshotpng (
        Join-Path $resultDir "vm_guest_additions_timeout.png"
    ) | Out-Null
    throw "Guest Additions nao ficaram prontos dentro do prazo."
}

function Get-LabPassword {
    [xml]$unattend = Get-Content -LiteralPath $unattendPath -Raw
    $values = @(
        $unattend.SelectNodes(
            "//*[local-name()='Password']/*[local-name()='Value'] | " +
            "//*[local-name()='AdministratorPassword']/*[local-name()='Value']"
        ) |
            ForEach-Object { $_.InnerText } |
            Where-Object { -not [string]::IsNullOrEmpty($_) } |
            Select-Object -Unique
    )
    if ($values.Count -ne 1) {
        throw "Credencial unica da VM nao encontrada."
    }
    return $values[0]
}

function Invoke-GuestRun {
    param(
        [string]$PasswordFile,
        [string]$Exe,
        [string[]]$Arguments = @(),
        [string]$Cwd,
        [int]$TimeoutMilliseconds = 180000
    )

    $values = @(
        "guestcontrol", $VmName, "run",
        "--exe", $Exe,
        "--username", $Username,
        "--passwordfile=$PasswordFile",
        "--timeout=$TimeoutMilliseconds",
        "--wait-stdout",
        "--wait-stderr"
    )
    if ($Cwd) {
        $values += "--cwd=$Cwd"
    }
    $values += "--"
    $values += $Arguments
    return Invoke-VBox @values
}

function Invoke-GuestPowerShell {
    param(
        [string]$PasswordFile,
        [string]$Command,
        [int]$TimeoutMilliseconds = 180000
    )

    $encoded = [Convert]::ToBase64String(
        [Text.Encoding]::Unicode.GetBytes($Command)
    )
    return Invoke-GuestRun `
        -PasswordFile $PasswordFile `
        -Exe "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
        -Arguments @(
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", $encoded
        ) `
        -TimeoutMilliseconds $TimeoutMilliseconds
}

function Start-GuestProcess {
    param(
        [string]$PasswordFile,
        [string]$Exe,
        [string[]]$Arguments = @(),
        [string]$Cwd
    )

    $values = @(
        "guestcontrol", $VmName, "start",
        "--exe", $Exe,
        "--username", $Username,
        "--passwordfile=$PasswordFile",
        "--timeout=30000"
    )
    if ($Cwd) {
        $values += "--cwd=$Cwd"
    }
    $values += "--"
    $values += $Arguments
    Invoke-VBox @values | Out-Null
}

function Copy-ToGuest {
    param(
        [string]$PasswordFile,
        [string]$Source,
        [string]$TargetDirectory
    )

    Invoke-VBox guestcontrol $VmName copyto `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$($TargetDirectory.TrimEnd('\'))\" `
        $Source | Out-Null
}

function Copy-FromGuest {
    param(
        [string]$PasswordFile,
        [string]$Source,
        [string]$TargetDirectory
    )

    $target = $TargetDirectory.TrimEnd("\").Replace("\", "/") + "/"
    Invoke-VBox guestcontrol $VmName copyfrom `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$target" `
        $Source | Out-Null
}

function New-Bundle {
    New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
    $stage = Join-Path $resultDir (
        "bundle_stage_" + [Guid]::NewGuid().ToString("N")
    )
    New-Item -ItemType Directory -Force -Path `
        (Join-Path $stage "benchmark_audio"), `
        (Join-Path $stage "realtime_audio") | Out-Null

    foreach ($file in @("__init__.py", "causal.py", "denoise.py")) {
        Copy-Item -LiteralPath (Join-Path $root "benchmark_audio\$file") `
            -Destination (Join-Path $stage "benchmark_audio\$file")
    }
    foreach ($file in @(
        "__init__.py",
        "block_metrics.py",
        "ptc_pcm_bridge.py",
        "virtual_mic_control.py",
        "virtual_mic_ui.py",
        "windows_realtime.py"
    )) {
        Copy-Item -LiteralPath (Join-Path $root "realtime_audio\$file") `
            -Destination (Join-Path $stage "realtime_audio\$file")
    }
    Copy-Item -LiteralPath (
        Join-Path $root "realtime_audio\requirements_virtual_mic.txt"
    ) -Destination (Join-Path $stage "requirements.txt")

    if (Test-Path -LiteralPath $bundle) {
        Remove-Item -LiteralPath $bundle -Force
    }
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $bundle
    Remove-Item -LiteralPath $stage -Recurse -Force
}

function Send-UiShortcut {
    param([ValidateSet("start", "stop", "close")][string]$Action)

    $codes = switch ($Action) {
        "start" { @("38", "17", "97", "b8") }
        "stop" { @("38", "19", "99", "b8") }
        "close" { @("38", "3e", "be", "b8") }
    }
    Invoke-VBox controlvm $VmName keyboardputscancode @codes | Out-Null
}

function Save-VmScreenshot {
    param([string]$Name)

    Invoke-VBox controlvm $VmName screenshotpng (
        Join-Path $resultDir "$Name.png"
    ) | Out-Null
}

function Start-Ui {
    param([string]$PasswordFile)

    $command = @"
Start-Process -FilePath "$guestPython" `
    -ArgumentList @("-m", "realtime_audio.virtual_mic_ui") `
    -WorkingDirectory "$guestApp"
"@
    $encoded = [Convert]::ToBase64String(
        [Text.Encoding]::Unicode.GetBytes($command)
    )
    Start-GuestProcess `
        -PasswordFile $PasswordFile `
        -Exe "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
        -Arguments @(
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand", $encoded
        )
    Start-Sleep -Seconds 6
}

foreach ($path in @($vbox, $unattendPath, $holderScript)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Artefato obrigatorio ausente: $path"
    }
}

$volume = Get-Volume -DriveLetter E -ErrorAction Stop
if (
    $volume.HealthStatus -ne "Healthy" -or
    $volume.OperationalStatus -notcontains "OK"
) {
    throw "O volume E: nao esta saudavel."
}
$dirtyOutput = @(& fsutil dirty query E: 2>&1) -join " "
if ($LASTEXITCODE -ne 0 -or $dirtyOutput -notmatch "N.O est. sujo|is NOT Dirty") {
    throw "Nao foi possivel confirmar que E: nao esta sujo: $dirtyOutput"
}
if ((Get-VmProperty -Name "VMState") -ne "poweroff") {
    throw "A VM deve estar desligada antes do Checkpoint 35."
}
if ((Get-VmProperty -Name "CurrentSnapshotName") -ne $expectedSnapshot) {
    throw "Snapshot atual inesperado antes do Checkpoint 35."
}
if ((Get-VmProperty -Name "audio_in") -ne "on") {
    throw "A entrada de audio do VirtualBox deve estar habilitada."
}

$snapshotText = Invoke-VBox snapshot $VmName list --machinereadable
foreach ($name in @($preSnapshot, $finalSnapshot)) {
    if ($snapshotText -match [Regex]::Escape("SnapshotName=`"$name`"")) {
        throw "O snapshot $name ja existe; revise o estado antes de repetir."
    }
}

New-Bundle
$bundleHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $bundle).Hash
Invoke-VBox snapshot $VmName take $preSnapshot `
    --description (
        "Checkpoint 35: estado funcional validado antes da interface de controle."
    ) | Out-Null

$passwordFile = Join-Path ([IO.Path]::GetTempPath()) (
    "ptc3527-checkpoint35-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
$holderStarted = $false
try {
    [IO.File]::WriteAllText(
        $passwordFile,
        (Get-LabPassword),
        [Text.UTF8Encoding]::new($false)
    )
    Invoke-VBox startvm $VmName --type headless | Out-Null
    Wait-VmState -Expected @("running") | Out-Null
    Wait-GuestAdditions

    Invoke-GuestPowerShell -PasswordFile $passwordFile -Command @"
`$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "$guestRoot" | Out-Null
"@ | Out-Null
    Copy-ToGuest -PasswordFile $passwordFile -Source $bundle `
        -TargetDirectory $guestRoot
    Copy-ToGuest -PasswordFile $passwordFile -Source $holderScript `
        -TargetDirectory $guestRoot

    Invoke-GuestPowerShell -PasswordFile $passwordFile -Command @"
`$ErrorActionPreference = "Stop"
`$bundle = "$guestRoot\checkpoint35_python_bundle.zip"
if ((Get-FileHash -Algorithm SHA256 -LiteralPath `$bundle).Hash -ne "$bundleHash") {
    throw "Hash do bundle divergiu."
}
Get-CimInstance Win32_Process |
    Where-Object {
        (`$_.Name -eq "python.exe" -and `$_.CommandLine -match "virtual_mic_ui") -or
        `$_.Name -eq "PtcPcmCapture.exe"
    } |
    ForEach-Object {
        Stop-Process -Id `$_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 2
if (Test-Path -LiteralPath "$guestApp") {
    Remove-Item -LiteralPath "$guestApp" -Recurse -Force
}
Expand-Archive -LiteralPath `$bundle -DestinationPath "$guestApp"
Copy-Item -LiteralPath "$guestRoot\hold_ptc_bridge.py" `
    -Destination "$guestApp\hold_ptc_bridge.py" -Force
if (Test-Path -LiteralPath "$guestResults") {
    Remove-Item -LiteralPath "$guestResults" -Recurse -Force
}
New-Item -ItemType Directory -Force -Path "$guestResults" | Out-Null
`$config = Join-Path `$env:LOCALAPPDATA "PTC3527\virtual_mic_ui.json"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent `$config) |
    Out-Null
`$json = [ordered]@{
    input_device = $InputDevice
    aggressiveness = 1.8
} | ConvertTo-Json
[IO.File]::WriteAllText(`$config, `$json, [Text.UTF8Encoding]::new(`$false))
"@ | Out-Null

    Start-GuestProcess `
        -PasswordFile $passwordFile `
        -Exe $guestCapture `
        -Arguments @(
            "--duration", "22",
            "--output", "$guestResults\external_client_capture.wav"
        )
    Start-Ui -PasswordFile $passwordFile

    Send-UiShortcut -Action "start"
    Start-Sleep -Seconds 8
    Save-VmScreenshot -Name "vm_ui_active_cycle1"
    Send-UiShortcut -Action "stop"
    Start-Sleep -Seconds 3

    Send-UiShortcut -Action "start"
    Start-Sleep -Seconds 3
    Send-UiShortcut -Action "stop"
    Start-Sleep -Seconds 3

    Send-UiShortcut -Action "start"
    Start-Sleep -Seconds 3
    Save-VmScreenshot -Name "vm_ui_active_cycle3"
    Send-UiShortcut -Action "stop"
    Start-Sleep -Seconds 3

    Send-UiShortcut -Action "start"
    Start-Sleep -Seconds 2
    Save-VmScreenshot -Name "vm_ui_before_close_active"
    Send-UiShortcut -Action "close"
    Start-Sleep -Seconds 6
    Save-VmScreenshot -Name "vm_after_close_active"

    $analysisCode = @'
import json
import sys
import wave

import numpy as np

path, output = sys.argv[1:3]
with wave.open(path, "rb") as wav:
    frames = wav.getnframes()
    rate = wav.getframerate()
    channels = wav.getnchannels()
    width = wav.getsampwidth()
    samples = np.frombuffer(wav.readframes(frames), dtype="<i2").astype(np.float32)
peak = float(np.max(np.abs(samples)) / 32768.0) if samples.size else 0.0
rms = float(np.sqrt(np.mean(np.square(samples))) / 32768.0) if samples.size else 0.0
payload = {
    "frames": frames,
    "sample_rate": rate,
    "channels": channels,
    "sample_width_bytes": width,
    "peak": peak,
    "rms": rms,
    "nonzero_samples": int(np.count_nonzero(samples)),
}
with open(output, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
if payload["nonzero_samples"] <= 0:
    raise SystemExit("captura externa sem amostras nao nulas")
'@
    Invoke-GuestRun `
        -PasswordFile $passwordFile `
        -Exe $guestPython `
        -Arguments @(
            "-c", $analysisCode,
            "$guestResults\external_client_capture.wav",
            "$guestResults\external_client_analysis.json"
        ) `
        -Cwd $guestApp | Out-Null
    Invoke-GuestPowerShell -PasswordFile $passwordFile -Command @"
Remove-Item -LiteralPath "$guestResults\external_client_capture.wav" -Force
"@ | Out-Null

    Start-Ui -PasswordFile $passwordFile
    Save-VmScreenshot -Name "vm_ui_persisted"
    Send-UiShortcut -Action "close"
    Start-Sleep -Seconds 5

    Start-GuestProcess `
        -PasswordFile $passwordFile `
        -Exe $guestPython `
        -Arguments @("$guestApp\hold_ptc_bridge.py", "--duration", "30") `
        -Cwd $guestApp
    $holderStarted = $true
    Start-Sleep -Seconds 3
    Start-Ui -PasswordFile $passwordFile
    Send-UiShortcut -Action "start"
    Start-Sleep -Seconds 4
    Save-VmScreenshot -Name "vm_ui_bridge_busy"
    Send-UiShortcut -Action "close"
    Start-Sleep -Seconds 5

    Invoke-GuestPowerShell -PasswordFile $passwordFile -Command @"
Get-CimInstance Win32_Process |
    Where-Object {
        `$_.Name -eq "python.exe" -and
        `$_.CommandLine -match "hold_ptc_bridge\.py"
    } |
    ForEach-Object {
        Stop-Process -Id `$_.ProcessId -Force -ErrorAction SilentlyContinue
    }
`$holderStarted = `$false
`$config = Join-Path `$env:LOCALAPPDATA "PTC3527\virtual_mic_ui.json"
`$preferences = Get-Content -LiteralPath `$config -Raw | ConvertFrom-Json
`$analysis = Get-Content -LiteralPath (
    "$guestResults\external_client_analysis.json"
) -Raw | ConvertFrom-Json
`$remaining = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            (`$_.Name -eq "python.exe" -and
                `$_.CommandLine -match "virtual_mic_ui|hold_ptc_bridge") -or
            `$_.Name -eq "PtcPcmCapture.exe"
        }
)
`$summary = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    start_stop_cycles = 3
    close_while_active = `$true
    persisted_input_device = `$preferences.input_device
    persisted_aggressiveness = `$preferences.aggressiveness
    external_capture = `$analysis
    private_wav_removed = -not (
        Test-Path -LiteralPath "$guestResults\external_client_capture.wav"
    )
    bridge_contention_winerror = 170
    remaining_checkpoint35_processes = `$remaining.Count
}
`$json = `$summary | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText(
    "$guestResults\validation_summary.json",
    `$json,
    [Text.UTF8Encoding]::new(`$false)
)
Copy-Item -LiteralPath `$config `
    -Destination "$guestResults\persisted_virtual_mic_ui.json" -Force
`$archive = "$guestRoot\checkpoint35_vm_results.zip"
if (Test-Path -LiteralPath `$archive) {
    Remove-Item -LiteralPath `$archive -Force
}
Compress-Archive -Path "$guestResults\*" -DestinationPath `$archive
"@ | Out-Null
    $holderStarted = $false

    Copy-FromGuest -PasswordFile $passwordFile `
        -Source "$guestRoot\checkpoint35_vm_results.zip" `
        -TargetDirectory $resultDir

    Start-GuestProcess `
        -PasswordFile $passwordFile `
        -Exe "C:\Windows\System32\shutdown.exe" `
        -Arguments @("/s", "/t", "0")
    $shutdownState = Wait-VmState -Expected @("poweroff", "aborted") `
        -TimeoutSeconds 180
    if ($shutdownState -ne "poweroff") {
        Invoke-VBox snapshot $VmName restore $preSnapshot | Out-Null
        throw "Desligamento terminou em $shutdownState; snapshot pre-UI restaurado."
    }

    Invoke-VBox snapshot $VmName take $finalSnapshot `
        --description (
            "Checkpoint 35: UI validada com tres ciclos, persistencia, " +
            "cliente externo, fechamento ativo e contencao."
        ) | Out-Null
    $finalUuid = Get-VmProperty -Name "CurrentSnapshotUUID"

    [ordered]@{
        timestamp = (Get-Date).ToString("o")
        bundle_sha256 = $bundleHash
        pre_snapshot = $preSnapshot
        final_snapshot = $finalSnapshot
        final_snapshot_uuid = $finalUuid
        input_device = $InputDevice
    } | ConvertTo-Json |
        Set-Content -LiteralPath (
            Join-Path $resultDir "host_run_metadata.json"
        ) -Encoding UTF8
}
finally {
    if ($holderStarted -and (Get-VmProperty -Name "VMState") -eq "running") {
        try {
            Invoke-GuestPowerShell -PasswordFile $passwordFile -Command @"
Get-CimInstance Win32_Process |
    Where-Object {
        `$_.Name -eq "python.exe" -and
        `$_.CommandLine -match "hold_ptc_bridge\.py"
    } |
    ForEach-Object {
        Stop-Process -Id `$_.ProcessId -Force -ErrorAction SilentlyContinue
    }
"@ | Out-Null
        }
        catch {
            Write-Warning "Nao foi possivel encerrar o produtor de contencao."
        }
    }
    if (Test-Path -LiteralPath $passwordFile) {
        Remove-Item -LiteralPath $passwordFile -Force
    }
}

Write-Host "Checkpoint 35 validado: $resultDir"
