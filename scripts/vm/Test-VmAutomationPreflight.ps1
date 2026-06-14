[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB-FAST",
    [string]$OriginalVmName = "PTC3527-SYSVAD-LAB",
    [string]$ExpectedSnapshot = "checkpoint45-causal-wpt-validated",
    [string]$OrchestratorPath = "",
    [string]$RuntimeRoot = (
        Join-Path $env:LOCALAPPDATA "PTC3527-Private\vm_runtime"
    ),
    [switch]$AudioRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$checks = [Collections.Generic.List[object]]::new()
. (Join-Path $PSScriptRoot "VmSsdRuntime.ps1")

function Add-Check {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail,
        [ValidateSet("error", "warning", "info")]
        [string]$Severity = "error"
    )

    $checks.Add([ordered]@{
        name = $Name
        passed = $Passed
        severity = $Severity
        detail = $Detail
    })
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
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    throw (
        "VM property unavailable: $TargetVm / $Name; " +
        ($output -join [Environment]::NewLine)
    )
}

Add-Check `
    -Name "vboxmanage_exists" `
    -Passed (Test-Path -LiteralPath $vbox -PathType Leaf) `
    -Detail $vbox

$staleCredentialFiles = @(
    Get-ChildItem `
        -LiteralPath ([IO.Path]::GetTempPath()) `
        -File `
        -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match (
                '^ptc3527-(checkpoint\d+|rnnoise|cadence|host-paced|' +
                'vbox)-[0-9a-f]{32}\.txt$'
            )
        }
)
Add-Check `
    "no_stale_credential_files" `
    ($staleCredentialFiles.Count -eq 0) `
    $(if ($staleCredentialFiles.Count -eq 0) {
        "none"
    } else {
        ($staleCredentialFiles.FullName -join "; ")
    })

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
Add-Check `
    "python_available" `
    ($null -ne $pythonCommand) `
    $(if ($null -eq $pythonCommand) { "missing" } else {
        $pythonCommand.Source
    })
if ($null -ne $pythonCommand) {
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $pythonProbe = @(
        & $pythonCommand.Source -c (
            "import psutil,sys;" +
            "print(sys.executable);" +
            "print(sys.version.split()[0]);" +
            "print(psutil.__version__)"
        ) 2>&1
    )
    $pythonProbeExitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    Add-Check `
        "python_psutil_available" `
        ($pythonProbeExitCode -eq 0) `
        ($pythonProbe -join "; ")
}

if (Test-Path -LiteralPath $vbox -PathType Leaf) {
    try {
        $cloneState = Get-VmProperty -TargetVm $VmName -Name "VMState"
        Add-Check "clone_poweroff" ($cloneState -eq "poweroff") $cloneState

        $snapshot = Get-VmProperty `
            -TargetVm $VmName `
            -Name "CurrentSnapshotName"
        Add-Check `
            "approved_snapshot" `
            ($snapshot -eq $ExpectedSnapshot) `
            $snapshot

        $audioIn = Get-VmProperty -TargetVm $VmName -Name "audio_in"
        Add-Check "audio_input_on" ($audioIn -eq "on") $audioIn

        $clipboard = Get-VmProperty -TargetVm $VmName -Name "clipboard"
        Add-Check `
            "clipboard_disabled" `
            ($clipboard -eq "disabled") `
            $clipboard

        $dragAndDrop = Get-VmProperty -TargetVm $VmName -Name "draganddrop"
        Add-Check `
            "drag_and_drop_disabled" `
            ($dragAndDrop -eq "disabled") `
            $dragAndDrop

        $nic1 = Get-VmProperty -TargetVm $VmName -Name "nic1"
        Add-Check "nic1_nat" ($nic1 -eq "nat") $nic1

    } catch {
        Add-Check "virtualbox_state_query" $false $_.Exception.Message
    }
}

