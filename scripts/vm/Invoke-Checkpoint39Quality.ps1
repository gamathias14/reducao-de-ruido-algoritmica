[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB-FAST",
    [string]$OriginalVmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527",
    [string]$ControlledCaptureName = "CABLE Output (VB-Audio Virtual Cable)",
    [string]$ControlledPlaybackName = "CABLE In 16ch (VB-Audio Virtual Cable), Windows WASAPI",
    [string]$FinalCaptureName = "Microfone (USB Audio Device)",
    [string]$PrivateRoot = (
        Join-Path $env:LOCALAPPDATA (
            "PTC3527-Private\checkpoint39_deterministic"
        )
    ),
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
$resultDir = Join-Path $root "resultados\sysvad_checkpoint39"
$privateRoot = $PrivateRoot
$rawRoot = Join-Path $privateRoot "matrix_raw"
$bundle = Join-Path $privateRoot "checkpoint39_python_bundle.zip"
$captureExe = $CaptureExe
$endpointTool = Join-Path $root (
    "resultados\sysvad_checkpoint33\SetDefaultCaptureEndpoint.exe"
)
$signalScript = Join-Path $root "scripts\audio\play_controlled_signal.py"
$analysisScript = Join-Path $root "scripts\audio\analyze_checkpoint39_quality.py"
$guestScript = Join-Path $root (
    "scripts\vm\guest\Invoke-Checkpoint39QualityMatrix.ps1"
)
$hostPython = Join-Path $root ".venv-checkpoint34\Scripts\python.exe"
$unattendPath = $UnattendPath
$guestRoot = "C:\PTC3527\checkpoint39"
$guestBundle = "$guestRoot\checkpoint39_python_bundle.zip"
$guestCapture = "$guestRoot\PtcPcmCapture.exe"
$guestScriptPath = "$guestRoot\Invoke-Checkpoint39QualityMatrix.ps1"
$guestHashes = "$guestRoot\checkpoint39_expected_hashes.json"
$guestArchive = "$guestRoot\checkpoint39_vm_results.zip"
$expectedSnapshot = "checkpoint38-poll2-hyperx-validated"
$finalSnapshot = "checkpoint39-quality-boundary-validated"

function Invoke-VBox {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = @(& $vbox @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    if ($exitCode -ne 0) {
        throw (
            "VBoxManage falhou (exit=$exitCode; args=" +
            ($Arguments -join " ") + "): " +
            ($output -join [Environment]::NewLine)
        )
    }
    return $output
}

function Get-VmProperty {
    param([string]$TargetVm, [string]$Name)

    $line = @(& $vbox showvminfo $TargetVm --machinereadable 2>$null) |
        Where-Object { $_ -like "$Name=*" } |
        Select-Object -First 1
    if ($line -match '^[^=]+="([^"]*)"$') {
        return $Matches[1]
    }
    throw "Propriedade indisponivel em $TargetVm`: $Name"
}

function Wait-VmState {
    param([string]$Expected, [int]$TimeoutSeconds = 240)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq $Expected) {
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Timeout aguardando VM em estado $Expected."
}

function Stop-VmGracefully {
    param(
        [string]$PasswordFile,
        [int]$AcpiTimeoutSeconds = 180,
        [int]$GuestTimeoutSeconds = 180
    )

    if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
        return $true
    }

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $vbox controlvm $VmName acpipowerbutton 2>&1 | Out-Null
    $ErrorActionPreference = $oldPreference
    try {
        Wait-VmState -Expected "poweroff" -TimeoutSeconds $AcpiTimeoutSeconds
        return $true
    } catch {
    }

    if (Test-Path -LiteralPath $PasswordFile) {
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $vbox guestcontrol $VmName start `
            --exe "C:\Windows\System32\shutdown.exe" `
            --username $Username `
            "--passwordfile=$PasswordFile" `
            --ignore-orphaned-processes -- `
            /s /t 5 /d p:0:0 2>&1 | Out-Null
        $ErrorActionPreference = $oldPreference
        try {
            Wait-VmState -Expected "poweroff" `
                -TimeoutSeconds $GuestTimeoutSeconds
            return $true
        } catch {
        }
    }

    return $false
}

