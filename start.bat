@echo off
echo Starting VLCouch production server...
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
pause