"""
GoldAnalyzer — concrete analyzer for gold futures (GC).
"""

import logging
from .BaseAssetAnalyzer import BaseAssetAnalyzer, AnalyzerFactory

logger = logging.getLogger(__name__)


class GoldAnalyzer(BaseAssetAnalyzer):
    """
    Analyzer for COMEX Gold Futures (symbol: GC).

    Data source: indexsysdb.df_akshare_futures_foreign_hist
    """

    def get_sql(self, symbol: str, start_date: str, end_date: str) -> str:
        """Generate ClickHouse SQL for gold futures data."""
        sql = f"""
            SELECT
                date      AS trade_date,
                open,
                close,
                low,
                high,
                pct_change
            FROM indexsysdb.df_akshare_futures_foreign_hist
            WHERE symbol = '{symbol}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date
        """
        logger.info(f"GoldAnalyzer SQL generated: symbol={symbol}, "
                     f"start={start_date}, end={end_date}")
        return sql

    def get_asset_name(self) -> str:
        return f"COMEX Gold Futures ({self.symbol})"


# Auto-register
AnalyzerFactory.register('GC', GoldAnalyzer)
