@echo off
setlocal
cd /d "%~dp0"
echo Running VLCouch setup...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-shortcuts.ps1"
if errorlevel 1 (
  echo.
  echo Setup failed. See the messages above.
  pause
  exit /b 1
)
echo.
echo Setup complete.
pause
