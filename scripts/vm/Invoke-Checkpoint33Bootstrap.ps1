[CmdletBinding()]
param(
    [string]$VmName = "PTC3527-SYSVAD-LAB",
    [string]$Username = "ptc3527"
)

$ErrorActionPreference = "Stop"

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$resultDir = Join-Path $root "resultados\sysvad_checkpoint33"
$bundle = Join-Path $resultDir "checkpoint33_python_bundle.zip"
$resultPath = Join-Path $resultDir "vm_bootstrap_result.json"
$expectedSnapshot = "checkpoint33-pre-dsp-user-audio-in"
$guestRoot = "C:\PTC3527\checkpoint33"
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

function Wait-VmRunning {
    $deadline = (Get-Date).AddMinutes(3)
    do {
        if ((Get-VmProperty -Name "VMState") -eq "running") {
            return
        }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Timeout aguardando a VM iniciar."
}

function Wait-GuestAdditions {
    $deadline = (Get-Date).AddMinutes(3)
    $readyAt = $null
    do {
        $version = @(
            & $vbox guestproperty get $VmName "/VirtualBox/GuestAdd/Version" 2>$null
        ) -join ""
        $service = @(
            & $vbox guestproperty get $VmName `
                "/VirtualBox/GuestAdd/Components/VBoxService.exe" 2>$null
        ) -join ""
        $loggedIn = @(
            & $vbox guestproperty get $VmName `
                "/VirtualBox/GuestInfo/OS/LoggedInUsersList" 2>$null
        ) -join ""
        if (
            $version -match "^Value:\s+\S+" -and
            $service -match "^Value:\s+\S+" -and
            $loggedIn -match [Regex]::Escape($Username)
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
    throw "Guest Additions nao ficaram prontas dentro do prazo."
}

function Invoke-Guest {
    param(
        [string]$PasswordFile,
        [string]$Command,
        [int]$TimeoutMilliseconds = 120000
    )

    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    $account = $accounts[0]
    $arguments = @(
        "guestcontrol", $VmName, "run",
        "--exe", "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "--username", $account.Username,
        "--passwordfile=$PasswordFile",
        "--timeout=$TimeoutMilliseconds",
        "--wait-stdout", "--wait-stderr", "--",
        "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", $encoded
    )

    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $output = @(& $vbox @arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    if ($exitCode -ne 0) {
        throw "Comando no convidado falhou: $($output -join [Environment]::NewLine)"
    }
    return $output
}

function Copy-ToGuest {
    param(
        [string]$PasswordFile,
        [string]$Source,
        [string]$TargetDirectory
    )

    foreach ($account in $accounts) {
        $arguments = @(
            "guestcontrol", $VmName, "copyto",
            "--username", $account.Username,
            "--passwordfile=$PasswordFile"
        )
        if ($account.Domain) {
            $arguments += @("--domain", $account.Domain)
        }
        $arguments += @(
            "--target-directory=$($TargetDirectory.TrimEnd('\'))\",
            $Source
        )

        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $output = @(& $vbox @arguments 2>&1)
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $oldPreference
        if ($exitCode -eq 0) {
            return
        }
    }
    throw "Copia para a VM falhou: $($output -join [Environment]::NewLine)"
}

foreach ($path in @($vbox, $bundle)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Artefato obrigatorio ausente: $path"
    }
}

$volume = Get-Volume -DriveLetter E -ErrorAction Stop
if ($volume.HealthStatus -ne "Healthy" -or $volume.OperationalStatus -notcontains "OK") {
    throw "Volume E: nao esta saudavel."
}
if ((Get-VmProperty -Name "CurrentSnapshotName") -ne $expectedSnapshot) {
    throw "Snapshot atual inesperado."
}

$securePassword = Read-Host "Senha existente do usuario $Username na VM" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$passwordFile = Join-Path ([IO.Path]::GetTempPath()) (
    "ptc3527-vbox-" + [Guid]::NewGuid().ToString("N") + ".txt"
)
try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    [IO.File]::WriteAllText(
        $passwordFile,
        $password,
        [Text.UTF8Encoding]::new($false)
    )
    Write-Host "Credencial recebida. Iniciando bootstrap..."

    if ((Get-VmProperty -Name "VMState") -eq "poweroff") {
        Write-Host "Iniciando VM..."
        Invoke-VBox startvm $VmName --type headless | Out-Null
        Wait-VmRunning
    }
    Write-Host "Aguardando Windows e Guest Additions..."
    Wait-GuestAdditions

    Write-Host "Preparando pasta no convidado..."
    Invoke-Guest -PasswordFile $passwordFile -Command @"
`$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "$guestRoot" | Out-Null
"@ | Out-Null

    Write-Host "Copiando bundle..."
    Copy-ToGuest -PasswordFile $passwordFile -Source $bundle -TargetDirectory $guestRoot

    $expectedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $bundle).Hash
    Write-Host "Validando bundle e estado da ponte..."
    $guestCommand = @"
`$ErrorActionPreference = "Stop"
`$root = "$guestRoot"
`$bundle = Join-Path `$root "checkpoint33_python_bundle.zip"
`$actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath `$bundle).Hash
if (`$actualHash -ne "$expectedHash") {
    throw "Hash do bundle divergiu."
}
`$app = Join-Path `$root "app"
if (Test-Path -LiteralPath `$app) {
    Remove-Item -LiteralPath `$app -Recurse -Force
}
Expand-Archive -LiteralPath `$bundle -DestinationPath `$app

`$python = ""
if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    `$python = "py.exe"
} elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
    `$python = "python.exe"
}
if (-not `$python) {
    throw "Python nao esta instalado no convidado."
}

