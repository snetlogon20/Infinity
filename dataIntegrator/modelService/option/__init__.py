"""
TuShareOptDailyIndicatorServiceTest 计算Option 各项数据及Greeks指标
    输入：df_tushare_opt_daily
    逻辑：OptDailyIndicatorReport - 根据 TuShareOptDailyIndicatorServiceTest 的数据出具最基础的Option分析报表
    输出：indexsysdb.tb_tushare_opt_daily_indicator

    OptionDailyIndicatorReportTest 根据 tb_tushare_opt_daily_indicator 数据出具最基础的Option分析报表
        输入：indexsysdb.tb_tushare_opt_daily_indicator
        逻辑：OptDailyIndicatorReport - 根据 TuShareOptDailyIndicatorServiceTest 的数据出具最基础的Option分析报表
        输出：indexsysdb.tb_option_daily_indicator_report


OptionTradingSingleStrategyAnalyzer 从专业交易员视角, 对 Option进行 分析策略分析器，得出结论是否买入
    输入：indexsysdb.tb_tushare_opt_daily_indicator
    逻辑：策略盈亏总览 LongCall详细分析 多情景盈亏 交易信号汇总
    输出：indexsysdb.tb_option_trading_strategy_indicator

    OptionSingleTradingStrategyAnalyzerReport 根据 tb_option_trading_strategy_indicator 数据出具最基础的Option分析报表
        输入：indexsysdb.tb_option_trading_strategy_indicator
        逻辑：OptTradingStrategyReport - 根据 OptionTradingSingleStrategyAnalyzer 的数据出具最基础的Option分析报表
        输出：indexsysdb.tb_option_trading_strategy_report




OptionPutCallParityMonitor =Put-Call Parity 实时监
    （模块：optionPutCallParityMonitor.OptionPutCallParityMonitor，落库 tb_option_pcp_monitor）

OptionPutCallParityReport
    （模块：optionPutCallParityMonitor.OptionPutCallParityReport）
    1. 从 tb_option_pcp_monitor 拉取监控数据（默认回看 90 天）
    2. 生成图表：PCP偏差时序图、z-score分布、告警汇总、股息分解图
    3. 生成 PDF 报告


optionVolatilityGreeksTrading 期权波动率交易与 Greeks 风险管理（选择器/评分器/风险汇总层，
    与 OptionTradingStrategyManager 的 12 个策略执行结构库分工互补）
    （目录：modelService/option/optionVolatilityGreeksTrading）

    GreeksEfficiencyAnalysis / GreeksEfficiencyReport
        1. VRP(IV−HV20) + Greeks 效率比扫描，联查 PCP z-score 过滤结构性错价
        2. 输出卖方分/买方分/角色推荐（SELL_VOL/BUY_VOL）
        3. 落库 tb_option_greeks_efficiency + PDF 报告（VRP时序/微笑/卖方效率/期限结构）

    PortfolioGreeksAggregator / PortfolioGreeksReport
        1. 持仓组合净 Δ/Γ/V/Θ/Rho 聚合（TOTAL/UNDERLYING/MATURITY 三视角）
        2. 动态 Delta 对冲建议（现货/ETF/股指期货）+ P&L Explain 损益归因
        3. 落库 tb_option_portfolio_greeks + PDF 报告

    VolSurfaceSkewTermAnalysis
        1. 波动率曲面切片指标：risk_reversal / skew_slope / butterfly / term_slope
        2. 落库 tb_option_vol_surface（偏度交易与日历价差信号研究）

"""