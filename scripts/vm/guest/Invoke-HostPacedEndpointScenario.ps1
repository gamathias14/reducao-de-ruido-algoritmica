[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$ScenarioRoot,
    [Parameter(Mandatory = $true)]
    [ValidateSet("bypass", "rnnoise")]
    [string]$Method,
    [Parameter(Mandatory = $true)][int]$Port,
    [int]$DurationSeconds = 20,
    [ValidateSet("normal", "mmcss")]
    [string]$WriterScheduling = "normal",
    [ValidateSet("sleep", "yield")]
    [string]$PollWaitStrategy = "sleep",
    [ValidateSet("sleep", "yield", "spin", "event")]
    [string]$CapturePollWaitStrategy = "sleep",
    [switch]$CaptureStartBarrier
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$python = "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
$probe = Join-Path $Root "host_guest_pcm_stream.py"
$schedulerProbe = Join-Path $Root "guest_scheduler_probe.py"
$capture = Join-Path $Root "PtcPcmCapture.exe"
$app = Join-Path $Root "app"
$dll = Join-Path $Root "ptc3527-rnnoise-v0.2.dll"
$results = Join-Path $ScenarioRoot "results"
$archive = Join-Path $ScenarioRoot "endpoint_results.zip"
$endpoint = Join-Path $results "endpoint.wav"
$captureTrace = Join-Path $results "capture_trace.csv"
$capturePollTrace = Join-Path $results "capture_poll_trace.csv"
$captureTimingTrace = Join-Path $results "capture_timing_trace.csv"
$captureStdout = Join-Path $results "capture.stdout.txt"
$captureStderr = Join-Path $results "capture.stderr.txt"
$clientStdout = Join-Path $results "client.stdout.txt"
$clientStderr = Join-Path $results "client.stderr.txt"
$clientReady = Join-Path $results "client.ready"
$clientStart = Join-Path $results "client.start"
$captureReady = Join-Path $results "capture.ready"
$captureStarted = Join-Path $results "capture.started"
$schedulerReady = Join-Path $results "scheduler.ready"
$schedulerStop = Join-Path $results "scheduler.stop"
$schedulerOutput = Join-Path $results "scheduler.json"
$schedulerStdout = Join-Path $results "scheduler.stdout.txt"
$schedulerStderr = Join-Path $results "scheduler.stderr.txt"

foreach ($path in @(
    $python,
    $probe,
    $schedulerProbe,
    $capture,
    $dll,
    $app
)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required endpoint artifact is missing: $path"
    }
}

