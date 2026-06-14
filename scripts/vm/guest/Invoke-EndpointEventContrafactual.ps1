[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$OutputRoot,
    [int]$DurationSeconds = 40
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$probe = Join-Path $Root "PtcEndpointEventProbe.exe"
$schedulerProbe = Join-Path $Root "guest_scheduler_probe.py"
$python = "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
$enumerationPath = Join-Path $OutputRoot "capture_endpoints.json"
$selectionPath = Join-Path $OutputRoot "endpoint_selection.json"

function ConvertTo-NormalizedEndpointText {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }
    $decomposed = $Value.Normalize(
        [Text.NormalizationForm]::FormD
    )
    $builder = [Text.StringBuilder]::new()
    foreach ($character in $decomposed.ToCharArray()) {
        if (
            [Globalization.CharUnicodeInfo]::GetUnicodeCategory($character) -ne
            [Globalization.UnicodeCategory]::NonSpacingMark
        ) {
            [void]$builder.Append($character)
        }
    }
    return $builder.ToString().Normalize(
        [Text.NormalizationForm]::FormC
    ).ToLowerInvariant()
}

foreach ($path in @($probe, $schedulerProbe, $python)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required contrafactual artifact is missing: $path"
    }
}
if ($DurationSeconds -lt 1 -or $DurationSeconds -gt 3600) {
    throw "DurationSeconds must be between 1 and 3600."
}

