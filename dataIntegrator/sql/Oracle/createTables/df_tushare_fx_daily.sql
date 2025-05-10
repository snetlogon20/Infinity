--drop table citi.df_tushare_fx_daily
CREATE TABLE df_tushare_fx_daily(
    ts_code        VARCHAR2(255) NOT NULL,
    trade_date     VARCHAR2(255) NOT NULL,
    bid_open       NUMBER NOT NULL,
    bid_close      NUMBER NOT NULL,
    bid_high       NUMBER NOT NULL,
    bid_low        NUMBER NOT NULL,
    ask_open       NUMBER NOT NULL,
    ask_close      NUMBER NOT NULL,
    ask_high       NUMBER NOT NULL,
    ask_low        NUMBER NOT NULL,
    tick_qty       NUMBER NOT NULL,
    CONSTRAINT pk_fx_daily PRIMARY KEY (trade_date, ts_code)
);