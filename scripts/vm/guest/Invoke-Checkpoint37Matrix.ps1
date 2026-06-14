[CmdletBinding()]
param(
    [string]$ExchangeRoot = "C:\PTC3527\checkpoint37"
)

$ErrorActionPreference = "Stop"
$root = "C:\PTC3527\checkpoint37"
$app = Join-Path $root "app"
$results = Join-Path $root "resultados"
$bundleSource = Join-Path $ExchangeRoot "checkpoint37_python_bundle.zip"
$captureSource = Join-Path $ExchangeRoot "PtcPcmCapture.exe"
$hashSource = Join-Path $ExchangeRoot "checkpoint37_expected_hashes.json"
$bundle = Join-Path $root "checkpoint37_python_bundle.zip"
$capture = Join-Path $root "PtcPcmCapture.exe"
$hashManifest = Join-Path $root "checkpoint37_expected_hashes.json"
$python = "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
$vboxControl = (
    "C:\Program Files\Oracle\VirtualBox Guest Additions\VBoxGuest\VBoxControl.exe"
)
$statusKey = "/PTC3527/Checkpoint37/Status"
$taskName = "PTC3527-Checkpoint37-Matrix"

function Set-MatrixStatus {
    param([string]$Value)

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $vboxControl guestproperty set $statusKey $Value 2>$null | Out-Null
    $ErrorActionPreference = $oldPreference
}

function Invoke-Producer {
    param(
        [string]$Name,
        [string]$Method,
        [string]$InputDevice,
        [bool]$VirtualMic,
        [int]$PollMs = 10
    )

    $before = @(
        Get-ChildItem $results -Filter "*_metrics.json" -ErrorAction SilentlyContinue |
            ForEach-Object { $_.FullName }
    )
    $progressPath = Join-Path $results ("{0}_progress.json" -f $Name)
    $arguments = @(
        "-m", "realtime_audio.windows_realtime",
        "--duration", "12",
        "--method", $Method,
        "--noise-mode", "adaptive",
        "--block-ms", "20",
        "--input-device", $InputDevice,
        "--output-dir", $results,
        "--progress-file", $progressPath
    )
    if ($VirtualMic) {
        $arguments += @(
            "--virtual-mic",
            "--bridge-target-depth", "2",
            "--bridge-user-queue", "4",
            "--bridge-poll-interval-ms", "2",
            "--diagnostic-trace"
        )
        $captureWav = Join-Path $results ("{0}_endpoint.wav" -f $Name)
        $captureTrace = Join-Path $results ("{0}_capture_trace.csv" -f $Name)
        $captureOut = Join-Path $results ("{0}_capture.stdout.txt" -f $Name)
        $captureErr = Join-Path $results ("{0}_capture.stderr.txt" -f $Name)
        $captureProcess = Start-Process -FilePath $capture -ArgumentList @(
            "--duration", "16",
            "--output", $captureWav,
            "--poll-ms", $PollMs.ToString(),
            "--trace", $captureTrace
        ) -RedirectStandardOutput $captureOut `
          -RedirectStandardError $captureErr -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds 2
    } else {
        $arguments += "--input-only"
        $captureProcess = $null
    }

    $producerOut = Join-Path $results ("{0}_producer.stdout.txt" -f $Name)
    $producerErr = Join-Path $results ("{0}_producer.stderr.txt" -f $Name)
    Push-Location $app
    try {
        $producer = Start-Process -FilePath $python -ArgumentList $arguments `
            -RedirectStandardOutput $producerOut `
            -RedirectStandardError $producerErr -WindowStyle Hidden -PassThru
        if (-not $producer.WaitForExit(30000)) {
            if (Test-Path -LiteralPath $progressPath) {
                Copy-Item -LiteralPath $progressPath `
                    -Destination (
                        Join-Path $ExchangeRoot (
                            "{0}_progress.json" -f $Name
                        )
                    ) -Force
            }
            [IO.File]::WriteAllText(
                (Join-Path $ExchangeRoot ("{0}_watchdog.txt" -f $Name)),
                (Get-Date).ToString("o"),
                [Text.UTF8Encoding]::new($false)
            )
            Stop-Process -Id $producer.Id -Force -ErrorAction SilentlyContinue
            throw "Timeout no produtor $Name."
        }
        $producer.Refresh()
        if ($producer.ExitCode -ne 0) {
            throw "Produtor $Name falhou com codigo $($producer.ExitCode)."
        }
    } finally {
        Pop-Location
    }

    if ($captureProcess) {
        if (-not $captureProcess.WaitForExit(40000)) {
            Stop-Process -Id $captureProcess.Id -Force -ErrorAction SilentlyContinue
            throw "Timeout no capturador $Name."
        }
        $captureProcess.Refresh()
        if ($captureProcess.ExitCode -ne 0) {
            throw "Capturador $Name falhou com codigo $($captureProcess.ExitCode)."
        }
    }

    $newMetric = @(
        Get-ChildItem $results -Filter "*_metrics.json" |
            Where-Object { $_.FullName -notin $before }
    )
    if ($newMetric.Count -ne 1) {
        throw "Metrica unica nao encontrada para $Name."
    }
    $sourceStem = $newMetric[0].BaseName -replace "_metrics$", ""
    Rename-Item -LiteralPath $newMetric[0].FullName `
        -NewName ("{0}_internal_metrics.json" -f $Name)
    foreach ($suffix in @("_blocks.csv", "_input.wav", "_output.wav")) {
        $source = Join-Path $results ($sourceStem + $suffix)
        if (Test-Path -LiteralPath $source) {
            Rename-Item -LiteralPath $source `
                -NewName ("{0}{1}" -f $Name, $suffix)
        }
    }
}

