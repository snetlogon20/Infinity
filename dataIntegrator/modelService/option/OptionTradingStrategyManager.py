r"""
期权策略分析/报告 统一管理器（全流水线统一入口）

按严格顺序串联期权数据全链路（上游 → 下游，前序阶段的落库数据是后序阶段的输入）：

    Step 1: OptionDailyIndicator.OptionDailyIndicatorManager
            期权日线指标计算落库（df_tushare_opt_daily → tb_tushare_opt_daily_indicator）
    Step 2: OptionDailyIndicator.OptionDailyIndicatorReport
            期权日线指标 PDF 报告（IV / Greeks / IV Smile 等）
    Step 3: OptionTradingSingleStrategyAnalyzer.OptionSingleTradingStrategyAnalyzer
            单策略（Long Call/Put）盈亏分析落库（→ tb_option_trading_strategy_indicator）
    Step 4: OptionTradingSingleStrategyAnalyzer.OptionSingleTradingStrategyAnalyzerReport
            单策略 Excel + PDF 报告
    Step 5: optionPutCallParityMonitor.OptionPutCallParityMonitor
            Put-Call Parity 监控落库（→ tb_option_pcp_monitor）
    Step 6: optionPutCallParityMonitor.OptionPutCallParityReport
            PCP 监控 PDF 报告
    Step 7: OptionTradingStrategyManager 目录下全部 12 个策略组合
            XxxStrategyAnalysisTest.py（分析落库）+ XxxStrategyReportTest.py（PDF 报告）

任一上游阶段失败即中止整条流水线（避免下游基于不完整数据出报表）。

用法：
    # 1. 全量跑（分析落库 + PDF 报告，全部 12 个策略）
    #    缺省区间 = CommonParameters.today 往前推 365 天 ~ CommonParameters.today
    manager = OptionTradingStrategyManager()
    manager.run()
    # 或显式指定区间
    manager.run("20251004", "20261004")

    # 2. 单策略跑（分析 + 报告）
    manager.run_strategy('SHORT_STRANGLE')

    # 3. 只跑分析 / 只跑报告
    manager.run_analysis('CALENDAR')
    manager.run_report('CALENDAR')

    # 4. 覆盖默认参数（换月滚动时改 symbol_filter 即可）
    manager.run_strategy('PROTECTIVE_PUT', {
        "name": "华夏上证50ETF认沽期权2603（Protective Put）",
        "start_date": "20251222",
        "end_date": "20260320",
        "call_put": "P",
        "symbol_filter": "510050P2603%",
    })

工厂模式：
    - 分析端：OptionStrategyFactory.create(strategy_type) 创建分析器
    - 报告端：本类 _report_registry 注册表映射 strategy_type -> 报告类

已接入策略（12 个，与 OptionStrategyFactory 注册表一一对应）：
    PROTECTIVE_PUT / COVERED_CALL / BULL_CALL_SPREAD / BEAR_PUT_SPREAD /
    BUTTERFLY_SPREAD / LONG_STRADDLE / SHORT_STRADDLE / STRIP / STRAP /
    LONG_STRANGLE / SHORT_STRANGLE / CALENDAR

调度入口：
    CICD\batch\report\run_Report.py（ReportRunner.report_method_dict）
"""

import traceback
from datetime import datetime, timedelta

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyFactory import (
    OptionStrategyFactory
)

# ---------- import 上游流水线模块（Step 1~6，严格顺序执行） ----------
from dataIntegrator.modelService.option.OptionDailyIndicator.OptionDailyIndicatorManager import (
    OptionDailyIndicatorManager
)
from dataIntegrator.modelService.option.OptionDailyIndicator.OptionDailyIndicatorReport import (
    OptionDailyIndicatorReport
)
from dataIntegrator.modelService.option.OptionTradingSingleStrategyAnalyzer.OptionSingleTradingStrategyAnalyzer import (
    OptionSingleTradingStrategyAnalyzer
)
from dataIntegrator.modelService.option.OptionTradingSingleStrategyAnalyzer.OptionSingleTradingStrategyAnalyzerReport import (
    OptionSingleTradingStrategyAnalyzerReport
)
from dataIntegrator.modelService.option.optionPutCallParityMonitor.OptionPutCallParityMonitor import (
    OptionPutCallParityMonitor
)
from dataIntegrator.modelService.option.optionPutCallParityMonitor.OptionPutCallParityReport import (
    OptionPutCallParityReport
)

