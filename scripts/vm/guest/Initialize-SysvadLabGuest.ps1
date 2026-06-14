$ErrorActionPreference = 'Stop'

$labRoot = 'C:\PTC3527'
New-Item -ItemType Directory -Path $labRoot -Force | Out-Null

# This VM is an isolated driver lab. Disabling UAC here lets VBox guestcontrol
# perform repeatable administrative tasks without weakening the host.
Set-ItemProperty `
    -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' `
    -Name EnableLUA `
    -Type DWord `
    -Value 0

powercfg.exe /hibernate off
powercfg.exe /change standby-timeout-ac 0
powercfg.exe /change standby-timeout-dc 0
powercfg.exe /change monitor-timeout-ac 0

$status = [ordered]@{
    InitializedAt = (Get-Date).ToString('o')
    ComputerName = $env:COMPUTERNAME
    User = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    UacDisabled = $true
    HibernateDisabled = $true
    LabRoot = $labRoot
}

$status | ConvertTo-Json | Set-Content `
    -LiteralPath (Join-Path $labRoot 'guest-bootstrap.json') `
    -Encoding UTF8

Restart-Computer -Force