Remove-Item -LiteralPath $results, $archive -Recurse -Force `
    -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $results | Out-Null

$captureProcess = $null
$client = $null
$scheduler = $null
try {
    $env:PYTHONPATH = $app
    $env:PTC3527_RNNOISE_DLL = $dll
    $scheduler = Start-Process `
        -FilePath $python `
        -ArgumentList @(
            $schedulerProbe,
            "--ready-file", $schedulerReady,
            "--start-file", $clientStart,
            "--stop-file", $schedulerStop,
            "--output", $schedulerOutput,
            "--interval-ms", "2",
            "--max-duration", [string]($DurationSeconds + 20)
        ) `
        -WorkingDirectory $app `
        -WindowStyle Hidden `
        -RedirectStandardOutput $schedulerStdout `
        -RedirectStandardError $schedulerStderr `
        -PassThru

    $arguments = @(
        $probe,
        "client",
        "--host", "10.0.2.2",
        "--port", [string]$Port,
        "--method", $Method,
        "--prefix-blocks", "500",
        "--bridge",
        "--bridge-target-depth", "2",
        "--bridge-user-queue", "4",
        "--bridge-poll-interval-ms", "2",
        "--bridge-thread-scheduling", $WriterScheduling,
        "--bridge-poll-wait-strategy", $PollWaitStrategy,
        "--bridge-trace",
        "--ready-file", $clientReady,
        "--start-file", $clientStart,
        "--start-wait-timeout", "120",
        "--output", (Join-Path $results "client.json"),
        "--trace", (Join-Path $results "client_trace.json")
    )
    $client = Start-Process `
        -FilePath $python `
        -ArgumentList $arguments `
        -WorkingDirectory $app `
        -WindowStyle Hidden `
        -RedirectStandardOutput $clientStdout `
        -RedirectStandardError $clientStderr `
        -PassThru

    $deadline = (Get-Date).AddSeconds(120)
    while (-not (Test-Path -LiteralPath $clientReady -PathType Leaf)) {
        if ($client.HasExited) {
            throw "Endpoint client exited before publishing readiness."
        }
        if ((Get-Date) -ge $deadline) {
            throw "Endpoint client readiness timed out."
        }
        Start-Sleep -Milliseconds 100
    }
    $deadline = (Get-Date).AddSeconds(30)
    while (-not (Test-Path -LiteralPath $schedulerReady -PathType Leaf)) {
        if ($scheduler.HasExited) {
            throw "Scheduler probe exited before publishing readiness."
        }
        if ((Get-Date) -ge $deadline) {
            throw "Scheduler probe readiness timed out."
        }
        Start-Sleep -Milliseconds 100
    }

    $captureArguments = @(
        "--output", $endpoint,
        "--duration", [string]($DurationSeconds + 4),
        "--poll-ms", "2",
        "--poll-wait-strategy", $CapturePollWaitStrategy,
        "--event-wait-timeout-ms", "1000",
        "--trace", $captureTrace,
        "--poll-trace", $capturePollTrace,
        "--timing-trace", $captureTimingTrace,
        "--ready-file", $captureReady,
        "--started-file", $captureStarted
    )
    if ($CaptureStartBarrier) {
        $captureArguments += @(
            "--start-when-bridge-depth", "2",
            "--start-bridge-timeout-ms", "30000"
        )
    }
    $captureProcess = Start-Process `
        -FilePath $capture `
        -ArgumentList $captureArguments `
        -WindowStyle Hidden `
        -RedirectStandardOutput $captureStdout `
        -RedirectStandardError $captureStderr `
        -PassThru

    $deadline = (Get-Date).AddSeconds(30)
    while (-not (Test-Path -LiteralPath $captureReady -PathType Leaf)) {
        if ($captureProcess.HasExited) {
            throw "Endpoint capture exited before publishing readiness."
        }
        if ((Get-Date) -ge $deadline) {
            throw "Endpoint capture readiness timed out."
        }
        Start-Sleep -Milliseconds 100
    }

    Set-Content -LiteralPath $clientStart -Value "start" -Encoding ASCII
    $deadline = (Get-Date).AddSeconds(30)
    while (-not (Test-Path -LiteralPath $captureStarted -PathType Leaf)) {
        if ($captureProcess.HasExited) {
            throw "Endpoint capture exited before starting IAudioClient."
        }
        if ((Get-Date) -ge $deadline) {
            throw "Endpoint capture IAudioClient start timed out."
        }
        Start-Sleep -Milliseconds 50
    }
    if (-not $client.WaitForExit(($DurationSeconds + 60) * 1000)) {
        Stop-Process -Id $client.Id -Force -ErrorAction SilentlyContinue
        throw "Host-paced endpoint client timed out."
    }
    $client.WaitForExit()
    $client.Refresh()
    if ($null -ne $client.ExitCode -and $client.ExitCode -ne 0) {
        throw "Host-paced endpoint client failed with code $($client.ExitCode)."
    }
    Set-Content -LiteralPath $schedulerStop -Value "stop" -Encoding ASCII
    if (-not $scheduler.WaitForExit(30000)) {
        Stop-Process -Id $scheduler.Id -Force -ErrorAction SilentlyContinue
        throw "Scheduler probe timed out."
    }
    $scheduler.WaitForExit()
    $scheduler.Refresh()
    if ($null -ne $scheduler.ExitCode -and $scheduler.ExitCode -ne 0) {
        throw "Scheduler probe failed with code $($scheduler.ExitCode)."
    }
} finally {
    if ($null -ne $client -and -not $client.HasExited) {
        Stop-Process -Id $client.Id -Force -ErrorAction SilentlyContinue
    }
    if ($null -ne $captureProcess -and -not $captureProcess.HasExited) {
        if (-not $captureProcess.WaitForExit(($DurationSeconds + 20) * 1000)) {
            Stop-Process `
                -Id $captureProcess.Id `
                -Force `
                -ErrorAction SilentlyContinue
            throw "Endpoint capture timed out."
        }
    }
    if ($null -ne $scheduler -and -not $scheduler.HasExited) {
        Set-Content `
            -LiteralPath $schedulerStop `
            -Value "stop" `
            -Encoding ASCII `
            -ErrorAction SilentlyContinue
        if (-not $scheduler.WaitForExit(5000)) {
            Stop-Process `
                -Id $scheduler.Id `
                -Force `
                -ErrorAction SilentlyContinue
        }
    }
    if ($null -ne $captureProcess) {
        $captureProcess.WaitForExit()
        $captureProcess.Refresh()
    }
}

if (
    $null -eq $captureProcess -or
    ($null -ne $captureProcess.ExitCode -and $captureProcess.ExitCode -ne 0)
) {
    throw "Endpoint capture failed with code $($captureProcess.ExitCode)."
}
if (
    -not (Test-Path -LiteralPath $endpoint -PathType Leaf) -or
    (Get-Item -LiteralPath $endpoint).Length -le 44
) {
    throw "Endpoint capture did not produce a usable WAV."
}
$clientResult = Get-Content `
    -LiteralPath (Join-Path $results "client.json") `
    -Raw |
    ConvertFrom-Json
if ($clientResult.status -ne "completed") {
    throw "Endpoint client JSON is not completed."
}
if ([int]$clientResult.bridge.write_errors -ne 0) {
    throw "Bridge reported write errors."
}
$schedulerResult = Get-Content -LiteralPath $schedulerOutput -Raw |
    ConvertFrom-Json
if ($schedulerResult.status -ne "completed") {
    throw "Scheduler probe JSON is not completed."
}

Compress-Archive `
    -Path (Join-Path $results "*") `
    -DestinationPath $archive `
    -CompressionLevel Optimal
Write-Output "ENDPOINT_SCENARIO=OK"
