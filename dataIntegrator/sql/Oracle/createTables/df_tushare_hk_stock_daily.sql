--drop table citi.df_tushare_hk_stock_daily
CREATE TABLE df_tushare_hk_stock_daily(
    ts_code        VARCHAR2(255) NOT NULL,
    trade_date     VARCHAR2(255) NOT NULL,
    open           NUMBER NOT NULL,
    high           NUMBER NOT NULL,
    low            NUMBER NOT NULL,
    close          NUMBER NOT NULL,
    pre_close      NUMBER NOT NULL,
    change         NUMBER NOT NULL,
    pct_chg        NUMBER NOT NULL,
    vol            NUMBER NOT NULL,
    amount         NUMBER NOT NULL,
    CONSTRAINT pk_hk_stock_daily PRIMARY KEY (trade_date, ts_code)
);
