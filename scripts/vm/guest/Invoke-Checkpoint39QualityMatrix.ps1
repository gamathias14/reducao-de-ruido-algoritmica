[CmdletBinding()]
param(
    [string]$Root = "C:\PTC3527\checkpoint39"
)

$ErrorActionPreference = "Stop"
$python = "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
$bundle = Join-Path $Root "checkpoint39_python_bundle.zip"
$capture = Join-Path $Root "PtcPcmCapture.exe"
$hashManifest = Join-Path $Root "checkpoint39_expected_hashes.json"
$app = Join-Path $Root "app"
$results = Join-Path $Root "results"
$archive = Join-Path $Root "checkpoint39_vm_results.zip"
$partialArchive = Join-Path $Root "checkpoint39_vm_partial.zip"
$statusPath = Join-Path $Root "matrix_status.json"
$vboxControl = (
    "C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxGuest\VBoxControl.exe"
)
$statusKey = "/PTC3527/Checkpoint39/Status"

function Set-CheckpointStatus {
    param([string]$State, [string]$Scenario = "")

    $payload = [ordered]@{
        timestamp = (Get-Date).ToString("o")
        state = $State
        scenario = $Scenario
    }
    $temporary = "$statusPath.tmp"
    $payload | ConvertTo-Json |
        Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $statusPath -Force
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $vboxControl guestproperty set $statusKey $State 2>$null | Out-Null
    $ErrorActionPreference = $oldPreference
}

function Find-InputDevice {
    $probe = @'
import json
import sounddevice as sd

devices = sd.query_devices()
hostapis = sd.query_hostapis()
rows = []
for index, device in enumerate(devices):
    if int(device["max_input_channels"]) <= 0:
        continue
    rows.append({
        "index": index,
        "name": str(device["name"]),
        "host_api": str(hostapis[int(device["hostapi"])]["name"]),
    })
candidates = [
    row for row in rows
    if row["host_api"] == "MME"
    and row["name"].startswith("Microfone (High Definition Audi")
]
if len(candidates) != 1:
    raise SystemExit(f"entrada MME ambigua: {candidates!r}; todas={rows!r}")
print(json.dumps({"selected": candidates[0], "inputs": rows}, ensure_ascii=False))
'@
    $probePath = Join-Path $Root "enumerate_checkpoint39_inputs.py"
    [IO.File]::WriteAllText(
        $probePath,
        $probe,
        [Text.UTF8Encoding]::new($false)
    )
    Push-Location $app
    try {
        $output = @(& $python $probePath 2>&1)
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($exitCode -ne 0) {
        throw "Falha ao enumerar entrada: $($output -join ' ')"
    }
    $json = $output[-1]
    [IO.File]::WriteAllText(
        (Join-Path $results "guest_input_devices.json"),
        $json,
        [Text.UTF8Encoding]::new($false)
    )
    return (($json | ConvertFrom-Json).selected.index).ToString()
}

function Invoke-Scenario {
    param(
        [string]$Name,
        [string]$Method,
        [string]$InputDevice
    )

    Set-CheckpointStatus -State "running" -Scenario $Name
    $directory = Join-Path $results $Name
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $progress = Join-Path $directory "progress.json"
    $endpoint = Join-Path $directory "endpoint.wav"
    $trace = Join-Path $directory "capture_trace.csv"
    $captureOut = Join-Path $directory "capture.stdout.txt"
    $captureErr = Join-Path $directory "capture.stderr.txt"
    $producerOut = Join-Path $directory "producer.stdout.txt"
    $producerErr = Join-Path $directory "producer.stderr.txt"

    $captureProcess = Start-Process -FilePath $capture -ArgumentList @(
        "--duration", "34",
        "--output", $endpoint,
        "--poll-ms", "2",
        "--trace", $trace
    ) -RedirectStandardOutput $captureOut `
      -RedirectStandardError $captureErr -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2

    $arguments = @(
        "-m", "realtime_audio.windows_realtime",
        "--duration", "30",
        "--method", $Method,
        "--noise-mode", "adaptive",
        "--block-ms", "20",
        "--input-device", $InputDevice,
        "--output-dir", $directory,
        "--progress-file", $progress,
        "--virtual-mic",
        "--bridge-target-depth", "2",
        "--bridge-user-queue", "4",
        "--bridge-poll-interval-ms", "2",
        "--diagnostic-trace"
    )
    Push-Location $app
    try {
        $producer = Start-Process -FilePath $python -ArgumentList $arguments `
            -RedirectStandardOutput $producerOut `
            -RedirectStandardError $producerErr -WindowStyle Hidden -PassThru
        if (-not $producer.WaitForExit(75000)) {
            Stop-Process -Id $producer.Id -Force -ErrorAction SilentlyContinue
            throw "Watchdog encerrou o produtor $Name."
        }
        $producer.Refresh()
        if ($null -ne $producer.ExitCode -and $producer.ExitCode -ne 0) {
            throw "Produtor $Name falhou com codigo $($producer.ExitCode)."
        }
    } finally {
        Pop-Location
    }

    if (-not $captureProcess.WaitForExit(50000)) {
        Stop-Process -Id $captureProcess.Id -Force -ErrorAction SilentlyContinue
        throw "Watchdog encerrou o capturador $Name."
    }
    $captureProcess.Refresh()
    if (
        $null -ne $captureProcess.ExitCode -and
        $captureProcess.ExitCode -ne 0
    ) {
        throw "Capturador $Name falhou com codigo $($captureProcess.ExitCode)."
    }
    if ((Get-Item -LiteralPath $endpoint).Length -le 44) {
        throw "Endpoint vazio em $Name."
    }
    $captureError = [string](Get-Content -Raw -LiteralPath $captureErr)
    if (-not [string]::IsNullOrWhiteSpace($captureError)) {
        throw "Erro do capturador em $Name`: $captureError"
    }
    $metrics = @(Get-ChildItem -LiteralPath $directory -Filter "*_metrics.json")
    $inputWavs = @(Get-ChildItem -LiteralPath $directory -Filter "*_input.wav")
    $outputWavs = @(Get-ChildItem -LiteralPath $directory -Filter "*_output.wav")
    if ($metrics.Count -ne 1 -or $inputWavs.Count -ne 1 -or $outputWavs.Count -ne 1) {
        throw "Artefatos internos incompletos em $Name."
    }
}

