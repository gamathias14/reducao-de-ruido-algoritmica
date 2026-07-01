[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB-FAST",
    [string]$OriginalVmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527",
    [string]$ExpectedSnapshot = "checkpoint45-causal-wpt-validated",
    [int]$Port = 35280,
    [string]$SourceWav = "tmp\dfn_native\wasapi_worker_bench\b3_inputs\mixed_60s_capi_input48.wav",
    [string]$RuntimeRoot = "C:\PTC3527-Private\vm_runtime",
    [string]$ResultRoot = "resultados\dfn3_vm_transport_48k",
    [string]$GuestConnectHost = "10.0.2.2",
    [string]$TemporaryHostOnlyAdapterName = "",
    [ValidateSet("Normal", "AboveNormal", "High")]
    [string]$ServerPriority = "High",
    [ValidateSet("Python", "Native")]
    [string]$ClientImplementation = "Native",
    [ValidateSet("tcp", "udp")]
    [string]$Transport = "tcp",
    [ValidateSet("memory", "wav")]
    [string]$ClientSink = "memory",
    [ValidateRange(1, 16)]
    [int]$BlocksPerPacket = 1,
    [switch]$QueueDiagnostic,
    [ValidateRange(0, 1000)]
    [int]$QueueBufferBlocks = 20,
    [switch]$RingDiagnostic,
    [ValidateRange(1, 1000)]
    [int]$RingCapacityBlocks = 12,
    [ValidateRange(0, 1000)]
    [int]$RingPrebufferBlocks = 8,
    [ValidateRange(0, 10000)]
    [double]$RingResyncLatenessMs = 0.0,
    [ValidateSet("hybrid", "waitable_timer")]
    [string]$ConsumerWaitMode = "hybrid",
    [ValidateSet("normal", "above_normal", "highest", "time_critical")]
    [string]$ConsumerThreadPriority = "normal",
    [ValidateSet("normal", "above_normal", "highest", "time_critical")]
    [string]$ReceiverThreadPriority = "normal",
    [ValidateSet("normal", "above_normal", "high", "realtime")]
    [string]$ReceiverProcessPriority = "normal",
    [string]$VmProcessAffinityMask = "",
    [ValidateSet("unchanged", "Normal", "AboveNormal", "High", "RealTime")]
    [string]$VmProcessPriority = "unchanged",
    [ValidateRange(1, 100000)]
    [int]$ProgressIntervalBlocks = 100,
    [ValidateSet("Run", "Start")]
    [string]$GuestLaunchMode = "Run"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$VBox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $PSScriptRoot "VmSsdRuntime.ps1")

