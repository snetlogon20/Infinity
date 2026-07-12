select * from indexsysdb.df_sys_calendar
trade_daet 20241006

select * from indexsysdb.df_tushare_shibor_daily
trade_date 20220104

select * from indexsysdb.df_tushare_shibor_lpr_daily
trade_date 20200120

select * from indexsysdb.df_tushare_us_treasury_yield_cruve
trade_date 20150102

select * from indexsysdb.df_tushare_cn_gdp
quarter 2018Q1


select * from indexsysdb.cn_money_supply
trade_date 200001

select * from indexsysdb.df_tushare_cn_cpi
trade_date 200001

select * from indexsysdb.df_macro_china_fx_gold
month 2008年01月份

select * from indexsysdb.df_macro_china_hgjck
month 2008年01月份

select * from indexsysdb.df_macro_china_imports_yoy
date 1996-02-01

select * from indexsysdb.df_macro_china_exports_yoy
date 1982-02-01

select * from indexsysdb.df_macro_china_shrzgm
month 201501

select * from indexsysdb.df_tushare_fx_daily where ts_code LIKE  'USDCNH.FXCM'
trade_date 20200102

select * from  df_akshare_bond_zh_us_rate
trade_date  19901219


--美元指数
SELECT USDX_index FROM df_tushare_usd_index_daily
trade_date 20200101

--黄金价格
SELECT * FROM indexsysdb.df_akshare_futures_foreign_hist WHERE symbol = 'GC'
trade_date  2016-07-11

--道琼斯
select * from indexsysdb.df_tushare_index_global
where ts_code = 'DJI'
order by trade_date desc

trade_date  20260709

--上证综指
select * from df_tushare_cn_index_daily
where ts_code = '000001.SH'

trade_date  20220523

--深证成指数
select * from df_tushare_cn_index_daily
where ts_code = '399001.SZ'

trade_date  20240102

