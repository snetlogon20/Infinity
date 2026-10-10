-- 期权 Greeks 效率扫描表 (Volatility Risk Premium / Greeks Efficiency Ratios)
-- 专业定位: 波动率风险溢价(VRP)交易 + 期权性价比筛选(Greeks efficiency ratios)
--   每行一个合约 x 交易日, 回答"今天该做买方还是卖方、选哪几个合约"
-- 核心指标:
--   vrp = IV - HV20 (波动率风险溢价: >0 偏卖方收租, <0 偏买方做多波动率)
--   gamma_breakeven_move = sqrt(2*|theta|/gamma): 日平衡波幅——
--     delta对冲持仓下, 当日标的真实波幅超过此值则 gamma 损失吃掉 theta 收入(卖方核心刻度)
--   gamma_per_premium / vega_per_premium: 买方性价比(每元权利金换多少 gamma/vega 敞口)
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
--           + tb_option_pcp_monitor (PCP z-score/deviation_type 联查, 结构性错价过滤)
--   HV20/HV60 由 indicator 表内 spot_price 序列现算(年化, sqrt(252))
-- 增量写入: 按 trade_date + symbol LIKE 删除后插入
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

--drop table indexsysdb.tb_option_greeks_efficiency;
--ALTER TABLE indexsysdb.tb_option_greeks_efficiency DELETE WHERE 1=1;

CREATE TABLE indexsysdb.tb_option_greeks_efficiency (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: GREEKS_EFFICIENCY(Greeks效率扫描)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON)',
    analysis_version String COMMENT '算法版本号',
    -- 合约标识
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code String COMMENT 'TS合约代码',
    symbol String COMMENT '合约代码(来自opt_basic)',
    opt_name String COMMENT '合约名称',
    opt_exchange String COMMENT '交易所(如SSE)',
    call_put String COMMENT '期权类型(C=认购/P=认沽)',
    underlying_key String COMMENT '标的键: ETF取symbol前6位, 股指期权取ts_code前缀(HO/IO/MO)',
    -- 合约要素
    exercise_price Float64 COMMENT '行权价 K',
    opt_multiplier Float64 COMMENT '合约单位(乘数)',
    s_month String COMMENT '结算月(YYYYMM)',
    maturity_date String COMMENT '到期日(YYYYMMDD)',
    days_to_maturity Int32 COMMENT '距离到期日历天数',
    years_to_maturity_calendar Float64 COMMENT '距离到期年数(日历日/365)',
    moneyness_status String COMMENT '价态: ITM/ATM/OTM',
    moneyness_log Float64 COMMENT '对数价态: ln(K/S)/sqrt(T年)',
    -- 标的市场
    spot_price Float64 COMMENT '标的资产当日收盘价',
    risk_free_rate Float64 COMMENT '无风险利率r',
    dividend_yield Float64 COMMENT '股息率q',
    -- 行情与波动率
    close Float64 COMMENT '期权收盘价(权利金)',
    implied_vol Float64 COMMENT '隐含波动率(小数)',
    iv_rank Float64 COMMENT 'IV分位数(0~1, 近60日)',
    hv20 Float64 COMMENT '20日实际波动率HV(年化, 小数, 现算)',
    hv60 Float64 COMMENT '60日实际波动率HV(年化, 小数, 现算)',
    -- 波动率风险溢价
    vrp Float64 COMMENT 'VRP = IV - HV20(正=隐含贵于实际, 偏卖方)',
    vrp_bp Float64 COMMENT 'VRP(bp) = (IV-HV20)*1e4',
    vrp_ratio Float64 COMMENT 'IV/HV20(>1=卖方溢价)',
    -- 单腿 Greeks
    delta Float64 COMMENT 'Delta',
    gamma Float64 COMMENT 'Gamma',
    theta Float64 COMMENT 'Theta(元/天, 买方为负)',
    vega Float64 COMMENT 'Vega(IV变动1%的权利金变化)',
    rho Float64 COMMENT 'Rho',
    -- Greeks 效率比
    gamma_breakeven_move Float64 COMMENT '日平衡波幅 = sqrt(2*|theta|/gamma)(标的价格单位)',
    gamma_breakeven_move_pct Float64 COMMENT '日平衡波幅%(占现价): delta对冲下当日真实波幅超过此值, gamma损失吃掉theta收入',
    theta_gamma_ratio Float64 COMMENT 'theta/gamma比(卖方效率: 单位gamma风险的时间价值收入)',
    vega_theta_ratio Float64 COMMENT 'vega/|theta|(买方效率: 每消耗1元theta换多少vega)',
    gamma_per_premium Float64 COMMENT 'gamma/close(买方: 每元权利金的gamma敞口)',
    vega_per_premium Float64 COMMENT 'vega/close(买方: 每元权利金的vega敞口)',
    -- 定价偏差
    bs_theoretical_price Float64 COMMENT 'BS理论价',
    close_vs_theoretical_pct Float64 COMMENT '市价偏离理论(%)',
    price_bias String COMMENT '定价偏差: 严重低估/低估/公允/高估/严重高估',
    -- PCP 结构性错价过滤(联查 tb_option_pcp_monitor)
    pcp_z_score Float64 COMMENT 'PCP z-score(同K同T配对, 20日滚动)',
    pcp_deviation_type String COMMENT 'PCP偏差分类: NORMAL/DIVIDEND_NOISE/REAL_ARBITRAGE/STRONG_ARBITRAGE',
    -- 流动性闸门
    oi Float64 COMMENT '持仓量(手)',
    vol Float64 COMMENT '成交量(手)',
    amount Float64 COMMENT '成交金额(万元)',
    turnover_ratio Float64 COMMENT '换手率(近似): vol/oi',
    liq_flag String COMMENT '流动性闸门: PASS/FAIL(FAIL不参与信号)',
    -- 评分与排名(百分位合成, 0~100)
    seller_score Float64 COMMENT '卖方分(高IV高VRP高日平衡波幅优先, 适合卖出的合约)',
    buyer_score Float64 COMMENT '买方分(低IV负VRP高gamma/vega性价比优先, 适合买入的合约)',
    seller_rank UInt32 COMMENT '同日卖方分排名(1=最优)',
    buyer_rank UInt32 COMMENT '同日买方分排名(1=最优)',
    role_recommend String COMMENT '角色推荐: SELLER/BUYER/NEUTRAL/AVOID',
    -- 交易信号
    trade_signal String COMMENT '交易信号: SELL_VOL(卖波动率)/BUY_VOL(买波动率)/NEUTRAL/AVOID',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, call_put, exercise_price)
SETTINGS index_granularity = 8192;
