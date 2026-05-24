--drop table indexsysdb.df_akshare_bond_china_close_return
CREATE TABLE IF NOT EXISTS indexsysdb.df_akshare_bond_china_close_return
(
    `bond_type` String COMMENT '债券类型',
    `bond_code` String COMMENT '债券代码',
    `date` Date COMMENT '日期',
    `tenor` Float64 COMMENT '期限（年）',
    `yield_to_maturity` Float64 COMMENT '到期收益率（%）',
    `spot_rate` Float64 COMMENT '即期收益率（%）',
    `forward_rate` Float64 COMMENT '远期收益率（%）'
) ENGINE = MergeTree
ORDER BY (bond_code, date, tenor)
SETTINGS index_granularity = 8192;
