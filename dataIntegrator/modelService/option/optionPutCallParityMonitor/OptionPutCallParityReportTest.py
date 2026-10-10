r"""
Put-Call Parity 监控 PDF 报告 测试入口

前置条件：先运行 OptionPutCallParityMonitorTest 落库监控数据（tb_option_pcp_monitor）。

运行方式：
    python -m dataIntegrator.modelService.option.optionPutCallParityMonitor.OptionPutCallParityReportTest
"""

from datetime import datetime, timedelta

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.optionPutCallParityMonitor.OptionPutCallParityReport import (
    OptionPutCallParityReport
)

if __name__ == "__main__":
    end_date = CommonParameters.today
    # 报告默认回看 90 天（约 60 个交易日：覆盖一个季月合约周期 + 分红季节点）
    start_date = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=90)).strftime("%Y%m%d")

    report = OptionPutCallParityReport()
    report.run({
        "name": "期权平价关系（Put-Call Parity）监控报告",
        "start_date": start_date,
        "end_date": end_date,
        "underlying_code": None,
    })