& `$python -m pip install --disable-pip-version-check -r (Join-Path `$app "requirements.txt")
if (`$LASTEXITCODE -ne 0) {
    throw "Instalacao das dependencias Python falhou."
}

Push-Location `$app
try {
    `$devices = @(& `$python -m realtime_audio.windows_realtime --list-devices 2>&1)
    `$devicesExitCode = `$LASTEXITCODE
} finally {
    Pop-Location
}
if (`$devicesExitCode -ne 0) {
    throw "Listagem de dispositivos de audio falhou: `$(`$devices -join [Environment]::NewLine)"
}

`$service = Get-Service -Name "sysvad_componentizedaudiosample" -ErrorAction SilentlyContinue
`$serviceStatus = if (`$service) { `$service.Status.ToString() } else { "Missing" }
`$producer = "C:\PTC3527\checkpoint32\tools\PtcPcmProducer.exe"
`$bridgeOutput = @()
`$bridgeExitCode = -1
if (Test-Path -LiteralPath `$producer) {
    `$bridgeOutput = @(& `$producer --stats-only 2>&1)
    `$bridgeExitCode = `$LASTEXITCODE
}

[ordered]@{
    Timestamp = (Get-Date).ToString("o")
    BundleHash = `$actualHash
    PythonCommand = `$python
    AudioDevices = (`$devices -join "`n")
    SysvadServiceStatus = `$serviceStatus
    BridgeStatsExitCode = `$bridgeExitCode
    BridgeStats = (`$bridgeOutput -join "`n")
} | ConvertTo-Json -Depth 6 -Compress
"@

    $jsonLine = Invoke-Guest `
        -PasswordFile $passwordFile `
        -Command $guestCommand `
        -TimeoutMilliseconds 900000 |
        Where-Object { $_ -match '^\{.*\}$' } |
        Select-Object -Last 1
    if (-not $jsonLine) {
        throw "Inventario JSON nao retornado pelo convidado."
    }
    $jsonLine | ConvertFrom-Json |
        ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $resultPath -Encoding UTF8

    Write-Host "Bootstrap concluido. Resultado: $resultPath"
}
finally {
    if (Test-Path -LiteralPath $passwordFile) {
        Remove-Item -LiteralPath $passwordFile -Force
    }
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    Remove-Variable password -ErrorAction SilentlyContinue
}
