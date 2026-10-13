@echo off
powershell.exe -NoProfile -File "%~dp0scripts\launch_remote_smooth.ps1" %*
set "LaunchExit=%errorlevel%"
if not "%LaunchExit%"=="0" pause
exit /b %LaunchExit%
