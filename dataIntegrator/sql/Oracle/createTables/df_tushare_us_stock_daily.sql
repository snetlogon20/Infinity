CREATE TABLE citi.df_tushare_us_stock_daily(
    ts_code          VARCHAR2(255) NOT NULL,
    trade_date       VARCHAR2(255) NOT NULL,
    close_point      NUMBER NOT NULL,
    open_point       NUMBER NOT NULL,
    high_point       NUMBER NOT NULL,
    low_point        NUMBER NOT NULL,
    pre_close        NUMBER NOT NULL,
    change_point     NUMBER NOT NULL,
    pct_change       NUMBER NOT NULL,
    vol              NUMBER NOT NULL,
    amount           NUMBER NOT NULL,
    vwap             NUMBER NOT NULL,
    turnover_ratio   NUMBER NOT NULL,
    total_mv         NUMBER NOT NULL,
    pe               NUMBER NOT NULL,
    pb               NUMBER NOT NULL,
    CONSTRAINT pk_us_stock_daily PRIMARY KEY (trade_date, ts_code)
);
