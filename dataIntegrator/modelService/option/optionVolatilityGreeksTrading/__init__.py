r"""
optionVolatilityGreeksTrading — 期权波动率交易与 Greeks 风险管理

专业定位(对三张输入表的专业回答):
    tb_tushare_opt_daily_indicator(全市场逐合约 BS Greeks/IV/moneyness)
    + tb_option_pcp_monitor(平价监控 z-score/股息分解)
    → 波动率交易体系(Volatility & Greeks Trading), 与既有 12 个策略表
      (执行结构库)分工: 本包是"选择器/评分器/风险汇总层"。

模块组成(按落地优先级):

    模块1 GreeksEfficiencyAnalysis / GreeksEfficiencyReport  (落库 tb_option_greeks_efficiency)
        VRP(波动率风险溢价) + Greeks 效率比扫描: 每合约 x 每日计算
        vrp=IV-HV20 / gamma_breakeven_move=sqrt(2|Θ|/Γ) / gamma_per_premium,
        联查 PCP z-score 过滤结构性错价, 输出卖方分/买方分/角色推荐
        (SELL_VOL/BUY_VOL) —— 回答"今天偏买方还是卖方、选哪几个合约"。

    模块2 PortfolioGreeksAggregator / PortfolioGreeksReport  (落库 tb_option_portfolio_greeks)
        组合 Greeks 聚合 + 动态 Delta 对冲 + P&L Explain 损益归因:
        持仓(positions 或 auto ATM straddle)按 TOTAL/UNDERLYING/MATURITY
        三视角聚合净 Δ/Γ/V/Θ/Rho, 输出对冲单位/手数/名义金额与 gamma/vega
        残留敞口; 用 T-1 日 Greeks 解释 T 日盯市损益(残差=数据质量监控)。

    模块3 VolSurfaceSkewTermAnalysis / VolSurfaceReport  (落库 tb_option_vol_surface)
        波动率曲面结构信号: 每切片(日 x 标的 x 到期月)的 atm_iv /
        risk_reversal(25Δ近似风险逆转) / skew_slope(偏度斜率) / butterfly
        (翼凸性溢价) / term_slope(期限斜率), 支撑偏度交易与日历价差选向。
        报告出口: VolSurfaceReport(RR/蝶式/期限斜率时序 + 最新信号一览)
        + GreeksEfficiencyReport 图2/图4(最新日截面快照)

配套建表 SQL(执行后启用):
    sql/ClickHouse/createTables/tb_option_greeks_efficiency.sql
    sql/ClickHouse/createTables/tb_option_portfolio_greeks.sql
    sql/ClickHouse/createTables/tb_option_vol_surface.sql

建议顺序:
    1. 建表(执行上述 DDL)
    2. GreeksEfficiencyAnalysisTest → GreeksEfficiencyReportTest
    3. PortfolioGreeksAggregatorTest → PortfolioGreeksReportTest
    4. VolSurfaceSkewTermAnalysisTest → VolSurfaceReportTest

dataIntegrator/modelService/option/optionVolatilityGreeksTrading/
├── __init__.py                        # 包文档(三模块定位+使用顺序)
├── GreeksEfficiencyAnalysis.py        # 模块1: VRP + Greeks效率扫描(核心)
├── GreeksEfficiencyReport.py          # 模块1: PDF报告(VRP时序/微笑/卖方效率/期限结构)
├── GreeksEfficiencyAnalysisTest.py / ...ReportTest.py
├── PortfolioGreeksAggregator.py      # 模块2: 组合Greeks聚合 + Delta对冲 + P&L Explain
├── PortfolioGreeksReport.py           # 模块2: PDF报告(分组净Greeks/对冲建议/归因分解)
├── PortfolioGreeksAggregatorTest.py / ...ReportTest.py
├── VolSurfaceSkewTermAnalysis.py     # 模块3: 偏度/期限结构信号(落库)
├── VolSurfaceSkewTermReport.py               # 模块3: PDF报告(RR/蝶式/期限斜率时序+信号一览)
└── VolSurfaceSkewTermAnalysisTest.py / VolSurfaceSkewTermReportTest.py

dataIntegrator/sql/ClickHouse/createTables/
├── tb_option_greeks_efficiency.sql   # 新表: 每合约x每日效率指标
├── tb_option_portfolio_greeks.sql    # 新表: TOTAL/UNDERLYING/MATURITY聚合
└── tb_option_vol_surface.sql         # 新表: 曲面切片(RR/skew/butterfly/term)
三模块对应你的三个需求
你的需求	实现
基于 Greeks 的组合	模块1 输出角色推荐（SELL_VOL/BUY_VOL）直接对接你已有的 12 个策略结构库（卖方分高的 K → short strangle 等）
组合层面 Greeks 汇总与对冲	模块2：净 Δ/Γ/V/Θ 三视角聚合 + 对冲单位/手数（SPOT/ETF_LOT/FUTURE）+ P&L Explain 归因（残差=免费的数据质量监控）
比较不同期权选最赚钱组合	模块1 卖方分/买方分（VRP 40% + IV分位/日平衡波幅/定价偏差 20%）+ 模块3 偏度/期限斜率信号
关键专业指标已全部落表：vrp = IV−HV20、gamma_breakeven_move = sqrt(2·|Θ|/Γ)（theta 安全垫能承受的日波幅）、gamma/vega_per_premium、risk_reversal、term_slope，且联查 tb_option_pcp_monitor 的 z-score 过滤结构性错价档，复用了你 OptionStrategyBase 的 IV 分位/落库/审计体系与自适应列宽表格。
"""