-- ============================================================
-- 宏观经济指标宽表：以 df_sys_calendar 为左表，关联所有宏观数据
-- 用于相关系数 & 线性回归分析
-- ============================================================
-- 【修正说明】基于实际数据样本修正 JOIN KEY：
--   cal.trade_month 存储月份数字  如 '10'，不是 YYYYMM
--   cal.quarter     存储季度数字  如 '4'， 不是 YYYYQN
--   日频：cal.trade_date         直连 (YYYYMMDD)
--   月频：substring(cal.trade_date, 1, 6) 构造 YYYYMM
--   季频：concat(cal.trade_year, 'Q', cal.quarter) 构造 YYYYQN
--
-- 各表主键采样值：
--   df_sys_calendar             trade_date  20241006  (YYYYMMDD),  trade_month='10', quarter='4'
--   df_tushare_shibor_daily      trade_date  20220104   (YYYYMMDD)
--   df_tushare_shibor_lpr_daily  trade_date  20200120   (YYYYMMDD)
--   df_tushare_us_treasury_yield_cruve  trade_date  20150102   (YYYYMMDD)
--   cn_money_supply              trade_date  200001     (YYYYMM, 6位)
--   df_tushare_cn_cpi            trade_date  200001     (YYYYMM, 6位)
--   df_macro_china_fx_gold       month       200801     (YYYYMM, transformDataFrame已自动转换)
--   df_macro_china_hgjck         month       200801     (YYYYMM, transformDataFrame已自动转换)
--   df_macro_china_imports_yoy   date        1996-02-01
--   df_macro_china_exports_yoy   date        1982-02-01
--   df_tushare_cn_gdp            quarter     2018Q1     (YYYYQN)
--   df_macro_china_shrzgm        month       201501     (YYYYMM)
--   df_tushare_fx_daily          trade_date  20200102   (YYYYMMDD), filter ts_code='USDCNH.FXCM'
--   df_akshare_bond_zh_us_rate   trade_date  19901219   (YYYYMMDD), 中美国债收益率日频
--   df_tushare_usd_index_daily   trade_date  20200101   (YYYYMMDD), 美元指数
--   df_akshare_futures_foreign_hist    date   2016-07-11 (YYYY-MM-DD), filter symbol='GC', 黄金期货
--   df_tushare_index_global      trade_date  20260709   (YYYYMMDD), filter ts_code='DJI', 道琼斯
--   df_tushare_cn_index_daily    trade_date  20220523   (YYYYMMDD), filter ts_code='000001.SH', 上证综指
--   df_tushare_cn_index_daily    trade_date  20240102   (YYYYMMDD), filter ts_code='399001.SZ', 深证成指
-- ============================================================
SELECT
    cal.trade_date,
    cal.trade_month,
    cal.trade_year,
    cal.quarter,
    -- ==================== 日频：利率 ====================
    shibor.tenor_on    AS shibor_on,
    shibor.tenor_1w    AS shibor_1w,
    shibor.tenor_1m    AS shibor_1m,
    shibor.tenor_3m    AS shibor_3m,
    shibor.tenor_1y    AS shibor_1y,
    lpr.tenor_1y       AS lpr_1y,
    lpr.tenor_5y       AS lpr_5y,
    ust.y2             AS ust_y2,
    ust.y10            AS ust_y10,
    ust.y30            AS ust_y30,
    -- ==================== 月频：货币、通胀 ====================
    ms.m1_yoy,
    ms.m2_yoy,
    cpi.nt_yoy         AS cpi_yoy,
    -- ==================== 月频：外储 & 黄金 ====================
    fg.forex_reserves_value  AS forex_reserves,
    fg.gold_reserves_value   AS gold_reserves,
    -- ==================== 月频：进出口 ====================
    hj.monthly_exports_yoy   AS exports_yoy,
    hj.monthly_imports_yoy   AS imports_yoy,
    -- ==================== 月频：社会融资规模 ====================
    shr.total_shrzgm,
    shr.rmb_loan,
    shr.entrusted_loan,
    shr.trust_loan,
    shr.corporate_bonds,
    shr.non_financial_enterprise_domestic_equity_financing AS equity_financing,
    -- ==================== 日频：外汇 USDCNH.FXCM ====================
    fx.bid_close       AS usdcnh_bid_close,
    fx.ask_close       AS usdcnh_ask_close,
    -- ==================== 日频：中国国债收益率 (df_akshare_bond_zh_us_rate) ====================
    cb.cn_yield_2y  AS cn_yield_2y,
    cb.cn_yield_5y  AS cn_yield_5y,
    cb.cn_yield_10y AS cn_yield_10y,
    -- ==================== 季频：GDP ====================
    gdp.gdp_yoy,
    gdp.pi_yoy,
    gdp.si_yoy,
    gdp.ti_yoy,
    -- ==================== 日频：美元指数 ====================
    udx.USDX_index      AS usdx_index,
    -- ==================== 日频：黄金期货 GC ====================
    gold.close          AS gold_close,
    -- ==================== 日频：道琼斯工业指数 ====================
    dji.close           AS dji_close,
    -- ==================== 日频：上证综指 ====================
    sh.close            AS sh_close,
    -- ==================== 日频：深证成指数 ====================
    sz.close            AS sz_close
FROM indexsysdb.df_sys_calendar cal
-- 日频：直连 trade_date（均为 YYYYMMDD）
LEFT JOIN indexsysdb.df_tushare_shibor_daily shibor
    ON cal.trade_date = shibor.trade_date
LEFT JOIN indexsysdb.df_tushare_shibor_lpr_daily lpr
    ON cal.trade_date = lpr.trade_date
LEFT JOIN indexsysdb.df_tushare_us_treasury_yield_cruve ust
    ON cal.trade_date = ust.trade_date
-- 月频：从 cal.trade_date 提取前6位 YYYYMM，与月频主键匹配
LEFT JOIN indexsysdb.cn_money_supply ms
    ON substring(cal.trade_date, 1, 6) = ms.trade_date
LEFT JOIN indexsysdb.df_tushare_cn_cpi cpi
    ON substring(cal.trade_date, 1, 6) = cpi.trade_date
-- 月频：month 已存为 YYYYMM（如 "200801"），直接匹配
LEFT JOIN indexsysdb.df_macro_china_fx_gold fg
    ON substring(cal.trade_date, 1, 6) = fg.month
