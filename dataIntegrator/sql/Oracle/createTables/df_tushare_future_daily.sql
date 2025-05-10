--drop table citi.df_tushare_future_daily;
CREATE TABLE df_tushare_future_daily(
    ts_code        VARCHAR2(255) NOT NULL,
    trade_date     VARCHAR2(255) NOT NULL,
    pre_close      NUMBER NOT NULL,
    pre_settle     NUMBER NOT NULL,
    open           NUMBER NOT NULL,
    high           NUMBER NOT NULL,
    low            NUMBER NOT NULL,
    close          NUMBER NOT NULL,
    settle         NUMBER NOT NULL,
    change1        NUMBER NOT NULL,
    change2        NUMBER NOT NULL,
    vol            NUMBER NOT NULL,
    amount         NUMBER NOT NULL,
    oi             NUMBER NOT NULL,
    oi_chg         NUMBER NOT NULL,
    CONSTRAINT pk_future_daily PRIMARY KEY (ts_code, trade_date)
);
