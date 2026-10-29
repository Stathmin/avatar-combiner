# Create Windows .lnk shortcuts next to start-web.bat / stop-web.bat with the
# four-nations app icon. .bat files cannot embed icons; shortcuts are the
# usual Windows approach for lab desktops and Start Menu pins.
#
# Usage (from repo root or from src\dist after a build):
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\create-shortcuts.ps1
#   .\create-shortcuts.bat
#
# Portable release zip: shortcuts invoke cmd.exe with a relative bat name and
# use a same-folder icon filename so they still work after unzip on another PC.

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
    # cmd.exe + relative bat name keeps the shortcut usable after the folder moves.
    $sc.TargetPath = Join-Path $env:SystemRoot 'System32\cmd.exe'
    $sc.Arguments = "/c `"$BatName`""
    $sc.WorkingDirectory = '.'
    $sc.WindowStyle = 1
    $sc.Description = $Description
    if ($IconPath) {
        $iconDir = [System.IO.Path]::GetDirectoryName($IconPath)
        if ($iconDir -and ((Resolve-Path -LiteralPath $iconDir).Path -eq $Dir)) {
            # Relative icon path survives unzip to another machine/folder.
            $sc.IconLocation = "$(Split-Path -Leaf $IconPath),0"
        } else {
            $sc.IconLocation = "$IconPath,0"
        }
    }
    $sc.Save()
    Write-Host "Created $lnkPath"
    if ($IconPath) { Write-Host "  icon: $($sc.IconLocation)" }
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
Write-Host 'Pin or copy the .lnk files to the desktop / taskbar. Double-click the shortcuts (not the .bat) to see the app icon.'