LEFT JOIN indexsysdb.df_macro_china_hgjck hj
    ON substring(cal.trade_date, 1, 6) = hj.month
-- 月频：社会融资规模，month='201501' → substring(cal.trade_date, 1, 6)
LEFT JOIN indexsysdb.df_macro_china_shrzgm shr
    ON substring(cal.trade_date, 1, 6) = shr.month
-- 日频：外汇 USDCNH.FXCM，trade_date='20200102'，限定 ts_code
LEFT JOIN indexsysdb.df_tushare_fx_daily fx
    ON cal.trade_date = fx.trade_date AND fx.ts_code = 'USDCNH.FXCM'
-- 日频：中国国债收益率，trade_date='19901219'
LEFT JOIN indexsysdb.df_akshare_bond_zh_us_rate cb
    ON cal.trade_date = cb.trade_date
-- 季频：cal.trade_year='2024' + cal.quarter='4' → '2024Q4'，匹配 gdp.quarter='2018Q1'
LEFT JOIN indexsysdb.df_tushare_cn_gdp gdp
    ON concat(cal.trade_year, 'Q', cal.quarter) = gdp.quarter
-- 日频：美元指数，trade_date='20200101'
LEFT JOIN indexsysdb.df_tushare_usd_index_daily udx
    ON cal.trade_date = udx.trade_date
-- 日频：黄金期货 GC，date='2016-07-11'，格式 YYYY-MM-DD → YYYYMMDD
LEFT JOIN indexsysdb.df_akshare_futures_foreign_hist gold
    ON cal.trade_date = replaceAll(gold.date, '-', '') AND gold.symbol = 'GC'
-- 日频：道琼斯工业指数 DJI，trade_date='20260709'
LEFT JOIN indexsysdb.df_tushare_index_global dji
    ON cal.trade_date = dji.trade_date AND dji.ts_code = 'DJI'
-- 日频：上证综指 000001.SH，trade_date='20220523'
LEFT JOIN indexsysdb.df_tushare_cn_index_daily sh
    ON cal.trade_date = sh.trade_date AND sh.ts_code = '000001.SH'
-- 日频：深证成指数 399001.SZ，trade_date='20240102'
LEFT JOIN indexsysdb.df_tushare_cn_index_daily sz
    ON cal.trade_date = sz.trade_date AND sz.ts_code = '399001.SZ'
WHERE cal.trade_date >= '20100101' and cal.trade_date <= '20260710'
ORDER BY cal.trade_date desc 

