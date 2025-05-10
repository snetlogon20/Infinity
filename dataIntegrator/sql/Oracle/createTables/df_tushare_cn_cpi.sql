--drop table df_tushare_cn_cpi
CREATE TABLE df_tushare_cn_cpi(
    trade_date    VARCHAR2(255) NOT NULL,
    nt_val       NUMBER NOT NULL,
    nt_yoy       NUMBER NOT NULL,
    nt_mom       NUMBER NOT NULL,
    nt_accu      NUMBER NOT NULL,
    town_val     NUMBER NOT NULL,
    town_yoy     NUMBER NOT NULL,
    town_mom     NUMBER NOT NULL,
    town_accu    NUMBER NOT NULL,
    cnt_val      NUMBER NOT NULL,
    cnt_yoy      NUMBER NOT NULL,
    cnt_mom      NUMBER NOT NULL,
    cnt_accu     NUMBER NOT NULL,
    CONSTRAINT pk_cn_cpi PRIMARY KEY (trade_date)
);