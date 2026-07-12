-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\tb_macro_economic_indicator.sql
--drop table indexsysdb.tb_macro_economic_indicator
--宏观经济指标月度数据（含环比增幅）
CREATE TABLE indexsysdb.tb_macro_economic_indicator (
    trade_year UInt32 COMMENT '年份',
    trade_month UInt32 COMMENT '月份(YYYYMM)',
    last_trade_date String COMMENT '当月最后交易日(YYYYMMDD)',
    -- === 利率 & 流动性 ===
    shibor_3m_eom Float64 COMMENT 'SHIBOR 3M 月末值(%)',
    lpr_5y_eom Float64 COMMENT 'LPR 5Y 月末值(%)',
    ust_y10_eom Float64 COMMENT '美国国债10Y 月末收益率(%)',
    -- === 货币 & 物价 ===
    m1_yoy Float64 COMMENT 'M1 同比(%)',
    m2_yoy Float64 COMMENT 'M2 同比(%)',
    cpi_yoy Float64 COMMENT 'CPI 同比(%)',
    -- === 外储 & 黄金 ===
    forex_reserves Float64 COMMENT '外汇储备(亿美元)',
    gold_reserves Float64 COMMENT '黄金储备(亿美元)',
    -- === 进出口 ===
    exports_yoy Float64 COMMENT '出口同比(%)',
    imports_yoy Float64 COMMENT '进口同比(%)',
    -- === 社会融资规模 ===
    total_shrzgm Float64 COMMENT '社会融资规模(亿元)',
    rmb_loan Float64 COMMENT '人民币贷款(亿元)',
    entrusted_loan Float64 COMMENT '委托贷款(亿元)',
    trust_loan Float64 COMMENT '信托贷款(亿元)',
    corporate_bonds Float64 COMMENT '企业债券(亿元)',
    equity_financing Float64 COMMENT '非金融企业境内股票融资(亿元)',
    -- === 外汇 ===
    usdcnh_bid_close Float64 COMMENT 'USDCNH 买入价月末值',
    usdcnh_ask_close Float64 COMMENT 'USDCNH 卖出价月末值',
    -- === 国债收益率 ===
    cn_yield_2y Float64 COMMENT '中国国债2Y收益率(%)',
    cn_yield_5y Float64 COMMENT '中国国债5Y收益率(%)',
    cn_yield_10y Float64 COMMENT '中国国债10Y收益率(%)',
    -- === GDP ===
    gdp_yoy Float64 COMMENT 'GDP 当季同比(%)',
    -- === 环比增幅 (当期-前期)/前期，小数表示 ===
    shibor_3m_eom_pct Float64 COMMENT 'SHIBOR 3M 环比增幅',
    lpr_5y_eom_pct Float64 COMMENT 'LPR 5Y 环比增幅',
    ust_y10_eom_pct Float64 COMMENT '美国国债10Y 环比增幅',
    m1_yoy_pct Float64 COMMENT 'M1 环比增幅',
    m2_yoy_pct Float64 COMMENT 'M2 环比增幅',
    cpi_yoy_pct Float64 COMMENT 'CPI 环比增幅',
    forex_reserves_pct Float64 COMMENT '外汇储备 环比增幅',
    gold_reserves_pct Float64 COMMENT '黄金储备 环比增幅',
    exports_yoy_pct Float64 COMMENT '出口 环比增幅',
    imports_yoy_pct Float64 COMMENT '进口 环比增幅',
    total_shrzgm_pct Float64 COMMENT '社会融资规模 环比增幅',
    rmb_loan_pct Float64 COMMENT '人民币贷款 环比增幅',
    entrusted_loan_pct Float64 COMMENT '委托贷款 环比增幅',
    trust_loan_pct Float64 COMMENT '信托贷款 环比增幅',
    corporate_bonds_pct Float64 COMMENT '企业债券 环比增幅',
    equity_financing_pct Float64 COMMENT '非金融企业境内股票融资 环比增幅',
    usdcnh_bid_close_pct Float64 COMMENT 'USDCNH买价 环比增幅',
    usdcnh_ask_close_pct Float64 COMMENT 'USDCNH卖价 环比增幅',
    cn_yield_2y_pct Float64 COMMENT '中国国债2Y 环比增幅',
    cn_yield_5y_pct Float64 COMMENT '中国国债5Y 环比增幅',
    cn_yield_10y_pct Float64 COMMENT '中国国债10Y 环比增幅',
    gdp_yoy_pct Float64 COMMENT 'GDP 环比增幅'
)
ENGINE=MergeTree()
ORDER BY (trade_month)
SETTINGS index_granularity = 8192;