--月度数据SQL
WITH
-- M1 / M2 月度预聚合
money_monthly AS (
    SELECT
        trade_date AS yyyymm,
        max(m1_yoy) AS m1_yoy,
        max(m2_yoy) AS m2_yoy
    FROM indexsysdb.cn_money_supply
    GROUP BY trade_date
),
-- CPI 月度预聚合
cpi_monthly AS (
    SELECT
        trade_date AS yyyymm,
        max(nt_yoy) AS cpi_yoy
    FROM indexsysdb.df_tushare_cn_cpi
    GROUP BY trade_date
),
-- 外储 & 黄金
fx_gold_monthly AS (
    SELECT
        month AS yyyymm,
        max(forex_reserves_value) AS forex_reserves,
        max(gold_reserves_value)  AS gold_reserves
    FROM indexsysdb.df_macro_china_fx_gold
    GROUP BY month
),
-- 进出口
trade_monthly AS (
    SELECT
        month AS yyyymm,
        max(monthly_exports_yoy) AS exports_yoy,
        max(monthly_imports_yoy) AS imports_yoy
    FROM indexsysdb.df_macro_china_hgjck
    GROUP BY month
),
-- 社会融资规模月度预聚合
shrzgm_monthly AS (
    SELECT
        month AS yyyymm,
        max(total_shrzgm)                                       AS total_shrzgm,
        max(rmb_loan)                                           AS rmb_loan,
        max(entrusted_loan)                                     AS entrusted_loan,
        max(trust_loan)                                         AS trust_loan,
        max(corporate_bonds)                                    AS corporate_bonds,
        max(non_financial_enterprise_domestic_equity_financing) AS equity_financing
    FROM indexsysdb.df_macro_china_shrzgm
    GROUP BY month
),
-- 外汇 USDCNH.FXCM 月度预聚合（取月末最后交易日值）
fx_daily_monthly AS (
    SELECT
        substring(trade_date, 1, 6) AS yyyymm,
        argMax(bid_close, trade_date) AS usdcnh_bid_close,
        argMax(ask_close, trade_date) AS usdcnh_ask_close
    FROM indexsysdb.df_tushare_fx_daily
    WHERE ts_code = 'USDCNH.FXCM'
    GROUP BY substring(trade_date, 1, 6)
),
-- 中国国债收益率月度预聚合（取月末最后交易日值）
cb_monthly AS (
    SELECT
        substring(trade_date, 1, 6) AS yyyymm,
        argMax(cn_yield_2y, trade_date)  AS cn_yield_2y,
        argMax(cn_yield_5y, trade_date)  AS cn_yield_5y,
        argMax(cn_yield_10y, trade_date) AS cn_yield_10y
    FROM indexsysdb.df_akshare_bond_zh_us_rate
    GROUP BY substring(trade_date, 1, 6)
),
-- GDP 季度
gdp_quarterly AS (
    SELECT
        quarter,
        max(gdp_yoy) AS gdp_yoy
    FROM indexsysdb.df_tushare_cn_gdp
    GROUP BY quarter
),
-- 美元指数月度预聚合（取月末最后交易日值）
usdx_monthly AS (
    SELECT
        substring(trade_date, 1, 6) AS yyyymm,
        argMax(USDX_index, trade_date) AS usdx_index
    FROM indexsysdb.df_tushare_usd_index_daily
    GROUP BY substring(trade_date, 1, 6)
),
-- 黄金期货 GC 月度预聚合（取月末最后交易日值），date格式 YYYY-MM-DD
gold_monthly AS (
    SELECT
        substring(replaceAll(date, '-', ''), 1, 6) AS yyyymm,
        argMax(close, replaceAll(date, '-', '')) AS gold_close
    FROM indexsysdb.df_akshare_futures_foreign_hist
    WHERE symbol = 'GC'
    GROUP BY substring(replaceAll(date, '-', ''), 1, 6)
),
-- 道琼斯工业指数 DJI 月度预聚合
dji_monthly AS (
    SELECT
        substring(trade_date, 1, 6) AS yyyymm,
        argMax(close, trade_date) AS dji_close
    FROM indexsysdb.df_tushare_index_global
    WHERE ts_code = 'DJI'
    GROUP BY substring(trade_date, 1, 6)
),
-- 上证综指 月度预聚合
sh_monthly AS (
    SELECT
        substring(trade_date, 1, 6) AS yyyymm,
        argMax(close, trade_date) AS sh_close
    FROM indexsysdb.df_tushare_cn_index_daily
    WHERE ts_code = '000001.SH'
    GROUP BY substring(trade_date, 1, 6)
),
-- 深证成指数 月度预聚合
sz_monthly AS (
    SELECT
        substring(trade_date, 1, 6) AS yyyymm,
        argMax(close, trade_date) AS sz_close
    FROM indexsysdb.df_tushare_cn_index_daily
    WHERE ts_code = '399001.SZ'
    GROUP BY substring(trade_date, 1, 6)
)
SELECT
    toUInt32(cal.trade_year) AS trade_year,
    toUInt32(concat(cal.trade_year, lpad(cal.trade_month, 2, '0'))) AS trade_month,
    max(cal.trade_date) AS last_trade_date,
    argMax(shibor.tenor_3m, cal.trade_date) AS shibor_3m_eom,
    argMax(lpr.tenor_5y, cal.trade_date) AS lpr_5y_eom,
    argMax(ust.y10, cal.trade_date) AS ust_y10_eom,
    max(mm.m1_yoy) AS m1_yoy,
    max(mm.m2_yoy) AS m2_yoy,
    max(cpi.cpi_yoy) AS cpi_yoy,
    max(fx.forex_reserves) AS forex_reserves,
    max(fx.gold_reserves)  AS gold_reserves,
    max(tr.exports_yoy) AS exports_yoy,
    max(tr.imports_yoy) AS imports_yoy,
    -- 社会融资规模
    max(shr.total_shrzgm)   AS total_shrzgm,
    max(shr.rmb_loan)       AS rmb_loan,
    max(shr.entrusted_loan) AS entrusted_loan,
    max(shr.trust_loan)     AS trust_loan,
    max(shr.corporate_bonds) AS corporate_bonds,
    max(shr.equity_financing) AS equity_financing,
    -- 外汇 USDCNH.FXCM 月末值
    max(fxd.usdcnh_bid_close) AS usdcnh_bid_close,
    max(fxd.usdcnh_ask_close) AS usdcnh_ask_close,
    -- 中国国债收益率月末值
    max(cb.cn_yield_2y)  AS cn_yield_2y,
    max(cb.cn_yield_5y)  AS cn_yield_5y,
    max(cb.cn_yield_10y) AS cn_yield_10y,
    max(gdp.gdp_yoy) AS gdp_yoy,
    -- 美元指数月末值
    max(udx.usdx_index) AS usdx_index,
    -- 黄金期货 GC 月末值
    max(gld.gold_close) AS gold_close,
    -- 道琼斯工业指数月末值
    max(dji.dji_close) AS dji_close,
    -- 上证综指月末值
    max(sh.sh_close) AS sh_close,
    -- 深证成指数月末值
    max(sz.sz_close) AS sz_close
