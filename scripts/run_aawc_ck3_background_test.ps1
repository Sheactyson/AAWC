[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$CertificationSession,
    # Benchmark launches auto-start and advance a world before a deliberate
    # fresh baseline can be captured.  Certification therefore permits only
    # the observed manual-start mode.
    [string[]]$GameArguments = @("-debug_mode"),
    [string]$Ck3Executable = $env:AAWC_CK3_EXECUTABLE,
    [string]$Ck3UserDirectory = $(if ($env:AAWC_CK3_USER_DIR) { $env:AAWC_CK3_USER_DIR } else { Join-Path $env:USERPROFILE "Documents\Paradox Interactive\Crusader Kings III" })
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Ck3Executable)) {
    throw 'Set AAWC_CK3_EXECUTABLE or pass -Ck3Executable with the CK3 executable path.'
}

$sessionRecord = Get-Content -LiteralPath (Join-Path $CertificationSession 'session.json') -Raw | ConvertFrom-Json
if ([System.IO.Path]::GetFullPath($sessionRecord.userdir) -ne [System.IO.Path]::GetFullPath($Ck3UserDirectory)) {
    throw 'Certification session belongs to a different CK3 user directory.'
}
if ($GameArguments.Count -ne 1 -or $GameArguments[0] -ne '-debug_mode') {
    throw 'Fresh certification requires exactly -debug_mode; benchmark auto-start and resume/load/userdir overrides are forbidden.'
}
$sessionTool = Join-Path $PSScriptRoot 'aawc_certification_session.py'
& python -X utf8 -B $sessionTool check --session $CertificationSession
if ($LASTEXITCODE -ne 0) { throw 'Certification session preflight failed.' }

function Get-Sha256Hex {
    param([Parameter(Mandatory)][byte[]]$Bytes)

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha256.ComputeHash($Bytes))).Replace("-", "")
    }
    finally {
        $sha256.Dispose()
    }
}

function Assert-RegexValue {
    param(
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][string]$Pattern,
        [Parameter(Mandatory)][string]$Expected,
        [Parameter(Mandatory)][string]$Label
    )

    $match = [System.Text.RegularExpressions.Regex]::Match($Text, $Pattern)
    if (-not $match.Success -or $match.Groups[1].Value -ne $Expected) {
        throw "$Label must be '$Expected'."
    }
}

function Close-Ck3CrashReporters {
    param([Parameter(Mandatory)][string]$ExpectedExecutable)

    $closed = 0
    $reporters = @(
        Get-CimInstance Win32_Process -Filter "Name = 'CrashReporter.exe'" -ErrorAction SilentlyContinue |
            Where-Object {
                $_.ExecutablePath -and
                [System.StringComparer]::OrdinalIgnoreCase.Equals($_.ExecutablePath, $ExpectedExecutable)
            }
    )
    foreach ($reporter in $reporters) {
        $process = Get-Process -Id $reporter.ProcessId -ErrorAction SilentlyContinue
        if (-not $process) {
            continue
        }
        if ($process.MainWindowHandle -ne 0) {
            [void]$process.CloseMainWindow()
            try {
                $process.WaitForExit(3000)
            }
            catch {
                # The exact CK3 reporter is force-closed below if its window ignored WM_CLOSE.
            }
        }
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction Stop
        }
        $closed++
    }
    return $closed
}

$settingsPath = Join-Path $Ck3UserDirectory "pdx_settings.txt"
$settingsBackupPath = "$settingsPath.aawc-background-test-backup"
$loadPath = Join-Path $Ck3UserDirectory "dlc_load.json"
$aawcDescriptorPath = Join-Path $Ck3UserDirectory "mod\AGOT_Alternate_World_Compatch.mod"
$crashReporterExecutable = Join-Path (Split-Path -Parent $Ck3Executable) "crash_reporter\binaries\CrashReporter.exe"
$expectedLoadOrder = @(
    "mod/ugc_2962333032.mod",
    "mod/AAWC_Dependencies_Modpack.mod",
    "mod/AGOT_Alternate_World_Compatch.mod"
)

foreach ($requiredPath in @($Ck3Executable, $settingsPath, $loadPath, $aawcDescriptorPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required file is missing: $requiredPath"
    }
}

$runningCk3 = @(Get-Process -Name "ck3" -ErrorAction SilentlyContinue)
if ($runningCk3.Count -ne 0) {
    throw "Refusing to launch because CK3 is already running (PID(s): $($runningCk3.Id -join ', '))."
}

if (Test-Path -LiteralPath $settingsBackupPath -PathType Leaf) {
    $interruptedOriginal = [System.IO.File]::ReadAllBytes($settingsBackupPath)
    [System.IO.File]::WriteAllBytes($settingsPath, $interruptedOriginal)
    Remove-Item -LiteralPath $settingsBackupPath -Force
    throw "Recovered CK3 audio settings left by an interrupted earlier background test. Run the command again to start a new test."
}

