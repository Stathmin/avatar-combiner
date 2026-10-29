# Create Windows .lnk shortcuts next to start-web.bat / stop-web.bat with the
# four-nations app icon. .bat files cannot embed icons; shortcuts are the
# usual Windows approach for lab desktops and Start Menu pins.
#
# Usage (from the release folder, repo root, or src\dist after a build):
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\create-shortcuts.ps1
#   .\create-shortcuts.bat
#
# IMPORTANT: shortcuts use absolute paths for target, working dir, and icon.
# That is required for icons and launch to work on Windows. After moving or
# unzipping the folder on another PC, run create-shortcuts.bat once.

param(
    [string]$TargetDir = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
$TargetDir = (Resolve-Path -LiteralPath $TargetDir).Path

function Find-Icon {
    param([string]$Dir)
    $candidates = @(
        (Join-Path $Dir 'app-icon.ico'),
        (Join-Path $Dir 'src\assets\app-icon.ico'),
        (Join-Path $Dir 'assets\app-icon.ico'),
        (Join-Path $Dir '..\assets\app-icon.ico'),
        (Join-Path $Dir '..\..\src\assets\app-icon.ico'),
        (Join-Path $Dir 'docs\media\icons\app-icon.ico')
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { return (Resolve-Path -LiteralPath $c).Path }
    }
    return $null
}

function New-BatShortcut {
    param(
        [string]$Dir,
        [string]$BatName,
        [string]$LnkName,
        [string]$Description,
        [string]$IconPath
    )
    $bat = Join-Path $Dir $BatName
    if (-not (Test-Path -LiteralPath $bat)) {
        Write-Warning "Skip $LnkName - missing $BatName in $Dir"
        return
    }
    $lnkPath = Join-Path $Dir $LnkName
    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($lnkPath)
    # Absolute paths: WorkingDirectory=. breaks (uses caller's cwd), and relative
    # IconLocation then fails to show app-icon.ico.
    $sc.TargetPath = $bat
    $sc.WorkingDirectory = $Dir
    $sc.WindowStyle = 1
    $sc.Description = $Description
    if ($IconPath) {
        $sc.IconLocation = "$IconPath,0"
    }
    $sc.Save()
    Write-Host "Created $lnkPath"
    Write-Host "  target: $bat"
    if ($IconPath) { Write-Host "  icon: $IconPath" }
}

$icon = Find-Icon -Dir $TargetDir
if (-not $icon) {
    Write-Warning "app-icon.ico not found near $TargetDir - shortcuts will use the default .bat icon"
}

New-BatShortcut -Dir $TargetDir -BatName 'start-web.bat' -LnkName 'Avatar Combiner Web.lnk' `
    -Description 'Start Avatar Combiner web UI' -IconPath $icon
New-BatShortcut -Dir $TargetDir -BatName 'stop-web.bat' -LnkName 'Stop Avatar Combiner Web.lnk' `
    -Description 'Stop Avatar Combiner web UI' -IconPath $icon

Write-Host ''
Write-Host 'Use the .lnk files (not the .bat) for the app icon.'
Write-Host 'After moving/unzipping this folder, run create-shortcuts.bat once.'