FROM indexsysdb.df_sys_calendar cal
ANY LEFT JOIN indexsysdb.df_tushare_shibor_daily shibor
    ON cal.trade_date = shibor.trade_date
ANY LEFT JOIN indexsysdb.df_tushare_shibor_lpr_daily lpr
    ON cal.trade_date = lpr.trade_date
ANY LEFT JOIN indexsysdb.df_tushare_us_treasury_yield_cruve ust
    ON cal.trade_date = ust.trade_date
ANY LEFT JOIN money_monthly mm
    ON substring(cal.trade_date, 1, 6) = mm.yyyymm
ANY LEFT JOIN cpi_monthly cpi
    ON substring(cal.trade_date, 1, 6) = cpi.yyyymm
ANY LEFT JOIN fx_gold_monthly fx
    ON substring(cal.trade_date, 1, 6) = fx.yyyymm
ANY LEFT JOIN trade_monthly tr
    ON substring(cal.trade_date, 1, 6) = tr.yyyymm
ANY LEFT JOIN shrzgm_monthly shr
    ON substring(cal.trade_date, 1, 6) = shr.yyyymm
ANY LEFT JOIN fx_daily_monthly fxd
    ON substring(cal.trade_date, 1, 6) = fxd.yyyymm
ANY LEFT JOIN cb_monthly cb
    ON substring(cal.trade_date, 1, 6) = cb.yyyymm
ANY LEFT JOIN gdp_quarterly gdp
    ON concat(cal.trade_year, 'Q', cal.quarter) = gdp.quarter
ANY LEFT JOIN usdx_monthly udx
    ON substring(cal.trade_date, 1, 6) = udx.yyyymm
ANY LEFT JOIN gold_monthly gld
    ON substring(cal.trade_date, 1, 6) = gld.yyyymm
ANY LEFT JOIN dji_monthly dji
    ON substring(cal.trade_date, 1, 6) = dji.yyyymm
ANY LEFT JOIN sh_monthly sh
    ON substring(cal.trade_date, 1, 6) = sh.yyyymm
ANY LEFT JOIN sz_monthly sz
    ON substring(cal.trade_date, 1, 6) = sz.yyyymm
WHERE cal.trade_date BETWEEN '20100101' AND '20260710'
GROUP BY
    toUInt32(cal.trade_year),
    toUInt32(concat(cal.trade_year, lpad(cal.trade_month, 2, '0')))
ORDER BY
    toUInt32(cal.trade_year) desc,
    toUInt32(concat(cal.trade_year, lpad(cal.trade_month, 2, '0'))) desc;
