@echo off
chcp 65001 >nul
echo ========================================
echo 投资组合指标分析报告生成器
echo ========================================
echo.

cd /d D:\workspace_python\infinity

echo 正在运行投资组合指标分析...
echo.

python dataIntegrator\modelService\financialAnalysis\PortfolioMetricsAnalysisTest.py

echo.
echo ========================================
echo 所有任务完成！
echo ========================================
pause
