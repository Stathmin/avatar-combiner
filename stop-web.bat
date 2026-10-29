@echo off
REM Stop the Avatar Combiner web UI started by start-web.bat

setlocal EnableExtensions
set "PIDFILE=%TEMP%\avatar-combiner-web.pid"
set "PORTFILE=%TEMP%\avatar-combiner-web.port"
set "APPDIR=%~dp0"
set "STOPPED=0"

echo Stopping Avatar Combiner web UI...

if exist "%PIDFILE%" (
  set /p PID=<"%PIDFILE%"
  if defined PID (
    taskkill /PID %PID% /T /F >nul 2>&1
    if not errorlevel 1 (
      echo Stopped process PID %PID%
      set "STOPPED=1"
    )
  )
  del "%PIDFILE%" >nul 2>&1
)

set "PORT=8080"
if exist "%PORTFILE%" (
  set /p PORT=<"%PORTFILE%"
)

REM Also clear anything still listening on the recorded/default port.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$port=%PORT%; $conns=Get-NetTCPConnection -LocalPort $port -State Listen -EA SilentlyContinue; foreach ($c in $conns) { try { Stop-Process -Id $c.OwningProcess -Force -EA Stop; Write-Output ('Killed PID '+$c.OwningProcess+' on port '+$port); } catch {} }" 2>nul

if exist "%PORTFILE%" del "%PORTFILE%" >nul 2>&1

REM Fallback: kill python/uv/avatar listeners, or any listener whose exe lives under this folder.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dir=$env:APPDIR; if (-not $dir) { $dir='%~dp0' }; 8080..8099 | ForEach-Object { $port=$_; Get-NetTCPConnection -LocalPort $port -State Listen -EA SilentlyContinue | ForEach-Object { $proc=Get-Process -Id $_.OwningProcess -EA SilentlyContinue; if (-not $proc) { return }; $path=''; try { $path=$proc.Path } catch {}; if ($proc.ProcessName -match 'python|uv|avatar' -or ($path -and $dir -and $path.StartsWith($dir))) { Stop-Process -Id $proc.Id -Force -EA SilentlyContinue; Write-Output ('Killed '+$proc.ProcessName+' PID '+$proc.Id+' on port '+$port) } } }" 2>nul

echo Done. You can close any leftover console titled "Avatar Combiner - Web UI".
pause
