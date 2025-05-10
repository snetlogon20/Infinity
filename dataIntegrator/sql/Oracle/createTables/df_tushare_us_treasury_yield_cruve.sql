--表名、列名、约束名均需 ≤ 30 字符（旧版本）或 ≤ 128 字符（新版本），故对表名进行了修改
-- DROP TABLE df_tushare_us_treasury_y_cruve;
CREATE TABLE df_tushare_us_treasury_y_cruve(
    trade_date   VARCHAR2(255) NOT NULL,
    m1           NUMBER NOT NULL,
    m2           NUMBER NOT NULL,
    m3           NUMBER NOT NULL,
    m6           NUMBER NOT NULL,
    y1           NUMBER NOT NULL,
    y2           NUMBER NOT NULL,
    y3           NUMBER NOT NULL,
    y5           NUMBER NOT NULL,
    y7           NUMBER NOT NULL,
    y10          NUMBER NOT NULL,
    y20          NUMBER NOT NULL,
    y30          NUMBER NOT NULL,
    CONSTRAINT pk_treasury_yield PRIMARY KEY (trade_date)
);