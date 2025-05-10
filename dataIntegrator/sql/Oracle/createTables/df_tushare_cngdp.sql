--drop table citi.df_tushare_cn_gdp;
CREATE TABLE df_tushare_cn_gdp(
    quarter      VARCHAR2(255) NOT NULL,
    gdp          NUMBER NOT NULL,
    gdp_yoy      NUMBER NOT NULL,
    pi           NUMBER NOT NULL,
    pi_yoy       NUMBER NOT NULL,
    si           NUMBER NOT NULL,
    si_yoy       NUMBER NOT NULL,
    ti           NUMBER NOT NULL,
    ti_yoy       NUMBER NOT NULL,
    CONSTRAINT pk_cn_gdp PRIMARY KEY (quarter)
);
