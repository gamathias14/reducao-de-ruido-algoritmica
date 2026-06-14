[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("isolated", "transport", "acoustic")]
    [string]$Phase,

    [string]$VmName = "PTC3527-SYSVAD-LAB-FAST",
    [string]$OriginalVmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527",
    [string]$ExpectedSnapshot = "checkpoint45-causal-wpt-validated",
    [string]$RuntimeRoot = (
        Join-Path $env:LOCALAPPDATA "PTC3527-Private\vm_runtime"
    ),
    [string]$PrivateBase = (
        Join-Path $env:LOCALAPPDATA "PTC3527-Private\rnnoise_vm_integration"
    ),
    [string]$Dll = (
        Join-Path $env:LOCALAPPDATA "PTC3527\bin\ptc3527-rnnoise-v0.2.dll"
    ),
    [string]$CaptureExe = (
        Join-Path $env:USERPROFILE (
            "source\repos\Windows-driver-samples\audio\sysvad\" +
            "tools\PtcPcmCapture\x64\Release\PtcPcmCapture.exe"
        )
    )
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$VBox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $PSScriptRoot "VmSsdRuntime.ps1")
$VmRuntime = Get-VmSsdRuntime -RuntimeRoot $RuntimeRoot
$ResultRoot = Join-Path $RepoRoot (
    "resultados\sysvad_checkpoint46_reopened\rnnoise_vm_integration"
)
$RunId = (Get-Date).ToString("yyyyMMdd-HHmmss") + "-$Phase"
$RunResult = Join-Path $ResultRoot "runs\$RunId"
$PrivateRoot = Join-Path $PrivateBase $RunId
$RawRoot = Join-Path $PrivateRoot "extracted"
$Bundle = Join-Path $PrivateRoot "rnnoise_vm_bundle.zip"
$GuestScript = Join-Path $RepoRoot (
    "scripts\vm\guest\Invoke-RNNoiseIntegrationGates.ps1"
)
$UnattendPath = $VmRuntime.CredentialPath
$GuestRoot = "C:\PTC3527\rnnoise_integration"
$GuestScriptPath = "$GuestRoot\Invoke-RNNoiseIntegrationGates.ps1"
$GuestArchive = "$GuestRoot\rnnoise_${Phase}_results.zip"
$ManifestPath = Join-Path $PrivateRoot "deployment_manifest.json"

