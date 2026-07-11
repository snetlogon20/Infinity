import os
import sys
import traceback
from datetime import datetime

# ensure project root is on sys.path so we can import from dataIntegrator
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dataIntegrator import CommonLib

# ---------- import all report runner classes ----------
from dataIntegrator.analysisService.report.financialAnalysis.RunPortfolioAnalysisReport import RunPortfolioAnalysisReport
from dataIntegrator.analysisService.report.financialAnalysis.RunCMLAnalysisReport import RunCMLAnalysisReport
from dataIntegrator.analysisService.report.financialAnalysis.RunCMLAnalysisWithCommoditiesReport import RunCMLAnalysisWithCommoditiesReport
from dataIntegrator.analysisService.report.financialAnalysis.RunSMLAnalysisReport import RunSMLAnalysisReport
from dataIntegrator.analysisService.report.financialAnalysis.RunInformationRatioAnalysisReport import RunInformationRatioAnalysisReport
from dataIntegrator.analysisService.report.financialAnalysis.RunPortfolioMetricsAnalysisReport import RunPortfolioMetricsAnalysisReport
from dataIntegrator.analysisService.report.financialAnalysis.RunSORAnalysisReport import RunSORAnalysisReport
from dataIntegrator.analysisService.report.financialAnalysis.RunTreynorRatioAnalysisReport import RunTreynorRatioAnalysisReport
from dataIntegrator.analysisService.report.financialAnalysis.RunChinaTreasuryForwardRateReport import RunChinaTreasuryForwardRateReport
from dataIntegrator.analysisService.report.financialAnalysis.RunShiborForwardRateReport import RunShiborForwardRateReport
from dataIntegrator.analysisService.report.financialAnalysis.RunPDAnalysisReport import RunPDAnalysisReport
from dataIntegrator.analysisService.report.bonds.RunConvertibleBondManagerReport import RunConvertibleBondManagerReport
from dataIntegrator.analysisService.report.bonds.RunBondYieldComparator import RunBondYieldComparator
from dataIntegrator.analysisService.report.systemSupport.RunSystemBatchStatusReport import RunSystemBatchStatusReport

logger = CommonLib.logger


class ReportRunner:

    def __init__(self):
        logger.info("ReportRunner __init__ started")
        # 预初始化所有报告运行器（工厂模式）
        self._portfolio_analysis_runner = RunPortfolioAnalysisReport()
        self._cml_runner = RunCMLAnalysisReport()
        self._cml_commodities_runner = RunCMLAnalysisWithCommoditiesReport()
        self._sml_runner = RunSMLAnalysisReport()
        self._ir_runner = RunInformationRatioAnalysisReport()
        self._portfolio_metrics_runner = RunPortfolioMetricsAnalysisReport()
        self._sor_runner = RunSORAnalysisReport()
        self._treynor_runner = RunTreynorRatioAnalysisReport()
        self._china_treasury_runner = RunChinaTreasuryForwardRateReport()
        self._shibor_runner = RunShiborForwardRateReport()
        self._convertible_bond_runner = RunConvertibleBondManagerReport()
        self._bond_yield_runner = RunBondYieldComparator()
        self._pd_runner = RunPDAnalysisReport()
        self._system_batch_status_runner = RunSystemBatchStatusReport()

    def run_all_reports(self):
        """工厂模式：按 run_reports.bat 顺序统一调用所有报告"""
        try:
            logger.info("run_all_reports started, %s", datetime.now())

            # 工厂映射：报告名称 -> 调用的无参 run() 方法
            report_method_dict = {
                "China Treasury Forward Rate Analysis Report":   self._china_treasury_runner.run,
                "CML Analysis Report (Pure Stocks)":             self._cml_runner.run,
                "CML Analysis With Commodities Report":          self._cml_commodities_runner.run,
                "Information Ratio Analysis Report":             self._ir_runner.run,
                "PD Analysis Report":                            self._pd_runner.run,
                # "Portfolio Analysis Report":                    self._portfolio_analysis_runner.run,
                "Portfolio Metrics Analysis Report":             self._portfolio_metrics_runner.run,
                "SHIBOR Forward Rate Analysis Report":           self._shibor_runner.run,
                "SML Analysis Report":                           self._sml_runner.run,
                "SOR Analysis Report":                           self._sor_runner.run,
                "Treynor Ratio Analysis Report":                 self._treynor_runner.run,
                "Bond Yield Comparator Report":                  self._bond_yield_runner.run,
                "Convertible Bond Manager Report":               self._convertible_bond_runner.run,
                #永远把System Batch Status Report放在最后面跑
                "System Batch Status Report":                    self._system_batch_status_runner.generate_report,
            }

            failed_reports = []

            for report_name, report_method in report_method_dict.items():
                try:
                    logger.info("\n%s", '=' * 60)
                    logger.info("Running: %s - started: %s", report_name, datetime.now())
                    logger.info("%s", '=' * 60)
                    report_method()
                    logger.info("%s executed successfully!", report_name)
                except Exception as e:
                    logger.error("%s failed: %s", report_name, e)
                    logger.error(traceback.format_exc())
                    failed_reports.append((report_name, str(e)))

            logger.info("\n%s", '=' * 60)
            logger.info("All Reports Execution Completed!")
            logger.info("Finished: %s", datetime.now())
            if failed_reports:
                logger.error("Failed reports (%d):", len(failed_reports))
                for rname, err in failed_reports:
                    logger.error("  - %s: %s", rname, err)
            else:
                logger.info("All reports executed successfully!")
            logger.info("%s", '=' * 60)

            logger.info("run_all_reports completed successfully")

        except Exception as e:
            logger.error('==============================================')
            logger.error('Exception: %s', e)
            logger.error('==============================================')
            raise e


def main():
    report_runner = ReportRunner()
    report_runner.run_all_reports()


if __name__ == '__main__':
    main()