foreach ($path in @($python, $bundle, $capture, $hashManifest)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Artefato ausente: $path"
    }
}
if (Get-Process python*, PtcPcmCapture -ErrorAction SilentlyContinue) {
    throw "Processo de audio residual encontrado antes da matriz."
}
if (Test-Path -LiteralPath $results) {
    Remove-Item -LiteralPath $results -Recurse -Force
}
if (Test-Path -LiteralPath $app) {
    Remove-Item -LiteralPath $app -Recurse -Force
}
foreach ($path in @($archive, $partialArchive, $statusPath)) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}
New-Item -ItemType Directory -Force -Path $results | Out-Null

try {
    Set-CheckpointStatus -State "preparing"
    $expected = Get-Content -Raw -LiteralPath $hashManifest | ConvertFrom-Json
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $bundle).Hash -ne $expected.bundle_sha256) {
        throw "Hash do bundle divergiu."
    }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $capture).Hash -ne $expected.capture_sha256) {
        throw "Hash do capturador divergiu."
    }
    Expand-Archive -LiteralPath $bundle -DestinationPath $app
    $inputDevice = Find-InputDevice
    $scenarios = @(
        @{ Name = "pair1_bypass"; Method = "bypass" },
        @{ Name = "pair1_stft"; Method = "stft_subtraction" },
        @{ Name = "pair2_stft"; Method = "stft_subtraction" },
        @{ Name = "pair2_bypass"; Method = "bypass" },
        @{ Name = "pair3_bypass"; Method = "bypass" },
        @{ Name = "pair3_stft"; Method = "stft_subtraction" }
    )
    foreach ($scenario in $scenarios) {
        Invoke-Scenario -Name $scenario.Name -Method $scenario.Method `
            -InputDevice $inputDevice
    }
    [ordered]@{
        timestamp = (Get-Date).ToString("o")
        state = "completed"
        input_device = $inputDevice
        scenario_count = $scenarios.Count
        scenarios = @($scenarios | ForEach-Object { $_.Name })
    } | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath (Join-Path $results "matrix_manifest.json") `
            -Encoding UTF8
    Compress-Archive -Path (Join-Path $results "*") -DestinationPath $archive
    Set-CheckpointStatus -State "completed"
    Write-Host "RESULT=OK"
} catch {
    $message = $_ | Out-String
    [IO.File]::WriteAllText(
        (Join-Path $results "matrix_error.txt"),
        $message,
        [Text.UTF8Encoding]::new($false)
    )
    if (Test-Path -LiteralPath $partialArchive) {
        Remove-Item -LiteralPath $partialArchive -Force
    }
    Compress-Archive -Path (Join-Path $results "*") -DestinationPath $partialArchive
    Set-CheckpointStatus -State "failed"
    Write-Error $message
    exit 1
}