$VmRuntime = Get-VmSsdRuntime -RuntimeRoot $RuntimeRoot
$Python = (Get-Command python -ErrorAction Stop).Source
$Preflight = Join-Path $PSScriptRoot "Test-VmAutomationPreflight.ps1"
$StreamProbe = Join-Path $RepoRoot "scripts\audio\host_guest_pcm_stream_dfn48.py"
$Analyzer = Join-Path $RepoRoot "scripts\audio\analyze_dfn48_vm_transport.py"
$NativeReceiver = Join-Path $RepoRoot "scripts\native\dfn48_native_receiver\bin\dfn48_native_receiver.exe"
$ResolvedSourceWav = if ([IO.Path]::IsPathRooted($SourceWav)) {
    $SourceWav
} else {
    Join-Path $RepoRoot $SourceWav
}
$ResolvedResultRoot = if ([IO.Path]::IsPathRooted($ResultRoot)) {
    $ResultRoot
} else {
    Join-Path $RepoRoot $ResultRoot
}
$GuestRoot = "C:\PTC3527\dfn3_transport_48k"
$GuestProbe = "$GuestRoot\host_guest_pcm_stream_dfn48.py"
$GuestNativeReceiver = "$GuestRoot\dfn48_native_receiver.exe"
$GuestNativeRunner = "$GuestRoot\run_native_receiver.ps1"
$GuestPython = "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
$implementationSlug = $ClientImplementation.ToLowerInvariant()
$transportSlug = $Transport.ToLowerInvariant()
$RingResyncLatenessArg = $RingResyncLatenessMs.ToString(
    [System.Globalization.CultureInfo]::InvariantCulture
)
$batchSlug = if ($BlocksPerPacket -gt 1) {
    "-batch$BlocksPerPacket-diagnostic"
} else {
    ""
}
$consumerSlug = ""
if ($ConsumerWaitMode -ne "hybrid") {
    $consumerSlug += "-wait$($ConsumerWaitMode.Replace('_', ''))"
}
if ($ConsumerThreadPriority -ne "normal") {
    $consumerSlug += "-prio$($ConsumerThreadPriority.Replace('_', ''))"
}
if ($ReceiverThreadPriority -ne "normal") {
    $consumerSlug += "-rxprio$($ReceiverThreadPriority.Replace('_', ''))"
}
if ($ReceiverProcessPriority -ne "normal") {
    $consumerSlug += "-proc$($ReceiverProcessPriority.Replace('_', ''))"
}
if ($VmProcessAffinityMask -ne "") {
    $consumerSlug += "-vmaff$($VmProcessAffinityMask.Replace('0x', '').Replace('0X', ''))"
}
if ($VmProcessPriority -ne "unchanged") {
    $consumerSlug += "-vmprio$VmProcessPriority"
}
$networkSlug = ""
if ($GuestConnectHost -ne "10.0.2.2") {
    $networkSlug += "-guesthost$($GuestConnectHost.Replace('.', 'p').Replace(':', 'p'))"
}
if ($TemporaryHostOnlyAdapterName -ne "") {
    $networkSlug += "-hostonly"
}
$queueSlug = if ($QueueDiagnostic) {
    "-queue$QueueBufferBlocks$consumerSlug-diagnostic"
} elseif ($RingDiagnostic) {
    $resyncSlug = if ($RingResyncLatenessMs -gt 0) {
        "-resync$($RingResyncLatenessArg.Replace('.', 'p'))"
    } else {
        ""
    }
    "-ring$RingCapacityBlocks-pre$RingPrebufferBlocks$resyncSlug$consumerSlug-diagnostic"
} else {
    ""
}
$RunId = (
    (Get-Date).ToString("yyyyMMdd-HHmmss") +
    "-dfn3-transport-48k-r9-$transportSlug-$implementationSlug-receiver$batchSlug$networkSlug$queueSlug"
)

New-Item -ItemType Directory -Force -Path $ResolvedResultRoot | Out-Null
$RunResult = Join-Path $ResolvedResultRoot "runs\$RunId"
New-Item -ItemType Directory -Force -Path $RunResult | Out-Null

$PreflightPath = Join-Path $RunResult "preflight_before.json"
$ManifestPath = Join-Path $RunResult "deployment_manifest.json"
$ServerPath = Join-Path $RunResult "server.json"
$ClientPath = Join-Path $RunResult "client.json"
$ServerTracePath = Join-Path $RunResult "server_trace.json"
$ClientTracePath = Join-Path $RunResult "client_trace.json"
$ConsumerTracePath = Join-Path $RunResult "consumer_trace.json"
$ProgressPath = Join-Path $RunResult "progress.json"
$SchedulerTracePath = Join-Path $RunResult "scheduler_trace.json"
$HashPath = Join-Path $RunResult "received_payload_hash.json"
$GatePath = Join-Path $RunResult "vm_transport_gate.json"
$SummaryPath = Join-Path $RunResult "transport_summary.json"
$TeardownPath = Join-Path $RunResult "teardown_result.json"
$HostResultPath = Join-Path $RunResult "host_result.json"
$VmProcessSchedulingPath = Join-Path $RunResult "vm_process_scheduling.json"
$ReceivedWavPath = Join-Path $RunResult "received.wav"

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

    $deadline = (Get-Date).AddSeconds(15)
    do {
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $output = @(& $VBox showvminfo $TargetVm --machinereadable 2>&1)
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

function Copy-OptionalFromGuest {
    param(
        [string]$PasswordFile,
        [string]$Name
    )

    $destination = Join-Path $RunResult $Name
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        return
    }
    try {
        Copy-FromGuest `
            -PasswordFile $PasswordFile `
            -Source "$GuestRoot\$Name" `
            -Destination $RunResult
    } catch {
    }
}

function Wait-GuestArtifact {
    param(
        [string]$PasswordFile,
        [string]$Name,
        [int]$TimeoutSeconds = 90
    )

    $guestPath = "$GuestRoot\$Name"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $output = Invoke-Guest `
                -PasswordFile $PasswordFile `
                -Command "if (Test-Path -LiteralPath '$guestPath') { 'present' } else { exit 2 }" `
                -TimeoutMilliseconds 15000
            if ($output -contains "present") {
                return
            }
        } catch {
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for guest artifact: $Name"
}

function Stop-VmGracefully {
    param([string]$PasswordFile)

    if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
        return
    }
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        if ($attempt -gt 1) {
            & $VBox guestcontrol $VmName closesession --all 2>&1 | Out-Null
            Start-Sleep -Seconds 10
        }
        $shutdownArguments = @(
            "guestcontrol", $VmName, "start",
            "--exe", "C:\Windows\System32\shutdown.exe",
            "--username", $Username,
            "--passwordfile=$PasswordFile",
            "--ignore-orphaned-processes", "--",
            "/s", "/t", "5", "/d", "p:0:0"
        )
        & $VBox @shutdownArguments 2>&1 | Out-Null
        $ErrorActionPreference = $oldPreference
        try {
            Wait-VmState -Expected "poweroff" -TimeoutSeconds 180
            return
        } catch {
        }
    }
    & $VBox controlvm $VmName acpipowerbutton 2>$null | Out-Null
    Wait-VmState -Expected "poweroff" -TimeoutSeconds 180
}

