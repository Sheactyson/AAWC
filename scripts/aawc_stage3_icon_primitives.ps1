$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

function New-AawcPointArray([int[]]$Coordinates) {
    if (($Coordinates.Count % 2) -ne 0) { throw 'Point coordinates must be x/y pairs' }
    $points = [System.Drawing.Point[]]::new($Coordinates.Count / 2)
    for ($index = 0; $index -lt $Coordinates.Count; $index += 2) {
        $points[$index / 2] = [System.Drawing.Point]::new($Coordinates[$index], $Coordinates[$index + 1])
    }
    return ,$points
}

function Add-AawcPolygon($Graphics, $Brush, [int[]]$Coordinates) {
    $Graphics.FillPolygon($Brush, (New-AawcPointArray $Coordinates))
}

function Add-AawcLine($Graphics, $Pen, [int[]]$Coordinates) {
    $Graphics.DrawLines($Pen, (New-AawcPointArray $Coordinates))
}

function Add-AawcHouse($Graphics, $Brush, [int]$Variant) {
    Add-AawcPolygon $Graphics $Brush @(42, 116, 128, 42, 214, 116)
    $Graphics.FillRectangle($Brush, 58, 108, 140, 104)
    $Graphics.FillRectangle($Brush, 184 - (($Variant % 3) * 18), 62, 18, 58)
    if (($Variant % 2) -eq 0) { $Graphics.FillRectangle($Brush, 28, 198, 200, 18) }
}

function Add-AawcFort($Graphics, $Brush, [int]$Variant) {
    $Graphics.FillRectangle($Brush, 42, 104, 172, 108)
    $Graphics.FillRectangle($Brush, 28, 72, 50, 144)
    $Graphics.FillRectangle($Brush, 178, 72, 50, 144)
    foreach ($x in @(28, 53, 178, 203)) { $Graphics.FillRectangle($Brush, $x, 54, 18, 34) }
    for ($x = 86; $x -le 158; $x += 36) { $Graphics.FillRectangle($Brush, $x, 86, 18, 34) }
    if (($Variant % 2) -eq 1) { Add-AawcPolygon $Graphics $Brush @(28, 54, 53, 24, 78, 54) }
}

function Add-AawcFarm($Graphics, $Brush, $Pen, [int]$Variant) {
    $Graphics.FillRectangle($Brush, 30, 202, 196, 18)
    for ($x = 54; $x -le 202; $x += 37) {
        Add-AawcLine $Graphics $Pen @($x, 205, $($x + ((($Variant % 3) - 1) * 5)), 70)
        Add-AawcPolygon $Graphics $Brush @($x, 92, $($x - 26), 68, $($x - 4), 112)
        Add-AawcPolygon $Graphics $Brush @($x, 126, $($x + 26), 102, $($x + 4), 146)
    }
}

function Add-AawcWater($Graphics, $Brush, $Pen, [int]$Variant) {
    Add-AawcPolygon $Graphics $Brush @(34, 150, 222, 150, 194, 198, 62, 198)
    $Graphics.FillRectangle($Brush, 118, 58, 18, 94)
    Add-AawcPolygon $Graphics $Brush @(136, 62, 194, 134, 136, 134)
    if (($Variant % 2) -eq 1) { Add-AawcPolygon $Graphics $Brush @(116, 82, 62, 136, 116, 136) }
    Add-AawcLine $Graphics $Pen @(30, 222, 68, 206, 106, 222, 144, 206, 182, 222, 226, 206)
}

function Add-AawcMine($Graphics, $Brush, $Pen, [int]$Variant) {
    Add-AawcPolygon $Graphics $Brush @(28, 210, 88, 86, 126, 144, 164, 64, 228, 210)
    Add-AawcLine $Graphics $Pen @(62, 70, 190, 190)
    Add-AawcLine $Graphics $Pen @(54, 78, 92, 42, 130, 78)
    if (($Variant % 2) -eq 1) { $Graphics.FillEllipse($Brush, 174, 44, 34, 34) }
}