if (Test-Path -LiteralPath $results) {
    Remove-Item -LiteralPath $results -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $results | Out-Null
New-Item -ItemType Directory -Force -Path $root | Out-Null
Copy-Item -LiteralPath $bundleSource -Destination $bundle -Force
Copy-Item -LiteralPath $captureSource -Destination $capture -Force
Copy-Item -LiteralPath $hashSource -Destination $hashManifest -Force
[IO.File]::WriteAllText(
    (Join-Path $results "task_started.txt"),
    (Get-Date).ToString("o"),
    [Text.UTF8Encoding]::new($false)
)

try {
    Set-MatrixStatus -Value "running"
    $expectedHashes = Get-Content -Raw -LiteralPath $hashManifest |
        ConvertFrom-Json
    if (
        (Get-FileHash -Algorithm SHA256 -LiteralPath $bundle).Hash -ne
        $expectedHashes.bundle_sha256
    ) {
        throw "Hash do bundle divergiu."
    }
    if (
        (Get-FileHash -Algorithm SHA256 -LiteralPath $capture).Hash -ne
        $expectedHashes.capture_sha256
    ) {
        throw "Hash do capturador divergiu."
    }
    if (Test-Path -LiteralPath $app) {
        Remove-Item -LiteralPath $app -Recurse -Force
    }
    Expand-Archive -LiteralPath $bundle -DestinationPath $app
    $deviceCode = @'
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
    if row["host_api"] == "Windows WASAPI"
    and row["name"] == "Microfone (High Definition Audio Device)"
]
if len(candidates) != 1:
    raise SystemExit(f"entrada fisica ambigua: {candidates!r}; todas={rows!r}")
print(json.dumps({"selected": candidates[0], "inputs": rows}, ensure_ascii=False))
'@
    $deviceProbe = Join-Path $root "enumerate_checkpoint37_inputs.py"
    [IO.File]::WriteAllText(
        $deviceProbe,
        $deviceCode,
        [Text.UTF8Encoding]::new($false)
    )
    Push-Location $app
    try {
        $deviceOutput = @(& $python $deviceProbe 2>&1)
        $deviceExitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($deviceExitCode -ne 0) {
        throw "Falha ao enumerar entradas: $($deviceOutput -join ' ')"
    }
    $deviceJson = $deviceOutput[-1]
    [IO.File]::WriteAllText(
        (Join-Path $results "guest_input_devices.json"),
        $deviceJson,
        [Text.UTF8Encoding]::new($false)
    )
    $inputDevice = (($deviceJson | ConvertFrom-Json).selected.index).ToString()

    Invoke-Producer -Name "raw_capture" -Method "bypass" `
        -InputDevice $inputDevice -VirtualMic $false
    Invoke-Producer -Name "bypass_prebridge" -Method "bypass" `
        -InputDevice $inputDevice -VirtualMic $false
    Invoke-Producer -Name "stft_prebridge" -Method "stft_subtraction" `
        -InputDevice $inputDevice -VirtualMic $false
    Invoke-Producer -Name "bypass_endpoint_poll10" -Method "bypass" `
        -InputDevice $inputDevice -VirtualMic $true -PollMs 10
    Invoke-Producer -Name "stft_endpoint_poll10" -Method "stft_subtraction" `
        -InputDevice $inputDevice -VirtualMic $true -PollMs 10
    Invoke-Producer -Name "stft_endpoint_poll2" -Method "stft_subtraction" `
        -InputDevice $inputDevice -VirtualMic $true -PollMs 2

    [ordered]@{
        timestamp = (Get-Date).ToString("o")
        status = "completed"
        input_device = $inputDevice
        scenarios = @(
            "raw_capture",
            "bypass_prebridge",
            "stft_prebridge",
            "bypass_endpoint_poll10",
            "stft_endpoint_poll10",
            "stft_endpoint_poll2"
        )
    } | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath (Join-Path $results "matrix_status.json") `
            -Encoding UTF8

    $archive = Join-Path $ExchangeRoot "checkpoint37_vm_results.zip"
    if (Test-Path -LiteralPath $archive) {
        Remove-Item -LiteralPath $archive -Force
    }
    Compress-Archive -Path (Join-Path $results "*") -DestinationPath $archive
    Set-MatrixStatus -Value "completed"
    cmd.exe /c "schtasks.exe /delete /tn `"$taskName`" /f >nul 2>&1" | Out-Null
} catch {
    $message = $_ | Out-String
    New-Item -ItemType Directory -Force -Path $results | Out-Null
    [IO.File]::WriteAllText(
        (Join-Path $results "matrix_error.txt"),
        $message,
        [Text.UTF8Encoding]::new($false)
    )
    $partialArchive = Join-Path $ExchangeRoot "checkpoint37_vm_partial.zip"
    if (Test-Path -LiteralPath $partialArchive) {
        Remove-Item -LiteralPath $partialArchive -Force
    }
    Compress-Archive -Path (Join-Path $results "*") `
        -DestinationPath $partialArchive
    Set-MatrixStatus -Value "failed"
    cmd.exe /c "schtasks.exe /delete /tn `"$taskName`" /f >nul 2>&1" | Out-Null
    exit 1
}
