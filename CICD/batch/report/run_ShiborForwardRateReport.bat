@echo off
chcp 65001
echo.
REM SHIBOR Forward Rate Analysis Report batch file (with logging)

REM Set paths
set PYTHON_PATH=C:\Users\ASUS\Anaconda3\envs\py312\python.exe
set PROJECT_PATH=D:\workspace_python\infinity
set LOG_PATH=D:\workspace_python\infinity_data\log
set INFINITY_LOG_FILE=%LOG_PATH%\shibor_forward_rate_analysis.log

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
echo SHIBOR Forward Rate Analysis Report started: %date% %time%
echo Log file: %INFINITY_LOG_FILE%
echo ========================================
echo.

REM Execute SHIBOR Forward Rate analysis report (Python logger handles both console and file)
"%PYTHON_PATH%" "%PROJECT_PATH%\dataIntegrator\analysisService\report\financialAnalysis\RunShiborForwardRateReport.py"

REM Check execution result
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SHIBOR Forward Rate Analysis Report executed successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo SHIBOR Forward Rate Analysis Report execution failed, error code: %ERRORLEVEL%
    echo ========================================
)

echo.
