[CmdletBinding()]
param(
    [string]$Root = (Join-Path $PSScriptRoot '..\..'),
    [string]$OutputDirectory = $PSScriptRoot,
    [string[]]$ExcludedRelativeGlobs = @(),
    [string[]]$ExcludedExtensions = @()
)

$ErrorActionPreference = 'Stop'
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$outputPath = (Resolve-Path -LiteralPath $OutputDirectory).Path
$metadataRelative = [IO.Path]::GetRelativePath($rootPath, $outputPath).Replace('\', '/')
$excludedPrefixes = @('.git', 'lfs', $metadataRelative)

function Get-RelativePath([string]$Path) {
    return [IO.Path]::GetRelativePath($rootPath, $Path).Replace('\', '/')
}

function Test-IsExcluded([string]$RelativePath) {
    foreach ($prefix in $excludedPrefixes) {
        if ($RelativePath -eq $prefix -or $RelativePath.StartsWith($prefix + '/', [StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    foreach ($glob in $ExcludedRelativeGlobs) {
        if ($RelativePath -like $glob) {
            return $true
        }
    }
    return $false
}

$files = @(Get-ChildItem -LiteralPath $rootPath -File -Recurse -Force | Where-Object {
    (-not (Test-IsExcluded (Get-RelativePath $_.FullName))) -and
    ($ExcludedExtensions -notcontains $_.Extension.ToLowerInvariant())
} | Sort-Object { Get-RelativePath $_.FullName })

$directories = @(Get-ChildItem -LiteralPath $rootPath -Directory -Recurse -Force | ForEach-Object {
    Get-RelativePath $_.FullName
} | Where-Object { -not (Test-IsExcluded $_) } | Sort-Object)

$representativeByHash = @{}
$entries = [Collections.Generic.List[object]]::new()
$representatives = [Collections.Generic.List[string]]::new()
$logicalBytes = [int64]0
$uniqueBytes = [int64]0

$index = 0
foreach ($file in $files) {
    $index++
    if (($index % 250) -eq 0) {
        Write-Progress -Activity 'Hashing AAWC pre-cleanup snapshot' -Status "$index / $($files.Count) files" -PercentComplete (($index / $files.Count) * 100)
    }
    $relative = Get-RelativePath $file.FullName
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $logicalBytes += $file.Length
    if ($representativeByHash.ContainsKey($hash)) {
        $contentPath = $representativeByHash[$hash]
        $stored = $false
    }
    else {
        $contentPath = $relative
        $stored = $true
        $representativeByHash[$hash] = $relative
        $representatives.Add($relative)
        $uniqueBytes += $file.Length
    }
    $entries.Add([ordered]@{
        path = $relative
        bytes = [int64]$file.Length
        sha256 = $hash
        last_write_time_utc = $file.LastWriteTimeUtc.ToString('o')
        content_path = $contentPath
        stored_in_payload = $stored
    })
}
Write-Progress -Activity 'Hashing AAWC pre-cleanup snapshot' -Completed

$manifest = [ordered]@{
    schema = 'aawc-pre-cleanup-snapshot-v1'
    snapshot_id = 'pre-cleanup-2026-11-11'
    created_utc = [DateTime]::UtcNow.ToString('o')
    source_root_name = Split-Path -Leaf $rootPath
    excluded_paths = $excludedPrefixes
    excluded_relative_globs = $ExcludedRelativeGlobs
    excluded_extensions = $ExcludedExtensions
    directory_count = $directories.Count
    file_count = $entries.Count
    logical_bytes = $logicalBytes
    unique_payload_count = $representatives.Count
    unique_payload_bytes = $uniqueBytes
    directories = $directories
    files = $entries
}

$manifestPath = Join-Path $outputPath 'snapshot-manifest.json'
$representativesPath = Join-Path $outputPath 'payload-representatives.txt'
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding utf8
[IO.File]::WriteAllText(
    $representativesPath,
    (($representatives -join "`n") + "`n"),
    [Text.UTF8Encoding]::new($false)
)

$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
[pscustomobject]@{
    Manifest = $manifestPath
    ManifestSHA256 = $manifestHash
    FileCount = $entries.Count
    DirectoryCount = $directories.Count
    LogicalGiB = [math]::Round($logicalBytes / 1GB, 3)
    UniquePayloadCount = $representatives.Count
    UniquePayloadGiB = [math]::Round($uniqueBytes / 1GB, 3)
}