$loadConfiguration = Get-Content -LiteralPath $loadPath -Raw | ConvertFrom-Json
$actualLoadOrder = @($loadConfiguration.enabled_mods)
if ($actualLoadOrder.Count -ne $expectedLoadOrder.Count) {
    throw "Test load order must contain exactly $($expectedLoadOrder.Count) enabled mods; found $($actualLoadOrder.Count)."
}
for ($index = 0; $index -lt $expectedLoadOrder.Count; $index++) {
    if ($actualLoadOrder[$index] -ne $expectedLoadOrder[$index]) {
        throw "Test load order mismatch at position ${index}: expected '$($expectedLoadOrder[$index])', found '$($actualLoadOrder[$index])'."
    }
}

$descriptorText = Get-Content -LiteralPath $aawcDescriptorPath -Raw
Assert-RegexValue -Text $descriptorText -Pattern '(?m)^version="([^"]+)"\s*$' -Expected "1.11.1.0" -Label "AAWC version"
Assert-RegexValue -Text $descriptorText -Pattern '(?m)^supported_version="([^"]+)"\s*$' -Expected "1.19.0.6" -Label "Supported CK3 version"

$originalSettingsBytes = [System.IO.File]::ReadAllBytes($settingsPath)
$originalSettingsHash = Get-Sha256Hex -Bytes $originalSettingsBytes
$settingsText = [System.Text.Encoding]::UTF8.GetString($originalSettingsBytes)
$masterBusPattern = '(?s)("Audio"\s*=\s*\{.*?"volume\.bus:/"\s*=\s*\{\s*version\s*=\s*\d+\s*value\s*=\s*)([0-9]+(?:\.[0-9]+)?)'
$masterBusMatches = [System.Text.RegularExpressions.Regex]::Matches($settingsText, $masterBusPattern)
if ($masterBusMatches.Count -ne 1) {
    throw "Expected exactly one CK3 Audio master-bus setting; found $($masterBusMatches.Count)."
}

$mutedSettingsText = [System.Text.RegularExpressions.Regex]::Replace(
    $settingsText,
    $masterBusPattern,
    { param($match) $match.Groups[1].Value + "0.000000" },
    1
)
$mutedSettingsBytes = [System.Text.Encoding]::UTF8.GetBytes($mutedSettingsText)

& python -X utf8 -B $sessionTool launch --session $CertificationSession --arguments=-debug_mode
if ($LASTEXITCODE -ne 0) { throw 'Candidate changed or certification session was already used.' }
$backupStream = [System.IO.File]::Open($settingsBackupPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
try {
    $backupStream.Write($originalSettingsBytes, 0, $originalSettingsBytes.Length)
}
finally {
    $backupStream.Dispose()
}

$process = $null
$startedAt = $null
$endedAt = $null
$exitCode = $null
$closedCrashReporters = 0
try {
    [System.IO.File]::WriteAllBytes($settingsPath, $mutedSettingsBytes)

    $process = Start-Process -FilePath $Ck3Executable -ArgumentList $GameArguments -WindowStyle Minimized -PassThru
    $startedAt = [System.DateTimeOffset]::Now
    Write-Host "Started CK3 PID $($process.Id) minimized with master audio muted."
    $process.WaitForExit()
    $process.Refresh()
    $exitCode = $process.ExitCode
    $endedAt = [System.DateTimeOffset]::Now
}
finally {
    [System.IO.File]::WriteAllBytes($settingsPath, $originalSettingsBytes)
    if (Test-Path -LiteralPath $settingsBackupPath -PathType Leaf) {
        Remove-Item -LiteralPath $settingsBackupPath -Force
    }

    $restoredSettingsBytes = [System.IO.File]::ReadAllBytes($settingsPath)
    $restoredSettingsHash = Get-Sha256Hex -Bytes $restoredSettingsBytes
    if ($restoredSettingsHash -ne $originalSettingsHash) {
        throw "CK3 settings restoration failed: expected SHA-256 $originalSettingsHash, found $restoredSettingsHash."
    }

    try {
        $closedCrashReporters = Close-Ck3CrashReporters -ExpectedExecutable $crashReporterExecutable
    }
    catch {
        Write-Warning "Could not close an exact-path CK3 CrashReporter process: $($_.Exception.Message)"
    }
    & python -X utf8 -B $sessionTool finish --session $CertificationSession
    if ($LASTEXITCODE -ne 0) { throw 'Session restoration or save isolation validation failed; inspect session.json.' }
}

[pscustomobject]@{
    ck3_pid = $process.Id
    ck3_version = "1.19.0.6"
    aawc_version = "1.11.1.0"
    selected_archive_sha256 = $sessionRecord.archive_sha256
    certification_session = $CertificationSession
    load_order = $actualLoadOrder -join " -> "
    arguments = $GameArguments -join " "
    started_at = $startedAt.ToString("o")
    ended_at = $endedAt.ToString("o")
    elapsed_seconds = [math]::Round(($endedAt - $startedAt).TotalSeconds, 3)
    exit_code = $exitCode
    launch_window_state = "Minimized"
    master_audio_muted_during_run = $true
    settings_restored_sha256 = $originalSettingsHash
    ck3_crash_reporters_closed = $closedCrashReporters
} | ConvertTo-Json -Depth 3
