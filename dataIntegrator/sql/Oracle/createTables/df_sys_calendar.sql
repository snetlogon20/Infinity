-- 创建表并定义主键
CREATE TABLE df_sys_calendar (
    trade_date VARCHAR2(255) PRIMARY KEY,
    trade_year VARCHAR2(255),
    trade_month VARCHAR2(255),
    trade_day VARCHAR2(255),
    day_of_week VARCHAR2(255),
    quarter VARCHAR2(255),
    calendar_date VARCHAR2(255)
)