function Wait-GuestAdditions {
    $deadline = (Get-Date).AddMinutes(6)
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
    throw "Guest Additions ou logon nao ficaram prontos."
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
        [int]$TimeoutMilliseconds = 120000
    )

    $encoded = [Convert]::ToBase64String(
        [Text.Encoding]::Unicode.GetBytes($Command)
    )
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
    param([string]$PasswordFile, [string]$Source)

    Invoke-VBox guestcontrol $VmName copyto `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$guestRoot\" `
        $Source | Out-Null
}

function Copy-FromGuest {
    param([string]$PasswordFile, [string]$Source, [string]$Destination)

    Invoke-VBox guestcontrol $VmName copyfrom `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$($Destination.Replace('\', '/'))/" `
        $Source | Out-Null
}

function Test-GuestControlWithRecovery {
    param([string]$PasswordFile)

    try {
        Invoke-Guest -PasswordFile $PasswordFile `
            -Command "'GUEST_CONTROL=OK'; hostname" `
            -TimeoutMilliseconds 90000 | Out-Null
        return
    } catch {
        $diagnostic = @(
            & $vbox guestcontrol $VmName list sessions 2>&1
            & $vbox guestproperty get $VmName "/VirtualBox/GuestAdd/Version" 2>&1
            & $vbox guestproperty get $VmName "/VirtualBox/GuestInfo/OS/LoggedInUsers" 2>&1
        )
        $diagnostic | Set-Content -LiteralPath (
            Join-Path $resultDir "guest_control_first_failure.txt"
        ) -Encoding UTF8
        Start-Sleep -Seconds 15
        Wait-GuestAdditions
        Invoke-Guest -PasswordFile $PasswordFile `
            -Command "'GUEST_CONTROL=RECOVERED'; hostname" `
            -TimeoutMilliseconds 120000 | Out-Null
    }
}