Remove-Item -LiteralPath $OutputRoot -Recurse -Force `
    -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

& $probe --list --output $enumerationPath
if ($LASTEXITCODE -ne 0) {
    throw "Endpoint enumeration failed with code $LASTEXITCODE."
}
$enumeration = Get-Content -LiteralPath $enumerationPath -Raw |
    ConvertFrom-Json
if ($enumeration.status -ne "completed") {
    throw "Endpoint enumeration JSON is not completed."
}

$active = @($enumeration.capture_endpoints | Where-Object {
    [int]$_.state -eq 1
})
$sysvadCandidates = @($active | Where-Object {
    $_.device_description -eq "External Microphone Headphone" -and
    $_.interface_friendly_name -eq "SYSVAD (with APO Extensions)"
})
$hdaNames = @(
    "high definition audio device",
    "dispositivo de audio de alta definicao"
)
$hdaCandidates = @($active | Where-Object {
    $interfaceName = ConvertTo-NormalizedEndpointText `
        ([string]$_.interface_friendly_name)
    $friendlyName = ConvertTo-NormalizedEndpointText `
        ([string]$_.friendly_name)
    $friendlyMatches = @($hdaNames | Where-Object {
        $friendlyName.EndsWith("($_)")
    })
    ($interfaceName -in $hdaNames) -or
        $friendlyMatches.Count -gt 0
})
if ($sysvadCandidates.Count -ne 1) {
    throw (
        "Expected one active SYSVAD endpoint with device description " +
        "'External Microphone Headphone' and interface " +
        "'SYSVAD (with APO Extensions)'; found " +
        "$($sysvadCandidates.Count). Enumeration was preserved."
    )
}
if ($hdaCandidates.Count -ne 1) {
    throw (
        "Expected one unambiguous active HDA capture endpoint after " +
        "enumeration; found $($hdaCandidates.Count). Enumeration was preserved."
    )
}
if ($sysvadCandidates[0].id -eq $hdaCandidates[0].id) {
    throw "SYSVAD and HDA resolved to the same endpoint ID."
}

$selection = [ordered]@{
    schema_version = 1
    status = "completed"
    selection_method = "enumerate_then_exact_id"
    sysvad = $sysvadCandidates[0]
    hda = $hdaCandidates[0]
}
$selection | ConvertTo-Json -Depth 6 |
    Set-Content -LiteralPath $selectionPath -Encoding UTF8

$scenarios = @(
    [ordered]@{
        Name = "01-sysvad-shared-event-a"
        Role = "sysvad"
        EndpointId = [string]$selection.sysvad.id
    },
    [ordered]@{
        Name = "02-hda-shared-event-a"
        Role = "hda"
        EndpointId = [string]$selection.hda.id
    },
    [ordered]@{
        Name = "03-hda-shared-event-b"
        Role = "hda"
        EndpointId = [string]$selection.hda.id
    },
    [ordered]@{
        Name = "04-sysvad-shared-event-b"
        Role = "sysvad"
        EndpointId = [string]$selection.sysvad.id
    }
)

$legFailures = [Collections.Generic.List[object]]::new()
foreach ($scenario in $scenarios) {
    $scenarioRoot = Join-Path $OutputRoot $scenario.Name
    New-Item -ItemType Directory -Force -Path $scenarioRoot | Out-Null
    $ready = Join-Path $scenarioRoot "scheduler.ready"
    $start = Join-Path $scenarioRoot "scheduler.start"
    $stop = Join-Path $scenarioRoot "scheduler.stop"
    $schedulerOutput = Join-Path $scenarioRoot "scheduler.json"
    $schedulerStdout = Join-Path $scenarioRoot "scheduler.stdout.txt"
    $schedulerStderr = Join-Path $scenarioRoot "scheduler.stderr.txt"
    $probeStdout = Join-Path $scenarioRoot "probe.stdout.txt"
    $probeStderr = Join-Path $scenarioRoot "probe.stderr.txt"
    $scheduler = $null
    $probeProcess = $null
    try {
        $scheduler = Start-Process `
            -FilePath $python `
            -ArgumentList @(
                $schedulerProbe,
                "--ready-file", $ready,
                "--start-file", $start,
                "--stop-file", $stop,
                "--output", $schedulerOutput,
                "--interval-ms", "2",
                "--max-duration", [string]($DurationSeconds + 10)
            ) `
            -WindowStyle Hidden `
            -RedirectStandardOutput $schedulerStdout `
            -RedirectStandardError $schedulerStderr `
            -PassThru
        $deadline = (Get-Date).AddSeconds(30)
        while (-not (Test-Path -LiteralPath $ready -PathType Leaf)) {
            if ($scheduler.HasExited) {
                throw "Scheduler probe exited before readiness."
            }
            if ((Get-Date) -ge $deadline) {
                throw "Scheduler probe readiness timed out."
            }
            Start-Sleep -Milliseconds 50
        }
        Set-Content -LiteralPath $start -Value "start" -Encoding ASCII
        $probeProcess = Start-Process `
            -FilePath $probe `
            -ArgumentList @(
                "--endpoint-id", $scenario.EndpointId,
                "--endpoint-role", $scenario.Role,
                "--duration", [string]$DurationSeconds,
                "--summary", (Join-Path $scenarioRoot "summary.json"),
                "--trace", (Join-Path $scenarioRoot "event_trace.csv"),
                "--event-timeout-ms", "1000"
            ) `
            -WindowStyle Hidden `
            -RedirectStandardOutput $probeStdout `
            -RedirectStandardError $probeStderr `
            -PassThru
        $probeProcess.Refresh()
        if ($probeProcess.HasExited) {
            $probeProcess.WaitForExit()
            throw (
                "Endpoint event probe exited before priority verification " +
                "in $($scenario.Name)."
            )
        }
        if ($probeProcess.PriorityClass.ToString() -ne "Normal") {
            throw (
                "Probe priority changed unexpectedly to " +
                "$($probeProcess.PriorityClass)."
            )
        }
        if (-not $probeProcess.WaitForExit(($DurationSeconds + 30) * 1000)) {
            Stop-Process -Id $probeProcess.Id -Force `
                -ErrorAction SilentlyContinue
            throw "Endpoint event probe timed out in $($scenario.Name)."
        }
        $probeProcess.WaitForExit()
        $probeProcess.Refresh()
        if (
            $null -ne $probeProcess.ExitCode -and
            $probeProcess.ExitCode -ne 0
        ) {
            throw (
                "Endpoint event probe failed in $($scenario.Name) with " +
                "code $($probeProcess.ExitCode)."
            )
        }
        Set-Content -LiteralPath $stop -Value "stop" -Encoding ASCII
        if (-not $scheduler.WaitForExit(15000)) {
            Stop-Process -Id $scheduler.Id -Force `
                -ErrorAction SilentlyContinue
            throw "Scheduler probe timed out in $($scenario.Name)."
        }
        $scheduler.WaitForExit()
        $scheduler.Refresh()
        if (
            $null -ne $scheduler.ExitCode -and
            $scheduler.ExitCode -ne 0
        ) {
            throw (
                "Scheduler probe failed in $($scenario.Name) with " +
                "code $($scheduler.ExitCode)."
            )
        }
    } catch {
        $legError = $_.Exception.Message
        if ($null -ne $probeProcess -and -not $probeProcess.HasExited) {
            Stop-Process -Id $probeProcess.Id -Force `
                -ErrorAction SilentlyContinue
        }
        $failure = [ordered]@{
            schema_version = 1
            status = "failed"
            scenario = $scenario.Name
            endpoint_role = $scenario.Role
            endpoint_id = $scenario.EndpointId
            reason = $legError
            audio_persisted = $false
        }
        $failure | ConvertTo-Json -Depth 4 |
            Set-Content `
                -LiteralPath (Join-Path $scenarioRoot "leg_failure.json") `
                -Encoding UTF8
        $legFailures.Add($failure)
    } finally {
        if ($null -ne $scheduler -and -not $scheduler.HasExited) {
            Set-Content -LiteralPath $stop -Value "stop" -Encoding ASCII `
                -ErrorAction SilentlyContinue
            if (-not $scheduler.WaitForExit(5000)) {
                Stop-Process -Id $scheduler.Id -Force `
                    -ErrorAction SilentlyContinue
            }
        }
    }
}

[ordered]@{
    schema_version = 1
    status = if ($legFailures.Count -eq 0) {
        "completed"
    } else {
        "completed_with_leg_failures"
    }
    audio_persisted = $false
    endpoint_selection = "exact_id_after_enumeration"
    scenario_order = @($scenarios | ForEach-Object { $_.Name })
    duration_seconds_per_leg = $DurationSeconds
    priority = "Normal"
    affinity = "unchanged"
    leg_failures = @($legFailures)
} | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath (Join-Path $OutputRoot "matrix.json") `
        -Encoding UTF8

Write-Output "ENDPOINT_EVENT_CONTRAFACTUAL=OK"
