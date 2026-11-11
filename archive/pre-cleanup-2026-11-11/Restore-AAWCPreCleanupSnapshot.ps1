[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$AssetDirectory,
    [Parameter(Mandatory)]
    [string]$Destination,
    [switch]$Verify
)

$ErrorActionPreference = 'Stop'
$assetPath = (Resolve-Path -LiteralPath $AssetDirectory).Path
$manifestPath = Join-Path $PSScriptRoot 'snapshot-manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$parts = @(Get-ChildItem -LiteralPath $assetPath -File -Filter 'aawc-pre-cleanup-2026-11-11.tar.gz.part-*' | Sort-Object Name)
if ($parts.Count -eq 0) { throw 'No snapshot payload parts were found.' }

$destinationPath = [IO.Path]::GetFullPath($Destination)
[IO.Directory]::CreateDirectory($destinationPath) | Out-Null
$combinedPath = Join-Path $assetPath 'aawc-pre-cleanup-2026-11-11.tar.gz'
$output = [IO.File]::Open($combinedPath, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::None)
try {
    foreach ($part in $parts) {
        $input = [IO.File]::OpenRead($part.FullName)
        try { $input.CopyTo($output) } finally { $input.Dispose() }
    }
}
finally { $output.Dispose() }

try {
    tar -xzf $combinedPath -C $destinationPath
    if ($LASTEXITCODE -ne 0) { throw 'tar extraction failed.' }
}
finally {
    Remove-Item -LiteralPath $combinedPath -Force
}

foreach ($directory in $manifest.directories) {
    [IO.Directory]::CreateDirectory((Join-Path $destinationPath $directory)) | Out-Null
}
foreach ($file in $manifest.files) {
    $target = Join-Path $destinationPath $file.path
    if (-not $file.stored_in_payload) {
        [IO.Directory]::CreateDirectory((Split-Path -Parent $target)) | Out-Null
        Copy-Item -LiteralPath (Join-Path $destinationPath $file.content_path) -Destination $target -Force
    }
    [IO.File]::SetLastWriteTimeUtc($target, [DateTime]::Parse($file.last_write_time_utc).ToUniversalTime())
    if ($Verify) {
        if ((Get-Item -LiteralPath $target).Length -ne [int64]$file.bytes) { throw "Length mismatch: $($file.path)" }
        $actual = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $file.sha256) { throw "SHA-256 mismatch: $($file.path)" }
    }
}

[pscustomobject]@{
    Destination = $destinationPath
    RestoredFiles = $manifest.file_count
    Verified = [bool]$Verify
}
