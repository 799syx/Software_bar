@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\stop_demo.ps1" %*
exit /b %errorlevel%
