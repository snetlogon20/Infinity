@echo off
chcp 65001 >nul
REM Data refresh scheduler batch file (with logging)

REM Set paths
set PYTHON_PATH=C:\Users\ASUS\Anaconda3\envs\py312\python.exe
set PROJECT_PATH=D:\workspace_python\infinity
set LOG_PATH=D:\workspace_python\infinity_data\log
set LOG_FILE=%LOG_PATH%\data_refresh_%date:~0,4%%date:~5,2%%date:~8,2%.log
set INFINITY_LOG_FILE=D:\workspace_python\infinity_data\log\dataIntegrater.log

REM Create log directory
if not exist "%LOG_PATH%" mkdir "%LOG_PATH%"

REM Set Python path
set PYTHONPATH=%PROJECT_PATH%;%PYTHONPATH%

REM Change to project directory
cd /d %PROJECT_PATH%

REM Record start time to log
echo ======================================== >> "%LOG_FILE%"
echo Data refresh task started: %date% %time% >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

REM Display start information
echo ========================================
echo Data refresh task started: %date% %time%
echo Log file: %LOG_FILE%
echo ========================================

REM Execute data refresh script and redirect output to log
"%PYTHON_PATH%" "%PROJECT_PATH%\dataIntegrator\analysisService\DataRefreshManager.py" >> "%LOG_FILE%" 2>&1
powershell -Command "Get-Content -Path '%INFINITY_LOG_FILE%' -Tail 50"

REM Check execution result
if %ERRORLEVEL% EQU 0 (
    echo Execution successful >> "%LOG_FILE%"
    echo Data refresh task executed successfully!
) else (
    echo Execution failed, error code: %ERRORLEVEL% >> "%LOG_FILE%"
    echo Data refresh task execution failed, error code: %ERRORLEVEL%
)

REM Record end time
echo ======================================== >> "%LOG_FILE%"
echo Data refresh task completed: %date% %time% >> "%LOG_FILE%"
echo ======================================== >> "%LOG_FILE%"

echo ========================================
echo Data refresh task completed: %date% %time%
echo ========================================

REM Keep window open
pause