function ConvertTo-ProcessArgument {
    param([string]$Value)

    return '"' + $Value.Replace('"', '\"') + '"'
}

function Start-DfnTransportServer {
    $arguments = @(
        $StreamProbe,
        "server",
        "--source-wav", $ResolvedSourceWav,
        "--bind", "0.0.0.0",
        "--port", [string]$Port,
        "--accept-timeout", "180",
        "--socket-timeout", "45",
        "--blocks-per-packet", [string]$BlocksPerPacket,
        "--transport", $Transport,
        "--output", $ServerPath,
        "--trace", $ServerTracePath
    ) | ForEach-Object { ConvertTo-ProcessArgument ([string]$_) }

    $process = Start-Process `
        -FilePath $Python `
        -ArgumentList ($arguments -join " ") `
        -RedirectStandardOutput (Join-Path $RunResult "server.stdout.txt") `
        -RedirectStandardError (Join-Path $RunResult "server.stderr.txt") `
        -WindowStyle Hidden `
        -PassThru
    try {
        $process.PriorityClass = $ServerPriority
        $process.Refresh()
    } catch {
        throw "Failed to set host stream server priority to ${ServerPriority}: $($_.Exception.Message)"
    }
    return $process
}

function Enable-TemporaryHostOnlyNic {
    if ([string]::IsNullOrWhiteSpace($TemporaryHostOnlyAdapterName)) {
        return
    }

    Invoke-VBox modifyvm $VmName `
        --nic2 hostonly `
        "--hostonlyadapter2=$TemporaryHostOnlyAdapterName" `
        --cableconnected2 on | Out-Null
}

function ConvertTo-AffinityMask {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }
    $trimmed = $Value.Trim()
    if ($trimmed.StartsWith("0x", [StringComparison]::OrdinalIgnoreCase)) {
        return [Int64]::Parse(
            $trimmed.Substring(2),
            [Globalization.NumberStyles]::HexNumber,
            [Globalization.CultureInfo]::InvariantCulture
        )
    }
    return [Int64]::Parse(
        $trimmed,
        [Globalization.NumberStyles]::Integer,
        [Globalization.CultureInfo]::InvariantCulture
    )
}

function Get-VmHostProcess {
    param([datetime]$StartedAfter)

    $processes = Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -in @("VirtualBoxVM.exe", "VBoxHeadless.exe") -and
            $null -ne $_.CommandLine
        }
    $escapedVmName = [regex]::Escape($VmName)
    $matched = @(
        $processes |
            Where-Object { $_.CommandLine -match $escapedVmName } |
            Sort-Object ProcessId -Descending
    )
    if ($matched.Count -gt 0) {
        return Get-Process -Id $matched[0].ProcessId -ErrorAction Stop
    }

    $fallback = @(
        Get-Process -Name VirtualBoxVM,VBoxHeadless -ErrorAction SilentlyContinue |
            Where-Object { $_.StartTime -ge $StartedAfter.AddSeconds(-5) } |
            Sort-Object StartTime -Descending
    )
    if ($fallback.Count -eq 1) {
        return $fallback[0]
    }
    if ($fallback.Count -gt 1) {
        throw "Multiple recent VirtualBox VM processes found; cannot safely choose one."
    }
    throw "VirtualBox VM process not found for $VmName."
}

function Set-VmProcessScheduling {
    param([datetime]$StartedAfter)

    $affinityMask = ConvertTo-AffinityMask -Value $VmProcessAffinityMask
    $result = [ordered]@{
        timestamp = (Get-Date).ToString("o")
        vm_name = $VmName
        requested_affinity_mask = $VmProcessAffinityMask
        requested_priority = $VmProcessPriority
        process_found = $false
        process_id = $null
        process_name = $null
        affinity_applied = $false
        priority_applied = $false
        effective_affinity_mask = $null
        effective_priority = $null
        error = $null
    }

    if ($null -eq $affinityMask -and $VmProcessPriority -eq "unchanged") {
        Write-JsonFile $VmProcessSchedulingPath $result
        return $result
    }

    try {
        $process = Get-VmHostProcess -StartedAfter $StartedAfter
        $result.process_found = $true
        $result.process_id = $process.Id
        $result.process_name = $process.ProcessName
        if ($null -ne $affinityMask) {
            if ($affinityMask -le 0) {
                throw "VmProcessAffinityMask must be a positive integer or hex mask."
            }
            $process.ProcessorAffinity = [IntPtr]$affinityMask
            $result.affinity_applied = $true
        }
        if ($VmProcessPriority -ne "unchanged") {
            $process.PriorityClass = $VmProcessPriority
            $result.priority_applied = $true
        }
        $process.Refresh()
        $result.effective_affinity_mask = "0x{0:X}" -f $process.ProcessorAffinity.ToInt64()
        $result.effective_priority = [string]$process.PriorityClass
    } catch {
        $result.error = $_.Exception.Message
        Write-JsonFile $VmProcessSchedulingPath $result
        throw
    }

    Write-JsonFile $VmProcessSchedulingPath $result
    return $result
}

function Write-JsonFile {
    param([string]$Path, [object]$Value)

    $Value |
        ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $Path -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $ResolvedSourceWav -PathType Leaf)) {
    throw "Source WAV not found: $ResolvedSourceWav"
}
if (-not (Test-Path -LiteralPath $StreamProbe -PathType Leaf)) {
    throw "Stream probe not found: $StreamProbe"
}
if (-not (Test-Path -LiteralPath $Analyzer -PathType Leaf)) {
    throw "Analyzer not found: $Analyzer"
}
if (
    $ClientImplementation -eq "Native" -and
    -not (Test-Path -LiteralPath $NativeReceiver -PathType Leaf)
) {
    throw "Native receiver not found. Build first: scripts\native\dfn48_native_receiver\build_release.ps1"
}
if ($ClientImplementation -eq "Native" -and $ClientSink -ne "memory") {
    throw "Native receiver currently supports only ClientSink=memory."
}
if ($ClientImplementation -eq "Python" -and $Transport -ne "tcp") {
    throw "The Python guest client currently supports only Transport=tcp. Use ClientImplementation=Native for UDP diagnostics."
}
if ($ClientImplementation -ne "Native" -and $QueueDiagnostic) {
    throw "QueueDiagnostic currently requires ClientImplementation=Native."
}
if ($ClientImplementation -ne "Native" -and $RingDiagnostic) {
    throw "RingDiagnostic currently requires ClientImplementation=Native."
}
if ($QueueDiagnostic -and $RingDiagnostic) {
    throw "QueueDiagnostic and RingDiagnostic are mutually exclusive."
}
if ($RingDiagnostic -and $RingPrebufferBlocks -gt $RingCapacityBlocks) {
    throw "RingPrebufferBlocks must be less than or equal to RingCapacityBlocks."
}

$preflightOutput = @(
    & powershell -NoProfile -ExecutionPolicy Bypass `
        -File $Preflight `
        -RuntimeRoot $RuntimeRoot `
        -OrchestratorPath "scripts\vm\Invoke-Dfn3TransportVm.ps1" `
        -AudioRun 2>&1
)
$preflightExitCode = $LASTEXITCODE
$preflightOutput |
    Set-Content -LiteralPath $PreflightPath -Encoding UTF8
if ($preflightExitCode -ne 0) {
    throw "Host-only preflight failed. See $PreflightPath"
}

$sourceHash = Get-FileHash -LiteralPath $ResolvedSourceWav -Algorithm SHA256
$manifestFiles = @($StreamProbe, $Analyzer, $ResolvedSourceWav)
if ($ClientImplementation -eq "Native") {
    $manifestFiles += $NativeReceiver
}
Write-JsonFile $ManifestPath ([ordered]@{
    timestamp = (Get-Date).ToString("o")
    run_id = $RunId
    phase = "VM-DFN3-TRANSPORT-48K"
    vm_name = $VmName
    expected_snapshot = $ExpectedSnapshot
    guest_root = $GuestRoot
    source_wav = [ordered]@{
        path = $ResolvedSourceWav
        sha256 = $sourceHash.Hash
        copied_to_guest = $false
    }
    contract = [ordered]@{
        sample_rate = 48000
        channels = 1
        format = "pcm_s16le"
        frames_per_block = 480
        block_duration_ms = 10
        blocks_per_second = 100
        sysvad_used = $false
        pcm_bridge_v1_used = $false
        rnnoise_used = $false
        host_stream_server_priority = $ServerPriority
        guest_connect_host = $GuestConnectHost
        temporary_hostonly_adapter_name = $TemporaryHostOnlyAdapterName
        client_implementation = $ClientImplementation
        transport_protocol = $Transport
        client_sink = $ClientSink
        transport_blocks_per_packet = $BlocksPerPacket
        queue_diagnostic = [bool]$QueueDiagnostic
        queue_buffer_blocks = $QueueBufferBlocks
        ring_diagnostic = [bool]$RingDiagnostic
        ring_capacity_blocks = $RingCapacityBlocks
        ring_prebuffer_blocks = $RingPrebufferBlocks
        ring_resync_lateness_ms = $RingResyncLatenessMs
        consumer_wait_mode = $ConsumerWaitMode
        consumer_thread_priority = $ConsumerThreadPriority
        receiver_thread_priority = $ReceiverThreadPriority
        receiver_process_priority = $ReceiverProcessPriority
        vm_process_affinity_mask = $VmProcessAffinityMask
        vm_process_priority = $VmProcessPriority
        progress_interval_blocks = $ProgressIntervalBlocks
        guest_launch_mode = $GuestLaunchMode
        diagnostic_only = (($BlocksPerPacket -gt 1) -or ($Transport -ne "tcp") -or [bool]$QueueDiagnostic -or [bool]$RingDiagnostic)
        udp_diagnostic = ($Transport -eq "udp")
        native_receiver_used = ($ClientImplementation -eq "Native")
        python_receiver_used = ($ClientImplementation -eq "Python")
    }
    files = @(
        foreach ($path in $manifestFiles) {
            [ordered]@{
                name = Split-Path -Leaf $path
                path = $path
                sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
            }
        }
    )
})

$passwordFile = Join-Path ([IO.Path]::GetTempPath()) (
    "ptc3527-dfn3-transport-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
$activeServer = $null
$succeeded = $false
$failureMessage = $null
$teardownFailure = $null
$restoreAttempted = $false
$forcedPoweroffUsed = $false
$vmProcessScheduling = $null

try {
    [IO.File]::WriteAllText(
        $passwordFile,
        (Get-LabPassword),
        [Text.UTF8Encoding]::new($false)
    )

    Enable-TemporaryHostOnlyNic
    $vmStartTime = Get-Date
    Invoke-VBox startvm $VmName --type gui | Out-Null
    Wait-VmState -Expected "running"
    $vmProcessScheduling = Set-VmProcessScheduling -StartedAfter $vmStartTime
    Wait-GuestAdditions

    Invoke-Guest -PasswordFile $passwordFile -Command @"
if (Test-Path -LiteralPath '$GuestRoot') {
    Remove-Item -LiteralPath '$GuestRoot' -Recurse -Force
}
New-Item -ItemType Directory -Force -Path '$GuestRoot' | Out-Null
"@ | Out-Null
    if ($ClientImplementation -eq "Python") {
        Copy-ToGuest -PasswordFile $passwordFile -Source $StreamProbe
    } else {
        Copy-ToGuest -PasswordFile $passwordFile -Source $NativeReceiver
    }
    Copy-ToGuest -PasswordFile $passwordFile -Source $ManifestPath

    $activeServer = Start-DfnTransportServer
    Start-Sleep -Milliseconds 750
    if ($activeServer.HasExited) {
        throw "Host DFN48 stream server exited before guest connection."
    }

    if ($ClientImplementation -eq "Python") {
        $guestCommand = (
            "& '$GuestPython' '$GuestProbe' client " +
            "--host $GuestConnectHost " +
            "--port $Port " +
            "--connect-timeout 180 " +
            "--socket-timeout 45 " +
            "--blocks-per-packet $BlocksPerPacket " +
            "--transport $Transport " +
            "--output '$GuestRoot\client.json' " +
            "--trace '$GuestRoot\client_trace.json' " +
            "--scheduler-trace '$GuestRoot\scheduler_trace.json' " +
            "--scheduler-interval-ms 2.0 " +
            "--sink '$ClientSink' " +
            $(if ($ClientSink -eq "wav") {
                "--output-wav '$GuestRoot\received.wav' "
            } else {
                ""
            }) +
            "--hash-output '$GuestRoot\received_payload_hash.json'; " +
            "if (`$LASTEXITCODE -ne 0) { " +
            "throw 'Guest DFN48 transport Python client failed with exit code ' + " +
            "`$LASTEXITCODE }"
        )
    } else {
        $queueArgs = if ($QueueDiagnostic) {
            "--queue-diagnostic --queue-buffer-blocks $QueueBufferBlocks --consumer-trace '$GuestRoot\consumer_trace.json' "
        } elseif ($RingDiagnostic) {
            "--ring-diagnostic --ring-capacity-blocks $RingCapacityBlocks --ring-prebuffer-blocks $RingPrebufferBlocks --ring-resync-lateness-ms $RingResyncLatenessArg --consumer-trace '$GuestRoot\consumer_trace.json' "
        } else {
            ""
        }
        $consumerArgs = if ($QueueDiagnostic -or $RingDiagnostic) {
            "--consumer-wait-mode $ConsumerWaitMode --consumer-thread-priority $ConsumerThreadPriority --receiver-thread-priority $ReceiverThreadPriority --process-priority $ReceiverProcessPriority "
        } else {
            "--receiver-thread-priority $ReceiverThreadPriority --process-priority $ReceiverProcessPriority "
        }
        $guestCommand = (
            "& '$GuestNativeReceiver' client " +
            "--host $GuestConnectHost " +
            "--port $Port " +
            "--connect-timeout 180 " +
            "--socket-timeout 45 " +
            "--blocks-per-packet $BlocksPerPacket " +
            "--transport $Transport " +
            "--output '$GuestRoot\client.json' " +
            "--trace '$GuestRoot\client_trace.json' " +
            $queueArgs +
            $consumerArgs +
            "--progress-output '$GuestRoot\progress.json' " +
            "--progress-interval-blocks $ProgressIntervalBlocks " +
            "--scheduler-trace '$GuestRoot\scheduler_trace.json' " +
            "--scheduler-interval-ms 2.0 " +
            "--sink '$ClientSink' " +
            "--hash-output '$GuestRoot\received_payload_hash.json'; " +
            "if (`$LASTEXITCODE -ne 0) { " +
            "throw 'Guest DFN48 transport native receiver failed with exit code ' + " +
            "`$LASTEXITCODE }"
        )
        if ($GuestLaunchMode -eq "Start") {
            $guestRunnerLocalPath = Join-Path $RunResult "run_native_receiver.ps1"
            @"
`$ErrorActionPreference = "Stop"
`$failure = `$null
try {
    $guestCommand
} catch {
    `$failure = `$_.Exception.Message
}
`$exitCode = if (`$null -eq `$failure) { 0 } else { 1 }
[ordered]@{
    timestamp = (Get-Date).ToString("o")
    exit_code = `$exitCode
    failure = `$failure
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath '$GuestRoot\guest_exit.json' -Encoding UTF8
exit `$exitCode
"@ | Set-Content -LiteralPath $guestRunnerLocalPath -Encoding UTF8
            Copy-ToGuest -PasswordFile $passwordFile -Source $guestRunnerLocalPath
        }
    }
    if ($ClientImplementation -eq "Native" -and $GuestLaunchMode -eq "Start") {
        Invoke-VBox guestcontrol $VmName start `
            --exe "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" `
            --username $Username `
            "--passwordfile=$passwordFile" `
            --ignore-orphaned-processes `
            "--" `
            -NoProfile -NonInteractive -ExecutionPolicy Bypass `
            -File $GuestNativeRunner | Out-Null
    } else {
        Invoke-Guest `
            -PasswordFile $passwordFile `
            -Command $guestCommand `
            -TimeoutMilliseconds 300000 |
            Set-Content `
                -LiteralPath (Join-Path $RunResult "client.stdout.txt") `
                -Encoding UTF8
    }

    if (-not $activeServer.WaitForExit(120000)) {
        Stop-Process -Id $activeServer.Id -Force
        throw "Host DFN48 stream server timed out after guest client returned."
    }
    $activeServer.WaitForExit()
    $activeServer.Refresh()
    $serverExitCode = $activeServer.ExitCode
    if ($null -ne $serverExitCode -and $serverExitCode -ne 0) {
        throw "Host DFN48 stream server failed with exit code $serverExitCode."
    }
    if (-not (Test-Path -LiteralPath $ServerPath -PathType Leaf)) {
        throw "Host DFN48 stream server did not produce server.json."
    }
    $serverResult = Get-Content -LiteralPath $ServerPath -Raw |
        ConvertFrom-Json
    if ($serverResult.status -ne "completed") {
        throw "Host DFN48 stream server did not complete successfully."
    }
    $activeServer = $null
    if ($ClientImplementation -eq "Native" -and $GuestLaunchMode -eq "Start") {
        Wait-GuestArtifact `
            -PasswordFile $passwordFile `
            -Name "guest_exit.json" `
            -TimeoutSeconds 90
    }

    $guestArtifacts = @(
        "client.json",
        "client_trace.json",
        "progress.json",
        "scheduler_trace.json",
        "received_payload_hash.json"
    )
    if ($QueueDiagnostic -or $RingDiagnostic) {
        $guestArtifacts += "consumer_trace.json"
    }
    foreach ($name in $guestArtifacts) {
        Copy-FromGuest `
            -PasswordFile $passwordFile `
            -Source "$GuestRoot\$name" `
            -Destination $RunResult
    }
    if ($ClientImplementation -eq "Native" -and $GuestLaunchMode -eq "Start") {
        Copy-OptionalFromGuest -PasswordFile $passwordFile -Name "guest_exit.json"
    }
    if ($ClientSink -eq "wav") {
        Copy-FromGuest `
            -PasswordFile $passwordFile `
            -Source "$GuestRoot\received.wav" `
            -Destination $RunResult
    }

    & $Python $Analyzer `
        --root $RunResult `
        --output $GatePath `
        --summary-output $SummaryPath `
        --expected-duration 60.0
    if ($LASTEXITCODE -ne 0) {
        throw "DFN48 VM transport gate was rejected."
    }
    $succeeded = $true
} catch {
    $failureMessage = $_.Exception.Message
} finally {
    if ($null -ne $activeServer -and -not $activeServer.HasExited) {
        Stop-Process -Id $activeServer.Id -Force
    }
    try {
        if (
            (Test-Path -LiteralPath $passwordFile) -and
            (Get-VmProperty -TargetVm $VmName -Name "VMState") -ne "poweroff"
        ) {
            if ($ClientImplementation -eq "Native") {
                foreach ($optionalName in @(
                    "client.json",
                    "client_trace.json",
                    "consumer_trace.json",
                    "progress.json",
                    "scheduler_trace.json",
                    "received_payload_hash.json",
                    "guest_exit.json"
                )) {
                    Copy-OptionalFromGuest -PasswordFile $passwordFile -Name $optionalName
                }
            }
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
            $restoreAttempted = $true
        }
    } catch {
        $teardownFailure = $_.Exception.Message
        if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -ne "poweroff") {
            $oldPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            & $VBox controlvm $VmName poweroff 2>&1 |
                Set-Content `
                    -LiteralPath (Join-Path $RunResult "forced_poweroff.txt") `
                    -Encoding UTF8
            $ErrorActionPreference = $oldPreference
            Wait-VmState -Expected "poweroff" -TimeoutSeconds 60
            $forcedPoweroffUsed = $true
            Invoke-VBox snapshot $VmName restore $ExpectedSnapshot | Out-Null
            $restoreAttempted = $true
        } else {
            Invoke-VBox snapshot $VmName restore $ExpectedSnapshot | Out-Null
            $restoreAttempted = $true
        }
    }
    if (Test-Path -LiteralPath $passwordFile) {
        Remove-Item -LiteralPath $passwordFile -Force
    }

    Write-JsonFile $TeardownPath ([ordered]@{
        timestamp = (Get-Date).ToString("o")
        restore_attempted = $restoreAttempted
        teardown_failure = $teardownFailure
        forced_poweroff_used = $forcedPoweroffUsed
        clone = [ordered]@{
            state = Get-VmProperty -TargetVm $VmName -Name "VMState"
            snapshot = Get-VmProperty -TargetVm $VmName -Name "CurrentSnapshotName"
            audio_in = Get-VmProperty -TargetVm $VmName -Name "audio_in"
            clipboard = Get-VmProperty -TargetVm $VmName -Name "clipboard"
            drag_and_drop = Get-VmProperty -TargetVm $VmName -Name "draganddrop"
            nic1 = Get-VmProperty -TargetVm $VmName -Name "nic1"
            nic2 = Get-VmProperty -TargetVm $VmName -Name "nic2"
        }
    })
}

