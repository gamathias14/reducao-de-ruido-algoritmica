[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$IsoPath,

    [Parameter(Mandatory)]
    [securestring]$Password,

    [string]$VmName = 'PTC3527-SYSVAD-LAB',
    [string]$VmRoot = (
        Join-Path $env:LOCALAPPDATA 'PTC3527-VM'
    ),
    [int]$MemoryMB = 8192,
    [int]$CpuCount = 4,
    [int]$DiskSizeMB = 131072,
    [int]$ImageIndex = 4
)

$ErrorActionPreference = 'Stop'
$vbox = 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'

if (-not (Test-Path -LiteralPath $vbox -PathType Leaf)) {
    throw 'VBoxManage nao foi encontrado. Instale o Oracle VirtualBox primeiro.'
}

$root = [System.IO.Path]::GetFullPath($VmRoot)
$driveRoot = [System.IO.Path]::GetPathRoot($root)
if (-not (Test-Path -LiteralPath $driveRoot -PathType Container)) {
    throw "A unidade de destino nao esta disponivel: $driveRoot"
}

$existing = & $vbox list vms
if ($existing -match [regex]::Escape('"' + $VmName + '"')) {
    throw "A VM '$VmName' ja existe."
}

$vmFolder = Join-Path $root $VmName
$diskPath = Join-Path $vmFolder "$VmName.vdi"
New-Item -ItemType Directory -Path $vmFolder -Force | Out-Null

& $vbox createvm --name $VmName --ostype Windows11_64 --basefolder $root --register
& $vbox modifyvm $VmName `
    --memory $MemoryMB `
    --cpus $CpuCount `
    --cpu-execution-cap 90 `
    --firmware efi `
    --tpm-type 2.0 `
    --chipset piix3 `
    --ioapic on `
    --paravirt-provider hyperv `
    --nested-paging on `
    --graphicscontroller vboxsvga `
    --vram 128 `
    --accelerate-3d off `
    --nic1 nat `
    --nic-type1 82540EM `
    --audio-enabled on `
    --audio-controller hda `
    --audio-in off `
    --audio-out on `
    --clipboard-mode disabled `
    --drag-and-drop disabled `
    --usb-xhci on `
    --boot1 dvd `
    --boot2 disk `
    --boot3 none `
    --boot4 none `
    --snapshot-folder (Join-Path $vmFolder 'Snapshots')

& $vbox createmedium disk --filename $diskPath --size $DiskSizeMB --format VDI --variant Standard
& $vbox storagectl $VmName --name 'SATA' --add sata --controller IntelAhci --portcount 4 --bootable on
& $vbox storageattach $VmName --storagectl 'SATA' --port 0 --device 0 --type hdd --medium $diskPath
& $vbox storagectl $VmName --name 'IDE' --add ide
& $vbox storageattach $VmName --storagectl 'IDE' --port 0 --device 0 --type dvddrive --medium $IsoPath

$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    $plainPassword | & $vbox unattended install $VmName `
        --iso $IsoPath `
        --user 'ptc3527' `
        --full-user-name 'PTC3527 Lab' `
        --user-password-file stdin `
        --locale 'pt_BR' `
        --country 'BR' `
        --hostname 'ptc3527-lab.local' `
        --image-index $ImageIndex `
        --install-additions `
        --start-vm headless
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $plainPassword = $null
}

Write-Host "Instalacao iniciada em modo headless: $VmName"
Write-Host "Disco virtual: $diskPath"
