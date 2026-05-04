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

REM Run SML Analysis Report
call .\run_SMLAnalysisReport.bat
echo.

REM Run Information Ratio Analysis Report
call .\run_InformationRatioAnalysisReport.bat
echo.

REM Run Portfolio Metrics Analysis Report
call .\run_PortfolioMetricsAnalysisReport.bat
echo.

REM Run SOR Analysis Report
call .\run_SORAnalysisReport.bat
echo.

REM Run Treynor Ratio Analysis Report
call .\run_TreynorRatioAnalysisReport.bat
echo.

echo ========================================
echo All Reports Execution Completed!
echo Finished: %date% %time%
echo ========================================
echo.
pause