Write-JsonFile $HostResultPath ([ordered]@{
    timestamp = (Get-Date).ToString("o")
    run_id = $RunId
    succeeded = $succeeded
    failure = $failureMessage
    result_root = $ResolvedResultRoot
    run_result = $RunResult
    vm_transport_gate = if (Test-Path -LiteralPath $GatePath -PathType Leaf) {
        (Get-Content -LiteralPath $GatePath -Raw | ConvertFrom-Json).status
    } else {
        $null
    }
    sysvad_used = $false
    pcm_bridge_v1_used = $false
    rnnoise_used = $false
    host_stream_server_priority = $ServerPriority
    guest_connect_host = $GuestConnectHost
    temporary_hostonly_adapter_name = $TemporaryHostOnlyAdapterName
    client_implementation = $ClientImplementation
    transport_protocol = $Transport
    client_sink = $ClientSink
    transport_blocks_per_packet = $BlocksPerPacket
    queue_diagnostic = [bool]$QueueDiagnostic
    queue_buffer_blocks = $QueueBufferBlocks
    ring_diagnostic = [bool]$RingDiagnostic
    ring_capacity_blocks = $RingCapacityBlocks
    ring_prebuffer_blocks = $RingPrebufferBlocks
    ring_resync_lateness_ms = $RingResyncLatenessMs
    consumer_wait_mode = $ConsumerWaitMode
    consumer_thread_priority = $ConsumerThreadPriority
    receiver_thread_priority = $ReceiverThreadPriority
    receiver_process_priority = $ReceiverProcessPriority
    vm_process_affinity_mask = $VmProcessAffinityMask
    vm_process_priority = $VmProcessPriority
    vm_process_scheduling = if (Test-Path -LiteralPath $VmProcessSchedulingPath -PathType Leaf) {
        Get-Content -LiteralPath $VmProcessSchedulingPath -Raw | ConvertFrom-Json
    } else {
        $vmProcessScheduling
    }
    guest_launch_mode = $GuestLaunchMode
    diagnostic_only = (($BlocksPerPacket -gt 1) -or ($Transport -ne "tcp") -or [bool]$QueueDiagnostic -or [bool]$RingDiagnostic)
    udp_diagnostic = ($Transport -eq "udp")
    forced_poweroff_used = $forcedPoweroffUsed
})

if (-not $succeeded) {
    throw "DFN3 transport VM phase failed: $failureMessage"
}
