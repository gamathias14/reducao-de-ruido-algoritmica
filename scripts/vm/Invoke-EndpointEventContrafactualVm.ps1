[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB-FAST",
    [string]$OriginalVmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527",
    [string]$ExpectedSnapshot = "checkpoint45-causal-wpt-validated",
    [int]$DurationSeconds = 40,
    [string]$RuntimeRoot = (
        Join-Path $env:LOCALAPPDATA "PTC3527-Private\vm_runtime"
    ),
    [string]$ProbePath = (
        Join-Path $env:USERPROFILE (
            "source\repos\Windows-driver-samples\audio\sysvad\" +
            "tools\PtcEndpointEventProbe\x64\Release\" +
            "PtcEndpointEventProbe.exe"
        )
    ),
    [string]$HostDefaultToolPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $PSScriptRoot "VmSsdRuntime.ps1")
$vmRuntime = Get-VmSsdRuntime -RuntimeRoot $RuntimeRoot
$probe = $ProbePath
$schedulerProbe = Join-Path $repoRoot "scripts\audio\guest_scheduler_probe.py"
$guestScript = Join-Path $repoRoot (
    "scripts\vm\guest\Invoke-EndpointEventContrafactual.ps1"
)
$analyzer = Join-Path $repoRoot (
    "scripts\audio\analyze_endpoint_event_contrafactual.py"
)
$preflight = Join-Path $PSScriptRoot "Test-VmAutomationPreflight.ps1"
$hostDefaultTool = if ($HostDefaultToolPath) {
    $HostDefaultToolPath
} else {
    Join-Path $repoRoot (
        "resultados\sysvad_checkpoint33\SetDefaultCaptureEndpoint.exe"
    )
}
$runId = (
    (Get-Date).ToString("yyyyMMdd-HHmmss") +
    "-endpoint-event-contrafactual"
)
$guestRoot = "C:\PTC3527\endpoint_event_contrafactual\$runId"
$guestOutput = "$guestRoot\results"
$guestArchive = "$guestRoot\results.zip"
$resultRoot = Join-Path $repoRoot (
    "resultados\sysvad_checkpoint46_reopened\" +
    "endpoint_event_contrafactual\runs"
)
$runResult = Join-Path $resultRoot $runId
$manifestPath = Join-Path $runResult "deployment_manifest.json"
$analysisPath = Join-Path $runResult "contrafactual_gate.json"
$python = (Get-Command python -ErrorAction Stop).Source

