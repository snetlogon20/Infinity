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

        conditions = [f"ts_code = '{ts_code}'"]
        if trade_date:
            conditions.append(f"trade_date = '{trade_date}'")
        if start_date:
            conditions.append(f"trade_date >= '{start_date}'")
        if end_date:
            conditions.append(f"trade_date <= '{end_date}'")

        sql = f"""
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
        WHERE {' AND '.join(conditions)}
        ORDER BY trade_date
        """

        df = self.clickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"获取可转债 {ts_code} 日线数据: {len(df)} 条记录")
        return df

    def get_bond_daily_history(self, ts_code, lookback_days=252, end_date=None):
        """
        获取可转债历史日线数据，用于 VaR/ES 计算

        参数:
        - ts_code: 转债代码
        - lookback_days: 回溯天数（默认252个交易日≈1年）
        - end_date: 截止日期 (YYYYMMDD)，默认取最新数据

        返回:
        - DataFrame: 历史日线行情（按 trade_date 升序排列）
        """
        if end_date:
            end_date_cond = f"AND trade_date <= '{end_date}'"
        else:
            end_date_cond = ""

        sql = f"""
        SELECT
            ts_code,
            trade_date,
            close
        FROM indexsysdb.df_tushare_cb_daily
        WHERE ts_code = '{ts_code}'
          {end_date_cond}
        ORDER BY trade_date DESC
        LIMIT {lookback_days}
        """

        df = self.clickhouseService.getDataFrameWithoutColumnsName(sql)
        df = df.sort_values('trade_date', ascending=True).reset_index(drop=True)
        logger.info(f"获取可转债 {ts_code} 历史日线: {len(df)} 条记录（lookback={lookback_days}）")
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

    # ==============================
    #  VaR & Expected Shortfall 方法
    # ==============================

    @staticmethod
    def _calculate_daily_returns(prices):
        """
        从价格序列计算日收益率

        参数:
        - prices: 价格序列（升序排列）

        返回:
        - np.array: 日收益率序列
        """
        prices = np.asarray(prices, dtype=float)
        if len(prices) < 2:
            return np.array([])
        returns = np.diff(prices) / prices[:-1]
        return returns

    # ==============================
    #  有效久期 & 有效凸性 & 价格变动
    # ==============================

    @staticmethod
    def _calc_bond_price(ytm_per_period, face_value, coupon_payment, periods):
        """
        计算债券理论价格（给定每期收益率）

        参数:
        - ytm_per_period: 每期收益率
        - face_value: 面值
        - coupon_payment: 每期付息金额
        - periods: 剩余付息期数

        返回:
        - float: 债券理论价格
        """
        price = 0.0
        for t in range(1, periods + 1):
            price += coupon_payment / (1 + ytm_per_period) ** t
        price += face_value / (1 + ytm_per_period) ** periods
        return price

    @staticmethod
    def calculate_effective_duration(market_price, face_value, coupon_payment, periods,
                                     pay_per_year, ytm_per_period, shock_bps=1):
        """
        计算有效久期（通过收益率上下波动计算）

        公式: Eff_Dur = (P_down - P_up) / (2 × P_0 × Δy)

        参数:
        - market_price: 当前市场价格
        - face_value: 面值
        - coupon_payment: 每期付息金额
        - periods: 剩余付息期数
        - pay_per_year: 年付息次数
        - ytm_per_period: 当前每期收益率（YTM）
        - shock_bps: 收益率波动基点（默认1bp）

        返回:
        - float: 年化有效久期
        """
        delta_y_ann = shock_bps / 10000.0  # bps → 小数
        y_ann = ytm_per_period * pay_per_year

        y_up_per_period = (y_ann + delta_y_ann) / pay_per_year
        y_down_per_period = (y_ann - delta_y_ann) / pay_per_year

        p_up = ConvertibleBondAnalyst._calc_bond_price(
            y_up_per_period, face_value, coupon_payment, periods)
        p_down = ConvertibleBondAnalyst._calc_bond_price(
            y_down_per_period, face_value, coupon_payment, periods)

        effective_duration = (p_down - p_up) / (2.0 * market_price * delta_y_ann)
        return round(effective_duration, 6)

    @staticmethod
    def calculate_effective_convexity(market_price, face_value, coupon_payment, periods,
                                      pay_per_year, ytm_per_period, shock_bps=1):
        """
        计算有效凸性（通过收益率上下波动计算）

        公式: Eff_Conv = (P_down + P_up - 2×P_0) / (P_0 × (Δy)²)

        参数:
        - market_price: 当前市场价格
        - face_value: 面值
        - coupon_payment: 每期付息金额
        - periods: 剩余付息期数
        - pay_per_year: 年付息次数
        - ytm_per_period: 当前每期收益率（YTM）
        - shock_bps: 收益率波动基点（默认1bp）

        返回:
        - float: 年化有效凸性
        """
        delta_y_ann = shock_bps / 10000.0
        y_ann = ytm_per_period * pay_per_year

        y_up_per_period = (y_ann + delta_y_ann) / pay_per_year
        y_down_per_period = (y_ann - delta_y_ann) / pay_per_year

        p_up = ConvertibleBondAnalyst._calc_bond_price(
            y_up_per_period, face_value, coupon_payment, periods)
        p_down = ConvertibleBondAnalyst._calc_bond_price(
            y_down_per_period, face_value, coupon_payment, periods)

        effective_convexity = (p_down + p_up - 2.0 * market_price) / (market_price * delta_y_ann ** 2)
        return round(effective_convexity, 6)

    @staticmethod
    def calculate_pct_price_change(effective_duration, effective_convexity,
                                   yield_shocks_bps=(50, -50, 100, -100)):
        """
        百分比价格变动，使用二阶近似公式:
            %ΔP ≈ -Eff_Dur × Δy + ½ × Eff_Conv × (Δy)²

        参数:
        - effective_duration: 年化有效久期
        - effective_convexity: 年化有效凸性
        - yield_shocks_bps: 收益率变动场景（基点，正=上升，负=下降）

        返回:
        - dict: {50: -2.3456, -50: 2.5678, 100: -4.8912, -100: 5.4321, ...}（%）
        """
        result = {}
        for shock_bps in yield_shocks_bps:
            delta_y = shock_bps / 10000.0  # bps → 小数
            pct_change = -effective_duration * delta_y + 0.5 * effective_convexity * (delta_y ** 2)
            result[shock_bps] = round(pct_change * 100, 4)  # 转为百分比
        return result

    @staticmethod
    def calculate_var_historical(returns, confidence_levels=(0.95, 0.99)):
        """
        历史模拟法计算 VaR

        参数:
        - returns: 日收益率序列
        - confidence_levels: 置信水平元组

        返回:
        - dict: {0.95: var_value, 0.99: var_value}（百分比形式，正值代表损失）
        """
        returns = np.asarray(returns, dtype=float)
        returns = returns[~np.isnan(returns)]
        if len(returns) < 10:
            return {cl: 0.0 for cl in confidence_levels}

        result = {}
        for cl in confidence_levels:
            var_value = -np.percentile(returns, (1 - cl) * 100) * 100
            result[cl] = round(var_value, 6)
        return result

    @staticmethod
    def calculate_var_parametric(returns, confidence_levels=(0.95, 0.99)):
        """
        参数法（方差-协方差法）计算 VaR，假设收益率服从正态分布

        参数:
        - returns: 日收益率序列
        - confidence_levels: 置信水平元组

        返回:
        - dict: {0.95: var_value, 0.99: var_value}（百分比形式，正值代表损失）
        """
        from scipy import stats
        returns = np.asarray(returns, dtype=float)
        returns = returns[~np.isnan(returns)]
        if len(returns) < 10:
            return {cl: 0.0 for cl in confidence_levels}

        mu = np.mean(returns)
        sigma = np.std(returns, ddof=1)

        result = {}
        for cl in confidence_levels:
            z_score = stats.norm.ppf(1 - cl)
            var_value = -(mu + z_score * sigma) * 100
            result[cl] = round(var_value, 6)
        return result

    @staticmethod
    def calculate_expected_shortfall(returns, confidence_levels=(0.95, 0.99)):
        """
        历史模拟法计算 Expected Shortfall (CVaR)

        参数:
        - returns: 日收益率序列
        - confidence_levels: 置信水平元组

        返回:
        - dict: {0.95: es_value, 0.99: es_value}（百分比形式，正值代表损失）
        """
        returns = np.asarray(returns, dtype=float)
        returns = returns[~np.isnan(returns)]
        if len(returns) < 10:
            return {cl: 0.0 for cl in confidence_levels}

        result = {}
        for cl in confidence_levels:
            threshold = np.percentile(returns, (1 - cl) * 100)
            tail = returns[returns <= threshold]
            if len(tail) == 0:
                es_value = -threshold * 100
            else:
                es_value = -np.mean(tail) * 100
            result[cl] = round(es_value, 6)
        return result

    def _calc_var_es_from_history(self, ts_code, trade_date, market_price, lookback_days=252):
        """
        从历史数据计算 VaR 和 ES

        参数:
        - ts_code: 转债代码
        - trade_date: 交易日期 (YYYYMMDD)
        - market_price: 当日收盘价
        - lookback_days: 回溯天数

        返回:
        - tuple: (var_hist_dict, var_param_dict, es_dict, actual_lookback_days)
        """
        empty = (
            {0.95: 0.0, 0.99: 0.0},
            {0.95: 0.0, 0.99: 0.0},
            {0.95: 0.0, 0.99: 0.0},
            0
        )

        try:
            history_df = self.get_bond_daily_history(ts_code, lookback_days=lookback_days, end_date=trade_date)

            # 确保包含当日价格以计算完整收益率
            prices = history_df['close'].astype(float).values
            if len(prices) < 10:
                logger.warning(f"可转债 {ts_code} 历史数据不足 ({len(prices)} 条)，无法计算 VaR/ES")
                return empty

            returns = self._calculate_daily_returns(prices)
            if len(returns) < 5:
                logger.warning(f"可转债 {ts_code} 收益率数据不足 ({len(returns)} 条)，无法计算 VaR/ES")
                return empty

            var_hist = self.calculate_var_historical(returns)
            var_param = self.calculate_var_parametric(returns)
            es = self.calculate_expected_shortfall(returns)

            logger.info(f"可转债 {ts_code} VaR/ES 计算完成（{len(returns)} 个日收益率样本）")
            return var_hist, var_param, es, len(returns)

        except Exception as e:
            logger.error(f"可转债 {ts_code} VaR/ES 计算异常: {e}")
            return empty

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

            # 11. 计算有效久期和有效凸性
            coupon_payment = par * (coupon_rate / 100.0) / pay_per_year
            periods = max(int(remaining_years * pay_per_year), 1)
            effective_duration = self.calculate_effective_duration(
                market_price, par, coupon_payment, periods, pay_per_year, ytm)
            effective_convexity = self.calculate_effective_convexity(
                market_price, par, coupon_payment, periods, pay_per_year, ytm)

            # 12. 计算百分比价格变动（+/-50bp, +/-100bp）
            pct_price_chg = self.calculate_pct_price_change(effective_duration, effective_convexity)

            # 13. 计算 VaR 和 Expected Shortfall
            var_hist, var_param, es, lookback_days = self._calc_var_es_from_history(ts_code, trade_date, market_price)

            # 14. 整理结果
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
                'pay_per_year': pay_per_year,
                # 有效久期 & 有效凸性
                'effective_duration': effective_duration,
                'effective_convexity': effective_convexity,
                # 百分比价格变动（%）
                'pct_price_chg_p50bp': pct_price_chg.get(50, 0.0),
                'pct_price_chg_m50bp': pct_price_chg.get(-50, 0.0),
                'pct_price_chg_p100bp': pct_price_chg.get(100, 0.0),
                'pct_price_chg_m100bp': pct_price_chg.get(-100, 0.0),
                # VaR & ES (百分数，正值=损失)
                'var_hist_95': var_hist.get(0.95, 0.0),
                'var_hist_99': var_hist.get(0.99, 0.0),
                'var_param_95': var_param.get(0.95, 0.0),
                'var_param_99': var_param.get(0.99, 0.0),
                'es_95': es.get(0.95, 0.0),
                'es_99': es.get(0.99, 0.0),
                # VaR & ES（绝对价格，正值=损失）
                'var_price_hist_95': var_hist.get(0.95, 0.0) / 100.0 * market_price,
                'var_price_hist_99': var_hist.get(0.99, 0.0) / 100.0 * market_price,
                'var_price_param_95': var_param.get(0.95, 0.0) / 100.0 * market_price,
                'var_price_param_99': var_param.get(0.99, 0.0) / 100.0 * market_price,
                'es_price_95': es.get(0.95, 0.0) / 100.0 * market_price,
                'es_price_99': es.get(0.99, 0.0) / 100.0 * market_price,
                'lookback_days': lookback_days,
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
            logger.info(f"   有效久期: {effective_duration:.4f}")
            logger.info(f"   有效凸性: {effective_convexity:.4f}")
            logger.info(f"   价格变动 +50bp / -50bp:   {pct_price_chg.get(50, 0):+.4f}% / {pct_price_chg.get(-50, 0):+.4f}%")
            logger.info(f"   价格变动 +100bp / -100bp: {pct_price_chg.get(100, 0):+.4f}% / {pct_price_chg.get(-100, 0):+.4f}%")
            logger.info(f"   VaR 历史 95%/99%: {var_hist.get(0.95, 0):.4f}% / {var_hist.get(0.99, 0):.4f}%")
            logger.info(f"   VaR 参数 95%/99%: {var_param.get(0.95, 0):.4f}% / {var_param.get(0.99, 0):.4f}%")
            logger.info(f"   ES 95%/99%:         {es.get(0.95, 0):.4f}% / {es.get(0.99, 0):.4f}%")
            logger.info(f"   lookback_days: {lookback_days}")

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
