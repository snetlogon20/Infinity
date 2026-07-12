"""
USStockAnalyzer — concrete analyzer for US stocks (e.g. C, AAPL, MSFT).
"""

import logging
from .BaseAssetAnalyzer import BaseAssetAnalyzer, AnalyzerFactory

logger = logging.getLogger(__name__)


class USStockAnalyzer(BaseAssetAnalyzer):
    """
    Analyzer for US stocks from AKShare (symbol: C, AAPL, MSFT, etc.).

    Data source: indexsysdb.df_akshare_stock_us_daily
    """

    def get_sql(self, symbol: str, start_date: str, end_date: str) -> str:
        """Generate ClickHouse SQL for US stock daily data."""
        sql = f"""
            SELECT
                date,
                open,
                close,
                low,
                high,
                pct_change
            FROM indexsysdb.df_akshare_stock_us_daily
            WHERE symbol = '{symbol}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date
        """
        logger.info(f"USStockAnalyzer SQL generated: symbol={symbol}, "
                     f"start={start_date}, end={end_date}")
        return sql

    def get_asset_name(self) -> str:
        return f"US Stock ({self.symbol})"


# Auto-register for US stocks
for _sym in ['C', 'JPM', 'SPY', 'AAPL', 'NVDA', 'MSFT']:
    AnalyzerFactory.register(_sym, USStockAnalyzer)
