[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB-FAST",
    [string]$OriginalVmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527",
    [string]$ExpectedSnapshot = "checkpoint45-causal-wpt-validated",
    [int]$DurationSeconds = 20,
    [ValidateSet("backend", "workload")]
    [string]$Mode = "backend",
    [string]$RuntimeRoot = (
        Join-Path $env:LOCALAPPDATA "PTC3527-Private\vm_runtime"
    ),
    [string]$Dll = (
        Join-Path $env:LOCALAPPDATA "PTC3527\bin\ptc3527-rnnoise-v0.2.dll"
    )
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$VBox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $PSScriptRoot "VmSsdRuntime.ps1")
$VmRuntime = Get-VmSsdRuntime -RuntimeRoot $RuntimeRoot
$Probe = Join-Path $RepoRoot "scripts\audio\probe_input_cadence.py"
$GuestScript = Join-Path $RepoRoot (
    "scripts\vm\guest\Invoke-InputCadenceBackendAudit.ps1"
)
$UnattendPath = $VmRuntime.CredentialPath
$GuestRoot = "C:\PTC3527\input_cadence_audit"
$GuestScriptPath = "$GuestRoot\Invoke-InputCadenceBackendAudit.ps1"
$GuestArchive = "$GuestRoot\input_cadence_results.zip"
$RunId = (Get-Date).ToString("yyyyMMdd-HHmmss") + "-$Mode-cadence"
$ResultRoot = Join-Path $RepoRoot (
    "resultados\sysvad_checkpoint46_reopened\input_cadence_audit"
)
$RunResult = Join-Path $ResultRoot "runs\$RunId"
$Bundle = Join-Path $RunResult "input_cadence_app.zip"
$ManifestPath = Join-Path $RunResult "deployment_manifest.json"

function New-PythonBundle {
    $stage = Join-Path $RunResult (
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
        if (Test-Path -LiteralPath $stage) {
            $resolvedStage = [IO.Path]::GetFullPath($stage)
            $runPrefix = [IO.Path]::GetFullPath($RunResult).TrimEnd("\") + "\"
            if (
                $resolvedStage.StartsWith(
                    $runPrefix,
                    [StringComparison]::OrdinalIgnoreCase
                )
            ) {
                Remove-Item -LiteralPath $stage -Recurse -Force
            }
        }
    }
}

function Invoke-VBox {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = @(& $VBox @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    if ($exitCode -ne 0) {
        throw "VBoxManage failed: $($output -join [Environment]::NewLine)"
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
    throw "VM property unavailable: $TargetVm / $Name"
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
    throw "Timed out waiting for VM state $Expected."
}

function Wait-GuestAdditions {
    $deadline = (Get-Date).AddMinutes(7)
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
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)
    throw "Guest Additions or interactive logon did not become ready."
}

function Get-LabPassword {
    return Get-LabPasswordFromRuntime -Runtime $VmRuntime
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
        "--target-directory=$GuestRoot\" `
        $Source | Out-Null
}

function Stop-VmGracefully {
    param([string]$PasswordFile)

    if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
        return
    }
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
    & $VBox controlvm $VmName acpipowerbutton 2>$null | Out-Null
    Wait-VmState -Expected "poweroff" -TimeoutSeconds 120
}

foreach ($path in @($VBox, $Probe, $GuestScript, $UnattendPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required artifact is missing: $path"
    }
}
if ($Mode -eq "workload" -and -not (Test-Path -LiteralPath $Dll -PathType Leaf)) {
    throw "RNNoise DLL is missing: $Dll"
}
if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -ne "poweroff") {
    throw "The fast VM clone must be powered off."
}
if (
    (Get-VmProperty -TargetVm $VmName -Name "CurrentSnapshotName") -ne
    $ExpectedSnapshot
) {
    throw "The fast clone is not at the approved snapshot."
}
if ((Get-VmProperty -TargetVm $VmName -Name "audio_in") -ne "on") {
    throw "VirtualBox audio input must remain enabled."
}
if ((Get-VmProperty -TargetVm $VmName -Name "clipboard") -ne "disabled") {
    throw "Clipboard must remain disabled."
}
$originalAuditBefore = Get-OriginalVmExternalAudit `
    -Runtime $VmRuntime `
    -VBoxPath $VBox `
    -OriginalVmName $OriginalVmName

New-Item -ItemType Directory -Force -Path $RunResult | Out-Null
$deploymentFiles = @($Probe, $GuestScript)
if ($Mode -eq "workload") {
    New-PythonBundle
    $deploymentFiles += @($Bundle, $Dll)
}
[ordered]@{
    created_at = (Get-Date).ToString("o")
    mode = $Mode
    files = @(
        foreach ($path in $deploymentFiles) {
            [ordered]@{
                name = Split-Path -Leaf $path
                sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
            }
        }
    )
} | ConvertTo-Json -Depth 6 |
    Set-Content -LiteralPath $ManifestPath -Encoding UTF8

$hostDefaultTool = Join-Path $RepoRoot (
    "resultados\sysvad_checkpoint33\SetDefaultCaptureEndpoint.exe"
)
$hostDefaultBefore = @(& $hostDefaultTool --list) |
    Where-Object { $_ -match "^default=1`t" } |
    Select-Object -First 1
