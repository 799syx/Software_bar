@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "FAST_MODE=false"
set "CHECK_ONLY=false"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--fast" (
    set "FAST_MODE=true"
) else if /I "%~1"=="--check" (
    set "CHECK_ONLY=true"
) else if /I "%~1"=="-h" (
    goto usage
) else if /I "%~1"=="--help" (
    goto usage
) else (
    echo Unknown option: %~1
    goto usage_error
)
shift
goto parse_args

:args_done
set "ROOT=%CD%"
set "PYTHON_EXE="
set "NPM_EXE="

echo [1/5] Checking Python...
if defined SCENIC_PYTHON (
    if exist "%SCENIC_PYTHON%" set "PYTHON_EXE=%SCENIC_PYTHON%"
)

if not defined PYTHON_EXE (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if not defined PYTHON_EXE (
    where py >nul 2>nul
    if not errorlevel 1 set "PYTHON_EXE=py"
)

if not defined PYTHON_EXE if exist "E:\DC\python.exe" (
    set "PATH=E:\DC;E:\DC\Library\bin;E:\DC\Scripts;E:\DC\condabin;%PATH%"
    set "PYTHON_EXE=E:\DC\python.exe"
)

if not defined PYTHON_EXE (
    echo Python was not found. Install Python 3.8+ or set SCENIC_PYTHON to python.exe.
    exit /b 1
)
echo   Python command: %PYTHON_EXE%

echo [2/5] Checking npm...
where npm.cmd >nul 2>nul
if not errorlevel 1 set "NPM_EXE=npm.cmd"

if not defined NPM_EXE (
    where npm >nul 2>nul
    if not errorlevel 1 set "NPM_EXE=npm"
)

if not defined NPM_EXE (
    echo npm was not found. Install Node.js 18+ or update PATH.
    exit /b 1
)
echo   npm command: %NPM_EXE%

echo [3/5] Checking ports...
set "PORT_BLOCKED=false"
for %%P in (8000 5173) do (
    set "PID_%%P="
    for /f "tokens=5" %%I in ('netstat -ano -p tcp ^| findstr /R /C:":%%P .*LISTENING"') do (
        if not defined PID_%%P set "PID_%%P=%%I"
    )
    if defined PID_%%P (
        echo   Port %%P is already in use by PID !PID_%%P!.
        set "PORT_BLOCKED=true"
    ) else (
        echo   Port %%P is available.
    )
)

if /I "%CHECK_ONLY%"=="true" (
    echo Check complete.
    exit /b 0
)

if /I "%PORT_BLOCKED%"=="true" (
    echo Stop the process using the port, then run this script again.
    exit /b 1
)

echo [4/5] Preparing environment...
if exist ".env" (
    echo   .env already exists.
) else if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo   Created .env from .env.example. Fill DASHSCOPE_API_KEY for online model calls.
) else (
    echo   .env.example was not found. Continuing without a local .env file.
)

if not exist "frontend-vue\node_modules" (
    echo   Installing Vue dependencies...
    pushd "frontend-vue" >nul
    call "%NPM_EXE%" install
    if errorlevel 1 (
        popd >nul
        echo npm install failed.
        exit /b 1
    )
    popd >nul
) else (
    echo   Vue dependencies already installed.
)

echo [5/5] Starting services...
set "FAST_BACKEND="
if /I "%FAST_MODE%"=="true" (
    set "FAST_BACKEND=set SCENIC_CHAT_FAST_MODE=true && "
    echo   Fast mode enabled for this backend process only.
)

start "Lingshan Backend API :8000" cmd /k "cd /d ^"%ROOT%^" && %FAST_BACKEND%^"%PYTHON_EXE%^" backend\app.py"
start "Lingshan Vue Frontend :5173" cmd /k "cd /d ^"%ROOT%\frontend-vue^" && call ^"%NPM_EXE%^" run dev"

echo.
echo Backend API: http://127.0.0.1:8000
echo Vue frontend: http://127.0.0.1:5173
echo.
echo Close the two service windows or press Ctrl+C in each window to stop.
exit /b 0

:usage
echo Usage: start_demo.bat [--fast] [--check]
echo.
echo   --fast   Set SCENIC_CHAT_FAST_MODE=true for the backend process only.
echo   --check  Verify Python, npm, and ports without starting services.
exit /b 0

:usage_error
echo Usage: start_demo.bat [--fast] [--check]
exit /b 1
