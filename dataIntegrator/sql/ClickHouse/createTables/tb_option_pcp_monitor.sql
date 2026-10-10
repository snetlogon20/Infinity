-- Put-Call Parity 实时监控表
-- 数据来源：tb_tushare_opt_daily_indicator (C/P 配对)
-- 按 trade_date + underlying_code + exercise_price + maturity_date 唯一
-- 每次运行按 trade_date 增量删除后插入

CREATE TABLE indexsysdb.tb_option_pcp_monitor (
    trade_date              String COMMENT '交易日 YYYYMMDD',
    underlying_code         String COMMENT '标的指数代码，如 000300.SH',
    exercise_price          Float64 COMMENT '行权价 K',
    maturity_date           String COMMENT '到期日 YYYYMMDD',
    days_to_maturity        Int32 COMMENT '剩余到期日历天数',

    -- 市场价格
    call_settle             Float64 COMMENT 'Call 结算价',
    put_settle              Float64 COMMENT 'Put 结算价',
    spot_price              Float64 COMMENT '标的价格 S',
    risk_free_rate          Float64 COMMENT '无风险利率 r (小数)',
    dividend_yield          Float64 COMMENT '股息率 q (小数, 模型使用值)',

    -- PCP 偏差
    pcp_deviation           Float64 COMMENT 'PCP 原始偏差 ε = P - C - K*e^(-rT) + S*e^(-qT) (元/手)',
    pcp_deviation_pct       Float64 COMMENT 'PCP 偏差 / 标的价格 (%)',
    pcp_theoretical_put     Float64 COMMENT '从 Call 反推的理论 Put 价',

    -- 滚动统计 (20日窗口)
    rolling_mean            Float64 COMMENT '20日滚动均值 μ',
    rolling_std             Float64 COMMENT '20日滚动标准差 σ',
    z_score                 Float64 COMMENT '当日 z-score = (ε - μ) / σ',

    -- 股息噪声分解
    dividend_q_std          Float64 COMMENT '股息率滚动标准差 σ_q',
    dividend_contribution   Float64 COMMENT '股息噪声贡献 = S * T * σ_q',
    residual_deviation      Float64 COMMENT '残差 ε_residual (剥离股息噪声后)',

    -- 告警分类
    alert_level             String COMMENT '告警等级: NORMAL / WARNING / ALERT',
    deviation_type          String COMMENT '偏差分类: NORMAL / DIVIDEND_NOISE / REAL_ARBITRAGE / STRONG_ARBITRAGE',

    -- 配对信息
    call_ts_code            String COMMENT 'Call 合约代码',
    put_ts_code             String COMMENT 'Put 合约代码',

    insert_time             DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY (trade_date, underlying_code, exercise_price, maturity_date)
SETTINGS index_granularity = 8192;
