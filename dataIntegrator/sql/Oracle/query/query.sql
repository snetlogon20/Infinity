SELECT * FROM citi.df_tushare_us_stock_basic
SELECT * FROM citi.us_stock_daily

DELETE FROM citi.us_stock_daily
WHERE ts_code = 'C' AND 
TRADE_DATE >= 20231003 AND 
TRADE_DATE <= 20241231 

COMMIT