"""
TuShareOptDailyIndicatorServiceTest 计算Option 各项数据及Greeks指标
    输入：df_tushare_opt_daily
    逻辑：OptDailyIndicatorReport - 根据 TuShareOptDailyIndicatorServiceTest 的数据出具最基础的Option分析报表
    输出：indexsysdb.tb_tushare_opt_daily_indicator

    OptionDailyIndicatorReportTest 根据 tb_tushare_opt_daily_indicator 数据出具最基础的Option分析报表
        输入：indexsysdb.tb_tushare_opt_daily_indicator
        逻辑：OptDailyIndicatorReport - 根据 TuShareOptDailyIndicatorServiceTest 的数据出具最基础的Option分析报表
        输出：indexsysdb.tb_option_daily_indicator_report


OptionTradingStrategyAnalyzer 从专业交易员视角, 对 Option进行 分析策略分析器，得出结论是否买入
    输入：indexsysdb.tb_tushare_opt_daily_indicator
    逻辑：策略盈亏总览 LongCall详细分析 多情景盈亏 交易信号汇总
    输出：indexsysdb.tb_option_trading_strategy_indicator

    OptionTradingStrategyAnalyzerReport 根据 tb_option_trading_strategy_indicator 数据出具最基础的Option分析报表
        输入：indexsysdb.tb_option_trading_strategy_indicator
        逻辑：OptTradingStrategyReport - 根据 OptionTradingStrategyAnalyzer 的数据出具最基础的Option分析报表
        输出：indexsysdb.tb_option_trading_strategy_report


OptionPutCallParityMonitor =Put-Call Parity 实时监

OptPutCallParityReport
    1. 从 tb_option_pcp_monitor 拉取监控数据
    2. 生成图表：PCP偏差时序图、z-score分布、告警汇总、股息分解图
    3. 生成 PDF 报告
"""