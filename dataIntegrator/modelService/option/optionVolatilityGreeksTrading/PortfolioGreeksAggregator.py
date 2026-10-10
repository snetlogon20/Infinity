r"""
期权组合 Greeks 聚合与对冲建议器 (Portfolio Greeks Aggregator + Delta Hedging + P&L Explain)

专业定位:
    Portfolio Greeks Aggregation(持仓组合希腊字母聚合) + 动态 Delta 对冲 +
    P&L Explain(损益归因分解) —— 真金白银下单前后的风控刚需:
        1. 全持仓净 Δ/Γ/V/Θ/Rho 聚合(按 TOTAL / UNDERLYING / MATURITY 三视角)
        2. Delta 对冲建议: 净Δ 用现货/ETF/股指期货对冲, 输出对冲单位数/手数/名义金额
        3. Gamma/Vega 剩余敞口与到期月分布(哪个月集中爆发)
        4. P&L Explain: 用 T-1 日 Greeks 解释 T 日盯市损益
           ΔP&L ≈ Δ·dS + 0.5·Γ·dS² + V·dIV·100 + Θ·dt, 残差=高阶项/数据误差
           覆盖率接近1 = Greeks 线性化解释力好; 残差大 = 报价失真需排查
           (与合成策略的净Vega非零校验一脉相承, 是免费的数据质量监控)

数据流:
    config.positions = [{ts_code, direction(+1买/-1卖), quantity}]
      (或 auto: symbol_filter + ATM straddle 自动构建)
    → tb_tushare_opt_daily_indicator (最新两日 Greeks/行情)
    → tb_option_portfolio_greeks (每行一个分组汇总)

使用:
    config = {
        "name": "50ETF期权组合Greeks监控",
        "end_date": CommonParameters.today,
        "positions": [
            {"ts_code": "10006564", "direction": +1, "quantity": 10},  # 买Call
            {"ts_code": "10006575", "direction": -1, "quantity": 5},   # 卖Put
        ],
        "hedge_instrument": "ETF_LOT",   # SPOT / ETF_LOT / FUTURE
    }
    PortfolioGreeksAggregator().run(config)
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class PortfolioGreeksAggregator:
    """期权组合 Greeks 聚合与对冲建议器"""

    STRATEGY_TYPE = 'PORTFOLIO_GREEKS'
    ANALYSIS_VERSION = 'v1'
    TABLE_INDICATOR = 'tb_tushare_opt_daily_indicator'
    TABLE_BASIC = 'df_tushare_opt_basic'
    TABLE_TARGET = 'tb_option_portfolio_greeks'

    # 对冲工具参数
    ETF_LOT_SIZE = 100.0        # ETF 期权对应现货一手 100 份
    DEFAULT_FUTURE_MULTIPLIER = 300.0  # IH/IF/IM/IC 默认乘数(实际以 config 覆写)

    # 目标表字段(与建表 SQL 逐列对齐)
    TARGET_COLUMNS = [
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        'trade_date', 'trade_date_prev', 'group_type', 'group_key',
        'n_positions', 'sum_long_qty', 'sum_short_qty',
        'net_delta', 'net_gamma', 'net_vega', 'net_theta', 'net_rho',
        'delta_hedge_units', 'delta_hedge_notional_cny', 'hedge_instrument',
        'hedge_contracts',
        'theta_carry_cny', 'net_delta_notional_cny',
        'pnl_observed_cny', 'pnl_delta_cny', 'pnl_gamma_cny', 'pnl_vega_cny',
        'pnl_theta_cny', 'pnl_residual_cny', 'pnl_explain_coverage',
    ]

    STR_COLUMNS = {'strategy_type', 'analysis_params', 'analysis_version',
                   'trade_date', 'trade_date_prev', 'group_type', 'group_key',
                   'hedge_instrument'}

    # ================================================================
    # 持仓解析
    # ================================================================
    def resolve_positions(self, config):
        """解析持仓清单: 显式 positions 优先, 否则按 auto_positions 构建

        auto_positions='ATM_STRADDLE' + symbol_filter:
            最新交易日 ATM(K 最接近 S)的 Call+Put 各买 1 张(买方跨式示例持仓)
        """
        positions = config.get('positions')
        if positions:
            valid = []
            for p in positions:
                ts_code = str(p.get('ts_code', '')).strip()
                direction = float(p.get('direction', 0))
                quantity = float(p.get('quantity', 0))
                if not ts_code or direction not in (+1.0, -1.0) or quantity <= 0:
                    logger.warning(f"跳过无效持仓: {p}")
                    continue
                valid.append({'ts_code': ts_code, 'direction': direction,
                              'quantity': quantity})
            logger.info(f"Positions resolved(explicit): {len(valid)} legs")
            return valid

        if config.get('auto_positions') == 'ATM_STRADDLE':
            return self._build_atm_straddle(
                symbol_filter=config.get('symbol_filter'),
                end_date=config.get('end_date') or CommonParameters.today,
                quantity=float(config.get('auto_quantity', 1)))

        raise ValueError("config 需要提供 positions 列表, "
                         "或 auto_positions='ATM_STRADDLE' + symbol_filter")

    def _build_atm_straddle(self, symbol_filter, end_date, quantity):
        """自动构建 ATM straddle 示例持仓(买 ATM Call + 买 ATM Put)"""
        sql = f"""
        SELECT ts_code, call_put, exercise_price, spot_price, trade_date
        FROM indexsysdb.{self.TABLE_INDICATOR}
        WHERE trade_date = (
            SELECT max(trade_date) FROM indexsysdb.{self.TABLE_INDICATOR}
            WHERE trade_date <= '{end_date}'
        ) AND spot_price > 0 AND exercise_price > 0
        AND ts_code IN (
            SELECT DISTINCT ts_code FROM indexsysdb.{self.TABLE_BASIC}
            WHERE symbol LIKE '{symbol_filter}' OR ts_code LIKE '{symbol_filter}'
        )
        ORDER BY abs(exercise_price - spot_price) ASC
        """
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        if len(df) == 0:
            raise ValueError(f"ATM_STRADDLE: {symbol_filter} 无可用数据")
        df['exercise_price'] = pd.to_numeric(df['exercise_price'], errors='coerce')
        df['spot_price'] = pd.to_numeric(df['spot_price'], errors='coerce')
        df['call_put'] = df['call_put'].astype(str)

        positions = []
        for cp in ('C', 'P'):
            leg = df[df['call_put'] == cp].copy()
            if leg.empty:
                continue
            # SQL 已按 |K-S| 升序, 此处再按距离排序防御返回顺序不稳(取最近K=ATM)
            leg = leg.assign(dist=(leg['exercise_price'] - leg['spot_price']).abs()) \
                .sort_values('dist')
            positions.append({'ts_code': str(leg.iloc[0]['ts_code']),
                              'direction': +1.0, 'quantity': quantity})
        if not positions:
            raise ValueError(f"ATM_STRADDLE: {symbol_filter} 无法配对 C/P 腿")
        logger.info(f"ATM_STRADDLE built: {positions}")
        return positions

    # ================================================================
    # 数据获取: 最新两日 Greeks/行情
    # ================================================================
    def fetch_position_data(self, positions, end_date):
        """拉取每个持仓合约的最新两日指标(T 与 T-1)"""
        codes_str = ",".join(f"'{p['ts_code']}'" for p in positions)
        sql = f"""
        SELECT ind.trade_date, ind.ts_code, ind.call_put, ind.exercise_price,
               ind.opt_multiplier, ind.s_month, ind.maturity_date, ind.spot_price,
               ind.close, ind.implied_vol,
               ind.delta, ind.gamma, ind.theta, ind.vega, ind.rho,
               b.symbol AS symbol
        FROM indexsysdb.{self.TABLE_INDICATOR} ind
        LEFT JOIN (
            SELECT ts_code, any(symbol) AS symbol
            FROM indexsysdb.{self.TABLE_BASIC}
            GROUP BY ts_code
        ) b ON ind.ts_code = b.ts_code
        WHERE ind.trade_date <= '{end_date}'
          AND ind.ts_code IN ({codes_str})
        ORDER BY ind.ts_code ASC, trade_date DESC
        LIMIT 2 BY ts_code
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        if len(df) == 0:
            raise ValueError("持仓合约在 indicator 表中无数据(检查 ts_code/end_date)")
        for col in ['exercise_price', 'opt_multiplier', 'spot_price', 'close',
                    'implied_vol', 'delta', 'gamma', 'theta', 'vega', 'rho']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        for col in ['trade_date', 'ts_code', 'call_put', 's_month', 'maturity_date']:
            df[col] = df[col].fillna('').astype(str)

        missing = [p['ts_code'] for p in positions
                   if p['ts_code'] not in set(df['ts_code'])]
        if missing:
            raise ValueError(f"持仓合约缺行情: {missing}")

        # 拆 T / T-1(每 ts_code 最近1条=T, 次近1条=T-1)
        df = df.sort_values(['ts_code', 'trade_date'], ascending=[True, False])
        rows_t, rows_prev, dates_prev = [], [], {}
        for _, g in df.groupby('ts_code'):
            rows_t.append(g.iloc[0])
            if len(g) >= 2:
                rows_prev.append(g.iloc[1])
                dates_prev[str(g.iloc[0]['ts_code'])] = str(g.iloc[1]['trade_date'])
        df_t = pd.DataFrame(rows_t).reset_index(drop=True)
        df_prev = pd.DataFrame(rows_prev).reset_index(drop=True) if rows_prev \
            else pd.DataFrame(columns=df_t.columns)
        trade_date = str(df_t['trade_date'].iloc[0])
        trade_date_prev = (max(dates_prev.values()) if dates_prev else '')
        logger.info(f"Position data: {len(df_t)} legs @T({trade_date}), "
                    f"{len(df_prev)} legs @T-1({trade_date_prev})")
        return df_t, df_prev, trade_date, trade_date_prev

    # ================================================================
    # 逐持仓计算: 带符号 Greeks + P&L Explain 分量
    # ================================================================
    def _calc_position_metrics(self, df_t, df_prev, positions):
        """逐持仓计算带符号 Greeks(方向x张数x乘数)与 P&L 归因分量"""
        pos_map = {p['ts_code']: p for p in positions}
        df_t = df_t.copy()
        df_t['direction'] = [pos_map[str(c)]['direction'] for c in df_t['ts_code']]
        df_t['quantity'] = [pos_map[str(c)]['quantity'] for c in df_t['ts_code']]
        sign = df_t['direction'] * df_t['quantity'] * df_t['opt_multiplier']

        df_t['underlying_key'] = [
            (str(s)[:6] if len(str(s) or '') >= 6 and str(s)[:6].isdigit()
             else str(t)[:2] if len(str(t) or '') >= 2 and str(t)[:2].isalpha()
             else (str(s) or str(t)))
            for s, t in zip(df_t.get('symbol', ''), df_t['ts_code'])]

        for g in ('delta', 'gamma', 'vega', 'theta', 'rho'):
            df_t[f'signed_{g}'] = sign * df_t[g]

        # ---- P&L Explain(T-1 日 Greeks 解释 T 日损益) ----
        for comp in ['pnl_observed', 'pnl_delta', 'pnl_gamma', 'pnl_vega',
                     'pnl_theta', 'pnl_residual']:
            df_t[comp] = np.nan

        if len(df_prev) > 0:
            prev_idx = df_prev.set_index('ts_code')
            pnl_obs, pnl_d, pnl_g, pnl_v, pnl_th = [], [], [], [], []
            for _, r in df_t.iterrows():
                code = str(r['ts_code'])
                if code not in prev_idx.index:
                    pnl_obs.append(np.nan); pnl_d.append(np.nan)
                    pnl_g.append(np.nan); pnl_v.append(np.nan)
                    pnl_th.append(np.nan)
                    continue
                p = prev_idx.loc[code]
                dS = float(r['spot_price']) - float(p['spot_price'])
                dIV = (float(r['implied_vol']) - float(p['implied_vol'])) * 100.0
                dt_days = 1.0
                try:
                    dt_days = max((datetime.strptime(str(r['trade_date']), '%Y%m%d')
                                   - datetime.strptime(str(p['trade_date']), '%Y%m%d')
                                   ).days, 1)
                except Exception:
                    pass
                s = float(r['direction']) * float(r['quantity']) * float(r['opt_multiplier'])
                obs = s * (float(r['close']) - float(p['close']))
                d = s * float(p['delta']) * dS
                g = 0.5 * s * float(p['gamma']) * dS * dS
                v = s * float(p['vega']) * dIV
                th = s * float(p['theta']) * dt_days
                pnl_obs.append(obs); pnl_d.append(d); pnl_g.append(g)
                pnl_v.append(v); pnl_th.append(th)
            df_t['pnl_observed'] = pnl_obs
            df_t['pnl_delta'] = pnl_d
            df_t['pnl_gamma'] = pnl_g
            df_t['pnl_vega'] = pnl_v
            df_t['pnl_theta'] = pnl_th
            df_t['pnl_residual'] = (df_t['pnl_observed']
                                    - df_t[['pnl_delta', 'pnl_gamma', 'pnl_vega',
                                            'pnl_theta']].sum(axis=1))
        return df_t

    # ================================================================
    # 聚合: TOTAL / UNDERLYING / MATURITY
    # ================================================================
    def _aggregate(self, df_t, trade_date, trade_date_prev, hedge_instrument,
                   future_multiplier):
        """按三视角聚合净 Greeks + 对冲建议 + P&L 归因"""
        rows = []

        def _agg_group(g, group_type, group_key):
            net_d = g['signed_delta'].sum()
            net_g = g['signed_gamma'].sum()
            net_v = g['signed_vega'].sum()
            net_th = g['signed_theta'].sum()
            net_r = g['signed_rho'].sum()
            spot = float(g['spot_price'].iloc[0]) if len(g) else np.nan

            # 对冲建议(UNDERLYING 行: 净Δ 用对应标的对冲)
            hedge_units = -net_d if pd.notna(net_d) else np.nan
            hedge_notional = abs(net_d) * spot if pd.notna(net_d) and spot > 0 else np.nan
            if hedge_instrument == 'ETF_LOT':
                hedge_contracts = hedge_units / self.ETF_LOT_SIZE \
                    if pd.notna(hedge_units) else np.nan
            elif hedge_instrument == 'FUTURE':
                hedge_contracts = (hedge_notional / (future_multiplier * spot)) \
                    if (pd.notna(hedge_notional) and spot > 0) else np.nan
            else:
                hedge_contracts = hedge_units

            pnl_obs = g['pnl_observed'].sum()
            pnl_d = g['pnl_delta'].sum()
            pnl_g = g['pnl_gamma'].sum()
            pnl_v = g['pnl_vega'].sum()
            pnl_th = g['pnl_theta'].sum()
            residual = pnl_obs - (pnl_d + pnl_g + pnl_v + pnl_th)
            with np.errstate(invalid='ignore', divide='ignore'):
                coverage = 1.0 - abs(residual / pnl_obs) \
                    if pnl_obs not in (0, np.nan) and pd.notna(pnl_obs) else np.nan

            return {
                'group_type': group_type, 'group_key': group_key,
                'n_positions': len(g),
                'sum_long_qty': float(g[g['direction'] > 0]['quantity'].sum()),
                'sum_short_qty': float(g[g['direction'] < 0]['quantity'].sum()),
                'net_delta': net_d, 'net_gamma': net_g, 'net_vega': net_v,
                'net_theta': net_th, 'net_rho': net_r,
                'delta_hedge_units': hedge_units,
                'delta_hedge_notional_cny': hedge_notional,
                'hedge_instrument': hedge_instrument,
                'hedge_contracts': hedge_contracts,
                'theta_carry_cny': net_th,
                'net_delta_notional_cny': net_d * spot if spot > 0 else np.nan,
                'pnl_observed_cny': pnl_obs, 'pnl_delta_cny': pnl_d,
                'pnl_gamma_cny': pnl_g, 'pnl_vega_cny': pnl_v, 'pnl_theta_cny': pnl_th,
                'pnl_residual_cny': residual,
                'pnl_explain_coverage': coverage,
            }

        base = {'trade_date': trade_date, 'trade_date_prev': trade_date_prev}

        # TOTAL
        rows.append({**base, **_agg_group(df_t, 'TOTAL', 'TOTAL')})
        # UNDERLYING
        for key, g in df_t.groupby('underlying_key'):
            rows.append({**base, **_agg_group(g, 'UNDERLYING', str(key))})
        # MATURITY
        for key, g in df_t.groupby('s_month'):
            rows.append({**base, **_agg_group(g, 'MATURITY', str(key))})

        return pd.DataFrame(rows)

    # ================================================================
    # 落库
    # ================================================================
    def save_to_clickhouse(self, df, config, trade_date):
        if len(df) == 0:
            logger.warning("Empty aggregation, nothing to save")
            return
        logger.info(f"Saving {len(df)} group rows to {self.TABLE_TARGET}")
        df = df.copy()
        df['strategy_type'] = self.STRATEGY_TYPE
        df['analysis_time'] = datetime.now().replace(microsecond=0)
        df['analysis_params'] = json.dumps(config, ensure_ascii=False, default=str)
        df['analysis_version'] = self.ANALYSIS_VERSION

        available_cols = [c for c in self.TARGET_COLUMNS if c in df.columns]
        df_output = df[available_cols].copy()
        for col in df_output.columns:
            if col == 'analysis_time':
                continue
            if col in self.STR_COLUMNS:
                df_output[col] = df_output[col].fillna('').astype(str)
            elif col == 'n_positions':
                df_output[col] = pd.to_numeric(
                    df_output[col], errors='coerce').fillna(0).astype(int)
            else:
                df_output[col] = pd.to_numeric(df_output[col], errors='coerce')
                df_output[col] = df_output[col].where(pd.notna(df_output[col]), None)

        del_sql = (f"ALTER TABLE indexsysdb.{self.TABLE_TARGET} DELETE WHERE "
                   f"strategy_type = '{self.STRATEGY_TYPE}' "
                   f"AND trade_date = '{trade_date}'")
        logger.info(f"SQL:\n{del_sql}")
        ClickhouseService.execute_sql(del_sql)
        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=df_output, table_name=self.TABLE_TARGET, database='indexsysdb')
        logger.info(f"Saved {len(df_output)} rows to {self.TABLE_TARGET}")
        return df_output

    # ================================================================
    # 主流程
    # ================================================================
    def run(self, config):
        """主流程: 解析持仓 → 拉最新两日数据 → 逐持仓Greeks/归因 → 聚合 → 落库

        Args:
            config: name / end_date / positions(或 auto_positions) /
                    hedge_instrument(SPOT|ETF_LOT|FUTURE) / future_multiplier
        """
        name = config.get('name', 'Unknown')
        end_date = config.get('end_date') or CommonParameters.today
        hedge_instrument = config.get('hedge_instrument', 'SPOT')
        future_multiplier = float(config.get('future_multiplier',
                                             self.DEFAULT_FUTURE_MULTIPLIER))

        logger.info("\n" + "=" * 80)
        logger.info(f"{self.__class__.__name__}.run: {name}")
        logger.info(f"  end_date={end_date}, hedge={hedge_instrument}")
        logger.info("=" * 80)

        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionStrategyAnalysis',
                             params={'report_name': name, 'end_date': end_date})
        try:
            # Step 1: 持仓解析
            logger.info("\nStep 1/5: Resolving positions...")
            positions = self.resolve_positions(config)
            if not positions:
                raise ValueError("No valid positions")

            # Step 2: 最新两日数据
            logger.info("\nStep 2/5: Fetching latest 2-day Greeks...")
            df_t, df_prev, trade_date, trade_date_prev = \
                self.fetch_position_data(positions, end_date)

            # Step 3: 逐持仓带符号 Greeks + P&L 归因
            logger.info("\nStep 3/5: Calculating signed Greeks & P&L explain...")
            df_t = self._calc_position_metrics(df_t, df_prev, positions)

            # Step 4: 聚合 + 对冲
            logger.info("\nStep 4/5: Aggregating (TOTAL/UNDERLYING/MATURITY)...")
            df_out = self._aggregate(df_t, trade_date, trade_date_prev,
                                     hedge_instrument, future_multiplier)
            total = df_out[df_out['group_type'] == 'TOTAL'].iloc[0]
            logger.info(f"  TOTAL: netΔ={total['net_delta']:+.2f}, "
                        f"netΓ={total['net_gamma']:+.4g}, "
                        f"netV={total['net_vega']:+.4g}, "
                        f"netΘ={total['net_theta']:+.4g}/day, "
                        f"hedge={total['delta_hedge_units']:+.2f} units")

            # Step 5: 落库
            logger.info("\nStep 5/5: Saving to ClickHouse...")
            self.save_to_clickhouse(df_out, config, trade_date)

            # 持仓明细附在返回值上(报告端复用)
            df_out.attrs['positions_detail'] = df_t
            logger.info(f"\n{'='*80}")
            logger.info(f"[{name}] Portfolio Greeks done: "
                        f"{len(df_out)} group rows -> {self.TABLE_TARGET}")
            logger.info(f"{'='*80}")
            job_logger.end_job_success(records_processed=len(df_out))
            return df_out

        except Exception as e:
            import traceback
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise
