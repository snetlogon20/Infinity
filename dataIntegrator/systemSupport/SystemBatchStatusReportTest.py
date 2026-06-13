from dataIntegrator.systemSupport.SystemBatchStatusReport import SystemBatchStatusReport


class SystemBatchStatusReportTest:
    """系统批量任务状态报告"""
    def __init__(self):
        pass

if __name__ == "__main__":
    report = SystemBatchStatusReport()
    report.generate_report()
