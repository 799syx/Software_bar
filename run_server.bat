@echo off
setlocal
cd /d "%~dp0"

if defined SCENIC_PYTHON (
    if exist "%SCENIC_PYTHON%" (
        "%SCENIC_PYTHON%" backend\app.py
        goto :eof
    )
)

where python >nul 2>nul
if %errorlevel%==0 (
    python backend\app.py
    goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
    py backend\app.py
    goto :eof
)

if exist "E:\DC\python.exe" (
    set "PATH=E:\DC;E:\DC\Library\bin;E:\DC\Scripts;E:\DC\condabin;%PATH%"
    "E:\DC\python.exe" backend\app.py
    goto :eof
)

echo Python was not found in PATH.
echo Install Python 3.8+, set SCENIC_PYTHON, or add your Python directory to PATH.
pause
