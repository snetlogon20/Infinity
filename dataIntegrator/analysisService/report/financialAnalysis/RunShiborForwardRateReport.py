"""
SHIBOR 远期利率分析报告生成器

本文件用于批量生成 SHIBOR 远期利率分析报告
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.modelService.forwards.ShiborForwardRateCalculator import ShiborForwardRateCalculator

logger = CommonLib.logger


class RunShiborForwardRateReport:
    """SHIBOR 远期利率分析报告生成器"""

    def __init__(self):
        self.calculator = ShiborForwardRateCalculator()
        self.job_logger = ReportJobLogger()

    def generate_report(self, start_date=None, end_date=None, case_name=None):
        """
        生成单个 SHIBOR 远期利率分析报告

        参数:
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - case_name: 案例名称

        返回:
        - result: 分析结果字典
        """
        if end_date is None:
            end_date = CommonParameters.today

        logger.info(f"\n{'=' * 80}")
        logger.info(f" 开始生成 SHIBOR 远期利率分析报告")
        logger.info(f"   案例名称: {case_name}")
        logger.info(f"   时间范围: {start_date} ~ {end_date}")
        logger.info(f"{'=' * 80}")

        try:
            result_df = self.calculator.run(
                start_date=start_date,
                end_date=end_date
            )

            logger.info(f"\n✅ 分析执行成功!")
            logger.info(f"   输出目录: {self.calculator.output_dir}")

            # 获取输出文件列表
            output_files = []
            for file in os.listdir(self.calculator.output_dir):
                if file.endswith(('.pdf', '.png', '.csv')):
                    file_path = os.path.join(self.calculator.output_dir, file)
                    file_size = os.path.getsize(file_path)
                    size_str = f"{file_size / 1024:.1f} KB"
                    output_files.append({
                        'name': file,
                        'path': file_path,
                        'size': size_str
                    })

            return {
                'name': case_name,
                'output_dir': self.calculator.output_dir,
                'output_files': output_files,
                'start_date': start_date,
                'end_date': end_date,
                'data_points': len(result_df) if result_df is not None else 0
            }

        except Exception as e:
            logger.error(f"❌ 分析执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise e

    def run_batch_reports(self, report_configs):
        """
        批量生成 SHIBOR 远期利率分析报告

        参数:
        - report_configs: 报告配置列表

        返回:
        - all_results: 所有分析结果列表
        """
        all_results = []

        for idx, config in enumerate(report_configs, 1):
            logger.info("\n" + "=" * 80)
            logger.info(f" 开始生成第 {idx}/{len(report_configs)} 个分析报告")
            logger.info(f"   报告名称: {config['name']}")
            logger.info("=" * 80)

            start_date = config.get("start_date")
            end_date = config.get("end_date")
            if end_date is None:
                end_date = CommonParameters.today

            self.job_logger.start_job('ShiborForwardRateReport', 'ForwardRate',
                                      params={'report_name': config['name'],
                                              'start_date': start_date, 'end_date': end_date})
            try:
                result = self.generate_report(
                    start_date=start_date,
                    end_date=end_date,
                    case_name=config["name"]
                )

                all_results.append(result)
                self.job_logger.end_job_success(records_processed=result.get('data_points', 0))

                logger.info(f"\n✅ 第 {idx} 个案例分析完成")
                logger.info(f"   数据点数: {result['data_points']}")
                logger.info(f"   输出文件数: {len(result['output_files'])}")

            except Exception as e:
                logger.error(f"❌ 第 {idx} 个分析失败: {config['name']}")
                logger.error(f"   错误信息: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                self.job_logger.end_job_failed(str(e), traceback.format_exc())
                continue

        # 总结
        if all_results:
            logger.info("\n" + "=" * 80)
            logger.info(" 所有 SHIBOR 远期利率分析任务完成！")
            logger.info(f" 成功生成 {len(all_results)} 个报告")
            logger.info(f" 报告输出目录: {all_results[0]['output_dir']}")
            logger.info("=" * 80)

            # 列出所有生成的文件
            logger.info(f"\n📁 生成的文件列表:")
            for result in all_results:
                logger.info(f"\n  [{result['name']}]")
                for file_info in result['output_files']:
                    icon = '📄' if file_info['name'].endswith('.pdf') else \
                           '📊' if file_info['name'].endswith('.png') else '📋'
                    logger.info(f"    {icon} {file_info['name']} ({file_info['size']})")
        else:
            logger.warning("⚠️ 没有成功的测试案例")

        return all_results


if __name__ == "__main__":
    """
    使用示例 - 批量生成 SHIBOR 远期利率分析报告
    """
    import os

    runReport = RunShiborForwardRateReport()

    # ========================================
    # 配置测试案例
    # ========================================
    report_configs = [
        {
            "name": "SHIBOR远期利率_最近1年",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today
        },
        {
            "name": "SHIBOR远期利率_最近3年",
            "start_date": CommonDataParameters.get_start_date(days=1095),
            "end_date": CommonParameters.today
        },
        {
            "name": "SHIBOR远期利率_最近5年",
            "start_date": CommonDataParameters.get_start_date(days=1825),
            "end_date": CommonParameters.today
        }
    ]

    # 执行批量报告生成
    all_results = runReport.run_batch_reports(report_configs)
