[CmdletBinding()]
param(
    [string]$Root = "C:\PTC3527\input_cadence_audit",
    [int]$DurationSeconds = 20,
    [ValidateSet("backend", "workload")]
    [string]$Mode = "backend"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
$Probe = Join-Path $Root "probe_input_cadence.py"
$ManifestPath = Join-Path $Root "deployment_manifest.json"
$ResultRoot = Join-Path $Root "results"
$LogRoot = Join-Path $Root "logs"
$Archive = Join-Path $Root "input_cadence_results.zip"
$Bundle = Join-Path $Root "input_cadence_app.zip"
$AppRoot = Join-Path $Root "app"
$Dll = Join-Path $Root "ptc3527-rnnoise-v0.2.dll"

New-Item -ItemType Directory -Force -Path $ResultRoot, $LogRoot | Out-Null

function Invoke-ProbeProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    $stdout = Join-Path $LogRoot "$Name.stdout.txt"
    $stderr = Join-Path $LogRoot "$Name.stderr.txt"
    $process = Start-Process `
        -FilePath $Python `
        -ArgumentList $Arguments `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        return 124
    }
    $process.Refresh()
    if ($null -eq $process.ExitCode) {
        return 0
    }
    return [int]$process.ExitCode
}

foreach ($path in @($Python, $Probe, $ManifestPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required file is missing: $path"
    }
}

$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
foreach ($entry in $manifest.files) {
    $path = Join-Path $Root ([string]$entry.name)
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($actual -ne [string]$entry.sha256) {
        throw "SHA-256 mismatch for $path."
    }
}
if ($Mode -eq "workload") {
    foreach ($path in @($Bundle, $Dll)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Workload artifact is missing: $path"
        }
    }
    Remove-Item -LiteralPath $AppRoot -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive -LiteralPath $Bundle -DestinationPath $AppRoot -Force
    $env:PYTHONPATH = $AppRoot
    $env:PTC3527_RNNOISE_DLL = $Dll
}

$enumerationPath = Join-Path $ResultRoot "input_enumeration.json"
$enumerationExit = Invoke-ProbeProcess `
    -Name "input_enumeration" `
    -Arguments @(
        $Probe,
        "--list-devices",
        "--sample-rate", "16000",
        "--block-size", "320",
        "--output", $enumerationPath
    ) `
    -TimeoutSeconds 30
if ($enumerationExit -ne 0) {
    throw "Input enumeration failed with exit code $enumerationExit."
}

$enumeration = Get-Content -LiteralPath $enumerationPath -Raw | ConvertFrom-Json
$apiNames = @("MME", "Windows DirectSound", "Windows WASAPI")
$selected = [ordered]@{}
foreach ($apiName in $apiNames) {
    $allApi = @(
        $enumeration.inputs | Where-Object {
            [string]$_.hostapi -eq $apiName -and
            (
                [bool]$_.supports_requested_format -or
                (
                    $apiName -eq "Windows WASAPI" -and
                    [bool]$_.supports_requested_format_with_wasapi_auto_convert
                )
            )
        }
    )
    $preferred = @(
        $allApi | Where-Object {
            ([string]$_.name -like "Microfone (High Definition Audi*") -or
            ([string]$_.name -like "Microphone (High Definition Audi*")
        }
    )
    $candidates = @(
        if ($preferred.Count -gt 0) {
            $preferred
        } else {
            $allApi | Where-Object {
                $name = ([string]$_.name).ToLowerInvariant()
                $name -notlike "*mapeador*" -and
                $name -notlike "*mapper*" -and
                $name -notlike "*primary*"
            }
        }
    )
    if ($candidates.Count -eq 1) {
        $selected[$apiName] = $candidates[0]
    } else {
        $selected[$apiName] = $null
    }
}

$scenarios = if ($Mode -eq "backend") {
    @(
        @{ name = "pair1_mme"; api = "MME"; method = "capture_only" },
        @{
            name = "pair1_directsound"
            api = "Windows DirectSound"
            method = "capture_only"
        },
        @{
            name = "pair1_wasapi"
            api = "Windows WASAPI"
            method = "capture_only"
        },
        @{
            name = "pair2_wasapi"
            api = "Windows WASAPI"
            method = "capture_only"
        },
        @{
            name = "pair2_directsound"
            api = "Windows DirectSound"
            method = "capture_only"
        },
        @{ name = "pair2_mme"; api = "MME"; method = "capture_only" }
    )
} else {
    @(
        @{ name = "mme_pair1_bypass"; api = "MME"; method = "bypass" },
        @{ name = "mme_pair1_rnnoise"; api = "MME"; method = "rnnoise" },
        @{ name = "mme_pair2_rnnoise"; api = "MME"; method = "rnnoise" },
        @{ name = "mme_pair2_bypass"; api = "MME"; method = "bypass" },
        @{
            name = "directsound_pair1_bypass"
            api = "Windows DirectSound"
            method = "bypass"
        },
        @{
            name = "directsound_pair1_rnnoise"
            api = "Windows DirectSound"
            method = "rnnoise"
        },
        @{
            name = "directsound_pair2_rnnoise"
            api = "Windows DirectSound"
            method = "rnnoise"
        },
        @{
            name = "directsound_pair2_bypass"
            api = "Windows DirectSound"
            method = "bypass"
        }
    )
}
$scenarioResults = [System.Collections.Generic.List[object]]::new()
foreach ($scenario in $scenarios) {
    $apiName = [string]$scenario.api
    $scenarioName = [string]$scenario.name
    $method = [string]$scenario.method
    $device = $selected[$apiName]
    if ($null -eq $device) {
        $scenarioResults.Add([ordered]@{
            name = $scenarioName
            hostapi = $apiName
            method = $method
            status = "not_selectable"
            exit_code = $null
        })
        continue
    }

    $scenarioRoot = Join-Path $ResultRoot $scenarioName
    New-Item -ItemType Directory -Force -Path $scenarioRoot | Out-Null
    $summaryPath = Join-Path $scenarioRoot "cadence.json"
    $csvPath = Join-Path $scenarioRoot "callbacks.csv"
    $probeArguments = @(
        $Probe,
        "--device", [string]$device.index,
        "--duration", [string]$DurationSeconds,
        "--sample-rate", "16000",
        "--block-size", "320",
        "--method", $method,
        "--output", $summaryPath,
        "--csv", $csvPath
    )
    $wasapiAutoConvert = (
        $apiName -eq "Windows WASAPI" -and
        -not [bool]$device.supports_requested_format -and
        [bool]$device.supports_requested_format_with_wasapi_auto_convert
    )
    if ($wasapiAutoConvert) {
        $probeArguments += "--wasapi-auto-convert"
    }
    $exitCode = Invoke-ProbeProcess `
        -Name $scenarioName `
        -Arguments $probeArguments `
        -TimeoutSeconds ($DurationSeconds + 45)
    $status = if (
        $exitCode -eq 0 -and
        (Test-Path -LiteralPath $summaryPath -PathType Leaf)
    ) {
        "completed"
    } else {
        "failed"
    }
    $scenarioResults.Add([ordered]@{
        name = $scenarioName
        hostapi = $apiName
        device_index = [int]$device.index
        device_name = [string]$device.name
        wasapi_auto_convert = $wasapiAutoConvert
        method = $method
        status = $status
        exit_code = $exitCode
    })
    Start-Sleep -Seconds 2
}

$completed = @($scenarioResults | Where-Object { $_.status -eq "completed" })
[ordered]@{
    timestamp = (Get-Date).ToString("o")
    duration_seconds = $DurationSeconds
    mode = $Mode
    sample_rate = 16000
    block_size = 320
    audio_saved = $false
    selected_devices = $selected
    scenarios = @($scenarioResults)
    completed_scenarios = $completed.Count
} | ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath (Join-Path $ResultRoot "matrix_manifest.json") `
        -Encoding UTF8

if ($completed.Count -eq 0) {
    throw "No cadence scenario completed."
}

Remove-Item -LiteralPath $Archive -Force -ErrorAction SilentlyContinue
Compress-Archive `
    -Path (Join-Path $ResultRoot "*"), (Join-Path $LogRoot "*") `
    -DestinationPath $Archive `
    -CompressionLevel Optimal
Write-Output "INPUT_CADENCE_AUDIT=OK"
