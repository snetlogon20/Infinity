--drop table citi.df_tushare_cn_money_supply;
CREATE TABLE df_tushare_cn_money_supply(
    trade_date   VARCHAR2(255) NOT NULL,
    m0           NUMBER NOT NULL,
    m0_yoy       NUMBER NOT NULL,
    m0_mom       NUMBER NOT NULL,
    m1           NUMBER NOT NULL,
    m1_yoy       NUMBER NOT NULL,
    m1_mom       NUMBER NOT NULL,
    m2           NUMBER NOT NULL,
    m2_yoy       NUMBER NOT NULL,
    m2_mom       NUMBER NOT NULL,
    CONSTRAINT pk_money_supply PRIMARY KEY (trade_date)
);
