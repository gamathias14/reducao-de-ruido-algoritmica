[CmdletBinding()]
param(
    [string]$RuntimeRoot = (
        Join-Path $env:LOCALAPPDATA "PTC3527-Private\vm_runtime"
    ),
    [string]$OriginalVmName = "PTC3527-SYSVAD-LAB",
    [string]$FastVmName = "PTC3527-SYSVAD-LAB-FAST",
    [string]$ExpectedOriginalSnapshot = "checkpoint37-pre-pop-diagnostics",
    [string]$ExpectedFastSnapshot = "checkpoint45-causal-wpt-validated",
    [Parameter(Mandatory = $true)]
    [string]$CredentialSource,
    [Parameter(Mandatory = $true)]
    [string]$OriginalConfigSource
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$credentialDestination = Join-Path $RuntimeRoot "lab-autounattend.xml"
$configDestination = Join-Path $RuntimeRoot "original-vm-config.vbox"
$manifestPath = Join-Path $RuntimeRoot "manifest.json"

function Get-VmProperty {
    param(
        [Parameter(Mandatory = $true)][string]$TargetVm,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $output = @(& $vbox showvminfo $TargetVm --machinereadable 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to query VM $TargetVm."
    }
    $line = $output |
        Where-Object { $_ -like "$Name=*" } |
        Select-Object -First 1
    if ($line -notmatch '^[^=]+="([^"]*)"$') {
        throw "VM property unavailable: $TargetVm / $Name."
    }
    return $Matches[1]
}

foreach ($path in @($vbox, $CredentialSource, $OriginalConfigSource)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required migration source is missing: $path"
    }
}
if ((Get-VmProperty -TargetVm $OriginalVmName -Name "VMState") -ne "poweroff") {
    throw "The original VM must be powered off during migration."
}
if ((Get-VmProperty -TargetVm $FastVmName -Name "VMState") -ne "poweroff") {
    throw "The fast VM clone must be powered off during migration."
}
$originalSnapshot = Get-VmProperty `
    -TargetVm $OriginalVmName `
    -Name "CurrentSnapshotName"
if ($originalSnapshot -ne $ExpectedOriginalSnapshot) {
    throw "The original VM is not at the expected protected snapshot."
}
$fastSnapshot = Get-VmProperty `
    -TargetVm $FastVmName `
    -Name "CurrentSnapshotName"
if ($fastSnapshot -ne $ExpectedFastSnapshot) {
    throw "The fast VM clone is not at the approved snapshot."
}

$systemDrive = Get-PSDrive -Name C
if ($systemDrive.Free -lt 20GB) {
    throw "At least 20 GiB free is required on the SSD before migration."
}

New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
$directorySecurity = New-Object Security.AccessControl.DirectorySecurity
$directorySecurity.SetAccessRuleProtection($true, $false)
$inheritance = (
    [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
    [Security.AccessControl.InheritanceFlags]::ObjectInherit
)
$propagation = [Security.AccessControl.PropagationFlags]::None
foreach ($sidValue in @("S-1-5-18", "S-1-5-32-544")) {
    $account = (
        New-Object Security.Principal.SecurityIdentifier($sidValue)
    ).Translate([Security.Principal.NTAccount])
    $directorySecurity.AddAccessRule(
        (New-Object Security.AccessControl.FileSystemAccessRule(
            $account,
            [Security.AccessControl.FileSystemRights]::FullControl,
            $inheritance,
            $propagation,
            [Security.AccessControl.AccessControlType]::Allow
        ))
    )
}
$currentAccount = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$directorySecurity.AddAccessRule(
    (New-Object Security.AccessControl.FileSystemAccessRule(
        $currentAccount,
        [Security.AccessControl.FileSystemRights]::FullControl,
        $inheritance,
        $propagation,
        [Security.AccessControl.AccessControlType]::Allow
    ))
)
Set-Acl -LiteralPath $RuntimeRoot -AclObject $directorySecurity

Copy-Item -LiteralPath $CredentialSource -Destination $credentialDestination -Force
Copy-Item -LiteralPath $OriginalConfigSource -Destination $configDestination -Force

$credentialHash = (
    Get-FileHash -LiteralPath $credentialDestination -Algorithm SHA256
).Hash
$configHash = (
    Get-FileHash -LiteralPath $configDestination -Algorithm SHA256
).Hash
if ($credentialHash -ne (
    Get-FileHash -LiteralPath $CredentialSource -Algorithm SHA256
).Hash) {
    throw "Credential copy verification failed."
}
if ($configHash -ne (
    Get-FileHash -LiteralPath $OriginalConfigSource -Algorithm SHA256
).Hash) {
    throw "Original VM configuration copy verification failed."
}

$manifest = [ordered]@{
    schema_version = 1
    created_at = (Get-Date).ToString("o")
    purpose = "SSD-local runtime inputs for active VM automation"
    storage_policy = [ordered]@{
        active_clone = "SSD"
        original_vm = "external archive, unchanged"
        full_original_vm_copied = $false
    }
    vm = [ordered]@{
        original_name = $OriginalVmName
        original_snapshot_name = $originalSnapshot
        original_snapshot_uuid = Get-VmProperty `
            -TargetVm $OriginalVmName `
            -Name "CurrentSnapshotUUID"
        fast_name = $FastVmName
        fast_snapshot_name = $fastSnapshot
        fast_snapshot_uuid = Get-VmProperty `
            -TargetVm $FastVmName `
            -Name "CurrentSnapshotUUID"
    }
    files = [ordered]@{
        credential = [ordered]@{
            name = Split-Path -Leaf $credentialDestination
            source_path = $CredentialSource
            length = (Get-Item -LiteralPath $credentialDestination).Length
            sha256 = $credentialHash
        }
        original_config = [ordered]@{
            name = Split-Path -Leaf $configDestination
            source_path = $OriginalConfigSource
            length = (Get-Item -LiteralPath $configDestination).Length
            sha256 = $configHash
        }
    }
}
$temporaryManifest = "$manifestPath.tmp"
$manifest | ConvertTo-Json -Depth 8 |
    Set-Content -LiteralPath $temporaryManifest -Encoding UTF8
Move-Item -LiteralPath $temporaryManifest -Destination $manifestPath -Force

. (Join-Path $PSScriptRoot "VmSsdRuntime.ps1")
$runtime = Get-VmSsdRuntime -RuntimeRoot $RuntimeRoot
[ordered]@{
    ready = $true
    runtime_root = $runtime.Root
    manifest = $runtime.ManifestPath
    copied_bytes = (
        (Get-Item -LiteralPath $credentialDestination).Length +
        (Get-Item -LiteralPath $configDestination).Length
    )
    original_vm_copied = $false
    external_source_modified = $false
} | ConvertTo-Json -Depth 4
