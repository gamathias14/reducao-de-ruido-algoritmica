[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527",
    [string]$ControlledCaptureName = "CABLE Output (VB-Audio Virtual Cable)",
    [string]$ControlledPlaybackName = "CABLE In 16ch (VB-Audio Virtual Cable), Windows WASAPI",
    [ValidateSet("depth", "queue")]
    [string]$MatrixName = "depth",
    [switch]$Resume,
    [Parameter(Mandatory = $true)]
    [string]$UnattendPath
)

$ErrorActionPreference = "Stop"

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$resultDir = Join-Path $root "resultados\sysvad_checkpoint34"
$bundle = Join-Path $resultDir "checkpoint34_python_bundle.zip"
$guestRoot = "C:\PTC3527\checkpoint34"
$guestArchiveName = "checkpoint34_$($MatrixName)_results.zip"
$expectedSnapshot = "checkpoint33-functional-validated"
$preSnapshot = "checkpoint34-pre-latency-refinement"
$unattendPath = $UnattendPath
$endpointTool = Join-Path $root (
    "resultados\sysvad_checkpoint33\SetDefaultCaptureEndpoint.exe"
)
$signalScript = Join-Path $root "scripts\audio\play_controlled_signal.py"
$python = Join-Path $root ".venv-checkpoint34\Scripts\python.exe"
$accounts = @(@{ Username = $Username; Domain = $null })

