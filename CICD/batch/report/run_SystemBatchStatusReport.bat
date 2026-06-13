@echo off
chcp 65001 >nul
echo.
echo ========================================
echo Running System Batch Status Report
echo ========================================
echo.

set SCRIPT_DIR=D:\workspace_python\infinity\CICD\batch\report
cd /d D:\workspace_python\infinity

python -m dataIntegrator.analysisService.report.systemSupport.RunSystemBatchStatusReport
if %ERRORLEVEL% NEQ 0 (
    echo System Batch Status Report FAILED with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================
echo System Batch Status Report Completed
echo ========================================
echo.