function Invoke-VBox {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = @(& $VBox @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    if ($exitCode -ne 0) {
        throw (
            "VBoxManage failed (exit=$exitCode; args=" +
            ($Arguments -join " ") + "): " +
            ($output -join [Environment]::NewLine)
        )
    }
    return $output
}

function Get-VmProperty {
    param(
        [Parameter(Mandatory = $true)][string]$TargetVm,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $line = @(& $VBox showvminfo $TargetVm --machinereadable 2>$null) |
        Where-Object { $_ -like "$Name=*" } |
        Select-Object -First 1
    if ($line -match '^[^=]+="([^"]*)"$') {
        return $Matches[1]
    }
    throw "VM property is unavailable on $TargetVm`: $Name"
}

function Wait-VmState {
    param(
        [Parameter(Mandatory = $true)][string]$Expected,
        [int]$TimeoutSeconds = 240
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (
            (Get-VmProperty -TargetVm $VmName -Name "VMState") -eq
            $Expected
        ) {
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for VM state $Expected."
}

function Wait-GuestAdditions {
    $deadline = (Get-Date).AddMinutes(7)
    $keyboardRecoverySent = $false
    do {
        $version = @(
            & $VBox guestproperty get $VmName `
                "/VirtualBox/GuestAdd/Version" 2>$null
        ) | Select-Object -First 1
        $users = @(
            & $VBox guestproperty get $VmName `
                "/VirtualBox/GuestInfo/OS/LoggedInUsers" 2>$null
        ) | Select-Object -First 1
        if (
            $version -match "^Value:\s+\S+" -and
            $users -match "^Value:\s+([1-9][0-9]*)$"
        ) {
            return
        }
        if (-not $keyboardRecoverySent -and (Get-Date) -gt $deadline.AddSeconds(-405)) {
            & $VBox controlvm $VmName keyboardputscancode 1c 9c 2>$null |
                Out-Null
            $keyboardRecoverySent = $true
        }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)
    throw "Guest Additions or the interactive logon did not become ready."
}

function Get-LabPassword {
    return Get-LabPasswordFromRuntime -Runtime $VmRuntime
}

function Invoke-Guest {
    param(
        [Parameter(Mandatory = $true)][string]$PasswordFile,
        [Parameter(Mandatory = $true)][string]$Command,
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
    param(
        [Parameter(Mandatory = $true)][string]$PasswordFile,
        [Parameter(Mandatory = $true)][string]$Source
    )

    Invoke-VBox guestcontrol $VmName copyto `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$GuestRoot\" `
        $Source | Out-Null
}

function Copy-FromGuest {
    param(
        [Parameter(Mandatory = $true)][string]$PasswordFile,
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    Invoke-VBox guestcontrol $VmName copyfrom `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$($Destination.Replace('\', '/'))/" `
        $Source | Out-Null
}

function Stop-VmGracefully {
    param([Parameter(Mandatory = $true)][string]$PasswordFile)

    if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
        return
    }
    if (Test-Path -LiteralPath $PasswordFile) {
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $VBox guestcontrol $VmName start `
            --exe "C:\Windows\System32\shutdown.exe" `
            --username $Username `
            "--passwordfile=$PasswordFile" `
            --ignore-orphaned-processes -- /s /t 5 /d p:0:0 2>&1 |
            Out-Null
        $ErrorActionPreference = $oldPreference
        try {
            Wait-VmState -Expected "poweroff" -TimeoutSeconds 120
            return
        } catch {
        }
    }

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $VBox controlvm $VmName acpipowerbutton 2>&1 | Out-Null
    $ErrorActionPreference = $oldPreference
    try {
        Wait-VmState -Expected "poweroff" -TimeoutSeconds 120
        return
    } catch {
    }

    throw "The VM did not shut down through ACPI or Guest Control."
}

function New-PythonBundle {
    $stage = Join-Path $PrivateRoot (
        "bundle_stage_" + [Guid]::NewGuid().ToString("N")
    )
    New-Item -ItemType Directory -Force -Path `
        (Join-Path $stage "benchmark_audio"), `
        (Join-Path $stage "realtime_audio") | Out-Null
    try {
        foreach ($file in @("__init__.py", "causal.py", "denoise.py")) {
            Copy-Item -LiteralPath (Join-Path $RepoRoot "benchmark_audio\$file") `
                -Destination (Join-Path $stage "benchmark_audio\$file")
        }
        foreach ($file in @(
            "__init__.py",
            "audio_continuity.py",
            "block_metrics.py",
            "ptc_pcm_bridge.py",
            "rnnoise_processor.py",
            "windows_realtime.py"
        )) {
            Copy-Item -LiteralPath (Join-Path $RepoRoot "realtime_audio\$file") `
                -Destination (Join-Path $stage "realtime_audio\$file")
        }
        Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $Bundle
    } finally {
        $resolvedStage = [IO.Path]::GetFullPath($stage)
        $privatePrefix = [IO.Path]::GetFullPath($PrivateRoot).TrimEnd("\") + "\"
        if (
            (Test-Path -LiteralPath $stage) -and
            $resolvedStage.StartsWith(
                $privatePrefix,
                [StringComparison]::OrdinalIgnoreCase
            )
        ) {
            Remove-Item -LiteralPath $stage -Recurse -Force
        }
    }
}

function Test-GuestControl {
    param([Parameter(Mandatory = $true)][string]$PasswordFile)

    try {
        Invoke-Guest -PasswordFile $PasswordFile `
            -Command "'GUEST_CONTROL=OK'; hostname" `
            -TimeoutMilliseconds 90000 | Out-Null
    } catch {
        $diagnostic = @(
            & $VBox guestcontrol $VmName list sessions 2>&1
            & $VBox guestcontrol $VmName list processes 2>&1
        )
        $diagnostic | Set-Content -LiteralPath (
            Join-Path $RunResult "guest_control_first_failure.txt"
        ) -Encoding UTF8
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $VBox guestcontrol $VmName closesession --all 2>&1 | Out-Null
        $ErrorActionPreference = $oldPreference
        Start-Sleep -Seconds 10
        Wait-GuestAdditions
        Invoke-Guest -PasswordFile $PasswordFile `
            -Command "'GUEST_CONTROL=RECOVERED'; hostname" `
            -TimeoutMilliseconds 120000 | Out-Null
    }
}

foreach ($path in @(
    $VBox,
    $Dll,
    $CaptureExe,
    $GuestScript,
    $UnattendPath
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required artifact is missing: $path"
    }
}

New-Item -ItemType Directory -Force -Path `
    $RunResult, $PrivateRoot, $RawRoot | Out-Null

if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -ne "poweroff") {
    throw "The fast VM clone must be powered off before the run."
}
if (
    (Get-VmProperty -TargetVm $VmName -Name "CurrentSnapshotName") -ne
    $ExpectedSnapshot
) {
    throw "The fast VM clone is not at the approved checkpoint 45 snapshot."
}
if ((Get-VmProperty -TargetVm $VmName -Name "audio_in") -ne "on") {
    throw "VirtualBox audio input must be enabled."
}
if ((Get-VmProperty -TargetVm $VmName -Name "clipboard") -ne "disabled") {
    throw "The VM clipboard must remain disabled."
}
$originalAuditBefore = Get-OriginalVmExternalAudit `
    -Runtime $VmRuntime `
    -VBoxPath $VBox `
    -OriginalVmName $OriginalVmName
$hostDefaultBefore = @(
    & (Join-Path $RepoRoot (
        "resultados\sysvad_checkpoint33\SetDefaultCaptureEndpoint.exe"
    )) --list
) | Where-Object { $_ -match "^default=1`t" } | Select-Object -First 1

New-PythonBundle
$deploymentFiles = @(
    @{ name = (Split-Path -Leaf $Bundle); path = $Bundle },
    @{ name = (Split-Path -Leaf $Dll); path = $Dll },
    @{ name = (Split-Path -Leaf $CaptureExe); path = $CaptureExe },
    @{ name = (Split-Path -Leaf $GuestScript); path = $GuestScript }
)
[ordered]@{
    created_at = (Get-Date).ToString("o")
    phase = $Phase
    rnnoise = [ordered]@{
        tag = "v0.2"
        commit = "904a876dce1f9ab8860c0a5000ed151f9f6eef58"
        model = "0b50c45"
    }
    files = @(
        foreach ($entry in $deploymentFiles) {
            [ordered]@{
                name = $entry.name
                sha256 = (
                    Get-FileHash -LiteralPath $entry.path -Algorithm SHA256
                ).Hash
            }
        }
    )
} | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath $ManifestPath -Encoding UTF8
Copy-Item -LiteralPath $ManifestPath -Destination (
    Join-Path $RunResult "deployment_manifest.json"
)

$passwordFile = Join-Path ([IO.Path]::GetTempPath()) (
    "ptc3527-rnnoise-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
$vmStarted = $false
$phaseSucceeded = $false
$archiveHash = $null
$runError = $null

try {
    [IO.File]::WriteAllText(
        $passwordFile,
        (Get-LabPassword),
        [Text.UTF8Encoding]::new($false)
    )
    Invoke-VBox startvm $VmName --type gui | Out-Null
    $vmStarted = $true
    Wait-VmState -Expected "running"
    Wait-GuestAdditions
    Test-GuestControl -PasswordFile $passwordFile

    Invoke-Guest -PasswordFile $passwordFile -Command @"
if (Test-Path -LiteralPath '$GuestRoot') {
    Remove-Item -LiteralPath '$GuestRoot' -Recurse -Force
}
New-Item -ItemType Directory -Force -Path '$GuestRoot' | Out-Null
"@ | Out-Null

    foreach ($source in @(
        $Bundle,
        $Dll,
        $CaptureExe,
        $GuestScript,
        $ManifestPath
    )) {
        Copy-ToGuest -PasswordFile $passwordFile -Source $source
    }

    $phaseTimeout = switch ($Phase) {
        "isolated" { 360000 }
        "transport" { 480000 }
        "acoustic" { 240000 }
    }
    Invoke-Guest -PasswordFile $passwordFile -Command (
        "& '$GuestScriptPath' -Phase '$Phase' -Root '$GuestRoot'"
    ) -TimeoutMilliseconds $phaseTimeout |
        Set-Content -LiteralPath (
            Join-Path $RunResult "guest_phase.stdout.txt"
        ) -Encoding UTF8

    Copy-FromGuest `
        -PasswordFile $passwordFile `
        -Source $GuestArchive `
        -Destination $PrivateRoot
    $hostArchive = Join-Path $PrivateRoot (
        "rnnoise_${Phase}_results.zip"
    )
    $archiveHash = (
        Get-FileHash -LiteralPath $hostArchive -Algorithm SHA256
    ).Hash
    Expand-Archive -LiteralPath $hostArchive -DestinationPath $RawRoot

    $privateLogs = Join-Path $RawRoot "logs"
    if (Test-Path -LiteralPath $privateLogs) {
        Copy-Item -LiteralPath $privateLogs -Destination $RunResult -Recurse
    }
    if ($Phase -eq "isolated") {
        $isolatedRoot = Join-Path $RawRoot "isolated"
        Copy-Item -LiteralPath $isolatedRoot -Destination $RunResult -Recurse
        $isolatedGate = Get-Content -LiteralPath (
            Join-Path $isolatedRoot "isolated_gate.json"
        ) -Raw | ConvertFrom-Json
        if (-not [bool]$isolatedGate.passed) {
            throw (
                "Isolated RNNoise gate failed: " +
                (@($isolatedGate.reasons) -join "; ")
            )
        }
    }

    Invoke-Guest -PasswordFile $passwordFile -Command @"
Get-Process python*, PtcPcmCapture -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath '$GuestRoot') {
    Remove-Item -LiteralPath '$GuestRoot' -Recurse -Force
}
"@ | Out-Null
    $phaseSucceeded = $true
} catch {
    $runError = $_ | Out-String
    $runError | Set-Content -LiteralPath (
        Join-Path $RunResult "run_error.txt"
    ) -Encoding UTF8
    throw
} finally {
    if (
        $vmStarted -and
        (Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "running"
    ) {
        try {
            Stop-VmGracefully -PasswordFile $passwordFile
        } catch {
            ($_ | Out-String) | Set-Content -LiteralPath (
                Join-Path $RunResult "shutdown_error.txt"
            ) -Encoding UTF8
            $oldPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            & $VBox controlvm $VmName poweroff 2>&1 | Out-Null
            $ErrorActionPreference = $oldPreference
            Wait-VmState -Expected "poweroff" -TimeoutSeconds 60
        }
    }
    if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
        Invoke-VBox snapshot $VmName restore $ExpectedSnapshot | Out-Null
    }
    if (Test-Path -LiteralPath $passwordFile) {
        Remove-Item -LiteralPath $passwordFile -Force
    }
}

$originalAuditAfter = Get-OriginalVmExternalAudit `
    -Runtime $VmRuntime `
    -VBoxPath $VBox `
    -OriginalVmName $OriginalVmName
$hostDefaultAfter = @(
    & (Join-Path $RepoRoot (
        "resultados\sysvad_checkpoint33\SetDefaultCaptureEndpoint.exe"
    )) --list
) | Where-Object { $_ -match "^default=1`t" } | Select-Object -First 1

[ordered]@{
    timestamp = (Get-Date).ToString("o")
    run_id = $RunId
    phase = $Phase
    succeeded = $phaseSucceeded
    raw_archive_sha256 = $archiveHash
    raw_results_private = $RawRoot
    audio_versioned = $false
    clone = [ordered]@{
        state = Get-VmProperty -TargetVm $VmName -Name "VMState"
        current_snapshot = Get-VmProperty `
            -TargetVm $VmName `
            -Name "CurrentSnapshotName"
        audio_in = Get-VmProperty -TargetVm $VmName -Name "audio_in"
        clipboard = Get-VmProperty -TargetVm $VmName -Name "clipboard"
    }
    original_vm = Compare-OriginalVmExternalAudit `
        -Before $originalAuditBefore `
        -After $originalAuditAfter
    host = [ordered]@{
        default_capture_before = $hostDefaultBefore
        default_capture_after = $hostDefaultAfter
        runtime_root = $VmRuntime.Root
        external_original_available = $originalAuditAfter.available
    }
} | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath (Join-Path $RunResult "host_result.json") `
        -Encoding UTF8

if (-not $phaseSucceeded) {
    throw "RNNoise VM phase did not complete: $Phase"
}
if (
    $originalAuditBefore.available -and
    (
        -not $originalAuditAfter.available -or
        $originalAuditBefore.config_hash -ne $originalAuditAfter.config_hash -or
        $originalAuditBefore.snapshot_uuid -ne $originalAuditAfter.snapshot_uuid
    )
) {
    throw "The original VM changed unexpectedly."
}
if ($hostDefaultBefore -ne $hostDefaultAfter) {
    throw "The host default capture endpoint changed unexpectedly."
}

Write-Host "RNNOISE_VM_PHASE=OK"
Write-Host "RUN_ID=$RunId"
Write-Host "RESULT_DIR=$RunResult"
Write-Host "PRIVATE_RAW_DIR=$RawRoot"
