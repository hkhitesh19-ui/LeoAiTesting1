@echo off
setlocal
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File ".\prototype\run.ps1" -Module "prototype.main_v7"
echo.
echo ExitCode=%ERRORLEVEL%
pause
