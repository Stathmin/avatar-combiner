@echo off
REM Create .lnk shortcuts with the four-nations app icon next to the bats.
REM Double-click this after unpacking, or from the repo root / src\dist.
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create-shortcuts.ps1" -TargetDir "%~dp0"
if errorlevel 1 (
  echo Failed to create shortcuts.
  pause
  exit /b 1
)
echo.
pause
endlocal
