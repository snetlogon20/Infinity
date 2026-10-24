from dataIntegrator.modelService.financialAnalysis.PDAnalysisReport import PDAnalysisReport

if __name__ == "__main__":
    report = PDAnalysisReport()

    # ---- 模式选择 ----

    # 模式1: 单只股票报告
    report.generate_single_stock_report(symbol='002093')

    # 模式2: 批量生成所有股票报告
    #report.generate_all_stocks_report()
