@echo off
REM Double-click to open Avatar Combiner in your browser.
REM Keep this window open while you work.
REM Stop: close this window, press Ctrl+C, or double-click stop-web.bat

setlocal EnableExtensions
cd /d "%~dp0"
title Avatar Combiner — Web UI  [close this window / Ctrl+C / stop-web.bat to stop]

set "EXE="
for %%F in ("%~dp0src\dist\*.exe") do set "EXE=%%~fF"
set "LAUNCHER=%~dp0src\launch_web_windows.py"
set "PORT=8080"

echo.
echo  ============================================================
echo   Avatar Combiner — web UI
echo  ============================================================
echo   Stop: close this window, Ctrl+C, or stop-web.bat
echo  ============================================================
echo.

REM Prefer the Python launcher (free-port pick + PID file + browser).
REM Fall back to the packaged exe with --web when uv/Python is unavailable.
if exist "%LAUNCHER%" (
  where uv >nul 2>&1
  if not errorlevel 1 (
    uv run python "%LAUNCHER%" --port %PORT%
    goto :eof
  )
  where python >nul 2>&1
  if not errorlevel 1 (
    python "%LAUNCHER%" --port %PORT%
    goto :eof
  )
)

if defined EXE if exist "%EXE%" (
  echo Starting packaged exe: --web --port %PORT%
  echo If the browser does not open, visit http://127.0.0.1:%PORT%
  echo %PORT%> "%TEMP%\avatar-combiner-web.port"
  start "" "http://127.0.0.1:%PORT%"
  "%EXE%" --web --port %PORT% --no-browser
  goto :eof
)

echo [error] Cannot start web UI.
echo Need either: uv/python + src\launch_web_windows.py
echo          or: src\dist\*.exe  (built with build_binary.py)
pause
exit /b 1
