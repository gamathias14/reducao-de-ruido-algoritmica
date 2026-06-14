param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("isolated", "transport", "acoustic")]
    [string]$Phase,

    [string]$Root = "C:\PTC3527\rnnoise_integration",
    [int]$IsolatedDurationSeconds = 60,
    [int]$TransportDurationSeconds = 30,
    [int]$AcousticDurationSeconds = 20
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
$Bundle = Join-Path $Root "rnnoise_vm_bundle.zip"
$AppRoot = Join-Path $Root "app"
$Dll = Join-Path $Root "ptc3527-rnnoise-v0.2.dll"
$CaptureExe = Join-Path $Root "PtcPcmCapture.exe"
$ManifestPath = Join-Path $Root "deployment_manifest.json"
$LogRoot = Join-Path $Root "logs"
$ResultRoot = Join-Path $Root "results"

New-Item -ItemType Directory -Force -Path $LogRoot, $ResultRoot | Out-Null

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Assert-Deployment {
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "Guest Python was not found: $Python"
    }

    $manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    foreach ($entry in $manifest.files) {
        $path = Join-Path $Root ([string]$entry.name)
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Deployment file is missing: $path"
        }
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        if ($actual -ne [string]$entry.sha256) {
            throw "SHA-256 mismatch for $path. Expected $($entry.sha256), got $actual."
        }
    }

    if (-not (Test-Path -LiteralPath $AppRoot -PathType Container)) {
        Expand-Archive -LiteralPath $Bundle -DestinationPath $AppRoot -Force
    }

    $env:PTC3527_RNNOISE_DLL = $Dll
}

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    $stdout = Join-Path $LogRoot "$Name.stdout.txt"
    $stderr = Join-Path $LogRoot "$Name.stderr.txt"
    Remove-Item -LiteralPath $stdout, $stderr -Force -ErrorAction SilentlyContinue

    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $AppRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -Wait `
        -PassThru

    $exitCode = $process.ExitCode
    if ($null -ne $exitCode -and $exitCode -ne 0) {
        $detail = if (Test-Path -LiteralPath $stderr) {
            Get-Content -LiteralPath $stderr -Raw
        } else {
            ""
        }
        throw "$Name failed with exit code $exitCode. $detail"
    }
}

function Get-InputDevice {
    $deviceJson = Join-Path $ResultRoot "input_devices.json"
    $listScript = @"
import json
import sounddevice as sd
devices = []
for index, device in enumerate(sd.query_devices()):
    devices.append({
        "index": index,
        "name": device["name"],
        "hostapi": sd.query_hostapis(device["hostapi"])["name"],
        "max_input_channels": int(device["max_input_channels"]),
        "default_samplerate": float(device["default_samplerate"]),
    })
with open(r"$deviceJson", "w", encoding="utf-8") as handle:
    json.dump(devices, handle, ensure_ascii=False, indent=2)
"@
    $listPath = Join-Path $Root "list_input_devices.py"
    Set-Content -LiteralPath $listPath -Value $listScript -Encoding UTF8
    Invoke-LoggedProcess `
        -Name "list_input_devices" `
        -FilePath $Python `
        -ArgumentList @($listPath) `
        -TimeoutSeconds 30

    $devices = Get-Content -LiteralPath $deviceJson -Raw | ConvertFrom-Json
    $candidates = @(
        $devices | Where-Object {
            $_.max_input_channels -gt 0 -and
            $_.hostapi -eq "MME" -and
            $_.name -like "Microfone (High Definition Audi*"
        }
    )
    if ($candidates.Count -ne 1) {
        $fallback = @(
            $devices | Where-Object {
                $_.max_input_channels -gt 0 -and $_.hostapi -eq "MME"
            }
        )
        if ($fallback.Count -ne 1) {
            throw "Expected exactly one usable guest MME input, found $($fallback.Count)."
        }
        return [int]$fallback[0].index
    }
    return [int]$candidates[0].index
}

function Get-SingleMetrics {
    param([Parameter(Mandatory = $true)][string]$Directory)

    $files = @(Get-ChildItem -LiteralPath $Directory -Filter "*_metrics.json" -File)
    if ($files.Count -ne 1) {
        throw "Expected one metrics JSON in $Directory, found $($files.Count)."
    }
    return Get-Content -LiteralPath $files[0].FullName -Raw | ConvertFrom-Json
}

function Test-CommonMetrics {
    param(
        [Parameter(Mandatory = $true)]$Metrics,
        [switch]$RequireZeroOverBudget
    )

    $reasons = [System.Collections.Generic.List[string]]::new()
    if ([string]$Metrics.config.method -ne "rnnoise") {
        $reasons.Add("method is not rnnoise")
    }
    if (
        $RequireZeroOverBudget -and
        [int]$Metrics.summary.blocks_over_budget -ne 0
    ) {
        $reasons.Add("blocks_over_budget is nonzero")
    }
    if ([double]$Metrics.summary.processing_p99_ms -ge 20.0) {
        $reasons.Add("processing_p99_ms is not below the 20 ms block budget")
    }
    if ($Metrics.PSObject.Properties.Name -contains "status_counts") {
        foreach ($property in $Metrics.status_counts.PSObject.Properties) {
            if ([int]$property.Value -ne 0) {
                $reasons.Add("status count $($property.Name) is nonzero")
            }
        }
    }
    return $reasons
}

function Invoke-IsolatedPhase {
    $phaseRoot = Join-Path $ResultRoot "isolated"
    Remove-Item -LiteralPath $phaseRoot -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $phaseRoot | Out-Null

    $selfTestRoot = Join-Path $phaseRoot "self_test"
    New-Item -ItemType Directory -Force -Path $selfTestRoot | Out-Null
    Invoke-LoggedProcess `
        -Name "isolated_self_test" `
        -FilePath $Python `
        -ArgumentList @(
            "-m", "realtime_audio.windows_realtime",
            "--self-test",
            "--method", "rnnoise",
            "--duration", [string]$IsolatedDurationSeconds,
            "--no-save",
            "--output-dir", $selfTestRoot
        ) `
        -TimeoutSeconds 120

    $inputDevice = Get-InputDevice
    $bypassRoot = Join-Path $phaseRoot "bypass_control"
    New-Item -ItemType Directory -Force -Path $bypassRoot | Out-Null
    Invoke-LoggedProcess `
        -Name "isolated_bypass_control" `
        -FilePath $Python `
        -ArgumentList @(
            "-m", "realtime_audio.windows_realtime",
            "--input-only",
            "--method", "bypass",
            "--duration", [string]$IsolatedDurationSeconds,
            "--input-device", [string]$inputDevice,
            "--no-save",
            "--output-dir", $bypassRoot
        ) `
        -TimeoutSeconds ($IsolatedDurationSeconds + 90)

    $inputOnlyRoot = Join-Path $phaseRoot "input_only"
    New-Item -ItemType Directory -Force -Path $inputOnlyRoot | Out-Null
    Invoke-LoggedProcess `
        -Name "isolated_input_only" `
        -FilePath $Python `
        -ArgumentList @(
            "-m", "realtime_audio.windows_realtime",
            "--input-only",
            "--method", "rnnoise",
            "--duration", [string]$IsolatedDurationSeconds,
            "--input-device", [string]$inputDevice,
            "--no-save",
            "--output-dir", $inputOnlyRoot
        ) `
        -TimeoutSeconds ($IsolatedDurationSeconds + 90)

    $selfMetrics = Get-SingleMetrics -Directory $selfTestRoot
    $bypassMetrics = Get-SingleMetrics -Directory $bypassRoot
    $inputMetrics = Get-SingleMetrics -Directory $inputOnlyRoot
    $reasons = [System.Collections.Generic.List[string]]::new()
    foreach ($reason in (
        Test-CommonMetrics -Metrics $selfMetrics -RequireZeroOverBudget
    )) {
        $reasons.Add("self_test: $reason")
    }
    foreach ($reason in (Test-CommonMetrics -Metrics $inputMetrics)) {
        $reasons.Add("input_only: $reason")
    }
    if (
        [int]$inputMetrics.summary.blocks_over_budget -gt
        [int]$bypassMetrics.summary.blocks_over_budget
    ) {
        $reasons.Add("input_only: more over-budget blocks than bypass control")
    }
    if (
        [double]$inputMetrics.summary.processing_worst_ms -gt
        [Math]::Max(
            25.0,
            [double]$bypassMetrics.summary.processing_worst_ms + 5.0
        )
    ) {
        $reasons.Add("input_only: worst case materially exceeds bypass control")
    }
    $minimumBlocks = [Math]::Floor($IsolatedDurationSeconds * 50 * 0.98)
    if ([int]$inputMetrics.summary.blocks -lt $minimumBlocks) {
        $reasons.Add("input_only: callback delivered fewer than 98% of expected blocks")
    }

    $latency = [double]$selfMetrics.algorithmic_latency_estimated_ms
    if ($latency -lt 20.0 -or $latency -gt 22.0) {
        $reasons.Add("algorithmic_latency_ms is outside [20, 22]")
    }

    $gate = [ordered]@{
        phase = "isolated"
        passed = ($reasons.Count -eq 0)
        reasons = @($reasons)
        input_device_index = $inputDevice
        self_test = [ordered]@{
            blocks = [int]$selfMetrics.summary.blocks
            mean_ms = [double]$selfMetrics.summary.processing_mean_ms
            p95_ms = [double]$selfMetrics.summary.processing_p95_ms
            p99_ms = [double]$selfMetrics.summary.processing_p99_ms
            worst_ms = [double]$selfMetrics.summary.processing_worst_ms
            blocks_over_budget = [int]$selfMetrics.summary.blocks_over_budget
            algorithmic_latency_ms = $latency
        }
        bypass_control = [ordered]@{
            blocks = [int]$bypassMetrics.summary.blocks
            mean_ms = [double]$bypassMetrics.summary.processing_mean_ms
            p95_ms = [double]$bypassMetrics.summary.processing_p95_ms
            p99_ms = [double]$bypassMetrics.summary.processing_p99_ms
            worst_ms = [double]$bypassMetrics.summary.processing_worst_ms
            blocks_over_budget = [int]$bypassMetrics.summary.blocks_over_budget
            status_counts = $bypassMetrics.status_counts
        }
        input_only = [ordered]@{
            blocks = [int]$inputMetrics.summary.blocks
            mean_ms = [double]$inputMetrics.summary.processing_mean_ms
            p95_ms = [double]$inputMetrics.summary.processing_p95_ms
            p99_ms = [double]$inputMetrics.summary.processing_p99_ms
            worst_ms = [double]$inputMetrics.summary.processing_worst_ms
            blocks_over_budget = [int]$inputMetrics.summary.blocks_over_budget
            status_counts = $inputMetrics.status_counts
        }
    }
    $gatePath = Join-Path $phaseRoot "isolated_gate.json"
    Write-JsonFile -Value $gate -Path $gatePath
}

function Invoke-BridgeScenario {
    param(
        [Parameter(Mandatory = $true)][string]$ScenarioName,
        [Parameter(Mandatory = $true)][ValidateSet("bypass", "rnnoise")][string]$Method,
        [Parameter(Mandatory = $true)][int]$InputDevice,
        [Parameter(Mandatory = $true)][bool]$DiagnosticSource,
        [Parameter(Mandatory = $true)][int]$DurationSeconds,
        [Parameter(Mandatory = $true)][string]$DestinationRoot
    )

    $scenarioRoot = Join-Path $DestinationRoot $ScenarioName
    New-Item -ItemType Directory -Force -Path $scenarioRoot | Out-Null
    $endpointWav = Join-Path $scenarioRoot "endpoint.wav"
    $captureTrace = Join-Path $scenarioRoot "capture_trace.csv"
    $captureStdout = Join-Path $LogRoot "$ScenarioName.capture.stdout.txt"
    $captureStderr = Join-Path $LogRoot "$ScenarioName.capture.stderr.txt"
    $captureArguments = @(
        "--output", $endpointWav,
        "--duration", [string]($DurationSeconds + 4),
        "--poll-ms", "2",
        "--trace", $captureTrace
    )
    $capture = Start-Process `
        -FilePath $CaptureExe `
        -ArgumentList $captureArguments `
        -WindowStyle Hidden `
        -RedirectStandardOutput $captureStdout `
        -RedirectStandardError $captureStderr `
        -PassThru

    Start-Sleep -Milliseconds 750
    try {
        $arguments = @(
            "-m", "realtime_audio.windows_realtime",
            "--virtual-mic",
            "--method", $Method,
            "--duration", [string]$DurationSeconds,
            "--input-device", [string]$InputDevice,
            "--bridge-target-depth", "2",
            "--bridge-user-queue", "4",
            "--bridge-poll-interval-ms", "2",
            "--diagnostic-trace",
            "--output-dir", $scenarioRoot
        )
        if ($DiagnosticSource) {
            $arguments += @(
                "--diagnostic-block-id-source",
                "--diagnostic-block-id-seed", "3527"
            )
        }
        Invoke-LoggedProcess `
            -Name $ScenarioName `
            -FilePath $Python `
            -ArgumentList $arguments `
            -TimeoutSeconds ($DurationSeconds + 90)
    } finally {
        if (-not $capture.HasExited) {
            if (-not $capture.WaitForExit(($DurationSeconds + 15) * 1000)) {
                Stop-Process -Id $capture.Id -Force -ErrorAction SilentlyContinue
                throw "Endpoint capture timed out for $ScenarioName."
            }
        }
        $capture.WaitForExit()
        $capture.Refresh()
    }
    if ($null -ne $capture.ExitCode -and $capture.ExitCode -ne 0) {
        $detail = if (Test-Path -LiteralPath $captureStderr) {
            Get-Content -LiteralPath $captureStderr -Raw
        } else {
            ""
        }
        throw "Endpoint capture failed for $ScenarioName with code $($capture.ExitCode). $detail"
    }
    if (
        -not (Test-Path -LiteralPath $endpointWav -PathType Leaf) -or
        (Get-Item -LiteralPath $endpointWav).Length -le 44
    ) {
        throw "Endpoint capture did not produce a usable WAV for $ScenarioName."
    }

    $metrics = Get-SingleMetrics -Directory $scenarioRoot
    if ([double]$metrics.summary.processing_p99_ms -ge 20.0) {
        throw "$ScenarioName processing p99 exceeded the 20 ms budget."
    }
    if ([int]$metrics.bridge.write_errors -ne 0) {
        throw "$ScenarioName reported bridge write errors."
    }
}

function Invoke-TransportPhase {
    $phaseRoot = Join-Path $ResultRoot "transport"
    Remove-Item -LiteralPath $phaseRoot -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $phaseRoot | Out-Null
    $inputDevice = Get-InputDevice

    $scenarios = @(
        @{ name = "pair1_bypass"; method = "bypass" },
        @{ name = "pair1_rnnoise"; method = "rnnoise" },
        @{ name = "pair2_rnnoise"; method = "rnnoise" },
        @{ name = "pair2_bypass"; method = "bypass" }
    )
    foreach ($scenario in $scenarios) {
        Invoke-BridgeScenario `
            -ScenarioName $scenario.name `
            -Method $scenario.method `
            -InputDevice $inputDevice `
            -DiagnosticSource $true `
            -DurationSeconds $TransportDurationSeconds `
            -DestinationRoot $phaseRoot
    }

    Write-JsonFile -Value ([ordered]@{
        phase = "transport"
        input_device_index = $inputDevice
        duration_seconds = $TransportDurationSeconds
        scenarios = $scenarios
    }) -Path (Join-Path $phaseRoot "transport_manifest.json")
}

function Invoke-AcousticPhase {
    $phaseRoot = Join-Path $ResultRoot "acoustic"
    Remove-Item -LiteralPath $phaseRoot -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $phaseRoot | Out-Null
    $inputDevice = Get-InputDevice
    Invoke-BridgeScenario `
        -ScenarioName "bypass_physical_input" `
        -Method "bypass" `
        -InputDevice $inputDevice `
        -DiagnosticSource $false `
        -DurationSeconds $AcousticDurationSeconds `
        -DestinationRoot $phaseRoot
    Invoke-BridgeScenario `
        -ScenarioName "rnnoise_physical_input" `
        -Method "rnnoise" `
        -InputDevice $inputDevice `
        -DiagnosticSource $false `
        -DurationSeconds $AcousticDurationSeconds `
        -DestinationRoot $phaseRoot
}

Assert-Deployment
switch ($Phase) {
    "isolated" {
        Invoke-IsolatedPhase
        $phasePath = Join-Path $ResultRoot "isolated"
    }
    "transport" {
        Invoke-TransportPhase
        $phasePath = Join-Path $ResultRoot "transport"
    }
    "acoustic" {
        Invoke-AcousticPhase
        $phasePath = Join-Path $ResultRoot "acoustic"
    }
}

$archivePath = Join-Path $Root "rnnoise_${Phase}_results.zip"
Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $phasePath, $LogRoot -DestinationPath $archivePath -CompressionLevel Optimal
Write-Output "RNNoise integration phase completed: $Phase"
