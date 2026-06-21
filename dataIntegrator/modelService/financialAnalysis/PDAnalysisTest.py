import traceback
from collections import defaultdict

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.modelService.financialAnalysis.PDAnalysis import PDAnalysis
from dataIntegrator.modelService.financialAnalysis.PDAnalysisReport import PDAnalysisReport
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class PDAnalysisTest:

    def run_single_analysis(self, symbol: str, name: str = None, generate_report: bool = False):
        """
        对单只股票执行 PD 分析

        Args:
            symbol (str): 股票代码，如 '002093'
            name (str): 股票名称（用于日志），如 '国脉科技'
            generate_report (bool): 是否在分析后生成 PDF 报告

        Returns:
            pd.DataFrame: 计算结果
        """
        stock_label = f"{name} ({symbol})" if name else symbol
        logger.info(f"====== 开始处理 {stock_label} ======")

        try:
            pdAnalysis = PDAnalysis()
            result_df = pdAnalysis.run(symbol)

            if result_df.empty:
                logger.warning(f"{stock_label} 无有效计算结果")
            else:
                logger.info(f"  {stock_label} 计算结果 ({len(result_df)} 行):")
                # 打印关键指标摘要
                summary_cols = ['date', 'z_score', 'risk_level', 'pd', 'el']
                display_cols = [c for c in summary_cols if c in result_df.columns]
                logger.info(f"\n{result_df[display_cols].tail(5).to_string(index=False)}")

                # 可选: 生成 PDF 报告
                if generate_report:
                    logger.info(f"  生成 {stock_label} PD 分析报告...")
                    report = PDAnalysisReport()
                    report.generate_single_stock_report(symbol)

        except Exception as e:
            logger.error(f"处理 {stock_label} 失败: %s", e)
            logger.error(traceback.format_exc())

        logger.info(f"====== 完成处理 {stock_label} ======")
        return result_df if 'result_df' in locals() else None

    def run_all_analysis(self, start_year=None, generate_reports: bool = False):
        """
        对 CommonDataParameters.STOCK_LIST 中所有股票批量执行 PD 分析

        Args:
            start_year (str|None): 起始年份（仅日志记录用）
            generate_reports (bool): 是否在批量分析后统一生成所有股票 PDF 报告
        """
        logger.info("=" * 80)
        logger.info("  批量 PD 分析开始")
        logger.info(f"  股票数量: {len(CommonDataParameters.STOCK_LIST)}")
        logger.info(f"  start_year: {start_year}")
        logger.info(f"  生成报告: {generate_reports}")
        logger.info("=" * 80)

        success_count = 0
        fail_count = 0

        for stock_info in CommonDataParameters.STOCK_LIST:
            ts_code = stock_info['ts_code']      # e.g. '002093.SZ'
            name = stock_info['name']             # e.g. '国脉科技'
            symbol = ts_code.split('.')[0]        # e.g. '002093'

            try:
                self.run_single_analysis(symbol=symbol, name=name, generate_report=False)
                success_count += 1
            except Exception as e:
                logger.error(f"处理 {name} ({symbol}) 异常: %s", e)
                fail_count += 1

        logger.info("=" * 80)
        logger.info(f"  批量 PD 分析完成！成功: {success_count}, 失败: {fail_count}")
        logger.info("=" * 80)

        # 统一生成 PDF 报告（在 ClickHouse 入库之后）
        if generate_reports:
            logger.info("\n" + "=" * 80)
            logger.info("  开始批量生成 PD 分析 PDF 报告...")
            logger.info("=" * 80)
            try:
                report = PDAnalysisReport()
                report_path = report.generate_all_stocks_report()
                logger.info(f"  PDF 综合报告生成完成: {report_path}")
            except Exception as e:
                logger.error(f"批量报告生成失败: {e}")
                logger.error(traceback.format_exc())

    def run_analysis_by_sector(self, start_year=None, generate_reports: bool = False):
        """
        按股票所属板块分组，批量执行 PD 分析并为每个板块生成独立报告

        1. 从 CommonDataParameters.STOCK_LIST 获取股票列表
        2. 通过 ClickHouse df_tushare_stock_basic 查询每只股票的 industry
        3. 按 industry 分组
        4. 对每个板块：先分析所有股票入库，再生成该板块的 PDF 报告
           → 文件名: PD分析综合报告_industry_[分析起始日-分析结束日]_yyyymmdd_hhmmss.pdf

        Args:
            start_year (str|None): 起始年份（仅日志记录用）
            generate_reports (bool): 是否生成板块 PDF 报告
        """
        logger.info("=" * 80)
        logger.info("  按板块分组 PD 分析开始")
        logger.info(f"  股票数量: {len(CommonDataParameters.STOCK_LIST)}")
        logger.info(f"  start_year: {start_year}")
        logger.info(f"  生成报告: {generate_reports}")
        logger.info("=" * 80)

        # ========== 步骤1: 获取每只股票的 industry ==========
        logger.info("\n--- 步骤1: 查询股票所属板块 ---")
        sector_map = defaultdict(list)  # industry -> [stock_info, ...]
        query_fail_count = 0

        for stock_info in CommonDataParameters.STOCK_LIST:
            ts_code = stock_info['ts_code']
            name = stock_info['name']
            symbol = ts_code.split('.')[0]

            # 优先从 STOCK_LIST 中获取 industry（如果已配置）
            industry = stock_info.get('industry')

            # 如果 STOCK_LIST 中没有 industry，则从 ClickHouse 查询
            if not industry:
                try:
                    sql = "SELECT industry FROM indexsysdb.df_tushare_stock_basic WHERE ts_code = %(ts_code)s"
                    result = ClickhouseService.clickhouseClient.execute(sql, {'ts_code': ts_code})
                    if result and result[0] and result[0][0]:
                        industry = result[0][0]
                        logger.info(f"  {name} ({symbol}) → 板块: {industry} (ClickHouse)")
                    else:
                        industry = '未知板块'
                        logger.warning(f"  {name} ({symbol}) → ClickHouse 未查到 industry，归入'未知板块'")
                except Exception as e:
                    industry = '未知板块'
                    logger.error(f"  {name} ({symbol}) → ClickHouse 查询 industry 失败: {e}")
                    query_fail_count += 1
            else:
                logger.info(f"  {name} ({symbol}) → 板块: {industry} (STOCK_LIST)")

            sector_map[industry].append(stock_info)

        logger.info(f"\n  板块分布: {dict((k, len(v)) for k, v in sector_map.items())}")
        if query_fail_count:
            logger.warning(f"  ClickHouse 查询失败数: {query_fail_count}")

        # ========== 步骤2: 按板块逐个处理 ==========
        total_success = 0
        total_fail = 0
        sector_count = len(sector_map)

        for sector_idx, (industry, stock_list) in enumerate(sector_map.items(), 1):
            logger.info("\n" + "=" * 80)
            logger.info(f"  [{sector_idx}/{sector_count}] 处理板块: {industry} ({len(stock_list)} 只股票)")
            logger.info("=" * 80)

            sector_success = 0
            sector_fail = 0

            # 2a. 批量分析该板块所有股票
            for stock_info in stock_list:
                ts_code = stock_info['ts_code']
                name = stock_info['name']
                symbol = ts_code.split('.')[0]

                try:
                    self.run_single_analysis(symbol=symbol, name=name, generate_report=False)
                    sector_success += 1
                except Exception as e:
                    logger.error(f"处理 {name} ({symbol}) 异常: %s", e)
                    sector_fail += 1

            total_success += sector_success
            total_fail += sector_fail

            logger.info(f"  板块 [{industry}] 分析完成！成功: {sector_success}, 失败: {sector_fail}")

            # 2b. 生成该板块的 PDF 报告
            if generate_reports and sector_success > 0:
                logger.info(f"\n  开始生成板块 [{industry}] 的 PD 分析 PDF 报告...")
                try:
                    report = PDAnalysisReport()
                    report_path = report.generate_sector_report(stock_list, industry)
                    logger.info(f"  板块 [{industry}] PDF 报告生成完成: {report_path}")
                except Exception as e:
                    logger.error(f"板块 [{industry}] 报告生成失败: {e}")
                    logger.error(traceback.format_exc())

        logger.info("\n" + "=" * 80)
        logger.info(f"  按板块分组 PD 分析全部完成！")
        logger.info(f"  总板块数: {sector_count}")
        logger.info(f"  总成功: {total_success}, 总失败: {total_fail}")
        logger.info("=" * 80)


