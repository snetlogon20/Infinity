@echo off
chcp 65001
echo.

REM Data refresh scheduler batch file (with logging)

REM Set paths
set PYTHON_PATH=C:\Users\Samuel\anaconda3\envs\py312\python.exe
set PROJECT_PATH=D:\workspace_python\infinity
set LOG_PATH=D:\workspace_python\infinity_data\log
set INFINITY_LOG_FILE=%LOG_PATH%\dataIntegrater.log

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
echo Data refresh task started: %date% %time%
echo Log file: %INFINITY_LOG_FILE%
echo ========================================
echo.

REM Execute data refresh script (Python logger handles both console and file)
"%PYTHON_PATH%" "%PROJECT_PATH%\dataIntegrator\analysisService\DataRefreshManager.py"

REM Check execution result
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Data refresh task executed successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Data refresh task execution failed, error code: %ERRORLEVEL%
    echo ========================================
)

echo.
REM Keep window open
pause
