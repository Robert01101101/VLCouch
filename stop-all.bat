@echo off
echo Stopping all VLCouch servers...
powershell -ExecutionPolicy Bypass -File "%~dp0stop-all.ps1"
pause