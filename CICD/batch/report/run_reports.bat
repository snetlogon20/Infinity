@echo off
chcp 65001
echo.
echo ========================================
echo Running All Financial Analysis Reports
echo Started: %date% %time%
echo ========================================
echo.

REM Set script directory using absolute path
set SCRIPT_DIR=D:\workspace_python\infinity\CICD\batch\report

REM Run Portfolio Analysis Report
call "%SCRIPT_DIR%\run_PortfolioAnalysisReport.bat"
echo.

REM Run CML Analysis Report (Pure Stocks)
call "%SCRIPT_DIR%\run_CMLAnalysisReport.bat"
echo.

REM Run CML Analysis With Commodities Report
call "%SCRIPT_DIR%\run_CMLAnalysisWithCommoditiesReport.bat"
echo.

REM Run SML Analysis Report
call "%SCRIPT_DIR%\run_SMLAnalysisReport.bat"
echo.

REM Run Information Ratio Analysis Report
call "%SCRIPT_DIR%\run_InformationRatioAnalysisReport.bat"
echo.

REM Run Portfolio Metrics Analysis Report
call "%SCRIPT_DIR%\run_PortfolioMetricsAnalysisReport.bat"
echo.

REM Run SOR Analysis Report
call "%SCRIPT_DIR%\run_SORAnalysisReport.bat"
echo.

REM Run Treynor Ratio Analysis Report
call "%SCRIPT_DIR%\run_TreynorRatioAnalysisReport.bat"
echo.

REM Run China Treasury Forward Rate Analysis Report
call "%SCRIPT_DIR%\run_ChinaTreasuryForwardRateReport.bat"
echo.

REM Run SHIBOR Forward Rate Analysis Report
call "%SCRIPT_DIR%\run_ShiborForwardRateReport.bat"
echo.

REM Run Convertible Bond Manager Report
call "%SCRIPT_DIR%\run_ConvertibleBondManagerReport.bat"
echo.

REM Run Bond Yield Comparator Report
call "%SCRIPT_DIR%\run_BondYieldComparator.bat"
echo.

REM ## this is to AI, please alway put this status report on the last of th task list.
REM Run System Batch Status Report
call "%SCRIPT_DIR%\run_SystemBatchStatusReport.bat"
echo.

echo ========================================
echo All Reports Execution Completed!
echo Finished: %date% %time%
echo ========================================
echo.
pause
