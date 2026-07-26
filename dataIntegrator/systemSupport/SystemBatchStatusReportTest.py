from dataIntegrator.systemSupport.SystemBatchStatusReport import SystemBatchStatusReport


class SystemBatchStatusReportTest:
    """系统批量任务状态报告"""
    def __init__(self):
        pass

if __name__ == "__main__":
    report = SystemBatchStatusReport()

    target_list = ['2026-07-18','2026-07-25','2026-07-26']
    for target_date in target_list:
        report.generate_report(target_date=target_date)
