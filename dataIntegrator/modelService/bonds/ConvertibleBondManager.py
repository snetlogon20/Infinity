import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

from dataIntegrator.modelService.bonds.ConvertibleBondAnalyst import ConvertibleBondAnalyst


class ConvertibleBondManager:
    """可转债指标管理器：计算、查询、保存可转债指标到 ClickHouse"""

    def __init__(self):
        self.analyst = ConvertibleBondAnalyst()

    # ---------- 辅助方法 ----------

    @staticmethod
    def print_result(result):
        """打印单个可转债计算结果"""
        if result and result.get('is_feasible'):
            print("\n" + "=" * 80)
            print(f"可转债指标计算结果")
            print("=" * 80)
            for key, value in result.items():
                if key not in ['is_feasible', 'description']:
                    print(f"{key}: {value}")
            print("=" * 80)
        else:
            print(f"计算失败: {result.get('description')}")

    @staticmethod
    def _sort_and_print_dataframe(df, trade_date, title):
        """排序并打印 DataFrame 结果"""
        if df.empty:
            return df
        # 所有债券都计算失败时，跳过排序直接打印
        sort_columns = ['macaulay_duration', 'modified_duration', 'convexity']
        if set(sort_columns).issubset(df.columns):
            df = df.sort_values(
                by=sort_columns,
                ascending=[True, True, False],
                ignore_index=True
            )
        print("\n" + "=" * 100)
        print(f"交易日 {trade_date} {title}（共 {len(df)} 只）")
        print("=" * 100)
        print(df.to_string(index=False))
        print("=" * 100)
        return df

    # ---------- 单个可转债计算 ----------

    def caculate_single_convertable_bond(self):
        """计算并打印单个可转债的指标（示例）"""
        ts_code = "110073.SH"
        trade_date = "20260525"
        result = self.analyst.get_bond_metrics(ts_code, trade_date)
        self.print_result(result)

    # ---------- 批量计算 ----------

    def calculate_selected_bonds(self, trade_date):
        """
        对预设的精选可转债列表计算指标

        参数:
        - trade_date: 交易日期 (YYYYMMDD)

        返回:
        - DataFrame: 包含所有精选可转债指标的 DataFrame
        """
        selected_ts_codes = [
            '110073.SH',
            '110074.SH',
            '110075.SH',
            '110076.SH',
            '110077.SH',
        ]

        logger.info(f"开始计算精选可转债列表，交易日期: {trade_date}，共 {len(selected_ts_codes)} 只")

        results = []
        for ts_code in selected_ts_codes:
            result = self.analyst.get_bond_metrics(ts_code, trade_date)
            self.print_result(result)
            results.append(result)

        calculated_bond_df = pd.DataFrame(results)
        calculated_bond_df = self._sort_and_print_dataframe(calculated_bond_df, trade_date, '精选可转债指标计算结果')
        return calculated_bond_df

    def calculate_all_bonds(self, trade_date):
        """
        获取指定交易日所有可转债的指标

        参数:
        - trade_date: 交易日期 (YYYYMMDD)

        返回:
        - DataFrame: 包含所有可转债指标的 DataFrame
        """
        clickhouse_service = ClickhouseService()

        # 从 ClickHouse 获取当天所有可转债的 ts_code
        sql = f"""
        SELECT DISTINCT ts_code
        FROM indexsysdb.df_tushare_cb_daily
        WHERE trade_date = '{trade_date}'
        ORDER BY ts_code
        """
        distinct_df = clickhouse_service.getDataFrameWithoutColumnsName(sql)

        if distinct_df.empty:
            logger.warning(f"未找到 {trade_date} 的可转债日线数据")
            return pd.DataFrame()

        ts_codes = distinct_df['ts_code'].tolist()
        logger.info(f"交易日 {trade_date} 共有 {len(ts_codes)} 只可转债")

        results = []
        for i, ts_code in enumerate(ts_codes):
            logger.info(f"[{i + 1}/{len(ts_codes)}] 正在计算 {ts_code} ...")
            result = self.analyst.get_bond_metrics(ts_code, trade_date)
            results.append(result)

        calculated_bond_df = pd.DataFrame(results)
        calculated_bond_df = self._sort_and_print_dataframe(calculated_bond_df, trade_date, '全部可转债指标计算结果')
        return calculated_bond_df

    # ---------- 数据持久化 ----------

    def _save_bonds_for_date(self, trade_date):
        """计算并保存单个交易日的可转债指标"""
        calculated_bond_df = self.calculate_all_bonds(trade_date)

        if calculated_bond_df.empty:
            logger.warning(f"交易日 {trade_date} 无可转债数据，跳过保存")
            return False

        # 清洗数据，确保类型匹配 ClickHouse 表定义
        # 字符串列: NaN -> 空字符串
        calculated_bond_df['description'] = calculated_bond_df['description'].fillna('')

        # 布尔/整型列: NaN -> 0, 然后转 int
        calculated_bond_df['is_feasible'] = calculated_bond_df['is_feasible'].fillna(0).astype(int)
        calculated_bond_df['pay_per_year'] = calculated_bond_df['pay_per_year'].fillna(0).astype(int)

        # 浮点列: NaN -> 0.0
        float_columns = ['ytm', 'macaulay_duration', 'modified_duration', 'convexity',
                         'dv01', 'pvbp', 'remaining_years', 'current_yield', 'simple_ytm',
                         'market_price', 'par', 'coupon_rate']
        calculated_bond_df[float_columns] = calculated_bond_df[float_columns].fillna(0.0)

        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=calculated_bond_df,
            table_name='df_tushare_cb_metrics',
            database='indexsysdb'
        )
        return True

    @staticmethod
    def _delete_bonds_in_date_range(start_date, end_date):
        """
        清除指定日期范围内的可转债指标旧数据

        参数:
        - start_date: 起始日期 (YYYYMMDD), 如 '20260101'
        - end_date: 结束日期 (YYYYMMDD), 如 '20260531'
        """
        del_sql = (
            "ALTER TABLE indexsysdb.df_tushare_cb_metrics "
            "DELETE WHERE trade_date >= '%s' AND trade_date <= '%s'"
        ) % (start_date, end_date)
        logger.info(f"清除旧数据: {start_date} ~ {end_date}")
        ClickhouseService.execute_sql(del_sql)

    def save_calculated_bonds(self, start_date, end_date):
        """
        按日期范围批量计算并保存可转债指标到 ClickHouse

        参数:
        - start_date: 起始日期 (YYYYMMDD), 如 '20260101'
        - end_date: 结束日期 (YYYYMMDD), 如 '20260531'
        """
        # 先清除对应日期范围的旧数据，避免重复
        self._delete_bonds_in_date_range(start_date, end_date)

        # 生成日期范围，参考 CalendarService.generate_date_range
        date_range = pd.date_range(start=start_date, end=end_date)
        trade_dates = [d.strftime('%Y%m%d') for d in date_range]

        logger.info(f"开始批量保存可转债指标，日期范围: {start_date} ~ {end_date}，共 {len(trade_dates)} 个交易日")

        success_count = 0
        for i, trade_date in enumerate(trade_dates):
            logger.info(f"[{i + 1}/{len(trade_dates)}] 处理交易日: {trade_date}")
            if self._save_bonds_for_date(trade_date):
                success_count += 1

        logger.info(f"批量保存完成: 成功 {success_count}/{len(trade_dates)}")


if __name__ == "__main__":
    # 测试代码
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    manager = ConvertibleBondManager()

    # 单日测试
    manager.caculate_single_convertable_bond()
    manager.calculate_selected_bonds("20260525")
    manager.calculate_all_bonds("20260525")

    # 单日保存
    manager._save_bonds_for_date("20260525")

    # 批量保存: start_date ~ end_date
    manager.save_calculated_bonds("20260101", "20260524")

