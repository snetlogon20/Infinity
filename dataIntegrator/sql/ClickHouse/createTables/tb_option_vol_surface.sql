-- 期权波动率曲面 偏度/期限结构指标表 (Vol Surface: Skew / Risk Reversal / Butterfly / Term Structure)
-- 专业定位: 偏度交易(skew trading) + 期限结构交易(term structure / calendar)的信号层
--   每行一个 (交易日 x 标的 x 到期月) 的曲面切片指标:
--     atm_iv        平值IV(|moneyness_log|<=0.05均值) —— 曲面锚点
--     put_wing_iv   Put翼IV(认沽 moneyness_log<=-0.15, 25Δ近似)
--     call_wing_iv  Call翼IV(认购 moneyness_log>=+0.15, 25Δ近似)
--     risk_reversal = call_wing - put_wing(正=Call翼贵, 负=左偏即恐慌Put贵)
--     skew_slope    IV对moneyness_log线性回归斜率(每单位log价态的IV变化, <0=左偏)
--     butterfly     (put_wing+call_wing)/2 - atm_iv(翼部对平值的凸性溢价, >0=微笑明显)
--     term_slope    同标的最远/最近月 atm_iv 差 / 年限差(>0=远月贵=正期限结构)
-- 数据来源: tb_tushare_opt_daily_indicator (moneyness_log/implied_vol) + df_tushare_opt_basic
-- 增量写入: 按 trade_date + underlying LIKE 删除后插入
-- 审计: analysis_time/analysis_params/analysis_version

--drop table indexsysdb.tb_option_vol_surface;
--ALTER TABLE indexsysdb.tb_option_vol_surface DELETE WHERE 1=1;

CREATE TABLE indexsysdb.tb_option_vol_surface (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: VOL_SURFACE(波动率曲面指标)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON)',
    analysis_version String COMMENT '算法版本号',
    -- 切片标识
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    underlying_key String COMMENT '标的键: ETF取symbol前6位, 股指期权取ts_code前缀(HO/IO/MO)',
    s_month String COMMENT '结算月(YYYYMM)',
    maturity_date String COMMENT '到期日(YYYYMMDD)',
    days_to_maturity Int32 COMMENT '距离到期日历天数',
    years_to_maturity_calendar Float64 COMMENT '距离到期年数(日历日/365)',
    n_contracts UInt32 COMMENT '切片内合约数',
    -- 曲面指标
    atm_iv Float64 COMMENT '平值IV(|moneyness_log|<=0.05均值, 小数)',
    put_wing_iv Float64 COMMENT 'Put翼IV(moneyness_log<=-0.15均值, 25Δ近似)',
    call_wing_iv Float64 COMMENT 'Call翼IV(moneyness_log>=+0.15均值, 25Δ近似)',
    risk_reversal Float64 COMMENT '风险逆转 = call_wing_iv - put_wing_iv(bp: *1e4, 正=Call翼贵)',
    skew_slope Float64 COMMENT '偏度斜率 = IV对moneyness_log回归斜率(每单位log价态的IV变化)',
    butterfly Float64 COMMENT '蝶式翼溢价 = (put_wing+call_wing)/2 - atm_iv',
    iv_dispersion Float64 COMMENT '切片内IV标准差(报价离散度, 大=流动性差/报价失真)',
    -- 期限结构(同标的当日跨月, 各行冗余存储同值)
    term_atm_iv_near Float64 COMMENT '最近月atm_iv',
    term_atm_iv_far Float64 COMMENT '最远月atm_iv',
    term_slope Float64 COMMENT '期限斜率 = (atm_iv_far-atm_iv_near)/(年限差年)(>0=远月贵)',
    n_term_months UInt32 COMMENT '参与期限结构计算的月份数',
    -- 信号
    trade_signal String COMMENT '交易信号: SELL_SKEW/BUY_SKEW/SELL_CALENDAR/BUY_CALENDAR/NEUTRAL',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, underlying_key, s_month)
SETTINGS index_granularity = 8192;