function New-PythonBundle {
    $stage = Join-Path $privateRoot (
        "bundle_stage_" + [Guid]::NewGuid().ToString("N")
    )
    New-Item -ItemType Directory -Force -Path `
        (Join-Path $stage "benchmark_audio"), `
        (Join-Path $stage "realtime_audio") | Out-Null
    try {
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
        if (Test-Path -LiteralPath $bundle) {
            Remove-Item -LiteralPath $bundle -Force
        }
        Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $bundle
    } finally {
        $resolvedStage = [IO.Path]::GetFullPath($stage)
        $resolvedPrivate = [IO.Path]::GetFullPath($privateRoot).TrimEnd("\") + "\"
        if (
            (Test-Path -LiteralPath $stage) -and
            $resolvedStage.StartsWith(
                $resolvedPrivate,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            Remove-Item -LiteralPath $stage -Recurse -Force
        }
    }
}

foreach ($path in @(
    $vbox,
    $captureExe,
    $endpointTool,
    $signalScript,
    $analysisScript,
    $guestScript,
    $hostPython,
    $unattendPath
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Artefato obrigatorio ausente: $path"
    }
}

if (Test-Path -LiteralPath $resultDir) {
    $resolvedResult = [IO.Path]::GetFullPath($resultDir)
    $resolvedExpected = [IO.Path]::GetFullPath(
        (Join-Path $root "resultados\sysvad_checkpoint39")
    )
    if (-not $resolvedResult.Equals(
        $resolvedExpected,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Diretorio de resultado inesperado."
    }
    Remove-Item -LiteralPath $resultDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $resultDir, $privateRoot | Out-Null
$volumeBefore = Get-Volume -DriveLetter E -ErrorAction Stop
if (
    $volumeBefore.HealthStatus -ne "Healthy" -or
    $volumeBefore.OperationalStatus -notcontains "OK"
) {
    throw "Volume E: nao esta saudavel."
}
if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -ne "poweroff") {
    throw "O clone rapido deve estar desligado."
}
if (
    (Get-VmProperty -TargetVm $VmName -Name "CurrentSnapshotName") -ne
    $expectedSnapshot
) {
    throw "Snapshot inicial inesperado no clone rapido."
}
if ((Get-VmProperty -TargetVm $VmName -Name "audio_in") -ne "on") {
    throw "Entrada de audio do clone deve estar habilitada."
}
if ((Get-VmProperty -TargetVm $OriginalVmName -Name "VMState") -ne "poweroff") {
    throw "A VM original deve permanecer desligada."
}
$originalCfg = Get-VmProperty -TargetVm $OriginalVmName -Name "CfgFile"
$originalHashBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $originalCfg).Hash
$originalSnapshotBefore = Get-VmProperty `
    -TargetVm $OriginalVmName -Name "CurrentSnapshotUUID"

$endpointLines = @(& $endpointTool --list)
$controlledLine = $endpointLines | Where-Object {
    $_ -match ("`tname=" + [Regex]::Escape($ControlledCaptureName) + "`t")
} | Select-Object -First 1
$finalLine = $endpointLines | Where-Object {
    $_ -match ("`tname=" + [Regex]::Escape($FinalCaptureName) + "`t")
} | Select-Object -First 1
if ($controlledLine -notmatch 'id=([^\s]+)$') {
    throw "Entrada controlada nao encontrada."
}
$controlledEndpointId = $Matches[1]
if ($finalLine -notmatch 'id=([^\s]+)$') {
    throw "HyperX final nao encontrado."
}
$finalEndpointId = $Matches[1]

New-PythonBundle
$bundleHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $bundle).Hash
$captureHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $captureExe).Hash
$hashManifest = Join-Path $privateRoot "checkpoint39_expected_hashes.json"
[ordered]@{
    bundle_sha256 = $bundleHash
    capture_sha256 = $captureHash
} | ConvertTo-Json |
    Set-Content -LiteralPath $hashManifest -Encoding UTF8

$passwordFile = Join-Path ([IO.Path]::GetTempPath()) (
    "ptc3527-checkpoint39-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
$signalProcess = $null
$vmStarted = $false
$snapshotCreated = $false
$matrixSucceeded = $false

try {
    [IO.File]::WriteAllText(
        $passwordFile,
        (Get-LabPassword),
        [Text.UTF8Encoding]::new($false)
    )
    & $endpointTool --set-id $controlledEndpointId | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao selecionar a entrada controlada."
    }

    Invoke-VBox modifyvm $VmName --clipboard-mode disabled | Out-Null
    Invoke-VBox startvm $VmName --type gui | Out-Null
    $vmStarted = $true
    Wait-VmState -Expected "running"
    Wait-GuestAdditions
    Test-GuestControlWithRecovery -PasswordFile $passwordFile
    Invoke-Guest -PasswordFile $passwordFile -Command @"
if (Test-Path -LiteralPath '$guestRoot') {
    Remove-Item -LiteralPath '$guestRoot' -Recurse -Force
}
New-Item -ItemType Directory -Force -Path '$guestRoot' | Out-Null
"@ | Out-Null
    foreach ($source in @($bundle, $captureExe, $guestScript, $hashManifest)) {
        Copy-ToGuest -PasswordFile $passwordFile -Source $source
    }

    $signalProcess = Start-Process -FilePath $hostPython -ArgumentList @(
        "`"$signalScript`"",
        "--output-device", "`"$ControlledPlaybackName`"",
        "--duration", "300",
        "--peak", "0.10",
        "--mode", "quality-matrix",
        "--seed", "3527"
    ) -RedirectStandardOutput (
        Join-Path $resultDir "controlled_signal.stdout.txt"
    ) -RedirectStandardError (
        Join-Path $resultDir "controlled_signal.stderr.txt"
    ) -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 5
    if ($signalProcess.HasExited) {
        throw "Gerador deterministico encerrou antes da matriz."
    }

    Invoke-Guest -PasswordFile $passwordFile -Command (
        "& '$guestScriptPath' -Root '$guestRoot'"
    ) -TimeoutMilliseconds 900000 | Set-Content -LiteralPath (
        Join-Path $resultDir "guest_matrix.stdout.txt"
    ) -Encoding UTF8

    if (Test-Path -LiteralPath $rawRoot) {
        $resolvedRaw = [IO.Path]::GetFullPath($rawRoot)
        $resolvedPrivate = [IO.Path]::GetFullPath($privateRoot).TrimEnd("\") + "\"
        if (-not $resolvedRaw.StartsWith(
            $resolvedPrivate,
            [StringComparison]::OrdinalIgnoreCase
        )) {
            throw "Caminho privado de extracao invalido."
        }
        Remove-Item -LiteralPath $rawRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $rawRoot | Out-Null
    Copy-FromGuest -PasswordFile $passwordFile -Source $guestArchive `
        -Destination $privateRoot
    $hostArchive = Join-Path $privateRoot "checkpoint39_vm_results.zip"
    Expand-Archive -LiteralPath $hostArchive -DestinationPath $rawRoot
    & $hostPython $analysisScript $rawRoot --output-dir $resultDir
    if ($LASTEXITCODE -ne 0) {
        throw "Analise da matriz falhou."
    }
    $matrixSucceeded = $true

    $archiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $hostArchive).Hash
    [ordered]@{
        timestamp = (Get-Date).ToString("o")
        vm = $VmName
        initial_snapshot = $expectedSnapshot
        bundle_sha256 = $bundleHash
        capture_sha256 = $captureHash
        raw_archive_sha256 = $archiveHash
        audio_versioned = $false
        source = "deterministic_quality_matrix_seed_3527"
    } | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath (
            Join-Path $resultDir "evidence_manifest.json"
        ) -Encoding UTF8

    Invoke-Guest -PasswordFile $passwordFile -Command @"
Get-Process python*, PtcPcmCapture -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath '$guestRoot') {
    Remove-Item -LiteralPath '$guestRoot' -Recurse -Force
}
"@ | Out-Null
    if (-not (Stop-VmGracefully -PasswordFile $passwordFile)) {
        throw "O convidado nao desligou por ACPI nem Guest Control."
    }
    Invoke-VBox snapshot $VmName take $finalSnapshot `
        --description (
            "Checkpoint 39: matriz deterministica localizou fronteiras de " +
            "chiado, piso e bordas; polling 2 ms; audio temporario removido; " +
            "DSP, driver e protocolo PCM v1 preservados."
        ) | Out-Null
    $snapshotCreated = $true
} finally {
    if ($signalProcess -and -not $signalProcess.HasExited) {
        Stop-Process -Id $signalProcess.Id -Force -ErrorAction SilentlyContinue
    }
    & $endpointTool --set-id $finalEndpointId | Out-Null
    if ($LASTEXITCODE -ne 0) {
        [IO.File]::WriteAllText(
            (Join-Path $resultDir "endpoint_restore_error.txt"),
            "Falha ao restaurar o HyperX como captura padrao.",
            [Text.UTF8Encoding]::new($false)
        )
    }
    try {
        if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
            & $vbox modifyvm $VmName --clipboard-mode disabled 2>$null | Out-Null
        }
    } catch {
    }
    $sharedFolders = @(
        & $vbox showvminfo $VmName --machinereadable 2>$null |
            Where-Object { $_ -match '^SharedFolderNameMachineMapping' }
    )
    if ($sharedFolders.Count -gt 0) {
        $sharedFolders | Set-Content -LiteralPath (
            Join-Path $resultDir "unexpected_shared_folders.txt"
        ) -Encoding UTF8
    }
    if (
        $vmStarted -and
        (Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "running"
    ) {
        try {
            Stop-VmGracefully -PasswordFile $passwordFile | Out-Null
        } catch {
        }
    }
    try {
        if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
            & $vbox modifyvm $VmName --clipboard-mode disabled 2>$null | Out-Null
        }
    } catch {
    }
    if ($matrixSucceeded -and -not $snapshotCreated) {
        try {
            if (
                (Get-VmProperty -TargetVm $VmName -Name "VMState") -eq
                "poweroff"
            ) {
                $existingSnapshot = @(
                    & $vbox snapshot $VmName list --machinereadable 2>$null |
                        Where-Object {
                            $_ -eq "SnapshotName=`"$finalSnapshot`""
                        }
                )
                if ($existingSnapshot.Count -eq 0) {
                    Invoke-VBox snapshot $VmName take $finalSnapshot `
                        --description (
                            "Checkpoint 39: recovery de fechamento; matriz " +
                            "deterministica concluida e audio temporario removido."
                        ) | Out-Null
                }
                $snapshotCreated = $true
            }
        } catch {
            $_ | Out-String | Set-Content -LiteralPath (
                Join-Path $resultDir "snapshot_recovery_error.txt"
            ) -Encoding UTF8
        }
    }
    if (Test-Path -LiteralPath $passwordFile) {
        Remove-Item -LiteralPath $passwordFile -Force
    }
    foreach ($path in @($rawRoot, $bundle, $hashManifest)) {
        if (Test-Path -LiteralPath $path) {
            $resolved = [IO.Path]::GetFullPath($path)
            $privatePrefix = [IO.Path]::GetFullPath($privateRoot).TrimEnd("\") + "\"
            if ($resolved.StartsWith(
                $privatePrefix,
                [StringComparison]::OrdinalIgnoreCase
            )) {
                Remove-Item -LiteralPath $path -Recurse -Force
            }
        }
    }
    $hostArchive = Join-Path $privateRoot "checkpoint39_vm_results.zip"
    if (Test-Path -LiteralPath $hostArchive) {
        Remove-Item -LiteralPath $hostArchive -Force
    }
}

$originalHashAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $originalCfg).Hash
$originalSnapshotAfter = Get-VmProperty `
    -TargetVm $OriginalVmName -Name "CurrentSnapshotUUID"
$volumeAfter = Get-Volume -DriveLetter E -ErrorAction Stop
$dirtyOutput = @(& fsutil dirty query E: 2>&1) -join " "
$finalEndpointLine = @(& $endpointTool --list) |
    Where-Object { $_ -match "^default=1`t" } |
    Select-Object -First 1
$finalState = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    matrix_succeeded = $matrixSucceeded
    snapshot_created = $snapshotCreated
    clone = [ordered]@{
        state = Get-VmProperty -TargetVm $VmName -Name "VMState"
        current_snapshot = Get-VmProperty `
            -TargetVm $VmName -Name "CurrentSnapshotName"
        audio_in = Get-VmProperty -TargetVm $VmName -Name "audio_in"
        clipboard = Get-VmProperty -TargetVm $VmName -Name "clipboard"
    }
    original_vm = [ordered]@{
        state = Get-VmProperty -TargetVm $OriginalVmName -Name "VMState"
        snapshot_unchanged = $originalSnapshotBefore -eq $originalSnapshotAfter
        config_hash_unchanged = $originalHashBefore -eq $originalHashAfter
        snapshot_uuid = $originalSnapshotAfter
    }
    host = [ordered]@{
        default_capture = $finalEndpointLine
        e_health = $volumeAfter.HealthStatus.ToString()
        e_operational = @($volumeAfter.OperationalStatus | ForEach-Object {
            $_.ToString()
        })
        e_dirty_query = $dirtyOutput
        deterministic_audio_preserved = false
    }
}
$finalState | ConvertTo-Json -Depth 6 |
    Set-Content -LiteralPath (Join-Path $resultDir "final_state.json") `
        -Encoding UTF8

if (-not $matrixSucceeded -or -not $snapshotCreated) {
    throw "Checkpoint 39 nao atingiu o fechamento completo."
}
if (
    $originalHashBefore -ne $originalHashAfter -or
    $originalSnapshotBefore -ne $originalSnapshotAfter
) {
    throw "A VM original sofreu alteracao inesperada."
}
Write-Host "CHECKPOINT39=OK"
