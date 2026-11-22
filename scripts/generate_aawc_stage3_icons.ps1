[CmdletBinding()]
param(
    [switch]$Check
)

$ErrorActionPreference = 'Stop'

# Build the 131 authored Stage 3 building icons from the nine retained source
# sheets. Sheets 01-08 are 4x4 grids in alphabetical chain order; sheet 09 is
# the final workshop icon. The runtime assets deliberately use the same raw
# 256x256 BGRA DDS layout as the established AAWC blocker icons.
$root = Split-Path -Parent $PSScriptRoot
$cataloguePath = Join-Path $root 'catalogue/stage3/catalogue.json'
$sourceDir = Join-Path $root 'catalogue/stage3/icon_sources'
$outputDir = Join-Path $root 'mod/AGOT_Alternate_World_Compatch/gfx/interface/icons/building_types'
$headerTemplate = Join-Path $outputDir 'aawc_blocker_blight_a.dds'
$primitiveLibrary = Join-Path $PSScriptRoot 'aawc_stage3_icon_primitives.ps1'

if (-not (Test-Path -LiteralPath $cataloguePath)) { throw "Missing catalogue: $cataloguePath" }
if (-not (Test-Path -LiteralPath $headerTemplate)) { throw "Missing DDS header template: $headerTemplate" }
if (-not (Test-Path -LiteralPath $primitiveLibrary)) { throw "Missing icon primitive library: $primitiveLibrary" }
. $primitiveLibrary

$chains = @((Get-Content -Raw -LiteralPath $cataloguePath | ConvertFrom-Json).chains |
    ForEach-Object { $_.id } | Sort-Object)
if ($chains.Count -ne 131) { throw "Expected 131 Stage 3 chains, found $($chains.Count)" }

# Do not infer sheet positions from alphabetical order. The generated artwork
# was art-directed in these purpose-led sheets, and this manifest is the source
# of truth for its chain-to-cell inventory.
$chainOrder = @(
    'aawc_amber_collection', 'aawc_apiaries', 'aawc_archery_ranges', 'aawc_archery_yards',
    'aawc_barracks', 'aawc_blacksmiths', 'aawc_breweries', 'aawc_building_moat',
    'aawc_burial_site', 'aawc_camel_farms', 'aawc_capital_bureau', 'aawc_caravanserai',
    'aawc_cavalry_courses', 'aawc_cereal_fields', 'aawc_citadel_shrine', 'aawc_coastal_fisheries',
    'aawc_common_tradeport', 'aawc_curtain_walls', 'aawc_dragon_kiln', 'aawc_duchy_agricultural_estates',
    'aawc_duchy_civic_court', 'aawc_duchy_grand_harbor', 'aawc_duchy_grand_hospital', 'aawc_duchy_military_college',
    'aawc_duchy_royal_theatre', 'aawc_elephant_pens', 'aawc_examination_hall', 'aawc_farm_estates',
    'aawc_glass_gardens', 'aawc_godswood', 'aawc_gold_mines', 'aawc_great_megalith',
    'aawc_guild_halls', 'aawc_hill_farms', 'aawc_hill_forts', 'aawc_hillside_grazing',
    'aawc_horse_pastures', 'aawc_hospices', 'aawc_hunting_grounds', 'aawc_idjang_forts',
    'aawc_infirmaries', 'aawc_iron_island_mines', 'aawc_ironwood', 'aawc_irrigation_estates',
    'aawc_jousting_lists', 'aawc_kora_kora_yards', 'aawc_leatherworkers', 'aawc_leisure_palace',
    'aawc_lighthouse', 'aawc_logging_camps', 'aawc_longhouses', 'aawc_march',
    'aawc_market_villages', 'aawc_megalith', 'aawc_military_academy', 'aawc_military_camps',
    'aawc_monastic_schools', 'aawc_monument_works', 'aawc_murex_farm', 'aawc_mustering_fields',
    'aawc_oath_faithful_building', 'aawc_oath_poor_building', 'aawc_oath_warriors_building', 'aawc_orchards',
    'aawc_outposts', 'aawc_paddy_fields', 'aawc_palisades', 'aawc_pastures',
    'aawc_peat_quarries', 'aawc_pirate_control', 'aawc_pirate_economic', 'aawc_pirate_fortification',
    'aawc_pirate_military', 'aawc_pirate_supply', 'aawc_pirate_troop', 'aawc_plantations',
    'aawc_powder_magazine', 'aawc_public_baths', 'aawc_public_squares', 'aawc_qanats',
    'aawc_quarries', 'aawc_ramparts', 'aawc_regimental_grounds', 'aawc_river_docks',
    'aawc_river_fisheries', 'aawc_royal_armory', 'aawc_royal_forest', 'aawc_royal_garden',
    'aawc_sacred_pool', 'aawc_saltworks', 'aawc_scholars_quarters', 'aawc_scholastic_guilds',
    'aawc_scriptorium', 'aawc_sewers', 'aawc_shipwrights', 'aawc_siege_works',
    'aawc_silver_mines', 'aawc_slave_camps', 'aawc_slave_diplomacy', 'aawc_slave_intrigue',
    'aawc_slave_learning', 'aawc_slave_martial', 'aawc_slave_stewardship', 'aawc_smiths',
    'aawc_spice_plantation', 'aawc_stables', 'aawc_steppe_farms', 'aawc_stilted_granaries',
    'aawc_tax_assessor', 'aawc_temple_citadel', 'aawc_terraced_farms', 'aawc_tower_of_silence',
    'aawc_trade_guilds', 'aawc_tribe', 'aawc_urban_farms', 'aawc_urban_tenements',
    'aawc_vihara_halls', 'aawc_village_cottages', 'aawc_vineyard', 'aawc_wantilan',
    'aawc_war_camps', 'aawc_warrior_lodges', 'aawc_watchtowers', 'aawc_water_temples',
    'aawc_watermills', 'aawc_waterworks', 'aawc_wind_furnace', 'aawc_windmills',
    'aawc_charnel_grounds', 'aawc_city_walls', 'aawc_workshops'
)
if ($chainOrder.Count -ne 131 -or (Compare-Object -ReferenceObject $chains -DifferenceObject ($chainOrder | Sort-Object))) {
    throw 'Stage 3 icon inventory is not an exact permutation of catalogue chains'
}

