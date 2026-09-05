@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_EXE="

if defined SCENIC_PYTHON (
    if exist "%SCENIC_PYTHON%" (
        set "PYTHON_EXE=%SCENIC_PYTHON%"
        call :prepend_python_runtime_paths "%SCENIC_PYTHON%"
    )
)

if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
    )
    if defined PYTHON_EXE call :prepend_python_runtime_paths "%PYTHON_EXE%"
)

if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('where py 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
    )
)

if not defined PYTHON_EXE if exist "E:\DC\python.exe" (
    set "PYTHON_EXE=E:\DC\python.exe"
    call :prepend_python_runtime_paths "E:\DC\python.exe"
)

if not defined PYTHON_EXE (
    echo Python was not found in PATH.
    echo Install Python 3.8+, set SCENIC_PYTHON, or add your Python directory to PATH.
    pause
    exit /b 1
)

call :ensure_python_runtime
if errorlevel 1 (
    pause
    exit /b 1
)

"%PYTHON_EXE%" backend\app.py
exit /b %errorlevel%

:prepend_python_runtime_paths
set "PYTHON_ROOT=%~dp1"
if "%PYTHON_ROOT%"=="" exit /b 0
if exist "%PYTHON_ROOT%Library\bin" (
    set "PATH=%PYTHON_ROOT%;%PYTHON_ROOT%Library\mingw-w64\bin;%PYTHON_ROOT%Library\usr\bin;%PYTHON_ROOT%Library\bin;%PYTHON_ROOT%Scripts;%PYTHON_ROOT%bin;%PATH%"
)
exit /b 0

:ensure_python_runtime
"%PYTHON_EXE%" -c "import sqlite3, ssl" >nul 2>nul
if not errorlevel 1 exit /b 0

if exist "E:\DC\python.exe" (
    set "PYTHON_EXE=E:\DC\python.exe"
    call :prepend_python_runtime_paths "E:\DC\python.exe"
    "%PYTHON_EXE%" -c "import sqlite3, ssl" >nul 2>nul
    if not errorlevel 1 exit /b 0
)

echo Python was found, but sqlite3 or ssl could not be imported.
echo For Conda/Anaconda Python, activate the environment or ensure Library\bin is on PATH.
exit /b 1