function Add-AawcMilitary($Graphics, $Brush, $Pen, [int]$Variant) {
    Add-AawcPolygon $Graphics $Brush @(128, 40, 202, 70, 190, 164, 128, 218, 66, 164, 54, 70)
    Add-AawcLine $Graphics $Pen @(42, 208, 210, 52)
    Add-AawcLine $Graphics $Pen @(46, 48, 214, 208)
    if (($Variant % 3) -eq 0) { $Graphics.FillRectangle($Brush, 92, 104, 72, 18) }
}

function Add-AawcCivic($Graphics, $Brush, $Pen, [int]$Variant) {
    Add-AawcPolygon $Graphics $Brush @(34, 92, 128, 40, 222, 92)
    $Graphics.FillRectangle($Brush, 30, 92, 196, 18)
    foreach ($x in @(52, 94, 136, 178)) { $Graphics.FillRectangle($Brush, $x, 104, 22, 92) }
    $Graphics.FillRectangle($Brush, 26, 194, 204, 24)
    if (($Variant % 2) -eq 1) { $Graphics.FillEllipse($Brush, 108, 52, 40, 40) }
}

function Add-AawcFaith($Graphics, $Brush, $Pen, [int]$Variant) {
    Add-AawcPolygon $Graphics $Brush @(44, 120, 128, 42, 212, 120)
    $Graphics.FillRectangle($Brush, 58, 112, 140, 102)
    $Graphics.FillRectangle($Brush, 118, 22, 20, 72)
    $Graphics.FillRectangle($Brush, 96, 42, 64, 18)
    if (($Variant % 2) -eq 1) { $Graphics.FillEllipse($Brush, 102, 130, 52, 52) }
}

function Add-AawcIndustry($Graphics, $Brush, $Pen, [int]$Variant) {
    $Graphics.FillEllipse($Brush, 68, 58, 120, 120)
    foreach ($angle in 0..7) {
        $x = 118 + [int](72 * [Math]::Cos($angle * [Math]::PI / 4))
        $y = 108 + [int](72 * [Math]::Sin($angle * [Math]::PI / 4))
        $Graphics.FillRectangle($Brush, $x, $y, 28, 28)
    }
    $Graphics.FillRectangle($Brush, 42, 184, 172, 30)
    if (($Variant % 2) -eq 1) { Add-AawcPolygon $Graphics $Brush @(74, 54, 110, 24, 146, 54) }
}

function Add-AawcNature($Graphics, $Brush, $Pen, [int]$Variant) {
    $Graphics.FillRectangle($Brush, 116, 104, 24, 116)
    $Graphics.FillEllipse($Brush, 70, 40, 116, 108)
    $Graphics.FillEllipse($Brush, 40, 82, 92, 80)
    $Graphics.FillEllipse($Brush, 124, 82, 92, 80)
    if (($Variant % 2) -eq 1) { $Graphics.FillEllipse($Brush, 102, 20, 52, 52) }
}

function Add-AawcAnimal($Graphics, $Brush, $Pen, [int]$Variant) {
    $Graphics.FillEllipse($Brush, 54, 92, 136, 86)
    $Graphics.FillEllipse($Brush, 160, 66, 58, 58)
    $Graphics.FillRectangle($Brush, 78, 158, 20, 62)
    $Graphics.FillRectangle($Brush, 154, 158, 20, 62)
    Add-AawcPolygon $Graphics $Brush @(184, 72, 196, 38, 208, 78)
    Add-AawcLine $Graphics $Pen @(62, 104, 34, 72)
    if (($Variant % 2) -eq 1) { $Graphics.FillEllipse($Brush, 182, 86, 10, 10) }
}