$expected = @{}
for ($index = 0; $index -lt $chainOrder.Count; $index++) {
    $sheet = [Math]::Floor($index / 16) + 1
    $cell = $index % 16
    $expected[$chainOrder[$index]] = [PSCustomObject]@{
        Sheet = ('aawc_stage3_icons_{0:D2}.png' -f [int]$sheet)
        Column = $cell % 4
        Row = [Math]::Floor($cell / 4)
        Output = ($chainOrder[$index] + '.dds')
    }
}

foreach ($entry in $expected.Values) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceDir $entry.Sheet))) {
        throw "Missing generated Stage 3 icon source sheet: $($entry.Sheet)"
    }
}

function Write-AawcStage3SourceSheets {
    foreach ($sheetNumber in 1..9) {
        $sheetName = 'aawc_stage3_icons_{0:D2}.png' -f $sheetNumber
        $sheetPath = Join-Path $sourceDir $sheetName
        $sheet = [System.Drawing.Bitmap]::new(1024, 1024, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            $graphics = [System.Drawing.Graphics]::FromImage($sheet)
            try {
                $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
                $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::None
                $graphics.Clear([System.Drawing.Color]::Transparent)
                for ($index = 0; $index -lt $chainOrder.Count; $index++) {
                    $entry = $expected[$chainOrder[$index]]
                    if ($entry.Sheet -ne $sheetName) { continue }
                    $icon = New-AawcStage3Icon -ChainId $chainOrder[$index] -Index $index
                    try {
                        $graphics.DrawImageUnscaled($icon, $entry.Column * 256, $entry.Row * 256)
                    } finally { $icon.Dispose() }
                }
            } finally { $graphics.Dispose() }
            $sheet.Save($sheetPath, [System.Drawing.Imaging.ImageFormat]::Png)
        } finally { $sheet.Dispose() }
    }
}

function Test-DdsAsset([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -ne 262272) { return $false }
    if ([Text.Encoding]::ASCII.GetString($bytes, 0, 4) -ne 'DDS ') { return $false }
    if ([BitConverter]::ToUInt32($bytes, 12) -ne 256 -or
        [BitConverter]::ToUInt32($bytes, 16) -ne 256) { return $false }
    $transparent = 0
    $opaque = 0
    for ($offset = 128; $offset -lt $bytes.Length; $offset += 4) {
        if ($bytes[$offset] -ne 0 -or $bytes[$offset + 1] -ne 0 -or $bytes[$offset + 2] -ne 0) { return $false }
        if ($bytes[$offset + 3] -eq 0) { $transparent++ }
        elseif ($bytes[$offset + 3] -eq 255) { $opaque++ }
        else { return $false }
    }
    return $transparent -gt 0 -and $opaque -gt 0
}

if ($Check) {
    $missing = @($expected.Values | Where-Object { -not (Test-DdsAsset (Join-Path $outputDir $_.Output)) })
    if ($missing.Count) { throw "Missing or invalid Stage 3 icon assets: $($missing.Output -join ', ')" }
    Write-Output "PASS: 131 chain-specific Stage 3 DDS icons resolve"
    exit 0
}

Add-Type -AssemblyName System.Drawing
$null = New-Item -ItemType Directory -Path $sourceDir -Force
Write-AawcStage3SourceSheets
$header = [System.IO.File]::ReadAllBytes($headerTemplate)[0..127]
foreach ($sheetNumber in 1..9) {
    $sheetPath = Join-Path $sourceDir ('aawc_stage3_icons_{0:D2}.png' -f $sheetNumber)
    $source = [System.Drawing.Bitmap]::new($sheetPath)
    try {
        $atlas = [System.Drawing.Bitmap]::new(1024, 1024, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            $graphics = [System.Drawing.Graphics]::FromImage($atlas)
            try {
                $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
                $graphics.Clear([System.Drawing.Color]::Transparent)
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::None
                $graphics.DrawImageUnscaled($source, 0, 0)
            } finally { $graphics.Dispose() }
            foreach ($entry in ($expected.Values | Where-Object { $_.Sheet -eq [IO.Path]::GetFileName($sheetPath) })) {
                $crop = $atlas.Clone([System.Drawing.Rectangle]::new($entry.Column * 256, $entry.Row * 256, 256, 256), [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
                try {
                    $rect = [System.Drawing.Rectangle]::new(0, 0, 256, 256)
                    $data = $crop.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
                    try {
                        $pixels = New-Object byte[] ($data.Stride * 256)
                        [Runtime.InteropServices.Marshal]::Copy($data.Scan0, $pixels, 0, $pixels.Length)
                    } finally { $crop.UnlockBits($data) }
                    [System.IO.File]::WriteAllBytes((Join-Path $outputDir $entry.Output), ($header + $pixels))
                } finally { $crop.Dispose() }
            }
        } finally { $atlas.Dispose() }
    } finally { $source.Dispose() }
}

& $PSCommandPath -Check