if __name__ == '__main__':
    pdAnalysisTest = PDAnalysisTest()

    # ---- 测试模式选择 ----

    # # 模式1: 单只股票测试 + 报告
    # pdAnalysisTest.run_single_analysis(symbol='002093', name='国脉科技', generate_report=True)
    # pdAnalysisTest.run_single_analysis(symbol='600490', name='鹏欣资源', generate_report=True)
    # pdAnalysisTest.run_single_analysis(symbol='000902', name='新洋丰', generate_report=True)
    # pdAnalysisTest.run_single_analysis(symbol='688498', name='源杰科技', generate_report=True)

    # 模式2: 批量处理 STOCK_LIST 中所有股票（分析 + 报告）
    pdAnalysisTest.run_all_analysis(start_year="2020", generate_reports=True)

    # 模式3: 批量处理 STOCK_LIST 中所有股票（分析 + 报告）
    # pdAnalysisTest.run_all_analysis(start_year="2020", generate_reports=False)

    # 模式4: 按板块分组处理（分析 + 报告）—— 为每个行业板块生成独立报告
    pdAnalysisTest.run_analysis_by_sector(start_year="2020", generate_reports=True)

    # # 模式5: 仅按板块分组分析（不生成报告）
    # pdAnalysisTest.run_analysis_by_sector(start_year="2020", generate_reports=False)
