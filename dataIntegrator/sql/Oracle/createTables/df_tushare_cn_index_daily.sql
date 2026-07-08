--step 0 create table
--drop table df_tushare_cn_index_daily
CREATE TABLE df_tushare_cn_index_daily(
    ts_code      VARCHAR2(255) NOT NULL,
    trade_date   VARCHAR2(255) NOT NULL,
    close        NUMBER NOT NULL,
    open         NUMBER NOT NULL,
    high         NUMBER NOT NULL,
    low          NUMBER NOT NULL,
    pre_close    NUMBER NOT NULL,
    change       NUMBER NOT NULL,
    pct_chg      NUMBER NOT NULL,
    vol          NUMBER NOT NULL,
    amount       NUMBER NOT NULL,
    CONSTRAINT pk_cn_index_daily PRIMARY KEY (ts_code, trade_date)
);