# ---------- import 所有报告类（报告端注册表用） ----------
from dataIntegrator.modelService.option.OptionTradingStrategyManager.ProtectivePutStrategyReport import (
    ProtectivePutStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.CoveredCallStrategyReport import (
    CoveredCallStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.BullCallSpreadStrategyReport import (
    BullCallSpreadStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.BearPutSpreadStrategyReport import (
    BearPutSpreadStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.ButterflySpreadStrategyReport import (
    ButterflySpreadStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.LongStraddleStrategyReport import (
    LongStraddleStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.ShortStraddleStrategyReport import (
    ShortStraddleStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.StripStrategyReport import (
    StripStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.StrapStrategyReport import (
    StrapStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.LongStrangleStrategyReport import (
    LongStrangleStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.ShortStrangleStrategyReport import (
    ShortStrangleStrategyReport
)
from dataIntegrator.modelService.option.OptionTradingStrategyManager.CalendarSpreadStrategyReport import (
    CalendarSpreadStrategyReport
)

logger = CommonLib.logger


class OptionTradingStrategyManager:
    """期权策略分析/报告 统一管理器（工厂模式）"""

    # ================================================================
    # 报告端注册表: strategy_type -> 报告类
    # （分析端走 OptionStrategyFactory，此处只注册报告类）
    # ================================================================
    _report_registry = {
        'PROTECTIVE_PUT': ProtectivePutStrategyReport,
        'COVERED_CALL': CoveredCallStrategyReport,
        'BULL_CALL_SPREAD': BullCallSpreadStrategyReport,
        'BEAR_PUT_SPREAD': BearPutSpreadStrategyReport,
        'BUTTERFLY_SPREAD': ButterflySpreadStrategyReport,
        'LONG_STRADDLE': LongStraddleStrategyReport,
        'SHORT_STRADDLE': ShortStraddleStrategyReport,
        'STRIP': StripStrategyReport,
        'STRAP': StrapStrategyReport,
        'LONG_STRANGLE': LongStrangleStrategyReport,
        'SHORT_STRANGLE': ShortStrangleStrategyReport,
        'CALENDAR': CalendarSpreadStrategyReport,
    }

    # ================================================================
    # 默认批次配置 — 与各 *AnalysisTest.py / *ReportTest.py 保持一致
    # （call_put=None 表示 Call+Put 双腿；CALENDAR 跨月配对 symbol_filter 不带月份）
    # ================================================================
    _default_configs = {
        'PROTECTIVE_PUT': {
            "name": "华夏上证50ETF认沽期权（Protective Put）",
            "call_put": "P",
            "symbol_filter": "510050P2612%",
        },
        'COVERED_CALL': {
            "name": "华夏上证50ETF认购期权（Covered Call）",
            "call_put": "C",
            "symbol_filter": "510050C2612%",
        },
        'BULL_CALL_SPREAD': {
            "name": "华夏上证50ETF认购期权（Bull Call Spread）",
            "call_put": "C",
            "symbol_filter": "510050C2612%",
        },
        'BEAR_PUT_SPREAD': {
            "name": "华夏上证50ETF认沽期权（Bear Put Spread）",
            "call_put": "P",
            "symbol_filter": "510050P2612%",
        },
        'BUTTERFLY_SPREAD': {
            "name": "华夏上证50ETF认购期权（Butterfly Spread 蝴蝶价差）",
            "call_put": "C",
            "symbol_filter": "510050C2612%",
        },
        'LONG_STRADDLE': {
            "name": "华夏上证50ETF期权（Long Straddle）",
            "call_put": None,
            "symbol_filter": "510050%2612%",
        },
        'SHORT_STRADDLE': {
            "name": "华夏上证50ETF期权（Short Straddle）",
            "call_put": None,
            "symbol_filter": "510050%2612%",
        },
        'STRIP': {
            "name": "华夏上证50ETF期权（Strip）",
            "call_put": None,
            "symbol_filter": "510050%2612%",
        },
        'STRAP': {
            "name": "华夏上证50ETF期权（Strap）",
            "call_put": None,
            "symbol_filter": "510050%2612%",
        },
        'LONG_STRANGLE': {
            "name": "华夏上证50ETF期权（Long Strangle）",
            "call_put": None,
            "symbol_filter": "510050%2612%",
        },
        'SHORT_STRANGLE': {
            "name": "华夏上证50ETF期权（Short Strangle）",
            "call_put": None,
            "symbol_filter": "510050%2612%",
        },
        'CALENDAR': {
            "name": "华夏上证50ETF期权（Calendar Spread）",
            "call_put": "C",
            "symbol_filter": "510050%",
        },
    }

    # ================================================================
    # 上游流水线批次配置 — 与各模块 *Test.py 保持一致
    # （日期由 run(start_date, end_date) 统一注入，此处只保留过滤条件）
    # ================================================================
    # Step 1: 期权日线指标计算落库（全量 510050 合约）
    _daily_indicator_configs = [
        {
            "name": "华夏上证50ETF看涨欧式期权",
            "call_put": "C",
            "exercise_type": "欧式",
            "symbol_filter": "510050%",
        },
        {
            "name": "华夏上证50ETF看跌欧式期权",
            "call_put": "P",
            "exercise_type": "欧式",
            "symbol_filter": "510050%",
        },
    ]

    # Step 2: 期权日线指标 PDF 报告（只取单月合约，否则数据量过大报表失去意义）
    _daily_indicator_report_configs = [
        {
            "name": "华夏上证50ETF看涨欧式期权",
            "call_put": "C",
            "symbol_filter": "510050_2612%",
        },
        {
            "name": "华夏上证50ETF看跌欧式期权",
            "call_put": "P",
            "symbol_filter": "510050_2612%",
        },
    ]

    # Step 3: 单策略（Long Call/Put）盈亏分析落库
    _single_strategy_analyzer_configs = [
        {
            "name": "HO2612看涨欧式期权",
            "call_put": "C",
            "exercise_type": "欧式",
            "ts_code_filter": "HO2612%",
        },
        {
            "name": "HO2612看跌欧式期权",
            "call_put": "P",
            "exercise_type": "欧式",
            "ts_code_filter": "HO2612%",
        },
    ]

    # Step 4: 单策略 Excel + PDF 报告（trade_date 由 run() 的 end_date 注入）
    _single_strategy_analyzer_report_configs = [
        {
            "name": "HO2612看涨欧式期权",
            "call_put": "C",
            "ts_code_filter": "HO2612%",
        },
        {
            "name": "HO2612看跌欧式期权",
            "call_put": "P",
            "ts_code_filter": "HO2612%",
        },
    ]

    # Step 6: PCP 监控 PDF 报告（全部标的，日期由 run() 注入）
    _pcp_report_config = {
        "name": "期权平价关系（Put-Call Parity）监控报告",
        "underlying_code": None,
    }

    def __init__(self):
        logger.info("OptionTradingStrategyManager __init__ started")
        # 分析端与报告端注册表对齐校验
        factory_strategies = set(OptionStrategyFactory.list_strategies().keys())
        report_strategies = set(self._report_registry.keys())
        if factory_strategies != report_strategies:
            logger.warning(
                f"注册表不一致: 分析器独有 {sorted(factory_strategies - report_strategies)}, "
                f"报告独有 {sorted(report_strategies - factory_strategies)}"
            )

    # ================================================================
    # 内部工具
    # ================================================================
    @staticmethod
    def _rolling_start_date(days=365):
        """滚动起点：CommonParameters.today 往前推 365 天（YYYYMMDD）"""
        end_date = CommonParameters.today
        return (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")

    @classmethod
    def _build_config(cls, strategy_type, param_dict=None):
        """合并默认配置与外部参数（param_dict 优先）"""
        base = dict(cls._default_configs.get(strategy_type, {}))
        if param_dict:
            base.update(param_dict)
        base.setdefault("name", strategy_type)
        base.setdefault("start_date", cls._rolling_start_date())
        base.setdefault("end_date", CommonParameters.today)
        return base

    @classmethod
    def _get_report_class(cls, strategy_type):
        """报告端工厂：按 strategy_type 取报告类"""
        report_class = cls._report_registry.get(strategy_type)
        if report_class is None:
            available = ', '.join(sorted(cls._report_registry.keys())) or '(none)'
            raise ValueError(f"Unknown strategy_type '{strategy_type}'. Available: {available}")
        return report_class

    @staticmethod
    def _with_dates(config, start_date, end_date):
        """向批次配置注入统一日期区间（不覆盖已有值）"""
        merged = dict(config)
        merged.setdefault("start_date", start_date)
        merged.setdefault("end_date", end_date)
        return merged

    @staticmethod
    def _run_pipeline_stage(stage_name, configs, runner):
        """通用流水线阶段执行器

        逐配置调用 runner(config) 并汇总失败；存在失败配置时抛出
        RuntimeError，由调用方中止下游阶段（下游依赖本阶段落库的数据，
        继续执行会基于不完整数据出报表）。

        :param stage_name: 阶段名（日志标识，如 'Step1_OptionDailyIndicatorManager'）
        :param configs: 批次配置列表
        :param runner: callable(config) -> 结果（DataFrame / 文件路径 / dict 等）
        """
        logger.info("\n%s", "#" * 60)
        logger.info("Pipeline Stage [%s]: %d config(s), started: %s",
                    stage_name, len(configs), datetime.now())
        logger.info("%s", "#" * 60)

        failures = []
        for idx, cfg in enumerate(configs, 1):
            name = cfg.get("name", "Unknown")
            logger.info("\n%s", "=" * 60)
            logger.info("  [%s] config [%d/%d]: %s - started: %s",
                        stage_name, idx, len(configs), name, datetime.now())
            logger.info("%s", "=" * 60)
            try:
                result = runner(cfg)
                if result is None:
                    logger.warning("  ⚠️ [%s] %s 数据为空，批次跳过", stage_name, name)
                elif isinstance(result, dict):
                    # dict 结果（如 Step 4 的 {'excel': ..., 'pdf': ...}）：
                    # 所有值均为空视为空数据
                    if any(v for v in result.values()):
                        logger.info("  ✅ [%s] %s 完成", stage_name, name)
                    else:
                        logger.warning("  ⚠️ [%s] %s 数据为空，批次跳过", stage_name, name)
                elif hasattr(result, "__len__") and len(result) == 0:
                    logger.warning("  ⚠️ [%s] %s 数据为空，批次跳过", stage_name, name)
                else:
                    logger.info("  ✅ [%s] %s 完成", stage_name, name)
            except Exception as e:
                logger.error("  ❌ [%s] %s 失败: %s", stage_name, name, e)
                logger.error(traceback.format_exc())
                failures.append((name, str(e)))

        if failures:
            raise RuntimeError(
                f"Pipeline stage {stage_name} failed for {len(failures)} config(s): "
                + "; ".join(f"{n}: {err}" for n, err in failures))

        logger.info("Pipeline Stage [%s] completed: %s", stage_name, datetime.now())

    # ================================================================
    # 单策略入口
    # ================================================================
    def run_analysis(self, strategy_type, param_dict=None):
        """单策略分析落库（整合各 XxxStrategyAnalysisTest 的内容）

        通过 OptionStrategyFactory.create(strategy_type) 创建分析器，
        按 _default_configs（可被 param_dict 覆盖）计算策略指标并写入 ClickHouse。
        """
        logger.info("run_analysis started, strategy=%s, %s", strategy_type, datetime.now())

        try:
            config = self._build_config(strategy_type, param_dict)

            logger.info("\n%s", "=" * 60)
            logger.info("  分析批次: %s", config.get("name"))
            logger.info("%s", "=" * 60)

            # 分析端工厂
            analyzer = OptionStrategyFactory.create(strategy_type)
            df = analyzer.run(config)

            if df is not None and len(df) > 0:
                latest_date = df['trade_date'].max()
                latest = df[df['trade_date'] == latest_date]
                signal_counts = latest['trade_signal'].value_counts().to_dict()
                logger.info("  ✅ 分析完成并落库: %s rows", len(df))
                logger.info("  最新交易日 %s 信号分布: %s", latest_date, signal_counts)
            else:
                logger.warning("  ⚠️ 数据为空，批次跳过")

            logger.info("run_analysis ended, strategy=%s", strategy_type)
            return df

        except Exception as e:
            logger.error("run_analysis failed, strategy=%s: %s", strategy_type, e)
            logger.error(traceback.format_exc())
            raise e

    def run_report(self, strategy_type, param_dict=None):
        """单策略 PDF 报告（整合各 XxxStrategyReportTest 的内容）

        前置条件：先运行 run_analysis 完成 tb_option_trading_strategy_xxx 落库。
        输出目录: CommonParameters.optionAnalysisReportPath
        """
        logger.info("run_report started, strategy=%s, %s", strategy_type, datetime.now())

        try:
            config = self._build_config(strategy_type, param_dict)

            logger.info("\n%s", "=" * 60)
            logger.info("  报告批次: %s", config.get("name"))
            logger.info("%s", "=" * 60)

            # 报告端工厂
            report_class = self._get_report_class(strategy_type)
            report = report_class()
            filepath = report.run(config)

            if filepath:
                logger.info("  ✅ PDF 报告已生成: %s", filepath)
            else:
                logger.warning("  ⚠️ 数据为空（先运行 run_analysis），报告跳过")

            logger.info("run_report ended, strategy=%s", strategy_type)
            return filepath

        except Exception as e:
            logger.error("run_report failed, strategy=%s: %s", strategy_type, e)
            logger.error(traceback.format_exc())
            raise e

    def run_strategy(self, strategy_type, param_dict=None):
        """单策略全流程：先分析落库，再生成 PDF 报告"""
        logger.info("run_strategy started, strategy=%s, %s", strategy_type, datetime.now())

        self.run_analysis(strategy_type, param_dict)
        self.run_report(strategy_type, param_dict)

        logger.info("run_strategy ended, strategy=%s", strategy_type)

    # ================================================================
    # 全量入口
    # ================================================================
    def run_all_strategies(self, param_dict=None):
        """工厂模式：按注册表顺序批量执行全部策略（分析落库 + PDF 报告）

        :return: failed_strategies, 失败策略列表 [(strategy_type, error), ...]，
                 空列表表示全部成功
        """
        logger.info("run_all_strategies started, %s", datetime.now())

        strategy_list = list(self._report_registry.keys())
        failed_strategies = []

        for idx, strategy_type in enumerate(strategy_list, 1):
            try:
                logger.info("\n%s", '=' * 60)
                logger.info("Running: [%d/%d] %s - started: %s",
                            idx, len(strategy_list), strategy_type, datetime.now())
                logger.info("%s", '=' * 60)
                self.run_strategy(strategy_type, param_dict)
                logger.info("%s executed successfully!", strategy_type)
            except Exception as e:
                logger.error("%s failed: %s", strategy_type, e)
                failed_strategies.append((strategy_type, str(e)))

        logger.info("\n%s", '=' * 60)
        logger.info("All Option Trading Strategies Execution Completed!")
        logger.info("Finished: %s", datetime.now())
        if failed_strategies:
            logger.error("Failed strategies (%d):", len(failed_strategies))
            for sname, err in failed_strategies:
                logger.error("  - %s: %s", sname, err)
        else:
            logger.info("All strategies executed successfully!")
        logger.info("%s", '=' * 60)

        logger.info("run_all_strategies completed successfully")
        return failed_strategies

    def run(self, start_date=None, end_date=None):
        """统一入口（供 run_Report.py 的 ReportRunner 工厂字典调用）

        严格按以下顺序执行完整期权数据流水线（前序阶段落库数据是后序阶段输入）：
            Step 1: OptionDailyIndicatorManager          期权日线指标计算落库
            Step 2: OptionDailyIndicatorReport           期权日线指标 PDF 报告
            Step 3: OptionSingleTradingStrategyAnalyzer        单策略盈亏分析落库
            Step 4: OptionSingleTradingStrategyAnalyzerReport  单策略 Excel + PDF 报告
            Step 5: OptionPutCallParityMonitor           PCP 监控落库
            Step 6: OptionPutCallParityReport            PCP 监控 PDF 报告
            Step 7: 12 个策略组合（run_all_strategies）  分析落库 + PDF 报告

        任一上游阶段失败即中止整条流水线，避免下游基于不完整数据出报表。

        :param start_date: 分析起始日期 YYYYMMDD，缺省 = CommonParameters.today 往前推 365 天
        :param end_date:   分析截止日期 YYYYMMDD，缺省 = CommonParameters.today
        """
        if start_date is None:
            start_date = self._rolling_start_date()
        if end_date is None:
            end_date = CommonParameters.today

        logger.info("OptionTradingStrategyManager.run: period=[%s, %s]", start_date, end_date)

        # 报表任务日志（与 BondYieldComparator 相同的 ReportJobLogger 机制）
        # 注：各子任务由各模块内部分别记录明细日志，此处仅记录整个批次的汇总状态。
        job_logger = ReportJobLogger()
        job_logger.start_job('OptionTradingStrategyManager', 'OptionTradingStrategy',
                             params={'start_date': start_date,
                                     'end_date': end_date,
                                     'strategies_count': len(self._report_registry)})

        try:
            # ================= 上游流水线 Step 1~6（严格顺序） =================

            # Step 1: 期权日线指标计算落库（tb_tushare_opt_daily_indicator，
            #         为 Step 2~7 全部下游提供基础数据）
            daily_indicator_manager = OptionDailyIndicatorManager()
            self._run_pipeline_stage(
                "Step1_OptionDailyIndicatorManager",
                self._daily_indicator_configs,
                lambda cfg: daily_indicator_manager.run(
                    start_date=start_date, end_date=end_date,
                    call_put=cfg.get("call_put"),
                    exercise_type=cfg.get("exercise_type"),
                    symbol_filter=cfg.get("symbol_filter")))

            # Step 2: 期权日线指标 PDF 报告（IV / Greeks / IV Smile 等）
            daily_indicator_reporter = OptionDailyIndicatorReport()
            self._run_pipeline_stage(
                "Step2_OptionDailyIndicatorReport",
                self._daily_indicator_report_configs,
                lambda cfg: daily_indicator_reporter.run(
                    start_date=start_date, end_date=end_date,
                    symbol_filter=cfg.get("symbol_filter"),
                    call_put=cfg.get("call_put")))

            # Step 3: 单策略（Long Call/Put）盈亏分析落库
            #         （tb_option_trading_strategy_indicator，供 Step 4 报表使用）
            single_strategy_analyzer = OptionSingleTradingStrategyAnalyzer()
            self._run_pipeline_stage(
                "Step3_OptionSingleTradingStrategyAnalyzer",
                self._single_strategy_analyzer_configs,
                lambda cfg: single_strategy_analyzer.run(
                    self._with_dates(cfg, start_date, end_date)))

            # Step 4: 单策略 Excel + PDF 报告（基于截止交易日快照）
            single_strategy_reporter = OptionSingleTradingStrategyAnalyzerReport()
            self._run_pipeline_stage(
                "Step4_OptionSingleTradingStrategyAnalyzerReport",
                self._single_strategy_analyzer_report_configs,
                lambda cfg: single_strategy_reporter.run(
                    trade_date=end_date,
                    ts_code_filter=cfg.get("ts_code_filter"),
                    call_put=cfg.get("call_put")))

            # Step 5: Put-Call Parity 监控落库（单日监控 end_date，
            #         内部自动回拉 LOOKBACK_DAYS 历史做滚动统计）
            self._run_pipeline_stage(
                "Step5_OptionPutCallParityMonitor",
                [{"name": "Put-Call Parity Monitor (trade_date=%s)" % end_date}],
                lambda cfg: OptionPutCallParityMonitor().run(trade_date=end_date))

            # Step 6: PCP 监控 PDF 报告（读取 Step 5 落库的 tb_option_pcp_monitor）
            #         注意：不注入统一 start_date，保留报告自身默认 90 天回看窗口
            #         （DEFAULT_LOOKBACK_DAYS，与 OptionPutCallParityReportTest 口径一致）
            pcp_cfg = dict(self._pcp_report_config)
            pcp_cfg.setdefault("end_date", end_date)
            self._run_pipeline_stage(
                "Step6_OptionPutCallParityReport",
                [pcp_cfg],
                lambda cfg: OptionPutCallParityReport().run(cfg))

            # ================= Step 7: 12 个策略组合（分析 + 报告） =================
            failed_strategies = self.run_all_strategies(
                {"start_date": start_date, "end_date": end_date})

            if failed_strategies:
                job_logger.end_job_failed(
                    f"{len(failed_strategies)} strategies failed: "
                    + "; ".join(f"{s}: {err}" for s, err in failed_strategies))
            else:
                job_logger.end_job_success(
                    records_processed=len(self._report_registry))
        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise


def main():
    # 分析区间：end_date = 今天，start_date = 今天往前推 365 天（一年）
    start_date = (datetime.strptime(CommonParameters.today, "%Y%m%d") - timedelta(days=365)).strftime("%Y%m%d")
    end_date = CommonParameters.today

    optionTradingStrategyManager = OptionTradingStrategyManager()
    optionTradingStrategyManager.run(start_date, end_date)


if __name__ == '__main__':
    main()
