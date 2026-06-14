@echo off
set "TASK_NAME=PTC3527-Checkpoint37-Matrix"
schtasks.exe /delete /tn "%TASK_NAME%" /f >nul 2>&1
schtasks.exe /create /tn "%TASK_NAME%" /sc once /st 23:59 /rl limited /f /tr "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File C:\PTC3527\checkpoint37\Invoke-Checkpoint37Matrix.ps1"
if errorlevel 1 exit /b %errorlevel%
schtasks.exe /run /tn "%TASK_NAME%"
exit /b %errorlevel%