function Add-AawcPirate($Graphics, $Brush, $Pen, [int]$Variant) {
    $Graphics.FillEllipse($Brush, 62, 38, 132, 126)
    Add-AawcPolygon $Graphics $Brush @(84, 138, 172, 138, 160, 202, 96, 202)
    Add-AawcLine $Graphics $Pen @(44, 212, 212, 54)
    Add-AawcLine $Graphics $Pen @(44, 54, 212, 212)
    if (($Variant % 2) -eq 1) { $Graphics.FillRectangle($Brush, 42, 30, 172, 22) }
}

function Add-AawcIdentityMarks($Graphics, $Brush, [int]$Index) {
    # A compact eight-position maker's mark keeps similar chains distinct
    # without introducing color or a baked background. The catalogue index is
    # stable and unique across the 131-chain registry.
    for ($bit = 0; $bit -lt 8; $bit++) {
        if (($Index -band (1 -shl $bit)) -ne 0) {
            $x = 18 + ($bit * 28)
            if (($bit % 2) -eq 0) { $Graphics.FillEllipse($Brush, $x, 226, 12, 12) }
            else { $Graphics.FillRectangle($Brush, $x, 226, 12, 12) }
        }
    }
}

function New-AawcStage3Icon([string]$ChainId, [int]$Index) {
    $bitmap = [System.Drawing.Bitmap]::new(256, 256, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $brush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::Black)
    $pen = [System.Drawing.Pen]::new([System.Drawing.Color]::Black, 18)
    try {
        $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::None
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::None
        $graphics.Clear([System.Drawing.Color]::Transparent)
        $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Square
        $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Square
        $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Miter

        $name = $ChainId -replace '^aawc_', ''
        $variant = $Index % 6
        if ($name -match 'pirate|slave_') { Add-AawcPirate $graphics $brush $pen $variant }
        elseif ($name -match 'camel|cavalry|elephant|horse|kora_kora|stables') { Add-AawcAnimal $graphics $brush $pen $variant }
        elseif ($name -match 'harbor|tradeport|dock|fisher|shipwright|murex|coastal|lighthouse|water_temples') { Add-AawcWater $graphics $brush $pen $variant }
        elseif ($name -match 'mine|quarr|peat|saltwork|amber|logging|ironwood') { Add-AawcMine $graphics $brush $pen $variant }
        elseif ($name -match 'archery|barracks|military|war_|warrior|joust|mustering|regimental|siege|armory|powder|march$|hunting') { Add-AawcMilitary $graphics $brush $pen $variant }
        elseif ($name -match 'wall|fort|rampart|palisade|moat|outpost|watchtower|citadel') { Add-AawcFort $graphics $brush $variant }
        elseif ($name -match 'farm|field|pasture|orchard|vineyard|plantation|paddy|terraced|grazing|irrigation|qanat|apiaries|spice') { Add-AawcFarm $graphics $brush $pen $variant }
        elseif ($name -match 'shrine|temple|monastic|vihara|godswood|oath_|burial|charnel|sacred|tower_of_silence') { Add-AawcFaith $graphics $brush $pen $variant }
        elseif ($name -match 'smith|workshop|brew|kiln|furnace|mill|leather|glass|sewer|waterworks') { Add-AawcIndustry $graphics $brush $pen $variant }
        elseif ($name -match 'bureau|guild|market|tax|public|examination|scholar|scriptorium|hospital|infirmar|hospice|academy|monument|theatre|leisure|garden') { Add-AawcCivic $graphics $brush $pen $variant }
        elseif ($name -match 'forest|wood|garden') { Add-AawcNature $graphics $brush $pen $variant }
        else { Add-AawcHouse $graphics $brush $variant }

        Add-AawcIdentityMarks $graphics $brush $Index
        return $bitmap
    } catch {
        $bitmap.Dispose()
        throw
    } finally {
        $pen.Dispose()
        $brush.Dispose()
        $graphics.Dispose()
    }
}
