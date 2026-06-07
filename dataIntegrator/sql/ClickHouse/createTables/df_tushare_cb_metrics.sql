-- 可转债指标计算结果表
--drop table indexsysdb.df_tushare_cb_metrics
CREATE TABLE IF NOT EXISTS indexsysdb.df_tushare_cb_metrics
(
    `ts_code` String COMMENT '转债代码',
    `trade_date` String COMMENT '交易日期',
    `is_feasible` UInt8 COMMENT '是否计算成功: 0-失败, 1-成功',
    `description` String COMMENT '描述信息/错误原因',
    `ytm` Float64 COMMENT '到期收益率(%)',
    `macaulay_duration` Float64 COMMENT '麦考利久期',
    `modified_duration` Float64 COMMENT '修正久期',
    `convexity` Float64 COMMENT '凸性',
    `dv01` Float64 COMMENT 'DV01',
    `pvbp` Float64 COMMENT 'PVBP(价格基点价值)',
    `remaining_years` Float64 COMMENT '剩余期限(年)',
    `current_yield` Float64 COMMENT '当期票息收益率(%)',
    `simple_ytm` Float64 COMMENT '简单到期收益率(%)',
    `market_price` Float64 COMMENT '市场价格',
    `par` Float64 COMMENT '面值',
    `coupon_rate` Float64 COMMENT '票面利率(%)',
    `pay_per_year` Int32 COMMENT '年付息次数',
    `var_hist_95` Float64 COMMENT '历史模拟VaR-95%置信(%)',
    `var_hist_99` Float64 COMMENT '历史模拟VaR-99%置信(%)',
    `var_param_95` Float64 COMMENT '参数法VaR-95%置信(%)',
    `var_param_99` Float64 COMMENT '参数法VaR-99%置信(%)',
    `es_95` Float64 COMMENT 'Expected Shortfall-95%置信(%)',
    `es_99` Float64 COMMENT 'Expected Shortfall-99%置信(%)',
    `var_price_hist_95` Float64 COMMENT '历史模拟VaR-95%置信(元)',
    `var_price_hist_99` Float64 COMMENT '历史模拟VaR-99%置信(元)',
    `var_price_param_95` Float64 COMMENT '参数法VaR-95%置信(元)',
    `var_price_param_99` Float64 COMMENT '参数法VaR-99%置信(元)',
    `es_price_95` Float64 COMMENT 'Expected Shortfall-95%置信(元)',
    `es_price_99` Float64 COMMENT 'Expected Shortfall-99%置信(元)',
    `lookback_days` Int32 COMMENT 'VaR/ES计算使用的历史样本天数',
    `effective_duration` Float64 COMMENT '有效久期',
    `effective_convexity` Float64 COMMENT '有效凸性',
    `pct_price_chg_p50bp` Float64 COMMENT '收益率+50bp价格变动(%)',
    `pct_price_chg_m50bp` Float64 COMMENT '收益率-50bp价格变动(%)',
    `pct_price_chg_p100bp` Float64 COMMENT '收益率+100bp价格变动(%)',
    `pct_price_chg_m100bp` Float64 COMMENT '收益率-100bp价格变动(%)'
)
ENGINE = MergeTree()
ORDER BY (ts_code, trade_date)
SETTINGS index_granularity = 8192;
