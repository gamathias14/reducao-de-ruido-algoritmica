[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527",
    [string]$ControlledCaptureName = "CABLE Output (VB-Audio Virtual Cable)",
    [string]$ControlledPlaybackName = "CABLE In 16ch (VB-Audio Virtual Cable), Windows WASAPI",
    [string]$FinalCaptureName = "Microfone (USB Audio Device)",
    [string]$CaptureExe = (
        Join-Path $env:USERPROFILE (
            "source\repos\Windows-driver-samples\audio\sysvad\" +
            "tools\PtcPcmCapture\x64\Release\PtcPcmCapture.exe"
        )
    ),
    [Parameter(Mandatory = $true)]
    [string]$UnattendPath
)

$ErrorActionPreference = "Stop"

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$resultDir = Join-Path $root "resultados\sysvad_checkpoint37"
$bundle = Join-Path $resultDir "checkpoint37_python_bundle.zip"
$captureExe = $CaptureExe
$guestRoot = "C:\PTC3527\checkpoint37"
$guestApp = "$guestRoot\app"
$guestResults = "$guestRoot\resultados"
$guestPython = (
    "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
)
$expectedSnapshot = "checkpoint37-pre-pop-diagnostics"
$endpointTool = Join-Path $root (
    "resultados\sysvad_checkpoint33\SetDefaultCaptureEndpoint.exe"
)
$signalScript = Join-Path $root "scripts\audio\play_controlled_signal.py"
$guestMatrixScript = Join-Path $root (
    "scripts\vm\guest\Invoke-Checkpoint37Matrix.ps1"
)
$guestMatrixLauncher = Join-Path $root (
    "scripts\vm\guest\Start-Checkpoint37Matrix.cmd"
)
$sharedFolderName = "PTC3527Checkpoint37"
$guestExchangeRoot = "\\VBOXSVR\$sharedFolderName"
$hostPython = Join-Path $root ".venv-checkpoint34\Scripts\python.exe"
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
    param([string]$Expected, [int]$TimeoutSeconds = 180)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if ((Get-VmProperty -Name "VMState") -eq $Expected) {
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Timeout aguardando VM em estado $Expected."
}

function Wait-GuestAdditions {
    param()
    $deadline = (Get-Date).AddMinutes(6)
    Start-Sleep -Seconds 20
    & $vbox controlvm $VmName keyboardputscancode 1c 9c 2>$null | Out-Null
    do {
        $version = @(
            & $vbox guestproperty get $VmName `
                "/VirtualBox/GuestAdd/Version" 2>$null
        ) | Select-Object -First 1
        $users = @(
            & $vbox guestproperty get $VmName `
                "/VirtualBox/GuestInfo/OS/LoggedInUsers" 2>$null
        ) | Select-Object -First 1
        if (
            $version -match "^Value:\s+\S+" -and
            $users -match "^Value:\s+([1-9][0-9]*)$"
        ) {
            return
        }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)
    throw "Guest Additions ou sessao interativa nao ficaram prontas no prazo."
}

