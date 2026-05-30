import pandas as pd
import numpy as np
from datetime import datetime
from scipy.optimize import fsolve
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator import CommonLib
import sys

logger = CommonLib.logger
commonLib = CommonLib()


class ConvertibleBondAnalyst:
    """
    可转债指标计算服务
    从 TuShare 的 cb_basic 和 cb_daily 接口获取数据，计算各种债券指标
    """

    def __init__(self):
        self.clickhouseService = ClickhouseService()

    def get_bond_basic_info(self, ts_code):
        """
        从 ClickHouse 获取可转债基础信息

        参数:
        - ts_code: 转债代码（必传）

        返回:
        - DataFrame: 可转债基础信息
        """
        sql = f"""
        SELECT 
            ts_code,
            bond_full_name,
            bond_short_name,
            cb_type,
            stk_code,
            par,
            issue_price,
            issue_size,
            remain_size,
            value_date,
            maturity_date,
            rate_type,
            coupon_rate,
            add_rate,
            pay_per_year,
            list_date,
            delist_date,
            conv_start_date,
            conv_end_date,
            first_conv_price,
            conv_price,
            maturity_call_price
        FROM indexsysdb.df_tushare_cb_basic
        WHERE ts_code = '{ts_code}'
        ORDER BY ts_code
        """

        df = self.clickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"获取可转债基础信息: {len(df)} 条记录")
        return df

    def get_bond_daily_data(self, ts_code, trade_date=None, start_date=None, end_date=None):
        """
        从 ClickHouse 获取可转债日线行情数据

        参数:
        - ts_code: 转债代码
        - trade_date: 交易日期 (YYYYMMDD)，指定单个日期
        - start_date: 开始日期 (YYYYMMDD)，指定日期范围
        - end_date: 结束日期 (YYYYMMDD)，指定日期范围
        """

        sql = rf"""
        SELECT
            ts_code,
            trade_date,
            close,
            vol,
            amount,
            bond_value,
            bond_over_rate,
            cb_value,
            cb_over_rate
        FROM indexsysdb.df_tushare_cb_daily
        WHERE ts_code = '{ts_code}'
          AND trade_date = '{trade_date}'
        ORDER BY trade_date
        """

        df = self.clickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"获取可转债 {ts_code} 日线数据: {len(df)} 条记录")
        return df

    def calculate_remaining_maturity(self, maturity_date, trade_date):
        """
        计算剩余期限（年）

        参数:
        - maturity_date: 到期日期 (YYYYMMDD 或 YYYY-MM-DD)
        - trade_date: 交易日期 (YYYYMMDD 或 YYYY-MM-DD)

        返回:
        - float: 剩余期限（年）
        """
        if isinstance(maturity_date, str):
            if '-' in maturity_date:
                maturity_dt = datetime.strptime(maturity_date, '%Y-%m-%d')
            else:
                maturity_dt = datetime.strptime(maturity_date, '%Y%m%d')
        else:
            maturity_dt = maturity_date

        if isinstance(trade_date, str):
            if '-' in trade_date:
                trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
            else:
                trade_dt = datetime.strptime(trade_date, '%Y%m%d')
        else:
            trade_dt = trade_date

        remaining_days = (maturity_dt - trade_dt).days
        remaining_years = remaining_days / 365.0

        return remaining_years

    def calculate_current_yield(self, coupon_rate, market_price, par=100):
        """
        计算当期票息收益率

        公式: Current Yield = 年票息 / 当前价格

        参数:
        - coupon_rate: 票面利率（%）
        - market_price: 当前市场价格
        - par: 面值（默认100）

        返回:
        - float: 当期票息收益率
        """
        annual_coupon = par * (coupon_rate / 100.0)
        current_yield = annual_coupon / market_price * 100
        return current_yield

    def calculate_simple_yield_to_maturity(self, coupon_rate, market_price, remaining_years, par=100):
        """
        计算简单到期收益率

        公式: Simple YTM = (年票息 + (面值 - 当前价格) / 剩余年限) / 当前价格

        参数:
        - coupon_rate: 票面利率（%）
        - market_price: 当前市场价格
        - remaining_years: 剩余期限（年）
        - par: 面值（默认100）

        返回:
        - float: 简单到期收益率（%）
        """
        if remaining_years <= 0:
            return 0.0

        annual_coupon = par * (coupon_rate / 100.0)
        simple_ytm = (annual_coupon + (par - market_price) / remaining_years) / market_price * 100
        return simple_ytm

    @staticmethod
    def _calculate_bond_yield(market_price, face_value, coupon_payment, periods, initial_guess=None):
        """
        通过数值求解计算到期收益率 YTM

        参数:
        - market_price: 当前市场价格
        - face_value: 面值
        - coupon_payment: 每期付息金额
        - periods: 剩余付息期数（最小为 1）
        - initial_guess: 初始猜测值，None 则自动按简单收益估算

        返回:
        - float: 每期收益率
        """
        if periods < 1:
            periods = 1

        if initial_guess is None:
            # 用简单收益率作为初始猜测，利于 fsolve 收敛
            total_coupon = coupon_payment * periods
            initial_guess = (total_coupon + face_value - market_price) / (market_price * periods) if market_price > 0 else 0.01
            initial_guess = max(min(initial_guess, 0.50), -0.30)  # 限制在合理范围

        def _bond_price_equation(ytm):
            price = 0
            for t in range(1, periods + 1):
                price += coupon_payment / (1 + ytm) ** t
            price += face_value / (1 + ytm) ** periods
            return price - market_price

        estimated_yield = fsolve(_bond_price_equation, initial_guess, maxfev=1000)[0]
        return estimated_yield

    @staticmethod
    def _calculate_modified_duration(duration, bond_yield, semester):
        """
        计算修正久期

        参数:
        - duration: 麦考利久期
        - bond_yield: 每期收益率
        - semester: 年付息次数

        返回:
        - float: 修正久期
        """
        return duration / (1 + (bond_yield / semester))

    @staticmethod
    def _calculate_bond_information(bond_yield, face_value, coupon_rate, tenor, semester,
                                    is_zero_coupon=False, is_perpetual_bonds=False):
        """
        计算债券的久期和凸性信息

        参数:
        - bond_yield: 每期收益率（YTM）
        - face_value: 面值
        - coupon_rate: 票面利率（小数形式，如 0.05 表示5%）
        - tenor: 剩余期限（以 period 为单位，如剩余5年、每年2次付息 => tenor=10）
        - semester: 年付息次数
        - is_zero_coupon: 是否为零息债券
        - is_perpetual_bonds: 是否为永续债

        返回:
        - tuple: (duration, modified_duration, convexity)
        """
        if tenor < 1:
            tenor = 1

        coupon_payment = face_value * (coupon_rate / semester)
        T = tenor * semester + 1

        present_value_total_sum = 0.0
        duration_total_sum = 0.0
        convexity_total_sum = 0.0

        for period_no in range(1, T):
            t = period_no
            if is_zero_coupon:
                coupon_t = 0.0
            else:
                coupon_t = coupon_payment

            # 最后一期加上本金
            if period_no == T - 1:
                coupon_t = coupon_payment + face_value

            bond_yield_t = bond_yield / semester
            present_value_t = coupon_t / (1 + bond_yield_t) ** t
            duration_t = t * present_value_t
            convexity_t = t * (t + 1) * present_value_t / (1 + bond_yield_t) ** 2

            present_value_total_sum += present_value_t
            duration_total_sum += duration_t
            convexity_total_sum += convexity_t

        if is_perpetual_bonds:
            duration = (1 + bond_yield) / bond_yield
            modified_duration = duration
            convexity = (2 + bond_yield) / (bond_yield ** 2)
        else:
            if not is_zero_coupon:
                duration = duration_total_sum / present_value_total_sum / semester
                modified_duration = ConvertibleBondAnalyst._calculate_modified_duration(duration, bond_yield, semester)
                convexity = convexity_total_sum / present_value_total_sum / (semester ** 2)
            else:
                duration = tenor
                modified_duration = (tenor / (1 + bond_yield * 100 / 200)) / semester
                convexity = ((tenor + 1) * tenor / (1 + bond_yield * 100 / 200) ** 2) / (semester ** 2)

        return duration, modified_duration, convexity

    @staticmethod
    def _calculate_dollar_duration_dvbp(modified_duration, market_price):
        """
        计算美元久期和 DV01/PVBP

        参数:
        - modified_duration: 修正久期
        - market_price: 当前市场价格

        返回:
        - tuple: (dollar_duration, dvbp)
        """
        dollar_duration = modified_duration * market_price
        dvbp = dollar_duration / 10000.0
        return dollar_duration, dvbp

    def get_bond_metrics(self, ts_code, trade_date):
        """
        获取可转债的完整指标

        参数:
        - ts_code: 转债代码
        - trade_date: 交易日期 (YYYYMMDD)

        返回:
        - dict: 包含各种指标的字典，如果不可行则返回 None
        """
        logger.info(f"开始计算可转债 {ts_code} 在 {trade_date} 的指标...")

        # 1. 获取可转债基础信息
        basic_df = self.get_bond_basic_info(ts_code)
        if basic_df.empty:
            logger.warning(f"未找到可转债 {ts_code} 的基础信息")
            return {
                'ts_code': ts_code,
                'trade_date': trade_date,
                'is_feasible': False,
                'description': f"未找到可转债 {ts_code} 的基础信息"
            }

        basic_info = basic_df.iloc[0].to_dict()

        # 2. 获取日线行情数据
        daily_df = self.get_bond_daily_data(ts_code, trade_date)
        if daily_df.empty:
            logger.warning(f"未找到可转债 {ts_code} 在 {trade_date} 的日线数据")
            return {
                'ts_code': ts_code,
                'trade_date': trade_date,
                'is_feasible': False,
                'description': f"未找到可转债 {ts_code} 在 {trade_date} 的日线数据"
            }

        daily_info = daily_df.iloc[0].to_dict()

        # 3. 检查是否已到期
        maturity_date = basic_info.get('maturity_date', '')
        if maturity_date and len(str(maturity_date)) >= 8:
            maturity_date_str = str(maturity_date).replace('-', '')
            if int(maturity_date_str) < int(trade_date):
                logger.warning(f"可转债 {ts_code} 已在 {maturity_date} 到期")
                return {
                    'ts_code': ts_code,
                    'trade_date': trade_date,
                    'is_feasible': False,
                    'description': f"可转债 {ts_code} 已在 {maturity_date} 到期"
                }

        # 4. 提取关键参数
        par = float(basic_info.get('par', 100))
        coupon_rate = float(basic_info.get('coupon_rate', 0))
        pay_per_year = int(basic_info.get('pay_per_year', 2))
        market_price = float(daily_info.get('close', 0))

        if market_price <= 0:
            logger.warning(f"可转债 {ts_code} 在 {trade_date} 的收盘价无效: {market_price}")
            return {
                'ts_code': ts_code,
                'trade_date': trade_date,
                'is_feasible': False,
                'description': f"可转债 {ts_code} 在 {trade_date} 的收盘价无效: {market_price}"
            }

        # 5. 计算剩余期限
        remaining_years = self.calculate_remaining_maturity(maturity_date, trade_date)

        if remaining_years <= 0:
            logger.warning(f"可转债 {ts_code} 在 {trade_date} 的剩余期限无效: {remaining_years}")
            return {
                'ts_code': ts_code,
                'trade_date': trade_date,
                'is_feasible': False,
                'description': f"可转债 {ts_code} 在 {trade_date} 的剩余期限无效: {remaining_years}"
            }

        try:
            # 6. 计算 YTM（到期收益率）—— 每期收益率，确保至少 1 个付息周期
            coupon_payment = par * (coupon_rate / 100.0) / pay_per_year
            periods = max(int(remaining_years * pay_per_year), 1)
            ytm = self._calculate_bond_yield(market_price, par, coupon_payment, periods)

            # 7. 计算久期和凸性，tenor 至少为 1
            coupon_rate_decimal = coupon_rate / 100.0
            tenor = max(int(remaining_years * pay_per_year), 1)
            duration, modified_duration, convexity = self._calculate_bond_information(
                bond_yield=ytm,
                face_value=par,
                coupon_rate=coupon_rate_decimal,
                tenor=tenor,
                semester=pay_per_year,
                is_zero_coupon=False,
                is_perpetual_bonds=False
            )

            # 8. 计算 DV01 / PVBP
            dollar_duration, dvbp = self._calculate_dollar_duration_dvbp(modified_duration, market_price)

            # 9. 计算当期票息收益率
            current_yield = self.calculate_current_yield(coupon_rate, market_price, par)

            # 10. 计算简单到期收益率
            simple_ytm = self.calculate_simple_yield_to_maturity(coupon_rate, market_price, remaining_years, par)

            # 11. 整理结果
            result = {
                'ts_code': ts_code,
                'trade_date': trade_date,
                'is_feasible': True,
                'description': '计算成功',
                'ytm': ytm * 100,  # 转换为百分比
                'macaulay_duration': duration,
                'modified_duration': modified_duration,
                'convexity': convexity,
                'dv01': dvbp,
                'pvbp': dvbp,
                'remaining_years': remaining_years,
                'current_yield': current_yield,
                'simple_ytm': simple_ytm,
                'market_price': market_price,
                'par': par,
                'coupon_rate': coupon_rate,
                'pay_per_year': pay_per_year
            }

            logger.info(f"✅ 可转债 {ts_code} 在 {trade_date} 的指标计算完成")
            logger.info(f"   YTM: {ytm * 100:.4f}%")
            logger.info(f"   麦考利久期: {duration:.4f}")
            logger.info(f"   修正久期: {modified_duration:.4f}")
            logger.info(f"   凸性: {convexity:.4f}")
            logger.info(f"   DV01/PVBP: {dvbp:.4f}")
            logger.info(f"   剩余期限: {remaining_years:.4f} 年")
            logger.info(f"   当期票息收益率: {current_yield:.4f}%")
            logger.info(f"   简单到期收益率: {simple_ytm:.4f}%")

            return result

        except Exception as e:
            logger.error(f"计算可转债 {ts_code} 指标时发生错误: {e}")
            return {
                'ts_code': ts_code,
                'trade_date': trade_date,
                'is_feasible': False,
                'description': f"计算时发生错误: {str(e)}"
            }

    def get_bond_metrics_batch(self, ts_codes, trade_date):
        """
        批量获取可转债指标

        参数:
        - ts_codes: 转债代码列表
        - trade_date: 交易日期 (YYYYMMDD)

        返回:
        - DataFrame: 包含所有可转债指标的 DataFrame
        """
        results = []

        for ts_code in ts_codes:
            result = self.get_bond_metrics(ts_code, trade_date)
            results.append(result)

        df = pd.DataFrame(results)
        return df


if __name__ == "__main__":
    # 测试代码
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    service = ConvertibleBondAnalyst()

    # 测试单个可转债
    trade_date = "20260525"
    ts_code = "110073.SH"
    result = service.get_bond_metrics(ts_code, trade_date)
    if result and result.get('is_feasible'):
        print("\n" + "=" * 80)
        print("可转债指标计算结果")
        print("=" * 80)
        for key, value in result.items():
            if key not in ['is_feasible', 'description']:
                print(f"{key}: {value}")
        print("=" * 80)
    else:
        print(f"计算失败: {result.get('description')}")
