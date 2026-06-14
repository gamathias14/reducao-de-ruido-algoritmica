[CmdletBinding()]
param(
    [string]$OutputRoot = (
        Join-Path $env:LOCALAPPDATA "PTC3527-Private\host_paced_pcm"
    ),
    [int]$DurationSeconds = 20
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$python = (Get-Command python -ErrorAction Stop).Source
$captureScript = Join-Path $PSScriptRoot "capture_host_pcm.py"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$pcmPath = Join-Path $OutputRoot "$stamp-controlled-speech.pcm"
$summaryPath = Join-Path $OutputRoot "$stamp-controlled-speech.json"
$stdoutPath = Join-Path $OutputRoot "$stamp-capture.stdout.txt"
$stderrPath = Join-Path $OutputRoot "$stamp-capture.stderr.txt"
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

function Quote-Argument {
    param([string]$Value)

    return '"' + $Value.Replace('"', '\"') + '"'
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "PTC3527 - Captura controlada"
$form.Size = New-Object System.Drawing.Size(720, 300)
$form.StartPosition = "CenterScreen"
$form.TopMost = $true
$form.BackColor = [System.Drawing.Color]::FromArgb(20, 24, 32)
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false

$label = New-Object System.Windows.Forms.Label
$label.Dock = "Fill"
$label.TextAlign = "MiddleCenter"
$label.ForeColor = [System.Drawing.Color]::White
$label.Font = New-Object System.Drawing.Font(
    "Segoe UI",
    34,
    [System.Drawing.FontStyle]::Bold
)
$label.Text = "Prepare-se"
$form.Controls.Add($label)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 100
$startedAt = [Diagnostics.Stopwatch]::StartNew()
$captureProcess = $null
$captureStartedAt = $null
$finishedAt = $null

$timer.Add_Tick({
    $elapsed = $startedAt.Elapsed.TotalSeconds
    if ($null -eq $captureProcess) {
        if ($elapsed -lt 1.0) {
            $label.Text = "3"
        } elseif ($elapsed -lt 2.0) {
            $label.Text = "2"
        } elseif ($elapsed -lt 3.0) {
            $label.Text = "1"
        } else {
            [Console]::Beep(1000, 300)
            $arguments = @(
                $captureScript,
                "--duration", "$DurationSeconds",
                "--countdown", "0",
                "--pcm-output", $pcmPath,
                "--summary-output", $summaryPath
            )
            $argumentLine = (
                $arguments | ForEach-Object { Quote-Argument $_ }
            ) -join " "
            $script:captureProcess = Start-Process `
                -FilePath $python `
                -ArgumentList $argumentLine `
                -WindowStyle Hidden `
                -PassThru `
                -RedirectStandardOutput $stdoutPath `
                -RedirectStandardError $stderrPath
            $script:captureStartedAt = [Diagnostics.Stopwatch]::StartNew()
            $label.ForeColor = [System.Drawing.Color]::Lime
            $label.Text = "FALE AGORA`n$DurationSeconds s restantes"
        }
        return
    }

    if (-not $captureProcess.HasExited) {
        $remaining = [Math]::Max(
            0,
            [Math]::Ceiling(
                $DurationSeconds - $captureStartedAt.Elapsed.TotalSeconds
            )
        )
        $label.Text = "GRAVANDO - FALE`n$remaining s restantes"
        return
    }

    if ($null -eq $finishedAt) {
        $script:finishedAt = [Diagnostics.Stopwatch]::StartNew()
        $label.ForeColor = [System.Drawing.Color]::White
        if (Test-Path -LiteralPath $summaryPath -PathType Leaf) {
            $summary = Get-Content -LiteralPath $summaryPath -Raw |
                ConvertFrom-Json
            if ([bool]$summary.valid) {
                $label.Text = "GRAVACAO CONCLUIDA`nValidacao aprovada"
            } else {
                $reasons = @($summary.failures) -join ", "
                $label.Text = "GRAVACAO CONCLUIDA`nRejeitada: $reasons"
            }
        } else {
            $label.Text = "GRAVACAO FALHOU`nNenhum resumo foi gerado"
        }
        [Console]::Beep(700, 250)
        return
    }

    if ($finishedAt.Elapsed.TotalSeconds -ge 4.0) {
        $timer.Stop()
        $form.Close()
    }
})

$form.Add_Shown({
    $form.Activate()
    $timer.Start()
})

[void]$form.ShowDialog()

if ($null -ne $captureProcess -and -not $captureProcess.HasExited) {
    Stop-Process -Id $captureProcess.Id -Force
}

[ordered]@{
    pcm_path = $pcmPath
    summary_path = $summaryPath
    stdout_path = $stdoutPath
    stderr_path = $stderrPath
} | ConvertTo-Json

if (
    -not (Test-Path -LiteralPath $summaryPath -PathType Leaf) -or
    -not [bool](
        (Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json).valid
    )
) {
    exit 1
}