function Wait-MatrixStatus {
    param(
        [int]$TimeoutSeconds = 600,
        [int]$StartTimeoutSeconds = 90
    )

    $startedDeadline = (Get-Date).AddSeconds($StartTimeoutSeconds)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $seenRunning = $false
    do {
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $lines = @(
            & $vbox guestproperty get $VmName `
                "/PTC3527/Checkpoint37/Status" 2>$null
        )
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $oldPreference
        if ($exitCode -eq 0) {
            $line = $lines | Select-Object -First 1
            if ($line -match "^Value:\s+(.+)$") {
                $status = $Matches[1].Trim()
                if ($status -eq "running") {
                    $seenRunning = $true
                }
                if ($status -in @("completed", "failed")) {
                    return $status
                }
            }
        }
        if (-not $seenRunning -and (Get-Date) -ge $startedDeadline) {
            throw "A matriz nao publicou o estado running no prazo."
        }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)
    throw "Timeout aguardando o status da matriz."
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

function Invoke-Guest {
    param(
        [string]$PasswordFile,
        [string]$Command,
        [int]$TimeoutMilliseconds = 360000
    )

    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    $arguments = @(
        "guestcontrol", $VmName, "run",
        "--exe", "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "--username", $Username,
        "--passwordfile=$PasswordFile",
        "--timeout=$TimeoutMilliseconds",
        "--wait-stdout", "--wait-stderr", "--",
        "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", $encoded
    )
    return Invoke-VBox @arguments
}

function Copy-ToGuest {
    param([string]$PasswordFile, [string]$Source, [string]$TargetDirectory)

    Invoke-VBox guestcontrol $VmName copyto `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$($TargetDirectory.TrimEnd('\'))\" `
        $Source | Out-Null
}

function Copy-FromGuest {
    param([string]$PasswordFile, [string]$Source, [string]$TargetDirectory)

    $target = $TargetDirectory.TrimEnd("\").Replace("\", "/") + "/"
    Invoke-VBox guestcontrol $VmName copyfrom `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$target" `
        $Source | Out-Null
}

function New-Bundle {
    New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
    $stage = Join-Path $resultDir ("bundle_stage_" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path `
        (Join-Path $stage "benchmark_audio"), `
        (Join-Path $stage "realtime_audio") | Out-Null

    foreach ($file in @("__init__.py", "causal.py", "denoise.py")) {
        Copy-Item -LiteralPath (Join-Path $root "benchmark_audio\$file") `
            -Destination (Join-Path $stage "benchmark_audio\$file")
    }
    foreach ($file in @(
        "__init__.py",
        "audio_continuity.py",
        "block_metrics.py",
        "ptc_pcm_bridge.py",
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

foreach ($path in @(
    $vbox,
    $captureExe,
    $endpointTool,
    $signalScript,
    $guestMatrixScript,
    $guestMatrixLauncher,
    $hostPython,
    $unattendPath
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Artefato obrigatorio ausente: $path"
    }
}

$volume = Get-Volume -DriveLetter E -ErrorAction Stop
if ($volume.HealthStatus -ne "Healthy" -or $volume.OperationalStatus -notcontains "OK") {
    throw "Volume E: nao esta saudavel."
}
if ((Get-VmProperty -Name "VMState") -ne "poweroff") {
    throw "A VM deve estar desligada."
}
if ((Get-VmProperty -Name "CurrentSnapshotName") -ne $expectedSnapshot) {
    throw "Snapshot atual inesperado."
}
if ((Get-VmProperty -Name "audio_in") -ne "on") {
    throw "A entrada de audio da VM deve estar habilitada."
}

$endpointLines = @(& $endpointTool --list)
$originalLine = $endpointLines | Where-Object { $_ -match "^default=1`t" } |
    Select-Object -First 1
if ($originalLine -notmatch 'id=([^\s]+)$') {
    throw "Endpoint de captura padrao original nao identificado."
}
$originalEndpointId = $Matches[1]
$finalLine = $endpointLines | Where-Object {
    $_ -match ("`tname=" + [Regex]::Escape($FinalCaptureName) + "`t")
} | Select-Object -First 1
if ($finalLine -notmatch 'id=([^\s]+)$') {
    throw "Endpoint de captura final nao identificado: $FinalCaptureName"
}
$finalEndpointId = $Matches[1]

New-Bundle
foreach ($stalePath in @(
    (Join-Path $resultDir "checkpoint37_vm_results.zip"),
    (Join-Path $resultDir "checkpoint37_vm_partial.zip"),
    (Join-Path $resultDir "raw_capture_progress.json"),
    (Join-Path $resultDir "raw_capture_watchdog.txt"),
    (Join-Path $resultDir "vm_results")
)) {
    if (Test-Path -LiteralPath $stalePath) {
        Remove-Item -LiteralPath $stalePath -Recurse -Force
    }
}
Copy-Item -LiteralPath $captureExe `
    -Destination (Join-Path $resultDir "PtcPcmCapture.exe") -Force
Copy-Item -LiteralPath $guestMatrixScript `
    -Destination (Join-Path $resultDir "Invoke-Checkpoint37Matrix.ps1") -Force
$bundleHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $bundle).Hash
$captureHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $captureExe).Hash
$hashManifest = Join-Path $resultDir "checkpoint37_expected_hashes.json"
[ordered]@{
    bundle_sha256 = $bundleHash
    capture_sha256 = $captureHash
} | ConvertTo-Json | Set-Content -LiteralPath $hashManifest -Encoding UTF8
$passwordFile = Join-Path ([IO.Path]::GetTempPath()) (
    "ptc3527-checkpoint37-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
$signalProcess = $null
$matrixCompleted = $false

try {
    [IO.File]::WriteAllText(
        $passwordFile,
        (Get-LabPassword),
        [Text.UTF8Encoding]::new($false)
    )

    & $endpointTool --set-name $ControlledCaptureName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel selecionar a entrada controlada do host."
    }

    Invoke-VBox sharedfolder add $VmName `
        --name $sharedFolderName --hostpath $resultDir --automount | Out-Null
    Invoke-VBox startvm $VmName --type headless | Out-Null
    Wait-VmState -Expected "running"
    Wait-GuestAdditions

    Invoke-VBox guestproperty delete $VmName `
        "/PTC3527/Checkpoint37/Status" | Out-Null

    $signalProcess = Start-Process -FilePath $hostPython `
        -ArgumentList @(
            "`"$signalScript`"",
            "--output-device", "`"$ControlledPlaybackName`"",
            "--duration", "240",
            "--peak", "0.10",
            "--mode", "continuous"
        ) `
        -RedirectStandardOutput (Join-Path $resultDir "controlled_signal.stdout.txt") `
        -RedirectStandardError (Join-Path $resultDir "controlled_signal.stderr.txt") `
        -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 3

    $matrixCommand = (
        "& '$guestExchangeRoot\Invoke-Checkpoint37Matrix.ps1' " +
        "-ExchangeRoot '$guestExchangeRoot'"
    )
    $matrixEncoded = [Convert]::ToBase64String(
        [Text.Encoding]::Unicode.GetBytes($matrixCommand)
    )
    $matrixArguments = @(
        "guestcontrol", $VmName, "run",
        "--exe", "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "--username", $Username,
        "--passwordfile=$passwordFile",
        "--timeout=60000", "--wait-stdout", "--wait-stderr", "--",
        "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", $matrixEncoded
    )
    $matrixRunFailed = $false
    try {
        Invoke-VBox @matrixArguments | Out-Null
    } catch {
        $matrixRunFailed = $true
    }
    $matrixStatusLine = @(
        & $vbox guestproperty get $VmName `
            "/PTC3527/Checkpoint37/Status" 2>$null
    ) | Select-Object -First 1
    $matrixStatus = if ($matrixStatusLine -match "^Value:\s+(.+)$") {
        $Matches[1].Trim()
    } else {
        "unknown"
    }
    if (
        Test-Path -LiteralPath (
            Join-Path $resultDir "checkpoint37_vm_results.zip"
        )
    ) {
        $matrixStatus = "completed"
    } elseif (
        (Test-Path -LiteralPath (
            Join-Path $resultDir "checkpoint37_vm_partial.zip"
        )) -or
        (Test-Path -LiteralPath (
            Join-Path $resultDir "vm_results\matrix_error.txt"
        ))
    ) {
        $matrixStatus = "failed"
    } elseif (
        Test-Path -LiteralPath (
            Join-Path $resultDir "raw_capture_progress.json"
        )
    ) {
        $matrixStatus = "failed"
    }
    if ($matrixStatus -eq "failed") {
        $localPartial = Join-Path $resultDir "checkpoint37_vm_partial.zip"
        $progressEvidence = Join-Path $resultDir "raw_capture_progress.json"
        throw (
            "A matriz falhou; evidencias: $localPartial; " +
            "progresso: $progressEvidence"
        )
    }
    if ($matrixRunFailed -or $matrixStatus -ne "completed") {
        throw "A sessao da matriz falhou sem estado final valido: $matrixStatus"
    }

    if ($false) {
    $signalProcess = Start-Process -FilePath $hostPython `
        -ArgumentList @(
            "`"$signalScript`"",
            "--output-device", "`"$ControlledPlaybackName`"",
            "--duration", "180",
            "--peak", "0.10",
            "--mode", "continuous"
        ) `
        -RedirectStandardOutput (Join-Path $resultDir "controlled_signal.stdout.txt") `
        -RedirectStandardError (Join-Path $resultDir "controlled_signal.stderr.txt") `
        -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 3

    Invoke-Guest -PasswordFile $passwordFile -Command @"
`$ErrorActionPreference = "Stop"
`$root = "$guestRoot"
`$app = "$guestApp"
`$results = "$guestResults"
`$bundle = Join-Path `$root "checkpoint37_python_bundle.zip"
`$capture = Join-Path `$root "PtcPcmCapture.exe"
if ((Get-FileHash -Algorithm SHA256 -LiteralPath `$bundle).Hash -ne "$bundleHash") {
    throw "Hash do bundle divergiu."
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath `$capture).Hash -ne "$captureHash") {
    throw "Hash do capturador divergiu."
}
if (Test-Path -LiteralPath `$app) {
    Remove-Item -LiteralPath `$app -Recurse -Force
}
Expand-Archive -LiteralPath `$bundle -DestinationPath `$app
if (Test-Path -LiteralPath `$results) {
    Remove-Item -LiteralPath `$results -Recurse -Force
}
New-Item -ItemType Directory -Force -Path `$results | Out-Null
`$python = "$guestPython"

`$deviceCode = @'
import json
import sounddevice as sd

devices = sd.query_devices()
hostapis = sd.query_hostapis()
rows = []
for index, device in enumerate(devices):
    if int(device["max_input_channels"]) <= 0:
        continue
    rows.append({
        "index": index,
        "name": str(device["name"]),
        "host_api": str(hostapis[int(device["hostapi"])]["name"]),
    })
candidates = [
    row for row in rows
    if "mapeador" not in row["name"].casefold()
    and "primary" not in row["name"].casefold()
    and "external microphone" not in row["name"].casefold()
]
if len(candidates) != 1:
    raise SystemExit(f"entrada fisica ambigua: {candidates!r}; todas={rows!r}")
print(json.dumps({"selected": candidates[0], "inputs": rows}, ensure_ascii=False))
'@
Push-Location `$app
try {
    `$deviceJson = & `$python -c `$deviceCode
} finally {
    Pop-Location
}
[IO.File]::WriteAllText(
    (Join-Path `$results "guest_input_devices.json"),
    `$deviceJson,
    [Text.UTF8Encoding]::new(`$false)
)
`$inputDevice = ((`$deviceJson | ConvertFrom-Json).selected.index).ToString()

function Invoke-Producer {
    param(
        [string]`$Name,
        [string]`$Method,
        [bool]`$VirtualMic,
        [int]`$PollMs = 10
    )

    `$before = @(
        Get-ChildItem `$results -Filter "*_metrics.json" -ErrorAction SilentlyContinue |
            ForEach-Object { `$_.FullName }
    )
    `$arguments = @(
        "-m", "realtime_audio.windows_realtime",
        "--duration", "12",
        "--method", `$Method,
        "--noise-mode", "adaptive",
        "--block-ms", "20",
        "--input-device", `$inputDevice,
        "--output-dir", `$results
    )
    if (`$VirtualMic) {
        `$arguments += @(
            "--virtual-mic",
            "--bridge-target-depth", "2",
            "--bridge-user-queue", "4",
            "--bridge-poll-interval-ms", "2",
            "--diagnostic-trace"
        )
        `$captureWav = Join-Path `$results ("{0}_endpoint.wav" -f `$Name)
        `$captureTrace = Join-Path `$results ("{0}_capture_trace.csv" -f `$Name)
        `$captureOut = Join-Path `$results ("{0}_capture.stdout.txt" -f `$Name)
        `$captureErr = Join-Path `$results ("{0}_capture.stderr.txt" -f `$Name)
        `$captureProcess = Start-Process -FilePath `$capture -ArgumentList @(
            "--duration", "16",
            "--output", `$captureWav,
            "--poll-ms", `$PollMs.ToString(),
            "--trace", `$captureTrace
        ) -RedirectStandardOutput `$captureOut `
          -RedirectStandardError `$captureErr -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds 2
    } else {
        `$arguments += "--input-only"
        `$captureProcess = `$null
    }

    `$producerOut = Join-Path `$results ("{0}_producer.stdout.txt" -f `$Name)
    `$producerErr = Join-Path `$results ("{0}_producer.stderr.txt" -f `$Name)
    Push-Location `$app
    try {
        `$producer = Start-Process -FilePath `$python -ArgumentList `$arguments `
            -RedirectStandardOutput `$producerOut `
            -RedirectStandardError `$producerErr -WindowStyle Hidden -PassThru
        if (-not `$producer.WaitForExit(60000)) {
            Stop-Process -Id `$producer.Id -Force -ErrorAction SilentlyContinue
            throw "Timeout no produtor `$Name."
        }
        `$producer.Refresh()
        if (`$producer.ExitCode -ne 0) {
            throw "Produtor `$Name falhou com codigo `$(`$producer.ExitCode)."
        }
    } finally {
        Pop-Location
    }
    if (`$captureProcess) {
        if (-not `$captureProcess.WaitForExit(40000)) {
            Stop-Process -Id `$captureProcess.Id -Force -ErrorAction SilentlyContinue
            throw "Timeout no capturador `$Name."
        }
        `$captureProcess.Refresh()
        if (`$captureProcess.ExitCode -ne 0) {
            throw "Capturador `$Name falhou com codigo `$(`$captureProcess.ExitCode)."
        }
    }

    `$newMetric = @(
        Get-ChildItem `$results -Filter "*_metrics.json" |
            Where-Object { `$_.FullName -notin `$before }
    )
    if (`$newMetric.Count -ne 1) {
        throw "Metrica unica nao encontrada para `$Name."
    }
    Rename-Item -LiteralPath `$newMetric[0].FullName `
        -NewName ("{0}_internal_metrics.json" -f `$Name)
    foreach (`$suffix in @("_blocks.csv", "_input.wav", "_output.wav")) {
        `$source = Get-ChildItem `$results -Filter ("*{0}" -f `$suffix) |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if (`$source) {
            Rename-Item -LiteralPath `$source.FullName `
                -NewName ("{0}{1}" -f `$Name, `$suffix)
        }
    }
}

Invoke-Producer -Name "raw_capture" -Method "bypass" -VirtualMic `$false
Invoke-Producer -Name "bypass_prebridge" -Method "bypass" -VirtualMic `$false
Invoke-Producer -Name "stft_prebridge" -Method "stft_subtraction" -VirtualMic `$false
Invoke-Producer -Name "bypass_endpoint_poll10" -Method "bypass" -VirtualMic `$true -PollMs 10
Invoke-Producer -Name "stft_endpoint_poll10" -Method "stft_subtraction" -VirtualMic `$true -PollMs 10
Invoke-Producer -Name "stft_endpoint_poll2" -Method "stft_subtraction" -VirtualMic `$true -PollMs 2

`$archive = Join-Path `$root "checkpoint37_vm_results.zip"
if (Test-Path -LiteralPath `$archive) {
    Remove-Item -LiteralPath `$archive -Force
}
Compress-Archive -Path (Join-Path `$results "*") -DestinationPath `$archive
"@ -TimeoutMilliseconds 420000 | Out-Null
    }

    if (-not (Test-Path -LiteralPath (
        Join-Path $resultDir "checkpoint37_vm_results.zip"
    ))) {
        throw "Arquivo final da matriz nao apareceu na pasta compartilhada."
    }
    $matrixCompleted = $true

    $shutdownArguments = @(
        "guestcontrol", $VmName, "start",
        "--exe", "C:\Windows\System32\cmd.exe",
        "--username", $Username,
        "--passwordfile=$passwordFile",
        "--timeout=30000", "--",
        "/c", "shutdown.exe", "/s", "/f", "/t", "0"
    )
    Invoke-VBox @shutdownArguments | Out-Null
    Wait-VmState -Expected "poweroff" -TimeoutSeconds 180

    [ordered]@{
        timestamp = (Get-Date).ToString("o")
        bundle_sha256 = $bundleHash
        capture_sha256 = $captureHash
        pre_snapshot = $expectedSnapshot
        original_capture_endpoint_id = $originalEndpointId
        final_capture_endpoint_id = $finalEndpointId
        final_capture_name = $FinalCaptureName
        controlled_capture_name = $ControlledCaptureName
        controlled_playback_name = $ControlledPlaybackName
        signal_mode = "continuous"
        signal_peak = 0.10
        matrix_completed = $matrixCompleted
    } | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath (
            Join-Path $resultDir "host_run_metadata.json"
        ) -Encoding UTF8
}
finally {
    if ($signalProcess -and -not $signalProcess.HasExited) {
        Stop-Process -Id $signalProcess.Id -Force -ErrorAction SilentlyContinue
    }
    & $endpointTool --set-id $finalEndpointId | Out-Null
    if (-not $matrixCompleted -and (Get-VmProperty -Name "VMState") -eq "running") {
        Invoke-VBox controlvm $VmName acpipowerbutton | Out-Null
        try {
            Wait-VmState -Expected "poweroff" -TimeoutSeconds 45
        } catch {
            Invoke-VBox controlvm $VmName poweroff | Out-Null
            Wait-VmState -Expected "poweroff" -TimeoutSeconds 30
        }
    }
    if (-not $matrixCompleted -and (Get-VmProperty -Name "VMState") -eq "poweroff") {
        Invoke-VBox snapshot $VmName restore $expectedSnapshot | Out-Null
    }
    if ((Get-VmProperty -Name "VMState") -eq "poweroff") {
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $vbox sharedfolder remove $VmName `
            --name $sharedFolderName 2>$null | Out-Null
        $ErrorActionPreference = $oldPreference
    }
    if (Test-Path -LiteralPath $passwordFile) {
        Remove-Item -LiteralPath $passwordFile -Force
    }
}

Write-Host "Matriz concluida: $resultDir"
