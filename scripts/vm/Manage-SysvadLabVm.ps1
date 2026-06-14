[CmdletBinding()]
param(
    [ValidateSet('status', 'start', 'stop', 'poweroff', 'snapshot', 'snapshots')]
    [string]$Action = 'status',
    [string]$VmName = 'PTC3527-SYSVAD-LAB',
    [string]$SnapshotName
)

$ErrorActionPreference = 'Stop'
$vbox = 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'

if (-not (Test-Path -LiteralPath $vbox -PathType Leaf)) {
    throw 'VBoxManage nao foi encontrado.'
}

switch ($Action) {
    'status' {
        & $vbox showvminfo $VmName
    }
    'start' {
        & $vbox startvm $VmName --type headless
    }
    'stop' {
        & $vbox controlvm $VmName acpipowerbutton
    }
    'poweroff' {
        & $vbox controlvm $VmName poweroff
    }
    'snapshot' {
        if ([string]::IsNullOrWhiteSpace($SnapshotName)) {
            throw 'Informe -SnapshotName.'
        }
        & $vbox snapshot $VmName take $SnapshotName --description "PTC3527 lab snapshot: $SnapshotName"
    }
    'snapshots' {
        & $vbox snapshot $VmName list --details
    }
}