try {
    $vmRuntime = Get-VmSsdRuntime -RuntimeRoot $RuntimeRoot
    Add-Check "ssd_runtime_valid" $true $vmRuntime.ManifestPath
    $password = Get-LabPasswordFromRuntime -Runtime $vmRuntime
    Add-Check `
        "ssd_runtime_credential_readable" `
        (-not [string]::IsNullOrEmpty($password)) `
        "one unique credential value"
    $password = $null

    $externalAudit = Get-OriginalVmExternalAudit `
        -Runtime $vmRuntime `
        -VBoxPath $vbox `
        -OriginalVmName $OriginalVmName
    Add-Check `
        "external_original_vm_audit" `
        ([bool]$externalAudit.available) `
        $externalAudit.state `
        "info"
} catch {
    Add-Check "ssd_runtime_valid" $false $_.Exception.Message
}

$defaultTool = Join-Path $repoRoot (
    "resultados\sysvad_checkpoint33\SetDefaultCaptureEndpoint.exe"
)
if (Test-Path -LiteralPath $defaultTool -PathType Leaf) {
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $defaultLines = @(& $defaultTool --list 2>&1)
    $defaultExitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    $defaultCapture = $defaultLines |
        Where-Object { $_ -match "^default=1`t" } |
        Select-Object -First 1
    Add-Check `
        "host_default_capture_readable" `
        ($defaultExitCode -eq 0 -and $null -ne $defaultCapture) `
        $(if ($null -eq $defaultCapture) { "unavailable" } else {
            [string]$defaultCapture
        })
} else {
    Add-Check `
        "host_default_capture_tool" `
        $false `
        $defaultTool `
        "warning"
}

if (-not [string]::IsNullOrWhiteSpace($OrchestratorPath)) {
    $resolvedOrchestrator = if ([IO.Path]::IsPathRooted($OrchestratorPath)) {
        $OrchestratorPath
    } else {
        Join-Path $repoRoot $OrchestratorPath
    }
    $exists = Test-Path -LiteralPath $resolvedOrchestrator -PathType Leaf
    Add-Check "orchestrator_exists" $exists $resolvedOrchestrator
    if ($exists) {
        $tokens = $null
        $parseErrors = $null
        [Management.Automation.Language.Parser]::ParseFile(
            $resolvedOrchestrator,
            [ref]$tokens,
            [ref]$parseErrors
        ) | Out-Null
        $parseMessages = @($parseErrors | ForEach-Object {
            "$($_.Extent.StartLineNumber): $($_.Message)"
        })
        Add-Check `
            "orchestrator_parses" `
            ($parseMessages.Count -eq 0) `
            $(if ($parseMessages.Count -eq 0) {
                "no parse errors"
            } else {
                $parseMessages -join "; "
            })

        $source = Get-Content -LiteralPath $resolvedOrchestrator -Raw
        $reservedAssignment = [regex]::Match(
            $source,
            '(?im)^\s*\$(host|input|args|error|matches|pid|home)\s*='
        )
        Add-Check `
            "no_reserved_variable_assignment" `
            (-not $reservedAssignment.Success) `
            $(if ($reservedAssignment.Success) {
                $reservedAssignment.Value.Trim()
            } else {
                "none"
            })

        if ($source -match '(?i)guestcontrol.+\brun\b') {
            $literalSeparator = (
                $source -match
                '"--wait-stdout"\s*,\s*"--wait-stderr"\s*,\s*"--"'
            )
            Add-Check `
                "guestcontrol_literal_separator" `
                $literalSeparator `
                $(if ($literalSeparator) { "literal array element found" } else {
                    "approved separator pattern not found"
                })
        }

        if ($AudioRun) {
            $usesHeadless = $source -match '(?i)--type\s+headless'
            Add-Check `
                "audio_run_uses_gui" `
                (-not $usesHeadless) `
                $(if ($usesHeadless) {
                    "headless start found"
                } else {
                    "no headless start found"
                })
        }
    }
}

$failures = @($checks | Where-Object {
    -not $_.passed -and $_.severity -eq "error"
})
$warnings = @($checks | Where-Object {
    -not $_.passed -and $_.severity -eq "warning"
})
$result = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    read_only = $true
    ready = $failures.Count -eq 0
    failures = $failures.Count
    warnings = $warnings.Count
    checks = $checks
}
$result | ConvertTo-Json -Depth 6

if ($failures.Count -ne 0) {
    throw "VM automation preflight failed with $($failures.Count) error(s)."
}
