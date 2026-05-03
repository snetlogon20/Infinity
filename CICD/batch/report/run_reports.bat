@echo off
chcp 65001
echo.
echo ========================================
echo Running All Financial Analysis Reports
echo Started: %date% %time%
echo ========================================
echo.

REM Run Portfolio Analysis Report
call .\run_PortfolioAnalysisReport.bat
echo.

REM Run CML Analysis Report (Pure Stocks)
call .\run_CMLAnalysisReport.bat
echo.

REM Run CML Analysis With Commodities Report
call .\run_CMLAnalysisWithCommoditiesReport.bat
echo.

echo ========================================
echo All Reports Execution Completed!
echo Finished: %date% %time%
echo ========================================
echo.
pause