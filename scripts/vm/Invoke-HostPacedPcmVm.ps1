[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB-FAST",
    [string]$OriginalVmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527",
    [string]$ExpectedSnapshot = "checkpoint45-causal-wpt-validated",
    [int]$DurationSeconds = 20,
    [int]$BasePort = 35270,
    [ValidateSet(
        "Synthetic",
        "PhysicalPair",
        "EndpointPair",
        "EndpointDiagnostic",
        "EndpointScheduling",
        "EndpointTimer",
        "EndpointPrefill",
        "EndpointCaptureTimer",
        "EndpointStartBarrier",
        "EndpointSendLead",
        "EndpointHostAffinity",
        "EndpointCaptureTiming",
        "EndpointCaptureSpin",
        "EndpointCaptureEvent"
    )]
    [string]$Mode = "Synthetic",
    [string]$PcmFile = "",
    [string]$RuntimeRoot = (
        Join-Path $env:LOCALAPPDATA "PTC3527-Private\vm_runtime"
    ),
    [string]$CaptureExe = (
        Join-Path $env:USERPROFILE (
            "source\repos\Windows-driver-samples\audio\sysvad\" +
            "tools\PtcPcmCapture\x64\Release\PtcPcmCapture.exe"
        )
    ),
    [string]$Dll = (
        Join-Path $env:LOCALAPPDATA "PTC3527\bin\ptc3527-rnnoise-v0.2.dll"
    ),
    [string]$PrivateBase = (
        Join-Path $env:LOCALAPPDATA (
            "PTC3527-Private\host_paced_pcm\endpoint_runs"
        )
    ),
    [UInt64]$PerformanceCpuMask = 0xFFF
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$VBox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. (Join-Path $PSScriptRoot "VmSsdRuntime.ps1")
$VmRuntime = Get-VmSsdRuntime -RuntimeRoot $RuntimeRoot
$StreamProbe = Join-Path $RepoRoot "scripts\audio\host_guest_pcm_stream.py"
$SchedulerProbe = Join-Path $RepoRoot "scripts\audio\guest_scheduler_probe.py"
$Analyzer = Join-Path $RepoRoot (
    "scripts\audio\analyze_host_guest_pcm_matrix.py"
)
$EndpointAnalyzer = Join-Path $RepoRoot (
    "scripts\audio\analyze_host_paced_endpoint.py"
)
$EndpointDiagnosticAnalyzer = Join-Path $RepoRoot (
    "scripts\audio\analyze_endpoint_stall.py"
)
$EndpointSchedulingAnalyzer = Join-Path $RepoRoot (
    "scripts\audio\analyze_endpoint_scheduling.py"
)
$CaptureTimingAnalyzer = Join-Path $RepoRoot (
    "scripts\audio\analyze_capture_timing.py"
)
$CaptureSpinAnalyzer = Join-Path $RepoRoot (
    "scripts\audio\analyze_capture_spin.py"
)
$CaptureEventAnalyzer = Join-Path $RepoRoot (
    "scripts\audio\analyze_capture_event.py"
)
$EndpointGuestScript = Join-Path $RepoRoot (
    "scripts\vm\guest\Invoke-HostPacedEndpointScenario.ps1"
)
$ExpectedDllHash = (
    "593D387801A7D0464D2F11449E43E466" +
    "811DEAEB66C39E367085E28DAAB0F84C"
)
$UnattendPath = $VmRuntime.CredentialPath
$GuestRoot = "C:\PTC3527\host_paced_pcm"
$GuestProbe = "$GuestRoot\host_guest_pcm_stream.py"
$GuestSchedulerProbe = "$GuestRoot\guest_scheduler_probe.py"
$GuestEndpointScript = "$GuestRoot\Invoke-HostPacedEndpointScenario.ps1"
$GuestApp = "$GuestRoot\app"
$GuestDll = "$GuestRoot\ptc3527-rnnoise-v0.2.dll"
$RunId = (
    (Get-Date).ToString("yyyyMMdd-HHmmss") +
    "-host-paced-" + $Mode.ToLowerInvariant()
)
$ResultRoot = Join-Path $RepoRoot (
    "resultados\sysvad_checkpoint46_reopened\host_paced_pcm"
)
$RunResult = Join-Path $ResultRoot "runs\$RunId"
$Bundle = Join-Path $RunResult "host_paced_app.zip"
$ManifestPath = Join-Path $RunResult "deployment_manifest.json"
$GatePath = Join-Path $RunResult "integration_gate.json"
$EndpointGatePath = Join-Path $RunResult "endpoint_gate.json"
$PrivateRunResult = Join-Path $PrivateBase $RunId
$Python = (Get-Command python -ErrorAction Stop).Source
$EndpointMode = $Mode -in @(
    "EndpointPair",
    "EndpointDiagnostic",
    "EndpointScheduling",
    "EndpointTimer",
    "EndpointPrefill",
    "EndpointCaptureTimer",
    "EndpointStartBarrier",
    "EndpointSendLead",
    "EndpointHostAffinity",
    "EndpointCaptureTiming",
    "EndpointCaptureSpin",
    "EndpointCaptureEvent"
)
$UsesPrivatePcm = $Mode -in @("PhysicalPair", "EndpointPair")

$Scenarios = if ($Mode -eq "EndpointCaptureEvent") {
    @(
        [ordered]@{
            Name = "01-yield-control-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "02-event-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "event"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "03-event-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "event"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "04-yield-control-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        }
    )
} elseif ($Mode -eq "EndpointCaptureSpin") {
    @(
        [ordered]@{
            Name = "01-yield-control-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "02-spin-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "spin"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "03-spin-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "spin"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "04-yield-control-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        }
    )
} elseif ($Mode -eq "EndpointCaptureTiming") {
    @(
        [ordered]@{
            Name = "01-capture-timing-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "diagnostic"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "02-capture-timing-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "diagnostic"
            HostVmPriority = "Unchanged"
        }
    )
} elseif ($Mode -eq "EndpointHostAffinity") {
    @(
        [ordered]@{
            Name = "01-all-cpus-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
            HostVmAffinity = "all"
        },
        [ordered]@{
            Name = "02-performance-cpus-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
            HostVmAffinity = "performance"
        },
        [ordered]@{
            Name = "03-performance-cpus-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
            HostVmAffinity = "performance"
        },
        [ordered]@{
            Name = "04-all-cpus-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
            HostVmAffinity = "all"
        }
    )
} elseif ($Mode -eq "EndpointSendLead") {
    @(
        [ordered]@{
            Name = "01-zero-lead-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "02-ten-ms-lead-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 10
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "03-ten-ms-lead-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 10
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "04-zero-lead-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            SendLeadMs = 0
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        }
    )
} elseif ($Mode -eq "EndpointStartBarrier") {
    @(
        [ordered]@{
            Name = "01-immediate-start-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $false
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "02-depth-two-start-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "03-depth-two-start-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $true
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "04-immediate-start-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            CaptureStartBarrier = $false
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        }
    )
} elseif ($Mode -eq "EndpointCaptureTimer") {
    @(
        [ordered]@{
            Name = "01-capture-sleep-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "sleep"
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "02-capture-yield-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "03-capture-yield-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "yield"
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "04-capture-sleep-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            CapturePollWaitStrategy = "sleep"
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        }
    )
} elseif ($Mode -eq "EndpointPrefill") {
    @(
        [ordered]@{
            Name = "01-unprimed-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            StartDelayMs = 250
            InitialBurstBlocks = 0
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "02-primed-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "03-primed-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            StartDelayMs = 0
            InitialBurstBlocks = 2
            ComparisonGroup = "mitigated"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "04-unprimed-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            StartDelayMs = 250
            InitialBurstBlocks = 0
            ComparisonGroup = "baseline"
            HostVmPriority = "Unchanged"
        }
    )
} elseif ($Mode -eq "EndpointTimer") {
    @(
        [ordered]@{
            Name = "01-sleep-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "sleep"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "02-yield-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "03-yield-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "yield"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "04-sleep-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            PollWaitStrategy = "sleep"
            HostVmPriority = "Unchanged"
        }
    )
} elseif ($Mode -eq "EndpointScheduling") {
    @(
        [ordered]@{
            Name = "01-baseline-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "02-mitigated-a"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "mmcss"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "03-mitigated-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "mmcss"
            HostVmPriority = "Unchanged"
        },
        [ordered]@{
            Name = "04-baseline-b"
            Method = "bypass"
            Variant = 0
            WriterScheduling = "normal"
            HostVmPriority = "Unchanged"
        }
    )
} elseif ($Mode -eq "EndpointDiagnostic") {
    ,@(
        [ordered]@{
            Name = "01-bypass-diagnostic"
            Method = "bypass"
            Variant = 0
        }
    )
} elseif ($Mode -ne "Synthetic") {
    @(
        [ordered]@{
            Name = "01-bypass-physical"
            Method = "bypass"
            Variant = 0
        },
        [ordered]@{
            Name = "02-rnnoise-physical"
            Method = "rnnoise"
            Variant = 0
        }
    )
} else {
    @(
        [ordered]@{ Name = "01-bypass-v0"; Method = "bypass"; Variant = 0 },
        [ordered]@{ Name = "02-rnnoise-v0"; Method = "rnnoise"; Variant = 0 },
        [ordered]@{ Name = "03-rnnoise-v1"; Method = "rnnoise"; Variant = 1 },
        [ordered]@{ Name = "04-bypass-v1"; Method = "bypass"; Variant = 1 }
    )
}
$EffectiveDurationSeconds = [double]$DurationSeconds

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
    if ($exitCode -ne 0) {
        throw (
            "VM property unavailable after retry: $TargetVm / $Name; " +
            ($output -join [Environment]::NewLine)
        )
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

function Stop-VmGracefully {
    param([string]$PasswordFile)

    if ((Get-VmProperty -TargetVm $VmName -Name "VMState") -eq "poweroff") {
        return
    }
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        if ($attempt -gt 1) {
            & $VBox guestcontrol $VmName closesession --all 2>&1 |
                Out-Null
            Start-Sleep -Seconds 10
        }
        & $VBox guestcontrol $VmName start `
            --exe "C:\Windows\System32\shutdown.exe" `
            --username $Username `
            "--passwordfile=$PasswordFile" `
            --ignore-orphaned-processes -- /s /t 5 /d p:0:0 2>&1 |
            Out-Null
        $ErrorActionPreference = $oldPreference
        try {
            Wait-VmState -Expected "poweroff" -TimeoutSeconds 75
            return
        } catch {
        }
    }
    & $VBox controlvm $VmName acpipowerbutton 2>$null | Out-Null
    Wait-VmState -Expected "poweroff" -TimeoutSeconds 120
}

function Get-VmFrontendProcess {
    param([string]$VmUuid)

    $uuidToken = $VmUuid.Trim().Trim("{", "}")
    $uuidCandidates = @(
        Get-CimInstance Win32_Process -Filter "Name='VirtualBoxVM.exe'" |
            Where-Object {
                -not [string]::IsNullOrWhiteSpace($_.CommandLine) -and
                $_.CommandLine.IndexOf(
                    $uuidToken,
                    [StringComparison]::OrdinalIgnoreCase
                ) -ge 0
            }
    )
    $candidates = @(
        $uuidCandidates |
            Where-Object {
                $_.CommandLine -match (
                    '^\s*"[^"]*\\VirtualBoxVM\.exe"\s+'
                )
            }
    )
    if ($candidates.Count -ne 1) {
        $details = (
            $uuidCandidates |
                ForEach-Object { "$($_.ProcessId):$($_.CommandLine)" }
        ) -join "; "
        throw (
            "Expected one primary VirtualBoxVM.exe for VM UUID $uuidToken; " +
            "found $($candidates.Count) among $($uuidCandidates.Count) " +
            "UUID matches. Candidates: $details"
        )
    }
    return Get-Process -Id ([int]$candidates[0].ProcessId)
}

function Set-VmFrontendAffinity {
    param(
        [System.Diagnostics.Process]$Process,
        [UInt64]$Mask,
        [string]$ExpectedPriority
    )

    $Process.Refresh()
    if ($Process.PriorityClass.ToString() -ne $ExpectedPriority) {
        throw (
            "VirtualBoxVM priority changed unexpectedly from " +
            "$ExpectedPriority to $($Process.PriorityClass)."
        )
    }
    $Process.ProcessorAffinity = [IntPtr]([Int64]$Mask)
    $Process.Refresh()
    $effectiveMask = [UInt64]$Process.ProcessorAffinity.ToInt64()
    if ($effectiveMask -ne $Mask) {
        throw (
            "VirtualBoxVM affinity verification failed: requested " +
            "$Mask, effective $effectiveMask."
        )
    }
    return $effectiveMask
}

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

function ConvertTo-ProcessArgument {
    param([string]$Value)

    return '"' + $Value.Replace('"', '\"') + '"'
}

function Start-StreamServer {
    param(
        [string]$ScenarioRoot,
        [int]$Port,
        [int]$Variant,
        [int]$StartDelayMs = 250,
        [int]$InitialBurstBlocks = 0,
        [int]$SendLeadMs = 0,
        [string]$InputPcm = ""
    )

    $arguments = @(
        $StreamProbe,
        "server",
        "--bind", "0.0.0.0",
        "--port", "$Port",
        "--duration", "$EffectiveDurationSeconds",
        "--variant", "$Variant",
        "--start-delay-ms", "$StartDelayMs",
        "--initial-burst-blocks", "$InitialBurstBlocks",
        "--send-lead-ms", "$SendLeadMs",
        "--prefix-blocks", "$([Math]::Min(500, $EffectiveDurationSeconds * 25))",
        "--accept-timeout", "180",
        "--output", (Join-Path $ScenarioRoot "server.json"),
        "--trace", (Join-Path $ScenarioRoot "server_trace.json")
    )
    if (-not [string]::IsNullOrWhiteSpace($InputPcm)) {
        $arguments += @("--pcm-file", $InputPcm)
    }
    $argumentLine = (
        $arguments | ForEach-Object { ConvertTo-ProcessArgument $_ }
    ) -join " "
    return Start-Process `
        -FilePath $Python `
        -ArgumentList $argumentLine `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput (Join-Path $ScenarioRoot "server.stdout.txt") `
        -RedirectStandardError (Join-Path $ScenarioRoot "server.stderr.txt")
}

foreach ($path in @(
    $VBox,
    $StreamProbe,
    $SchedulerProbe,
    $Analyzer,
    $Dll,
    $UnattendPath
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required artifact is missing: $path"
    }
}
if ($EndpointMode) {
    foreach ($path in @(
        $EndpointDiagnosticAnalyzer,
        $EndpointGuestScript,
        $CaptureExe
    )) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required endpoint artifact is missing: $path"
        }
    }
    if (
        $Mode -eq "EndpointCaptureTiming" -and
        -not (
            Test-Path `
                -LiteralPath $CaptureTimingAnalyzer `
                -PathType Leaf
        )
    ) {
        throw "Required capture timing analyzer is missing: $CaptureTimingAnalyzer"
    }
    if (
        $Mode -eq "EndpointCaptureSpin" -and
        -not (
            Test-Path `
                -LiteralPath $CaptureSpinAnalyzer `
                -PathType Leaf
        )
    ) {
        throw "Required capture spin analyzer is missing: $CaptureSpinAnalyzer"
    }
    if (
        $Mode -eq "EndpointCaptureEvent" -and
        -not (
            Test-Path `
                -LiteralPath $CaptureEventAnalyzer `
                -PathType Leaf
        )
    ) {
        throw "Required capture event analyzer is missing: $CaptureEventAnalyzer"
    }
    if (
        $Mode -eq "EndpointScheduling" -and
        -not (
            Test-Path `
                -LiteralPath $EndpointSchedulingAnalyzer `
                -PathType Leaf
        )
    ) {
        throw "Required scheduling analyzer is missing: $EndpointSchedulingAnalyzer"
    }
    if (
        $Mode -eq "EndpointPair" -and
        -not (Test-Path -LiteralPath $EndpointAnalyzer -PathType Leaf)
    ) {
        throw "Required endpoint analyzer is missing: $EndpointAnalyzer"
    }
}
if ((Get-FileHash -LiteralPath $Dll -Algorithm SHA256).Hash -ne $ExpectedDllHash) {
    throw "RNNoise DLL hash differs from the frozen v0.2 artifact."
}
if ($DurationSeconds -lt 1) {
    throw "DurationSeconds must be at least 1."
}
if ($Mode -eq "EndpointHostAffinity") {
    $hostLogicalMask = if ([Environment]::ProcessorCount -ge 64) {
        [UInt64]::MaxValue
    } else {
        ([UInt64]1 -shl [Environment]::ProcessorCount) - 1
    }
    if (
        $PerformanceCpuMask -eq 0 -or
        ($PerformanceCpuMask -band $hostLogicalMask) -ne $PerformanceCpuMask
    ) {
        throw (
            "PerformanceCpuMask must be a nonzero subset of the host " +
            "logical processor mask."
        )
    }
}
if ($UsesPrivatePcm) {
    if (-not (Test-Path -LiteralPath $PcmFile -PathType Leaf)) {
        throw "PhysicalPair requires an existing private PCM file."
    }
    $pcmLength = (Get-Item -LiteralPath $PcmFile).Length
    if ($pcmLength -le 0 -or $pcmLength % 640 -ne 0) {
        throw "The private PCM file does not contain whole 320-sample blocks."
    }
    $EffectiveDurationSeconds = ($pcmLength / 640) / 50.0
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
    throw "VirtualBox audio input must remain enabled and unchanged."
}
if ((Get-VmProperty -TargetVm $VmName -Name "clipboard") -ne "disabled") {
    throw "Clipboard must remain disabled."
}
if ((Get-VmProperty -TargetVm $VmName -Name "nic1") -ne "nat") {
    throw "NIC 1 must remain on the existing NAT configuration."
}
$originalAuditBefore = Get-OriginalVmExternalAudit `
    -Runtime $VmRuntime `
    -VBoxPath $VBox `
    -OriginalVmName $OriginalVmName

New-Item -ItemType Directory -Force -Path $RunResult | Out-Null
if ($EndpointMode) {
    New-Item -ItemType Directory -Force -Path $PrivateRunResult | Out-Null
}
New-PythonBundle
$deploymentFiles = @($StreamProbe, $SchedulerProbe, $Bundle, $Dll)
if ($EndpointMode) {
    $deploymentFiles += @($CaptureExe, $EndpointGuestScript)
}
$manifestFiles = $deploymentFiles + @($Analyzer)
if ($Mode -eq "EndpointCaptureTiming") {
    $manifestFiles += $CaptureTimingAnalyzer
    } elseif ($Mode -eq "EndpointCaptureSpin") {
        $manifestFiles += @(
            $CaptureSpinAnalyzer,
            $CaptureTimingAnalyzer,
            $EndpointSchedulingAnalyzer
        )
    } elseif ($Mode -eq "EndpointCaptureEvent") {
        $manifestFiles += @(
            $CaptureEventAnalyzer,
            $CaptureTimingAnalyzer,
            $EndpointSchedulingAnalyzer
        )
}
[ordered]@{
    created_at = (Get-Date).ToString("o")
    mode = $Mode
    duration_seconds = $EffectiveDurationSeconds
    vm_cpu_count = [int](
        Get-VmProperty -TargetVm $VmName -Name "cpus"
    )
    host_affinity_gate = if ($Mode -eq "EndpointHostAffinity") {
        [ordered]@{
            logical_processor_count = [Environment]::ProcessorCount
            performance_cpu_mask_decimal = $PerformanceCpuMask
            performance_cpu_mask_hex = "0x{0:X}" -f $PerformanceCpuMask
            priority_change_requested = $false
            administrative_elevation_requested = $false
        }
    } else {
        $null
    }
    host_address_from_nat_guest = "10.0.2.2"
    private_pcm = if ($UsesPrivatePcm) {
        [ordered]@{
            bytes = (Get-Item -LiteralPath $PcmFile).Length
            sha256 = (Get-FileHash -LiteralPath $PcmFile -Algorithm SHA256).Hash
            copied_to_guest = $false
        }
    } else {
        $null
    }
    files = @(
        foreach ($path in $manifestFiles) {
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
    "ptc3527-host-paced-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
$activeServer = $null
$vmFrontendProcess = $null
$originalVmAffinity = $null
$originalVmPriority = $null
$succeeded = $false
$failureMessage = $null

try {
    [IO.File]::WriteAllText(
        $passwordFile,
        (Get-LabPassword),
        [Text.UTF8Encoding]::new($false)
    )
    Invoke-VBox startvm $VmName --type gui | Out-Null
    Wait-VmState -Expected "running"
    Wait-GuestAdditions
    if ($Mode -eq "EndpointHostAffinity") {
        $vmFrontendProcess = Get-VmFrontendProcess -VmUuid (
            Get-VmProperty -TargetVm $VmName -Name "UUID"
        )
        $vmFrontendProcess.Refresh()
        $originalVmAffinity = [UInt64](
            $vmFrontendProcess.ProcessorAffinity.ToInt64()
        )
        $originalVmPriority = $vmFrontendProcess.PriorityClass.ToString()
        if (
            ($PerformanceCpuMask -band $originalVmAffinity) -ne
            $PerformanceCpuMask
        ) {
            throw (
                "PerformanceCpuMask is not a subset of the VirtualBoxVM " +
                "original affinity."
            )
        }
    }

    Invoke-Guest -PasswordFile $passwordFile -Command @"
if (Test-Path -LiteralPath '$GuestRoot') {
    Remove-Item -LiteralPath '$GuestRoot' -Recurse -Force
}
New-Item -ItemType Directory -Force -Path '$GuestRoot' | Out-Null
"@ | Out-Null
    foreach ($source in $deploymentFiles + @($ManifestPath)) {
        Copy-ToGuest -PasswordFile $passwordFile -Source $source
    }
    Invoke-Guest -PasswordFile $passwordFile -Command (
        "Expand-Archive -LiteralPath " +
        "'$GuestRoot\$(Split-Path -Leaf $Bundle)' " +
        "-DestinationPath '$GuestApp'"
    ) | Out-Null

    for ($index = 0; $index -lt $Scenarios.Count; $index++) {
        $scenario = $Scenarios[$index]
        $writerScheduling = if ($scenario.Contains("WriterScheduling")) {
            [string]$scenario.WriterScheduling
        } else {
            "normal"
        }
        $hostVmPriority = if ($scenario.Contains("HostVmPriority")) {
            [string]$scenario.HostVmPriority
        } else {
            "Normal"
        }
        $hostVmAffinity = if ($scenario.Contains("HostVmAffinity")) {
            [string]$scenario.HostVmAffinity
        } else {
            "unchanged"
        }
        $effectiveVmAffinity = $null
        if ($Mode -eq "EndpointHostAffinity") {
            $requestedVmAffinity = if ($hostVmAffinity -eq "performance") {
                $PerformanceCpuMask
            } else {
                $originalVmAffinity
            }
            $effectiveVmAffinity = Set-VmFrontendAffinity `
                -Process $vmFrontendProcess `
                -Mask $requestedVmAffinity `
                -ExpectedPriority $originalVmPriority
        }
        $pollWaitStrategy = if ($scenario.Contains("PollWaitStrategy")) {
            [string]$scenario.PollWaitStrategy
        } else {
            "sleep"
        }
        $capturePollWaitStrategy = if (
            $scenario.Contains("CapturePollWaitStrategy")
        ) {
            [string]$scenario.CapturePollWaitStrategy
        } else {
            "sleep"
        }
        $captureStartBarrier = (
            $scenario.Contains("CaptureStartBarrier") -and
            [bool]$scenario.CaptureStartBarrier
        )
        $sendLeadMs = if ($scenario.Contains("SendLeadMs")) {
            [int]$scenario.SendLeadMs
        } else {
            0
        }
        $startDelayMs = if ($scenario.Contains("StartDelayMs")) {
            [int]$scenario.StartDelayMs
        } else {
            250
        }
        $initialBurstBlocks = if ($scenario.Contains("InitialBurstBlocks")) {
            [int]$scenario.InitialBurstBlocks
        } else {
            0
        }
        $comparisonGroup = if ($scenario.Contains("ComparisonGroup")) {
            [string]$scenario.ComparisonGroup
        } elseif (
            $writerScheduling -eq "mmcss" -or
            $pollWaitStrategy -eq "yield"
        ) {
            "mitigated"
        } else {
            "baseline"
        }
        $port = $BasePort + $index
        $scenarioRoot = Join-Path $RunResult $scenario.Name
        $guestScenario = "$GuestRoot\$($scenario.Name)"
        New-Item -ItemType Directory -Force -Path $scenarioRoot | Out-Null
        [ordered]@{
            writer_scheduling = $writerScheduling
            poll_wait_strategy = $pollWaitStrategy
            capture_poll_wait_strategy = $capturePollWaitStrategy
            capture_start_barrier = $captureStartBarrier
            send_lead_ms = $sendLeadMs
            start_delay_ms = $startDelayMs
            initial_burst_blocks = $initialBurstBlocks
            comparison_group = $comparisonGroup
            host_vm_priority = $hostVmPriority
            host_vm_priority_effective = if (
                $Mode -eq "EndpointHostAffinity"
            ) {
                $vmFrontendProcess.PriorityClass.ToString()
            } else {
                $null
            }
            host_vm_affinity = $hostVmAffinity
            host_vm_affinity_mask_decimal = $effectiveVmAffinity
            host_vm_affinity_mask_hex = if ($null -ne $effectiveVmAffinity) {
                "0x{0:X}" -f $effectiveVmAffinity
            } else {
                $null
            }
            target_driver_depth = 2
            user_queue_blocks = 4
            poll_interval_ms = 2
        } | ConvertTo-Json |
            Set-Content `
                -LiteralPath (Join-Path $scenarioRoot "scenario_config.json") `
                -Encoding UTF8
        Invoke-Guest -PasswordFile $passwordFile -Command (
            "New-Item -ItemType Directory -Force -Path " +
            "'$guestScenario' | Out-Null"
        ) | Out-Null

        $scenarioSucceeded = $false
        for ($attempt = 1; $attempt -le 2; $attempt++) {
            $attemptRoot = Join-Path $scenarioRoot "attempt-$attempt"
            $guestAttempt = "$guestScenario\attempt-$attempt"
            $privateAttempt = if ($EndpointMode) {
                Join-Path (
                    Join-Path $PrivateRunResult $scenario.Name
                ) "attempt-$attempt"
            } else {
                $null
            }
            New-Item -ItemType Directory -Force -Path $attemptRoot | Out-Null
            if ($null -ne $privateAttempt) {
                New-Item `
                    -ItemType Directory `
                    -Force `
                    -Path $privateAttempt |
                    Out-Null
            }
            Invoke-Guest -PasswordFile $passwordFile -Command (
                "New-Item -ItemType Directory -Force -Path " +
                "'$guestAttempt' | Out-Null"
            ) | Out-Null
            try {
                $activeServer = Start-StreamServer `
                    -ScenarioRoot $attemptRoot `
                    -Port $port `
                    -Variant $scenario.Variant `
                    -StartDelayMs $startDelayMs `
                    -InitialBurstBlocks $initialBurstBlocks `
                    -SendLeadMs $sendLeadMs `
                    -InputPcm $PcmFile
                Start-Sleep -Milliseconds 750
                if ($activeServer.HasExited) {
                    throw (
                        "Host stream server exited before guest connection " +
                        "in $($scenario.Name), attempt $attempt."
                    )
                }
                $prefixBlocks = [Math]::Min(
                    500,
                    $EffectiveDurationSeconds * 25
                )
                $guestCommand = if ($EndpointMode) {
                    $captureBarrierArgument = if ($captureStartBarrier) {
                        " -CaptureStartBarrier"
                    } else {
                        ""
                    }
                    (
                        "& '$GuestEndpointScript' " +
                        "-Root '$GuestRoot' " +
                        "-ScenarioRoot '$guestAttempt' " +
                        "-Method '$($scenario.Method)' " +
                        "-Port $port " +
                        "-DurationSeconds " +
                        "$([Math]::Ceiling($EffectiveDurationSeconds)) " +
                        "-WriterScheduling '$writerScheduling' " +
                        "-PollWaitStrategy '$pollWaitStrategy' " +
                        "-CapturePollWaitStrategy " +
                        "'$capturePollWaitStrategy'" +
                        $captureBarrierArgument
                    )
                } else {
                    (
                        "`$env:PYTHONPATH='$GuestApp'; " +
                        "`$env:PTC3527_RNNOISE_DLL='$GuestDll'; " +
                        "& python '$GuestProbe' client --host 10.0.2.2 " +
                        "--port $port --method '$($scenario.Method)' " +
                        "--prefix-blocks $prefixBlocks " +
                        "--output '$guestAttempt\client.json' " +
                        "--trace '$guestAttempt\client_trace.json'; " +
                        "if (`$LASTEXITCODE -ne 0) { " +
                        "throw 'Guest PCM client failed with exit code ' + " +
                        "`$LASTEXITCODE }"
                    )
                }
                Invoke-Guest `
                    -PasswordFile $passwordFile `
                    -Command $guestCommand `
                    -TimeoutMilliseconds (
                        ([Math]::Ceiling($EffectiveDurationSeconds) + 180) *
                        1000
                    ) |
                    Set-Content -LiteralPath (
                        Join-Path $attemptRoot "client.stdout.txt"
                    ) -Encoding UTF8

                if (
                    -not $activeServer.WaitForExit(
                        ([Math]::Ceiling($EffectiveDurationSeconds) + 60) *
                        1000
                    )
                ) {
                    Stop-Process -Id $activeServer.Id -Force
                    throw (
                        "Host stream server timed out in " +
                        "$($scenario.Name), attempt $attempt."
                    )
                }
                $activeServer.WaitForExit()
                $serverResultPath = Join-Path $attemptRoot "server.json"
                if (
                    -not (
                        Test-Path `
                            -LiteralPath $serverResultPath `
                            -PathType Leaf
                    )
                ) {
                    throw (
                        "Host stream server did not produce a result in " +
                        "$($scenario.Name), attempt $attempt."
                    )
                }
                $serverResult = Get-Content `
                    -LiteralPath $serverResultPath `
                    -Raw |
                    ConvertFrom-Json
                if ($serverResult.status -ne "completed") {
                    throw (
                        "Host stream server failed in " +
                        "$($scenario.Name), attempt $attempt."
                    )
                }
                $activeServer = $null
                if ($EndpointMode) {
                    Copy-FromGuest `
                        -PasswordFile $passwordFile `
                        -Source "$guestAttempt\endpoint_results.zip" `
                        -Destination $privateAttempt
                    $endpointArchive = Join-Path `
                        $privateAttempt `
                        "endpoint_results.zip"
                    Expand-Archive `
                        -LiteralPath $endpointArchive `
                        -DestinationPath $privateAttempt
                    foreach ($name in @(
                        "client.json",
                        "client_trace.json"
                    )) {
                        Copy-Item `
                            -LiteralPath (Join-Path $privateAttempt $name) `
                            -Destination (Join-Path $attemptRoot $name)
                    }
                    $privateScenario = Join-Path `
                        $PrivateRunResult `
                        $scenario.Name
                    New-Item `
                        -ItemType Directory `
                        -Force `
                        -Path $privateScenario |
                        Out-Null
                    foreach ($file in Get-ChildItem `
                        -LiteralPath $privateAttempt `
                        -File) {
                        if ($file.Name -ne "endpoint_results.zip") {
                            Copy-Item `
                                -LiteralPath $file.FullName `
                                -Destination (
                                    Join-Path $privateScenario $file.Name
                                ) `
                                -Force
                        }
                    }
                } else {
                    Copy-FromGuest `
                        -PasswordFile $passwordFile `
                        -Source "$guestAttempt\client.json" `
                        -Destination $attemptRoot
                    Copy-FromGuest `
                        -PasswordFile $passwordFile `
                        -Source "$guestAttempt\client_trace.json" `
                        -Destination $attemptRoot
                }
                foreach ($name in @(
                    "server.json",
                    "server_trace.json",
                    "server.stdout.txt",
                    "server.stderr.txt",
                    "client.json",
                    "client_trace.json",
                    "client.stdout.txt"
                )) {
                    $sourcePath = Join-Path $attemptRoot $name
                    if (Test-Path -LiteralPath $sourcePath -PathType Leaf) {
                        Copy-Item `
                            -LiteralPath $sourcePath `
                            -Destination (Join-Path $scenarioRoot $name) `
                            -Force
                    }
                }
                $scenarioSucceeded = $true
                break
            } catch {
                $attemptFailure = $_.Exception.Message
                if ($null -ne $activeServer -and -not $activeServer.HasExited) {
                    Stop-Process -Id $activeServer.Id -Force
                }
                $activeServer = $null
                $attemptFailure |
                    Set-Content `
                        -LiteralPath (
                            Join-Path $attemptRoot "automation_failure.txt"
                        ) `
                        -Encoding UTF8
                $oldPreference = $ErrorActionPreference
                $ErrorActionPreference = "Continue"
                @(
                    & $VBox guestcontrol $VmName list sessions 2>&1
                ) | Set-Content `
                    -LiteralPath (
                        Join-Path $attemptRoot "guest_sessions.txt"
                    ) `
                    -Encoding UTF8
                @(
                    & $VBox guestcontrol $VmName list processes 2>&1
                ) | Set-Content `
                    -LiteralPath (
                        Join-Path $attemptRoot "guest_processes.txt"
                    ) `
                    -Encoding UTF8
                & $VBox guestcontrol $VmName closesession --all 2>&1 |
                    Set-Content `
                        -LiteralPath (
                            Join-Path $attemptRoot "close_sessions.txt"
                        ) `
                        -Encoding UTF8
                $ErrorActionPreference = $oldPreference
                if ($attempt -ge 2) {
                    throw
                }
                Start-Sleep -Seconds 10
                Wait-GuestAdditions
                try {
                    Invoke-Guest `
                        -PasswordFile $passwordFile `
                        -Command "'guest-control-recovery-ok'" `
                        -TimeoutMilliseconds 120000 |
                        Set-Content `
                            -LiteralPath (
                                Join-Path $attemptRoot "recovery_probe.txt"
                            ) `
                            -Encoding UTF8
                } catch {
                    throw (
                        "Scenario recovery failed after: $attemptFailure; " +
                        $_.Exception.Message
                    )
                }
                Start-Sleep -Seconds 2
            }
        }
        if (-not $scenarioSucceeded) {
            throw "Scenario did not complete: $($scenario.Name)."
        }
    }

    if (
        $Mode -notin @(
            "EndpointDiagnostic",
            "EndpointScheduling",
            "EndpointTimer",
            "EndpointPrefill",
            "EndpointCaptureTimer",
            "EndpointStartBarrier",
            "EndpointSendLead",
            "EndpointHostAffinity",
            "EndpointCaptureTiming",
            "EndpointCaptureSpin",
            "EndpointCaptureEvent"
        )
    ) {
        $analysisMode = if ($Mode -ne "Synthetic") {
            "physical"
        } else {
            "synthetic"
        }
        & $Python $Analyzer `
            --root $RunResult `
            --output $GatePath `
            --mode $analysisMode
        if ($LASTEXITCODE -ne 0) {
            throw "The host-paced PCM matrix failed its acceptance gate."
        }
    }
    if ($Mode -eq "EndpointPair") {
        & $Python $EndpointAnalyzer `
            --private-root $PrivateRunResult `
            --output $EndpointGatePath `
            --prepare-blind
        if ($LASTEXITCODE -ne 0) {
            throw "The host-paced endpoint pair failed its acceptance gate."
        }
    } elseif ($Mode -eq "EndpointDiagnostic") {
        & $Python $EndpointDiagnosticAnalyzer `
            --private-root $PrivateRunResult `
            --output $EndpointGatePath
        if ($LASTEXITCODE -ne 0) {
            throw "The endpoint diagnostic did not produce complete evidence."
        }
    } elseif ($Mode -eq "EndpointCaptureTiming") {
        & $Python $CaptureTimingAnalyzer `
            --private-root $PrivateRunResult `
            --output $EndpointGatePath
        if ($LASTEXITCODE -ne 0) {
            throw "The capture timing diagnostic did not produce complete evidence."
        }
    } elseif ($Mode -eq "EndpointCaptureSpin") {
        & $Python $CaptureSpinAnalyzer `
            --run-root $RunResult `
            --private-root $PrivateRunResult `
            --output $EndpointGatePath
        if ($LASTEXITCODE -ne 0) {
            throw "The capture spin gate did not produce complete evidence."
        }
    } elseif ($Mode -eq "EndpointCaptureEvent") {
        & $Python $CaptureEventAnalyzer `
            --run-root $RunResult `
            --private-root $PrivateRunResult `
            --output $EndpointGatePath
        if ($LASTEXITCODE -ne 0) {
            throw "The capture event gate did not produce complete evidence."
        }
    } elseif (
        $Mode -in @(
            "EndpointScheduling",
            "EndpointTimer",
            "EndpointPrefill",
            "EndpointCaptureTimer",
            "EndpointStartBarrier",
            "EndpointSendLead",
            "EndpointHostAffinity"
        )
    ) {
        & $Python $EndpointSchedulingAnalyzer `
            --run-root $RunResult `
            --private-root $PrivateRunResult `
            --output $EndpointGatePath
        if ($LASTEXITCODE -ne 0) {
            throw "The scheduling diagnostic did not produce complete evidence."
        }
    }
    $succeeded = $true
} catch {
    $failureMessage = $_.Exception.Message
} finally {
    if ($null -ne $activeServer -and -not $activeServer.HasExited) {
        Stop-Process -Id $activeServer.Id -Force
    }
    if (
        $null -ne $vmFrontendProcess -and
        $null -ne $originalVmAffinity
    ) {
        try {
            if (-not $vmFrontendProcess.HasExited) {
                Set-VmFrontendAffinity `
                    -Process $vmFrontendProcess `
                    -Mask $originalVmAffinity `
                    -ExpectedPriority $originalVmPriority |
                    Out-Null
            }
        } catch {
            if ($null -eq $failureMessage) {
                $failureMessage = (
                    "Failed to restore VirtualBoxVM affinity: " +
                    $_.Exception.Message
                )
            }
            $succeeded = $false
        }
    }
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
    succeeded = $succeeded
    failure = $failureMessage
    audio_saved = $EndpointMode -or $Mode -eq "PhysicalPair"
    audio_location = if ($EndpointMode) {
        "private_host_endpoint_pair"
    } elseif ($Mode -eq "PhysicalPair") {
        "private_host_only"
    } else {
        "none"
    }
    pipeline_modified = $false
    bridge_exercised = $EndpointMode
    clone = [ordered]@{
        state = Get-VmProperty -TargetVm $VmName -Name "VMState"
        snapshot = Get-VmProperty -TargetVm $VmName -Name "CurrentSnapshotName"
        audio_in = Get-VmProperty -TargetVm $VmName -Name "audio_in"
        clipboard = Get-VmProperty -TargetVm $VmName -Name "clipboard"
        nic1 = Get-VmProperty -TargetVm $VmName -Name "nic1"
    }
    original_vm = Compare-OriginalVmExternalAudit `
        -Before $originalAuditBefore `
        -After $originalAuditAfter
    host_default_capture_unchanged = $hostDefaultBefore -eq $hostDefaultAfter
} | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath (Join-Path $RunResult "host_result.json") `
        -Encoding UTF8

if (-not $succeeded) {
    throw "Host-paced PCM VM audit failed: $failureMessage"
}
