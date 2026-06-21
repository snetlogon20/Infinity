-- 集思录可转债实时数据表 (akshare bond_cb_jsl)
--主要是为了拿评级
-- drop table indexsysdb.df_akshare_bond_cb_jsl
CREATE TABLE IF NOT EXISTS indexsysdb.df_akshare_bond_cb_jsl (
    `ts_code` String COMMENT '转债代码',
    `bond_name` String COMMENT '转债名称',
    `price` Float64 COMMENT '现价',
    `pct_chg` Float64 COMMENT '涨跌幅(%)',
    `stk_code` String COMMENT '正股代码',
    `stk_name` String COMMENT '正股名称',
    `stk_price` Float64 COMMENT '正股价',
    `stk_pct_chg` Float64 COMMENT '正股涨跌(%)',
    `stk_pb` Float64 COMMENT '正股PB',
    `conv_price` Float64 COMMENT '转股价',
    `conv_value` Float64 COMMENT '转股价值',
    `conv_premium` Float64 COMMENT '转股溢价率(%)',
    `bond_rating` String COMMENT '债券评级',
    `put_trigger_price` Float64 COMMENT '回售触发价',
    `call_trigger_price` Float64 COMMENT '强赎触发价',
    `cb_ratio` Float64 COMMENT '转债占比(%)',
    `maturity_date` String COMMENT '到期时间',
    `remain_years` Float64 COMMENT '剩余年限(年)',
    `remain_size` Float64 COMMENT '剩余规模(亿元)',
    `amount` Float64 COMMENT '成交额(万元)',
    `turnover_rate` Float64 COMMENT '换手率(%)',
    `ytm_pre_tax` Float64 COMMENT '到期税前收益(%)',
    `double_low` Float64 COMMENT '双低',
    `trade_date` String COMMENT '数据抓取日期'
)
ENGINE = MergeTree()
ORDER BY (trade_date, ts_code)
SETTINGS index_granularity = 8192;