$passwordFile = Join-Path ([IO.Path]::GetTempPath()) (
    "ptc3527-cadence-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
$succeeded = $false
$archiveHash = $null

try {
    [IO.File]::WriteAllText(
        $passwordFile,
        (Get-LabPassword),
        [Text.UTF8Encoding]::new($false)
    )
    Invoke-VBox startvm $VmName --type gui | Out-Null
    Wait-VmState -Expected "running"
    Wait-GuestAdditions

    Invoke-Guest -PasswordFile $passwordFile -Command @"
if (Test-Path -LiteralPath '$GuestRoot') {
    Remove-Item -LiteralPath '$GuestRoot' -Recurse -Force
}
New-Item -ItemType Directory -Force -Path '$GuestRoot' | Out-Null
"@ | Out-Null
    foreach ($source in @($deploymentFiles) + @($ManifestPath)) {
        Copy-ToGuest -PasswordFile $passwordFile -Source $source
    }

    $scenarioCount = if ($Mode -eq "workload") { 8 } else { 6 }
    $timeoutMs = 180000 + $scenarioCount * ($DurationSeconds + 5) * 1000
    Invoke-Guest -PasswordFile $passwordFile -Command (
        "& '$GuestScriptPath' -Root '$GuestRoot' " +
        "-DurationSeconds $DurationSeconds -Mode '$Mode'"
    ) -TimeoutMilliseconds $timeoutMs |
        Set-Content -LiteralPath (
            Join-Path $RunResult "guest.stdout.txt"
        ) -Encoding UTF8

    Invoke-VBox guestcontrol $VmName copyfrom `
        --username $Username `
        "--passwordfile=$passwordFile" `
        "--target-directory=$($RunResult.Replace('\', '/'))/" `
        $GuestArchive | Out-Null
    $hostArchive = Join-Path $RunResult "input_cadence_results.zip"
    $archiveHash = (
        Get-FileHash -LiteralPath $hostArchive -Algorithm SHA256
    ).Hash
    Expand-Archive `
        -LiteralPath $hostArchive `
        -DestinationPath (Join-Path $RunResult "extracted")
    $succeeded = $true
} finally {
    if (
        (Get-VmProperty -TargetVm $VmName -Name "VMState") -ne "poweroff" -and
        (Test-Path -LiteralPath $passwordFile)
    ) {
        try {
            Invoke-Guest -PasswordFile $passwordFile -Command (
                "Remove-Item -LiteralPath '$GuestRoot' -Recurse -Force " +
                "-ErrorAction SilentlyContinue"
            ) | Out-Null
        } catch {
        }
        Stop-VmGracefully -PasswordFile $passwordFile
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
$hostDefaultAfter = @(& $hostDefaultTool --list) |
    Where-Object { $_ -match "^default=1`t" } |
    Select-Object -First 1
[ordered]@{
    timestamp = (Get-Date).ToString("o")
    run_id = $RunId
    mode = $Mode
    succeeded = $succeeded
    archive_sha256 = $archiveHash
    audio_saved = $false
    clone = [ordered]@{
        state = Get-VmProperty -TargetVm $VmName -Name "VMState"
        snapshot = Get-VmProperty -TargetVm $VmName -Name "CurrentSnapshotName"
        audio_in = Get-VmProperty -TargetVm $VmName -Name "audio_in"
        clipboard = Get-VmProperty -TargetVm $VmName -Name "clipboard"
    }
    original_vm = Compare-OriginalVmExternalAudit `
        -Before $originalAuditBefore `
        -After $originalAuditAfter
    host_default_capture_unchanged = $hostDefaultBefore -eq $hostDefaultAfter
} | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath (Join-Path $RunResult "host_result.json") `
        -Encoding UTF8

if (-not $succeeded) {
    throw "Input cadence backend audit did not complete."
}
if (
    (
        $originalAuditBefore.available -and
        (
            -not $originalAuditAfter.available -or
            $originalAuditBefore.config_hash -ne
                $originalAuditAfter.config_hash -or
            $originalAuditBefore.snapshot_uuid -ne
                $originalAuditAfter.snapshot_uuid
        )
    ) -or
    $hostDefaultBefore -ne $hostDefaultAfter
) {
    throw "A protected host or original-VM state changed."
}

Write-Host "INPUT_CADENCE_VM_AUDIT=OK"
Write-Host "RUN_ID=$RunId"
Write-Host "RESULT_DIR=$RunResult"
