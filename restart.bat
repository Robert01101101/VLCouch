@echo off
echo Restarting VLCouch servers...
powershell -ExecutionPolicy Bypass -File "%~dp0restart.ps1"
pause