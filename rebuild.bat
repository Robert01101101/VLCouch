@echo off
setlocal
cd /d "%~dp0"
echo Rebuilding VLCouch production build...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\rebuild.ps1"
if errorlevel 1 (
  echo.
  echo Rebuild failed. See the messages above.
  pause
  exit /b 1
)
echo.
echo Rebuild complete.
pause
