Set-StrictMode -Version Latest

function Get-VmSsdRuntime {
    [CmdletBinding()]
    param(
        [string]$RuntimeRoot = (
            Join-Path $env:LOCALAPPDATA "PTC3527-Private\vm_runtime"
        )
    )

    $manifestPath = Join-Path $RuntimeRoot "manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw (
            "SSD VM runtime is not initialized: $manifestPath. Run " +
            "scripts\vm\Initialize-VmSsdRuntime.ps1 first."
        )
    }

    $manifest = Get-Content -LiteralPath $manifestPath -Raw |
        ConvertFrom-Json
    if ([int]$manifest.schema_version -ne 1) {
        throw "Unsupported SSD VM runtime manifest schema."
    }

    $credentialPath = Join-Path $RuntimeRoot $manifest.files.credential.name
    $originalConfigPath = Join-Path `
        $RuntimeRoot `
        $manifest.files.original_config.name
    foreach ($entry in @(
        @{
            label = "credential"
            path = $credentialPath
            hash = $manifest.files.credential.sha256
        },
        @{
            label = "original VM configuration reference"
            path = $originalConfigPath
            hash = $manifest.files.original_config.sha256
        }
    )) {
        if (-not (Test-Path -LiteralPath $entry.path -PathType Leaf)) {
            throw "Missing SSD runtime $($entry.label): $($entry.path)"
        }
        $actualHash = (
            Get-FileHash -LiteralPath $entry.path -Algorithm SHA256
        ).Hash
        if ($actualHash -ne $entry.hash) {
            throw "SSD runtime hash mismatch for $($entry.label)."
        }
    }

    [pscustomobject]@{
        Root = $RuntimeRoot
        ManifestPath = $manifestPath
        Manifest = $manifest
        CredentialPath = $credentialPath
        OriginalConfigPath = $originalConfigPath
    }
}

function Get-LabPasswordFromRuntime {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]$Runtime
    )

    [xml]$unattend = Get-Content `
        -LiteralPath $Runtime.CredentialPath `
        -Raw
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
        throw "The SSD runtime credential does not contain one unique password."
    }
    return $values[0]
}

function Get-OriginalVmExternalAudit {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]$Runtime,
        [Parameter(Mandatory = $true)][string]$VBoxPath,
        [Parameter(Mandatory = $true)][string]$OriginalVmName
    )

    $sourcePath = [string]$Runtime.Manifest.files.original_config.source_path
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        return [pscustomobject]@{
            available = $false
            state = "external_source_unavailable"
            config_hash = $null
            config_hash_matches_manifest = $null
            snapshot_uuid = $null
        }
    }

    $sourceHash = (
        Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256
    ).Hash
    if ($sourceHash -ne $Runtime.Manifest.files.original_config.sha256) {
        throw "The external original VM configuration differs from the manifest."
    }

    function Get-ExternalVmProperty {
        param([string]$Name)

        $deadline = (Get-Date).AddSeconds(15)
        do {
            $oldPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $output = @(
                & $VBoxPath showvminfo $OriginalVmName --machinereadable 2>&1
            )
            $exitCode = $LASTEXITCODE
            $ErrorActionPreference = $oldPreference
            if ($exitCode -eq 0) {
                $line = $output |
                    Where-Object { $_ -like "$Name=*" } |
                    Select-Object -First 1
                if ($line -match '^[^=]+="([^"]*)"$') {
                    return $Matches[1]
                }
            }
            Start-Sleep -Milliseconds 500
        } while ((Get-Date) -lt $deadline)
        throw "External original VM property unavailable: $Name."
    }

    $state = Get-ExternalVmProperty -Name "VMState"
    if ($state -ne "poweroff") {
        throw "The external original VM must remain powered off."
    }

    [pscustomobject]@{
        available = $true
        state = $state
        config_hash = $sourceHash
        config_hash_matches_manifest = $true
        snapshot_uuid = Get-ExternalVmProperty -Name "CurrentSnapshotUUID"
    }
}

function Compare-OriginalVmExternalAudit {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]$Before,
        [Parameter(Mandatory = $true)]$After
    )

    [ordered]@{
        external_source_audited = [bool]($Before.available -and $After.available)
        state = $After.state
        config_hash_unchanged = if ($Before.available -and $After.available) {
            $Before.config_hash -eq $After.config_hash
        } else {
            $null
        }
        snapshot_unchanged = if ($Before.available -and $After.available) {
            $Before.snapshot_uuid -eq $After.snapshot_uuid
        } else {
            $null
        }
        local_reference_verified = $true
    }
}
