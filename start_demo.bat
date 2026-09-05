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
if not defined LIVETALKING_DIR set "LIVETALKING_DIR=%ROOT%\..\portable_livetalking"
if not defined LIVETALKING_PORT set "LIVETALKING_PORT=8010"
if not defined LIVETALKING_AVATAR set "LIVETALKING_AVATAR=test1"
if not defined LIVETALKING_TTS set "LIVETALKING_TTS=edgetts"

echo [1/6] Checking Python...
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
    echo Python was not found. Install Python 3.8+ or set SCENIC_PYTHON to python.exe.
    exit /b 1
)
call :ensure_python_runtime
if errorlevel 1 exit /b 1
echo   Python command: %PYTHON_EXE%

echo [2/6] Checking npm...
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

echo [3/6] Checking ports...
set "PORT_BLOCKED=false"
for %%P in (8000 5173 %LIVETALKING_PORT%) do (
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

echo [4/6] Preparing environment...
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

echo [5/6] Checking LiveTalking module...
if exist "%LIVETALKING_DIR%\app.py" (
    echo   LiveTalking module: %LIVETALKING_DIR%
) else (
    echo   LiveTalking module was not found at %LIVETALKING_DIR%; realtime avatar service will be skipped.
)

echo [6/6] Starting services...
set "FAST_BACKEND="
if /I "%FAST_MODE%"=="true" (
    set "FAST_BACKEND=set SCENIC_CHAT_FAST_MODE=true && "
    echo   Fast mode enabled for this backend process only.
)

if exist "%LIVETALKING_DIR%\app.py" (
    start "LiveTalking Digital Human :%LIVETALKING_PORT%" cmd /k pushd "%LIVETALKING_DIR%" ^&^& "%PYTHON_EXE%" app.py --transport webrtc --model wav2lip --avatar_id %LIVETALKING_AVATAR% --tts %LIVETALKING_TTS% --listenport %LIVETALKING_PORT%
)
start "Lingshan Backend API :8000" cmd /k pushd "%ROOT%" ^&^& %FAST_BACKEND%"%PYTHON_EXE%" backend\app.py
start "Lingshan Vue Frontend :5173" cmd /k pushd "%ROOT%\frontend-vue" ^&^& call "%NPM_EXE%" run dev

echo.
echo Backend API: http://127.0.0.1:8000
echo Vue frontend: http://127.0.0.1:5173
echo LiveTalking: http://127.0.0.1:%LIVETALKING_PORT%
echo.
echo Close the service windows or press Ctrl+C in each window to stop.
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
