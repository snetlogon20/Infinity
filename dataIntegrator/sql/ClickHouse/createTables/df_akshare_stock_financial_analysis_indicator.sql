--AkShare-股票数据-财务指标
--摊薄每股收益(元)
--加权每股收益(元)
--每股收益_调整后(元)
--扣除非经常性损益后的每股收益(元)
--每股净资产_调整前(元)
--每股净资产_调整后(元)
--每股经营性现金流(元)
--每股资本公积金(元)
--每股未分配利润(元)
--调整后的每股净资产(元)
--总资产利润率(%)
--主营业务利润率(%)
--总资产净利润率(%)
--成本费用利润率(%)
--营业利润率(%)

--drop table indexsysdb.df_akshare_stock_financial_analysis_indicator
CREATE TABLE indexsysdb.df_akshare_stock_financial_analysis_indicator (
    date String,
    symbol String,
    diluted_eps String,
    weighted_eps String,
    adjusted_eps String,
    deducted_eps String,
    net_asset_per_share_before_adj String,
    net_asset_per_share_after_adj String,
    operating_cash_flow_per_share String,
    capital_reserve_per_share String,
    retained_earnings_per_share String,
    adjusted_net_asset_per_share String,
    total_asset_margin String,
    main_business_margin String,
    roa String,
    cost_profit_margin String,
    operating_profit_margin String,
    main_cost_ratio String,
    net_sales_margin String,
    equity_return_rate String,
    roe_return String,
    asset_return_rate String,
    gross_margin String,
    three_fee_ratio String,
    non_main_ratio String,
    main_profit_ratio String,
    dividend_payout_ratio String,
    investment_return_ratio String,
    main_profit_amount String,
    roe String,
    weighted_roe String,
    deducted_net_profit String,
    main_income_growth_rate String,
    net_profit_growth_rate String,
    net_asset_growth_rate String,
    total_asset_growth_rate String,
    receivables_turnover String,
    receivables_turnover_days String,
    inventory_turnover_days String,
    inventory_turnover String,
    fixed_asset_turnover String,
    total_asset_turnover String,
    total_asset_turnover_days String,
    current_asset_turnover String,
    current_asset_turnover_days String,
    equity_turnover String,
    current_ratio String,
    quick_ratio String,
    cash_ratio String,
    interest_coverage String,
    long_debt_to_working_capital_ratio String,
    equity_ratio String,
    long_term_liability_ratio String,
    equity_to_fixed_assets_ratio String,
    liabilities_to_equity_ratio String,
    long_assets_to_long_funds_ratio String,
    capitalization_ratio String,
    fixed_asset_net_value_ratio String,
    capital_fixed_ratio String,
    debt_to_equity_ratio String,
    liquidation_value_ratio String,
    fixed_asset_ratio String,
    asset_liability_ratio String,
    total_assets String,
    operating_cash_flow_to_sales_ratio String,
    operating_cash_flow_roa String,
    operating_cash_flow_to_net_profit_ratio String,
    operating_cash_flow_to_liability_ratio String,
    cash_flow_ratio String,
    short_stock_investment String,
    short_bond_investment String,
    short_other_operating_investment String,
    long_stock_investment String,
    long_bond_investment String,
    long_other_operating_investment String,
    receivables_within_1y String,
    receivables_within_1_2y String,
    receivables_within_2_3y String,
    receivables_within_3y String,
    prepayments_within_1y String,
    prepayments_within_1_2y String,
    prepayments_within_2_3y String,
    prepayments_within_3y String,
    other_receivables_within_1y String,
    other_receivables_within_1_2y String,
    other_receivables_within_2_3y String,
    other_receivables_within_3y String
)
ENGINE=SummingMergeTree(date)
ORDER BY (date, symbol)
SETTINGS index_granularity = 8192;