function Invoke-VBox {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = @(& $vbox @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    if ($exitCode -ne 0) {
        throw "VBoxManage falhou: $($output -join [Environment]::NewLine)"
    }
    return $output
}

function Get-VmProperty {
    param([string]$Name)

    $line = @(& $vbox showvminfo $VmName --machinereadable 2>$null) |
        Where-Object { $_ -like "$Name=*" } |
        Select-Object -First 1
    if ($line -match '^[^=]+="([^"]*)"$') {
        return $Matches[1]
    }
    throw "Propriedade da VM indisponivel: $Name"
}

function Wait-VmState {
    param([string]$Expected, [int]$TimeoutSeconds = 180)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if ((Get-VmProperty -Name "VMState") -eq $Expected) {
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Timeout aguardando VM em estado $Expected."
}

function Wait-GuestAdditions {
    $deadline = (Get-Date).AddMinutes(6)
    $readyAt = $null
    do {
        $version = @(
            & $vbox guestproperty get $VmName "/VirtualBox/GuestAdd/Version" 2>$null
        ) -join ""
        $service = @(
            & $vbox guestproperty get $VmName `
                "/VirtualBox/GuestAdd/Components/VBoxService.exe" 2>$null
        ) -join ""
        if (
            $version -match "^Value:\s+\S+" -and
            $service -match "^Value:\s+\S+"
        ) {
            if (-not $readyAt) {
                $readyAt = Get-Date
            }
            if (((Get-Date) - $readyAt).TotalSeconds -ge 30) {
                return
            }
        } else {
            $readyAt = $null
        }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)
    throw "Guest Additions nao ficaram prontos dentro do prazo."
}

function Get-LabPassword {
    [xml]$unattend = Get-Content -LiteralPath $unattendPath -Raw
    $values = @(
        $unattend.SelectNodes(
            "//*[local-name()='Password']/*[local-name()='Value'] | " +
            "//*[local-name()='AdministratorPassword']/*[local-name()='Value']"
        ) |
            ForEach-Object { $_.InnerText } |
            Where-Object { -not [string]::IsNullOrEmpty($_) } |
            Select-Object -Unique
    )
    if ($values.Count -ne 1) {
        throw "Credencial unica da VM nao encontrada."
    }
    return $values[0]
}

function Invoke-Guest {
    param(
        [string]$PasswordFile,
        [string]$Command,
        [int]$TimeoutMilliseconds = 180000
    )

    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
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
    param([string]$PasswordFile, [string]$Source, [string]$TargetDirectory)

    Invoke-VBox guestcontrol $VmName copyto `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$($TargetDirectory.TrimEnd('\'))\" `
        $Source | Out-Null
}

function Copy-FromGuest {
    param([string]$PasswordFile, [string]$Source, [string]$TargetDirectory)

    $normalizedTarget = $TargetDirectory.TrimEnd("\").Replace("\", "/") + "/"
    Invoke-VBox guestcontrol $VmName copyfrom `
        --username $Username `
        "--passwordfile=$PasswordFile" `
        "--target-directory=$normalizedTarget" `
        $Source | Out-Null
}

function New-Bundle {
    New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
    $stagePath = Join-Path $resultDir (
        "bundle_stage_" + [Guid]::NewGuid().ToString("N")
    )
    New-Item -ItemType Directory -Force -Path `
        (Join-Path $stagePath "benchmark_audio"), `
        (Join-Path $stagePath "realtime_audio") | Out-Null

    foreach ($file in @("__init__.py", "causal.py", "denoise.py")) {
        Copy-Item -LiteralPath (Join-Path $root "benchmark_audio\$file") `
            -Destination (Join-Path $stagePath "benchmark_audio\$file")
    }
    foreach ($file in @(
        "__init__.py",
        "block_metrics.py",
        "ptc_pcm_bridge.py",
        "windows_realtime.py"
    )) {
        Copy-Item -LiteralPath (Join-Path $root "realtime_audio\$file") `
            -Destination (Join-Path $stagePath "realtime_audio\$file")
    }
    Copy-Item -LiteralPath (
        Join-Path $root "realtime_audio\requirements_virtual_mic.txt"
    ) -Destination (Join-Path $stagePath "requirements.txt")

    if (Test-Path -LiteralPath $bundle) {
        Remove-Item -LiteralPath $bundle -Force
    }
    Compress-Archive -Path (Join-Path $stagePath "*") -DestinationPath $bundle
    try {
        Remove-Item -LiteralPath $stagePath -Recurse -Force
    } catch {
        Write-Warning "OneDrive manteve o staging temporariamente bloqueado."
    }
}

foreach ($path in @(
    $vbox,
    $unattendPath,
    $endpointTool,
    $signalScript,
    $python
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Artefato obrigatorio ausente: $path"
    }
}

$volume = Get-Volume -DriveLetter E -ErrorAction Stop
if ($volume.HealthStatus -ne "Healthy" -or $volume.OperationalStatus -notcontains "OK") {
    throw "Volume E: nao esta saudavel."
}
$vmState = Get-VmProperty -Name "VMState"
$currentSnapshot = Get-VmProperty -Name "CurrentSnapshotName"
if ($Resume) {
    if ($currentSnapshot -ne $preSnapshot) {
        throw "A retomada exige o snapshot atual $preSnapshot."
    }
    if ($vmState -notin @("poweroff", "running")) {
        throw "Estado da VM incompativel com retomada: $vmState."
    }
} else {
    if ($vmState -ne "poweroff") {
        throw "A VM deve estar desligada antes da abertura do Checkpoint 34."
    }
    if ($currentSnapshot -ne $expectedSnapshot) {
        throw "Snapshot atual inesperado."
    }
}

New-Bundle
$bundleHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $bundle).Hash
if (-not $Resume) {
    $snapshotText = Invoke-VBox snapshot $VmName list --machinereadable
    if ($snapshotText -match [Regex]::Escape("SnapshotName=`"$preSnapshot`"")) {
        throw "O snapshot $preSnapshot ja existe; revise o estado antes de repetir."
    }
    Invoke-VBox snapshot $VmName take $preSnapshot `
        --description (
            "Checkpoint 34: estado funcional do Checkpoint 33 antes do bundle " +
            "de telemetria e da matriz de latencia."
        ) | Out-Null
}

$endpointLines = @(& $endpointTool --list)
$originalLine = $endpointLines | Where-Object { $_ -match "^default=1`t" } |
    Select-Object -First 1
if ($originalLine -notmatch 'id=([^\s]+)$') {
    throw "Endpoint de captura padrao original nao identificado."
}
$originalEndpointId = $Matches[1]
$passwordFile = Join-Path ([IO.Path]::GetTempPath()) (
    "ptc3527-checkpoint34-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
$signalProcess = $null
$matrixCompleted = $false

try {
    [IO.File]::WriteAllText(
        $passwordFile,
        (Get-LabPassword),
        [Text.UTF8Encoding]::new($false)
    )
    & $endpointTool --set-name $ControlledCaptureName
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel selecionar a entrada controlada do host."
    }

    if ((Get-VmProperty -Name "VMState") -eq "poweroff") {
        Invoke-VBox startvm $VmName --type headless | Out-Null
        Wait-VmState -Expected "running"
    }
    Wait-GuestAdditions

    Invoke-Guest -PasswordFile $passwordFile -Command @"
`$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "$guestRoot" | Out-Null
"@ | Out-Null
    Copy-ToGuest -PasswordFile $passwordFile -Source $bundle `
        -TargetDirectory $guestRoot

    $guestCommand = @"
`$ErrorActionPreference = "Stop"
`$root = "$guestRoot"
`$bundle = Join-Path `$root "checkpoint34_python_bundle.zip"
if ((Get-FileHash -Algorithm SHA256 -LiteralPath `$bundle).Hash -ne "$bundleHash") {
    throw "Hash do bundle divergiu."
}
`$app = Join-Path `$root "app"
if (Test-Path -LiteralPath `$app) {
    Remove-Item -LiteralPath `$app -Recurse -Force
}
Expand-Archive -LiteralPath `$bundle -DestinationPath `$app
`$results = Join-Path `$root "resultados"
if (Test-Path -LiteralPath `$results) {
    Remove-Item -LiteralPath `$results -Recurse -Force
}
New-Item -ItemType Directory -Force -Path `$results | Out-Null
`$python = "C:\Users\ptc3527\AppData\Local\Programs\Python\Python312\python.exe"
`$capture = "C:\PTC3527\checkpoint32\tools\PtcPcmCapture.exe"
if ("$MatrixName" -eq "queue") {
    `$scenarios = @(
        [pscustomobject]@{ Name = "depth2_queue1"; Depth = 2; UserQueue = 1 },
        [pscustomobject]@{ Name = "depth2_queue2"; Depth = 2; UserQueue = 2 },
        [pscustomobject]@{ Name = "depth2_queue4"; Depth = 2; UserQueue = 4 }
    )
} else {
    `$scenarios = @(
        [pscustomobject]@{ Name = "depth1_queue4"; Depth = 1; UserQueue = 4 },
        [pscustomobject]@{ Name = "depth2_queue4"; Depth = 2; UserQueue = 4 },
        [pscustomobject]@{ Name = "depth4_queue4"; Depth = 4; UserQueue = 4 }
    )
}
foreach (`$scenario in `$scenarios) {
    `$name = `$scenario.Name
    `$depth = `$scenario.Depth
    `$userQueue = `$scenario.UserQueue
    `$wav = Join-Path `$results ("controlled_{0}.wav" -f `$name)
    `$captureOut = Join-Path `$results ("controlled_{0}_capture.stdout.txt" -f `$name)
    `$captureErr = Join-Path `$results ("controlled_{0}_capture.stderr.txt" -f `$name)
    `$producerOut = Join-Path `$results ("controlled_{0}_producer.stdout.txt" -f `$name)
    `$producerErr = Join-Path `$results ("controlled_{0}_producer.stderr.txt" -f `$name)
    `$producerExitPath = Join-Path `$results (
        "controlled_{0}_producer_exit.txt" -f `$name
    )
    `$captureParameters = @{
        FilePath = `$capture
        ArgumentList = @("--duration", "18", "--output", `$wav)
        RedirectStandardOutput = `$captureOut
        RedirectStandardError = `$captureErr
        WindowStyle = "Hidden"
        PassThru = `$true
    }
    `$captureProcess = Start-Process @captureParameters
    Start-Sleep -Seconds 2
    `$metricsBefore = @(
        Get-ChildItem `$results -Filter "*_metrics.json" -ErrorAction SilentlyContinue |
            ForEach-Object { `$_.FullName }
    )
    Push-Location `$app
    try {
        `$producerArguments = @(
            "-m", "realtime_audio.windows_realtime",
            "--virtual-mic",
            "--duration", "12",
            "--method", "stft_subtraction",
            "--noise-mode", "adaptive",
            "--block-ms", "20",
            "--input-device", "1",
            "--bridge-target-depth", `$depth.ToString(),
            "--bridge-user-queue", `$userQueue.ToString(),
            "--output-dir", `$results
        )
        `$producerParameters = @{
            FilePath = `$python
            ArgumentList = `$producerArguments
            RedirectStandardOutput = `$producerOut
            RedirectStandardError = `$producerErr
            WindowStyle = "Hidden"
            PassThru = `$true
        }
        `$producerProcess = Start-Process @producerParameters
        `$producerExited = `$producerProcess.WaitForExit(45000)
        if (-not `$producerExited) {
            Stop-Process -Id `$producerProcess.Id -Force -ErrorAction SilentlyContinue
            `$producerExit = "forced_after_metrics_timeout"
        } else {
            `$producerProcess.Refresh()
            `$producerExit = `$producerProcess.ExitCode
        }
    } finally {
        Pop-Location
    }
    `$producerExit | Set-Content -LiteralPath `$producerExitPath
    `$newMetrics = @(
        Get-ChildItem `$results -Filter "*_metrics.json" -ErrorAction SilentlyContinue |
            Where-Object { `$_.FullName -notin `$metricsBefore }
    )
    if (`$newMetrics.Count -ne 1) {
        throw "Produtor falhou no cenario `$name."
    }
    if (-not `$captureProcess.WaitForExit(30000)) {
        Stop-Process -Id `$captureProcess.Id -Force -ErrorAction SilentlyContinue
        throw "Timeout aguardando capturador no cenario `$name."
    }
    `$captureProcess.Refresh()
    `$captureExitPath = Join-Path `$results (
        "controlled_{0}_capture_exit_code.txt" -f `$name
    )
    `$captureProcess.ExitCode | Set-Content -LiteralPath `$captureExitPath
    `$wavInfo = Get-Item -LiteralPath `$wav -ErrorAction SilentlyContinue
    if (`$captureProcess.ExitCode -ne 0 -and (-not `$wavInfo -or `$wavInfo.Length -le 44)) {
        throw "Capturador falhou no cenario `$name."
    }
}
`$archive = Join-Path `$root "$guestArchiveName"
if (Test-Path -LiteralPath `$archive) {
    Remove-Item -LiteralPath `$archive -Force
}
Compress-Archive -Path (Join-Path `$results "*") -DestinationPath `$archive
"@

    $signalStdout = Join-Path $resultDir "controlled_signal.stdout.txt"
    $signalStderr = Join-Path $resultDir "controlled_signal.stderr.txt"
    $signalProcess = Start-Process -FilePath $python `
        -ArgumentList @(
            "`"$signalScript`"",
            "--output-device", "`"$ControlledPlaybackName`"",
            "--duration", "120",
            "--peak", "0.10"
        ) `
        -RedirectStandardOutput $signalStdout `
        -RedirectStandardError $signalStderr `
        -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2

    Invoke-Guest -PasswordFile $passwordFile -Command $guestCommand `
        -TimeoutMilliseconds 180000 | Out-Null
    Copy-FromGuest -PasswordFile $passwordFile `
        -Source "$guestRoot\$guestArchiveName" `
        -TargetDirectory $resultDir
    $matrixCompleted = $true

    if ($signalProcess -and -not $signalProcess.HasExited) {
        Wait-Process -Id $signalProcess.Id -Timeout 30
    }

    try {
        Invoke-Guest -PasswordFile $passwordFile `
            -Command "& shutdown.exe /s /t 0" `
            -TimeoutMilliseconds 30000 | Out-Null
    } catch {
        Write-Warning "Guest Control encerrou durante o shutdown; aguardando a VM."
    }
    Wait-VmState -Expected "poweroff" -TimeoutSeconds 180

    [ordered]@{
        Timestamp = (Get-Date).ToString("o")
        BundleHash = $bundleHash
        PreSnapshot = $preSnapshot
        MatrixName = $MatrixName
        ControlledCaptureName = $ControlledCaptureName
        ControlledPlaybackName = $ControlledPlaybackName
        OriginalCaptureEndpointId = $originalEndpointId
    } | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath (
            Join-Path $resultDir "host_run_metadata.json"
        ) -Encoding UTF8
}
finally {
    if ($signalProcess -and -not $signalProcess.HasExited) {
        Stop-Process -Id $signalProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($matrixCompleted -and (Get-VmProperty -Name "VMState") -eq "running") {
        Invoke-VBox controlvm $VmName acpipowerbutton | Out-Null
        try {
            Wait-VmState -Expected "poweroff" -TimeoutSeconds 120
        } catch {
            Write-Warning "A VM nao desligou por ACPI; nao foi forçado poweroff."
        }
    } elseif (-not $matrixCompleted -and (Get-VmProperty -Name "VMState") -eq "running") {
        Write-Warning "Matriz incompleta; VM mantida ligada para retomada."
    }
    & $endpointTool --set-id $originalEndpointId | Out-Null
    if (Test-Path -LiteralPath $passwordFile) {
        Remove-Item -LiteralPath $passwordFile -Force
    }
}

Write-Host "Matriz concluida: $resultDir"
