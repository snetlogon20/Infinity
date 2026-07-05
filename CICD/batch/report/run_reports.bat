@echo off
chcp 65001
echo.

REM Financial Analysis Reports batch file (with logging)

REM Set paths (portable: %~dp0 resolves to this script's directory)
set SCRIPT_DIR=%~dp0
set PYTHON_PATH=C:\Users\ASUS\Anaconda3\envs\py312\python.exe
set PROJECT_PATH=%SCRIPT_DIR%..\..\..
set LOG_PATH=%PROJECT_PATH%_data\log
set INFINITY_LOG_FILE=%LOG_PATH%\reports.log

REM Create log directory
if not exist "%LOG_PATH%" mkdir "%LOG_PATH%"

REM Set Python path
set PYTHONPATH=%PROJECT_PATH%;%PYTHONPATH%

REM Change to project directory
cd /d %PROJECT_PATH%

REM Set environment variable for Python
set PYTHONIOENCODING=utf-8

REM Display start information
echo ========================================
echo Running All Financial Analysis Reports
echo Started: %date% %time%
echo Log file: %INFINITY_LOG_FILE%
echo ========================================
echo.

REM Execute report script (Python logger handles both console and file)
"%PYTHON_PATH%" "%SCRIPT_DIR%run_Report.py"

REM Check execution result
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo All Reports Execution Completed!
    echo Finished: %date% %time%
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Reports Execution Failed, error code: %ERRORLEVEL%
    echo Finished: %date% %time%
    echo ========================================
)

echo.
REM Keep window open
pause