function Invoke-VBox {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = @(& $vbox @Arguments 2>&1)
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

    $deadline = (Get-Date).AddSeconds(15)
    do {
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $output = @(& $vbox showvminfo $TargetVm --machinereadable 2>&1)
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $oldPreference
        if ($exitCode -eq 0) {
            $line = $output |
                Where-Object { $_ -like "$Name=*" } |
                Select-Object -First 1
            if ($line -match '^[^=]+="([^"]*)"$') {
                return $Matches[1]
            }
            if ($line -match '^[^=]+=([^"]\S*)$') {
                return $Matches[1]
            }
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw (
        "VM property unavailable: $TargetVm / $Name; " +
        ($output -join [Environment]::NewLine)
    )
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
    throw "Guest Additions or interactive logon did not become ready."
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
    param(
        [string]$PasswordFile,
        [string]$Source,
        [string]$Destination
    )

    Invoke-VBox guestcontrol $VmName copyfrom `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$($Destination.Replace('\', '/'))/" `
        $Source | Out-Null
}

function Copy-PartialGuestResults {
    param([string]$PasswordFile)

    $partialArchive = "$guestRoot\partial-results.zip"
    $command = @"
if (Test-Path -LiteralPath '$guestOutput' -PathType Container) {
    Remove-Item -LiteralPath '$partialArchive' -Force -ErrorAction SilentlyContinue
    Compress-Archive -Path '$guestOutput\*' -DestinationPath '$partialArchive' -CompressionLevel Optimal
}
"@
    Invoke-Guest `
        -PasswordFile $PasswordFile `
        -Command $command `
        -TimeoutMilliseconds 120000 | Out-Null
    $partialHostRoot = Join-Path $runResult "partial"
    New-Item -ItemType Directory -Force -Path $partialHostRoot | Out-Null
    Copy-FromGuest `
        -PasswordFile $PasswordFile `
        -Source $partialArchive `
        -Destination $partialHostRoot
    Expand-Archive `
        -LiteralPath (Join-Path $partialHostRoot "partial-results.zip") `
        -DestinationPath $partialHostRoot `
        -Force
}

function Stop-VmGracefully {
    param([string]$PasswordFile)

    if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
        return "already_poweroff"
    }
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $vbox guestcontrol $VmName start `
        --exe "C:\Windows\System32\shutdown.exe" `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        --ignore-orphaned-processes -- /s /t 0 /d p:0:0 2>&1 |
        Out-Null
    $ErrorActionPreference = $oldPreference
    try {
        Wait-VmState -Expected "poweroff" -TimeoutSeconds 180
        return "guest_shutdown"
    } catch {
    }
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $vbox guestcontrol $VmName closesession --all 2>&1 | Out-Null
    & $vbox controlvm $VmName acpipowerbutton 2>$null | Out-Null
    $ErrorActionPreference = $oldPreference
    try {
        Wait-VmState -Expected "poweroff" -TimeoutSeconds 180
        return "acpi_power_button"
    } catch {
    }
    Invoke-VBox controlvm $VmName poweroff | Out-Null
    Wait-VmState -Expected "poweroff" -TimeoutSeconds 60
    return "forced_poweroff_after_clean_shutdown_timeout"
}

function Invoke-ReadOnlyPreflight {
    param([string]$OutputPath)

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = @(
        & powershell.exe `
            -NoProfile `
            -ExecutionPolicy Bypass `
            -File $preflight `
            -VmName $VmName `
            -OriginalVmName $OriginalVmName `
            -ExpectedSnapshot $ExpectedSnapshot `
            -OrchestratorPath $PSCommandPath `
            -RuntimeRoot $RuntimeRoot `
            -AudioRun 2>&1
    )
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    $output | Set-Content -LiteralPath $OutputPath -Encoding UTF8
    if ($exitCode -ne 0) {
        throw (
            "Read-only VM preflight failed; see $OutputPath. " +
            ($output -join [Environment]::NewLine)
        )
    }
}

foreach ($path in @(
    $vbox,
    $probe,
    $schedulerProbe,
    $guestScript,
    $analyzer,
    $preflight,
    $hostDefaultTool
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required contrafactual artifact is missing: $path"
    }
}
if ($DurationSeconds -lt 1 -or $DurationSeconds -gt 3600) {
    throw "DurationSeconds must be between 1 and 3600."
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
if ([int](Get-VmProperty -TargetVm $VmName -Name "cpus") -ne 4) {
    throw "The contrafactual requires exactly four vCPUs."
}
if ((Get-VmProperty -TargetVm $VmName -Name "audio_in") -ne "on") {
    throw "VirtualBox audio input must remain enabled."
}
if ((Get-VmProperty -TargetVm $VmName -Name "clipboard") -ne "disabled") {
    throw "Clipboard must remain disabled."
}
if ((Get-VmProperty -TargetVm $VmName -Name "draganddrop") -ne "disabled") {
    throw "Drag-and-drop must remain disabled."
}
if ((Get-VmProperty -TargetVm $VmName -Name "nic1") -ne "nat") {
    throw "NIC 1 must remain on NAT."
}

$originalAuditBefore = Get-OriginalVmExternalAudit `
    -Runtime $vmRuntime `
    -VBoxPath $vbox `
    -OriginalVmName $OriginalVmName
$hostDefaultBefore = @(& $hostDefaultTool --list) |
    Where-Object { $_ -match "^default=1`t" } |
    Select-Object -First 1
if ($null -eq $hostDefaultBefore) {
    throw "The host default capture endpoint could not be read before the run."
}

New-Item -ItemType Directory -Force -Path $runResult | Out-Null
Invoke-ReadOnlyPreflight -OutputPath (
    Join-Path $runResult "preflight_before.json"
)
$deploymentFiles = @($probe, $schedulerProbe, $guestScript)
$manifestFiles = $deploymentFiles + @($analyzer)
[ordered]@{
    created_at = (Get-Date).ToString("o")
    checkpoint = "46-R/ENDPOINT-EVENT-CONTRAFACTUAL"
    duration_seconds_per_leg = $DurationSeconds
    matrix = @(
        "01-sysvad-shared-event-a",
        "02-hda-shared-event-a",
        "03-hda-shared-event-b",
        "04-sysvad-shared-event-b"
    )
    fixed_configuration = [ordered]@{
        share_mode = "AUDCLNT_SHAREMODE_SHARED"
        stream_flags = "AUDCLNT_STREAMFLAGS_EVENTCALLBACK"
        buffer_duration = 0
        periodicity = 0
        format = "GetMixFormat"
        vm_cpu_count = 4
        priority = "Normal"
        affinity = "unchanged"
        producer = "none"
        dsp = "none"
        audio_persisted = $false
    }
    files = @(
        foreach ($path in $manifestFiles) {
            [ordered]@{
                name = Split-Path -Leaf $path
                path = $path
                sha256 = (
                    Get-FileHash -LiteralPath $path -Algorithm SHA256
                ).Hash
            }
        }
    )
} | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath $manifestPath -Encoding UTF8

$passwordFile = Join-Path ([IO.Path]::GetTempPath()) (
    "ptc3527-host-paced-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
$succeeded = $false
$failureMessage = $null
$teardownMethod = $null
$teardownFailure = $null
try {
    [IO.File]::WriteAllText(
        $passwordFile,
        (Get-LabPasswordFromRuntime -Runtime $vmRuntime),
        [Text.UTF8Encoding]::new($false)
    )
    Invoke-VBox startvm $VmName --type gui | Out-Null
    Wait-VmState -Expected "running"
    Wait-GuestAdditions

    Invoke-VBox guestcontrol $VmName mkdir `
        --username $Username `
        "--passwordfile=$passwordFile" `
        --parents `
        $guestRoot | Out-Null
    foreach ($source in $deploymentFiles + @($manifestPath)) {
        Copy-ToGuest -PasswordFile $passwordFile -Source $source
    }
    $guestCommand = (
        "& '$guestRoot\$(Split-Path -Leaf $guestScript)' " +
        "-Root '$guestRoot' -OutputRoot '$guestOutput' " +
        "-DurationSeconds $DurationSeconds; " +
        "Compress-Archive -Path '$guestOutput\*' " +
        "-DestinationPath '$guestArchive' -CompressionLevel Optimal"
    )
    Invoke-Guest `
        -PasswordFile $passwordFile `
        -Command $guestCommand `
        -TimeoutMilliseconds (($DurationSeconds * 4 + 180) * 1000) |
        Set-Content -LiteralPath (Join-Path $runResult "guest.stdout.txt") `
            -Encoding UTF8
    Copy-FromGuest `
        -PasswordFile $passwordFile `
        -Source $guestArchive `
        -Destination $runResult
    Expand-Archive `
        -LiteralPath (Join-Path $runResult "results.zip") `
        -DestinationPath $runResult `
        -Force
    & $python $analyzer --root $runResult --output $analysisPath
    if ($LASTEXITCODE -ne 0) {
        throw "Contrafactual analyzer reported incomplete evidence."
    }
    $succeeded = $true
} catch {
    $failureMessage = $_.Exception.Message
    if (
        (Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "running" -and
        (Test-Path -LiteralPath $passwordFile)
    ) {
        try {
            Copy-PartialGuestResults -PasswordFile $passwordFile
        } catch {
            $failureMessage += (
                " Partial artifact recovery also failed: " +
                $_.Exception.Message
            )
        }
    }
} finally {
    try {
        if (
            (Get-VmProperty -TargetVm $VmName -Name "VMState") -ne
            "poweroff" -and
            (Test-Path -LiteralPath $passwordFile)
        ) {
            try {
                Invoke-VBox guestcontrol $VmName rmdir `
                    --username $Username `
                    "--passwordfile=$passwordFile" `
                    --recursive `
                    $guestRoot | Out-Null
            } catch {
            }
            $teardownMethod = Stop-VmGracefully -PasswordFile $passwordFile
        }
        if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
            Invoke-VBox snapshot $VmName restore $ExpectedSnapshot | Out-Null
        }
    } catch {
        $teardownFailure = $_.Exception.Message
        $succeeded = $false
        if ($null -eq $failureMessage) {
            $failureMessage = "Teardown failed: $teardownFailure"
        }
    } finally {
        if (Test-Path -LiteralPath $passwordFile) {
            Remove-Item -LiteralPath $passwordFile -Force
        }
    }
}

$originalAuditAfter = Get-OriginalVmExternalAudit `
    -Runtime $vmRuntime `
    -VBoxPath $vbox `
    -OriginalVmName $OriginalVmName
$hostDefaultAfter = @(& $hostDefaultTool --list) |
    Where-Object { $_ -match "^default=1`t" } |
    Select-Object -First 1
$hostDefaultReadableAfter = $null -ne $hostDefaultAfter
[ordered]@{
    timestamp = (Get-Date).ToString("o")
    run_id = $runId
    succeeded = $succeeded
    failure = $failureMessage
    teardown_method = $teardownMethod
    teardown_failure = $teardownFailure
    audio_saved = $false
    clone = [ordered]@{
        state = Get-VmProperty -TargetVm $VmName -Name "VMState"
        snapshot = Get-VmProperty `
            -TargetVm $VmName `
            -Name "CurrentSnapshotName"
        cpus = [int](Get-VmProperty -TargetVm $VmName -Name "cpus")
        audio_in = Get-VmProperty -TargetVm $VmName -Name "audio_in"
        clipboard = Get-VmProperty -TargetVm $VmName -Name "clipboard"
        draganddrop = Get-VmProperty -TargetVm $VmName -Name "draganddrop"
        nic1 = Get-VmProperty -TargetVm $VmName -Name "nic1"
    }
    original_vm = Compare-OriginalVmExternalAudit `
        -Before $originalAuditBefore `
        -After $originalAuditAfter
    host_default_capture_readable_after = $hostDefaultReadableAfter
    host_default_capture_unchanged = (
        $hostDefaultReadableAfter -and
        $hostDefaultBefore -eq $hostDefaultAfter
    )
} | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath (Join-Path $runResult "host_result.json") `
        -Encoding UTF8

try {
    Invoke-ReadOnlyPreflight -OutputPath (
        Join-Path $runResult "preflight_after.json"
    )
} catch {
    if ($null -eq $failureMessage) {
        $failureMessage = $_.Exception.Message
    }
    $succeeded = $false
}
if (-not $succeeded) {
    throw "Endpoint event contrafactual failed: $failureMessage"
}
