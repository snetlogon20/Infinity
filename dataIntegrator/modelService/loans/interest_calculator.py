"""
InterestCalculator
~~~~~~~~~~~~~~~~~~

利息计算核心类。

职责边界：**只算利息，不管本金怎么还**。
- 接收"当期剩余本金"，不关心等额本息还是等额本金
- 对调用方开放：月利率换算、单期利息、累计利息、总成本汇总
- 对内部维护：输入归一化、参数校验、分段利率表

设计约定
--------
1. 金额一律用 ``decimal.Decimal``，禁止 float，避免长周期误差累积。
2. 利率内部统一为"百分比数值"形态（如 4.9 表示 4.9%），
   对外同时接受 ``4.9`` 与 ``0.049`` 两种写法，内部归一化。
3. 月利率 = 年利率 / 12；当输入为百分比数值时，
   单期利息 = 余额 × 年利率 / 1200。
4. 支持分段利率：通过 ``set_rate_schedule()`` 为指定期次
   指定不同年利率，用于 LPR 重定价等场景。
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional, Sequence, Tuple, Union

from dataIntegrator.modelService.loans.Interest_summary import InterestSummary
from dataIntegrator.modelService.loans.class_alias import RateInput, RateMode, _PERCENT_THRESHOLD, Money
from dataIntegrator.modelService.loans.rate_schedule_entry import RateScheduleEntry

logger = logging.getLogger(__name__)


# ===========================================================================
# 还款方式常量（枚举替代）
# ===========================================================================


class RepaymentMode:
    """还款方式常量。"""

    ANNUITY = "ANNUITY"                    # 等额本息
    EQUAL_PRINCIPAL = "EQUAL_PRINCIPAL"    # 等额本金

    @classmethod
    def all(cls) -> Tuple[str, ...]:
        return (cls.ANNUITY, cls.EQUAL_PRINCIPAL)


# ===========================================================================
# 单期还款明细（输出用的数据结构）
# ===========================================================================


@dataclass
class AmortizationPeriod:
    """某一期的还款明细：适用利率 + 本金 + 利息 + 余额。"""

    period: int
    payment_date: Optional[date]
    annual_rate: Decimal        # 当期实际适用的年化百分比利率
    beginning_balance: Decimal
    installment: Decimal        # 当期还款总额 = 本金 + 利息
    principal: Decimal          # 当期偿还本金
    interest: Decimal           # 当期利息
    ending_balance: Decimal     # 期末剩余本金

    def as_dict(self) -> Dict[str, object]:
        return {
            "period": self.period,
            "payment_date": str(self.payment_date) if self.payment_date else None,
            "annual_rate": str(self.annual_rate),
            "beginning_balance": str(self.beginning_balance),
            "installment": str(self.installment),
            "principal": str(self.principal),
            "interest": str(self.interest),
            "ending_balance": str(self.ending_balance),
        }


# ===========================================================================
# 主类
# ===========================================================================


class InterestCalculator:
    """利息计算器。

    Parameters
    ----------
    principal : RateInput
        贷款本金。
    annual_rate : RateInput
        年化利率。接受 ``4.9``（百分比）或 ``0.049``（小数）两种写法。
    periods : int
        总还款期数（月）。
    rate_mode : RateMode, optional
        利率模式，默认 ``FIXED``。
    start_date : date | str, optional
        起息日（本金开始计息的日期）。用于 :meth:`build_schedule`
        自动生成每期还款日；可传 ``date`` 或 ``"2026-11-01"`` 这样的 ISO 字符串。
    """

    #: 金额与利率计算保留的小数位数
    PRECISION = 28
    #: 输出金额默认量化到几位小数（分）
    OUTPUT_QUANTIZE = Decimal("0.01")

    def __init__(
        self,
        principal: RateInput,
        annual_rate: RateInput,
        periods: int,
        rate_mode: RateMode = RateMode.FIXED,
        start_date: Optional[Union[date, str]] = None,
    ) -> None:
        self._principal = self._to_decimal(principal)
        self._annual_rate = self.normalize_rate_input(annual_rate)
        self._periods = int(periods)
        self._rate_mode = rate_mode
        self._start_date = self._to_date(start_date)
        self._rate_schedule: Dict[int, Decimal] = {}
        self._schedule_cache: Optional[Sequence["_PeriodStub"]] = None

        self.validate()

        if self._rate_mode == RateMode.FLOATING and not self._rate_schedule:
            # 浮动利率但没给分段表时，用初始年利率填满全期
            self._rate_schedule[1] = self._annual_rate

        logger.info(
            "InterestCalculator 初始化输入: principal=%s annual_rate=%s%% "
            "periods=%s rate_mode=%s start_date=%s",
            self._principal,
            self._annual_rate,
            self._periods,
            self._rate_mode,
            self._start_date,
        )

    # ------------------------------------------------------------------
    # 构造与校验
    # ------------------------------------------------------------------

    @staticmethod
    def _to_decimal(value: RateInput) -> Decimal:
        """将任意合法数值输入转为 Decimal。"""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, bool):  # bool 是 int 的子类，需单独排除
            raise TypeError("不接受 bool 类型")
        try:
            return Decimal(str(value))
        except Exception as exc:  # noqa: BLE001
            raise TypeError(f"无法转为 Decimal: {value!r}") from exc

    @staticmethod
    def _to_date(value: Optional[Union[date, str]]) -> Optional[date]:
        """将起息日归一化为 ``date``；接受 ``date`` 或 ISO 字符串（如 ``"2026-11-01"``）。"""
        if value is None or isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value)
        raise TypeError(f"无法转为 date: {value!r}")

    def normalize_rate_input(self, rate: RateInput) -> Decimal:
        """归一化利率输入。

        - 传入 ``4.9`` / ``"4.9"`` 视为百分比数值，原样返回。
        - 传入 ``0.049`` / ``0.049`` 视为小数形态，乘 100 后返回 ``4.9``。
        - 传入负值或零一律报错。

        判定规则：值 **小于** ``_PERCENT_THRESHOLD``（默认 1）视为小数形态，
        等于或大于 1 视为百分比数值。因此传入 ``1`` 会正确理解为 1%。
        """
        value = self._to_decimal(rate).normalize()
        if value < 0:
            raise ValueError("利率不能为负")
        if value == 0:
            return Decimal("0")
        if value < _PERCENT_THRESHOLD:
            value = (value * Decimal("100")).normalize()
        return value

    def validate(self) -> None:
        """校验全部入参，不通过立即抛异常。"""
        if self._principal <= 0:
            raise ValueError("本金必须大于 0")
        if self._annual_rate < 0:
            raise ValueError("利率不能为负")
        if self._periods <= 0:
            raise ValueError("期数必须为正整数")
        if self._rate_mode not in RateMode.all():
            raise ValueError(f"不支持的利率模式: {self._rate_mode}")

    # ------------------------------------------------------------------
    # 利率相关
    # ------------------------------------------------------------------

    @property
    def principal(self) -> Money:
        return self._principal

    @property
    def annual_rate(self) -> Decimal:
        """归一化后的年化**百分比**数值。"""
        return self._annual_rate

    @property
    def periods(self) -> int:
        return self._periods

    @property
    def rate_mode(self) -> RateMode:
        return self._rate_mode

    @property
    def start_date(self) -> Optional[date]:
        """起息日（可能为 ``None``）。"""
        return self._start_date

    def monthly_rate(self) -> Decimal:
        """月利率（小数形态，如 0.0040833...）。"""
        return (self._annual_rate / Decimal("100") / Decimal("12")).normalize()

    def period_rate(self) -> Decimal:
        """每个还款周期的利率。

        按"月供月付"约定，等同于 :meth:`monthly_rate`。
        保留此方法是为了在季付 / 年付扩展时只改这里。
        """
        return self.monthly_rate()

    def rate_for_period(self, period_index: int) -> Decimal:
        """返回指定期次对应的年化**百分比**数值利率。

        - 固定利率：始终返回初始年利率。
        - 浮动利率：查分段表，取覆盖该期次的第一条记录。
        """
        if period_index < 1 or period_index > self._periods:
            raise IndexError(f"期次越界: {period_index}，有效范围 1~{self._periods}")

        if self._rate_mode == RateMode.FIXED:
            result = self._annual_rate
        else:
            # 浮动利率：遍历已排序的分段表，取最后一个 start <= period 的条目
            effective_rate: Optional[Decimal] = None
            for start_period, rate in sorted(self._rate_schedule.items()):
                if start_period <= period_index:
                    effective_rate = rate
                else:
                    break
            result = (
                effective_rate if effective_rate is not None else self._annual_rate
            )

        logger.debug(
            "rate_for_period 输入期次=%s -> 年利率=%s%% (mode=%s)",
            period_index,
            result,
            self._rate_mode,
        )
        return result

    def set_rate_schedule(
        self, entries: Sequence[RateScheduleEntry]
    ) -> None:
        """设置分段利率表（仅浮动利率模式有效）。

        参数
        ----
        entries : 序列 of RateScheduleEntry
            分段记录。``start_period`` 必须递增且不重复。
        """
        if self._rate_mode != RateMode.FLOATING:
            raise RuntimeError("仅 FLOATING 模式可设置分段利率表")

        self._rate_schedule.clear()
        last_start = -1
        for entry in entries:
            if entry.start_period <= last_start:
                raise ValueError("分段记录的 start_period 必须严格递增")
            last_start = entry.start_period
            self._rate_schedule[entry.start_period] = self.normalize_rate_input(
                entry.annual_rate
            )

        logger.info(
            "set_rate_schedule 完成: 分段表={%s}",
            ", ".join(
                f"{k}: {v}%" for k, v in sorted(self._rate_schedule.items())
            ),
        )

    # ------------------------------------------------------------------
    # 核心：利息计算
    # ------------------------------------------------------------------

    def interest_for_period(
        self,
        balance: RateInput,
        period_index: int,
        annual_rate: Optional[RateInput] = None,
    ) -> Money:
        """计算某一期应计利息。

        Parameters
        ----------
        balance : Decimal | float | int | str
            该期**期初**剩余本金。
        period_index : int
            期次（1-based）。用于浮动利率查分段表。
        annual_rate : RateInput, optional
            可选覆盖利率（百分比数值）。若给定，忽略分段表直接用它算。
            用于提前还款后临时调整等场景。

        Returns
        -------
        Decimal
            当期利息，精度保留到 ``PRECISION`` 位。
        """
        bal = self._to_decimal(balance)
        if bal < 0:
            raise ValueError("剩余本金不能为负")

        if annual_rate is not None:
            rate_pct = self.normalize_rate_input(annual_rate)
        else:
            rate_pct = self.rate_for_period(period_index)

        # 单期利息 = 期初余额 × 年化百分比 / 1200
        interest = bal * rate_pct / Decimal("1200")
        result = interest.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP).normalize()
        logger.info(
            "interest_for_period 输入 balance=%s period_index=%s rate=%s%% -> 利息=%s",
            bal,
            period_index,
            rate_pct,
            result,
        )
        return result

    def total_interest(
        self,
        schedule: Sequence[object],
        interest_attr: str = "interest",
    ) -> Money:
        """汇总某份还款计划表的全部利息。

        Parameters
        ----------
        schedule : 序列
            还款计划表，元素需有 ``interest`` 属性或可下标取值。
        interest_attr : str, optional
            利息字段名，默认 ``"interest"``。
        """
        total = Decimal("0")
        for period in schedule:
            value = getattr(period, interest_attr, None)
            if value is None and hasattr(period, "__getitem__"):
                value = period[interest_attr]
            if value is None:
                raise AttributeError(
                    f"计划表元素缺少字段 {interest_attr!r}"
                )
            total += self._to_decimal(value)
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def interest_to_date(
        self,
        schedule: Sequence[object],
        as_of: date,
        payment_date_attr: str = "payment_date",
        interest_attr: str = "interest",
    ) -> Money:
        """按还款日累计到指定日期的利息。

        规则：还款日早于（或等于）``as_of`` 的期次计入，其余不计。
        """
        total = Decimal("0")
        for period in schedule:
            pd = getattr(period, payment_date_attr, None)
            if pd is None:
                raise AttributeError(
                    f"计划表元素缺少字段 {payment_date_attr!r}"
                )
            if pd <= as_of:
                total += self._to_decimal(getattr(period, interest_attr))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def summarize(
        self,
        schedule: Sequence[object],
        interest_attr: str = "interest",
        principal_attr: str = "principal",
    ) -> InterestSummary:
        """汇总一份还款计划表的利息与成本信息。"""
        total_interest = Decimal("0")
        total_principal = Decimal("0")
        for period in schedule:
            total_interest += self._to_decimal(getattr(period, interest_attr))
            total_principal += self._to_decimal(getattr(period, principal_attr))

        total_payment = total_principal + total_interest
        ratio = (
            (total_interest / total_principal).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            if total_principal > 0
            else Decimal("0")
        )

        return InterestSummary(
            total_interest=total_interest.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            principal=total_principal.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            total_payment=total_payment.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            interest_ratio=ratio,
        )

    # ------------------------------------------------------------------
    # 生成完整还款计划表：输入快照 + 每期(本金, 利息)列表 + 表格输出
    # ------------------------------------------------------------------

    def input_snapshot(self) -> Dict[str, object]:
        """返回本次计算的全部输入，便于核对。"""
        return {
            "principal": self._principal,
            "annual_rate(%)": self._annual_rate,
            "periods": self._periods,
            "rate_mode": self._rate_mode,
            "start_date": str(self._start_date) if self._start_date else None,
            "monthly_rate": self.monthly_rate(),
            "rate_schedule": {
                k: str(v) for k, v in sorted(self._rate_schedule.items())
            },
        }

    def build_schedule(
        self,
        repayment_mode: str = RepaymentMode.ANNUITY,
        start_date: Optional[Union[date, str]] = None,
        quant: Decimal = Decimal("0.01"),
    ) -> List[AmortizationPeriod]:
        """生成"每期本金 + 利息"的完整还款计划表。

        Parameters
        ----------
        repayment_mode : str
            ``ANNUITY`` 等额本息 / ``EQUAL_PRINCIPAL`` 等额本金。
        start_date : date | str, optional
            起息日（本金开始计息日）。给定后据此逐月顺延生成各期还款日；
            缺省时沿用构造时设置的 :attr:`start_date`；两者都为空则不生成还款日。
        quant : Decimal
            金额量化精度，默认到分（0.01）。

        约定：
        - 浮动利率模式下，每期利率通过 :meth:`rate_for_period` 查分段表，
          等额本息会按"剩余本金·剩余期数·当期利率"逐期反推月供，
          固定利率时各期月供保持恒定。
        - 末期一次性清偿剩余本金，吸收全程四舍五入残差，保证本金归零。
        """
        if repayment_mode not in RepaymentMode.all():
            raise ValueError(f"不支持的还款方式: {repayment_mode}")

        logger.info(
            "build_schedule 输入: %s | repayment_mode=%s",
            self.input_snapshot(),
            repayment_mode,
        )

        effective_start = (
            self._to_date(start_date)
            if start_date is not None
            else self._start_date
        )

        rows: List[AmortizationPeriod] = []
        n = self._periods
        balance = self._principal

        base_principal: Optional[Decimal] = None
        if repayment_mode == RepaymentMode.EQUAL_PRINCIPAL:
            base_principal = (self._principal / Decimal(n)).quantize(
                quant, rounding=ROUND_HALF_UP
            )

        for p in range(1, n + 1):
            annual_pct = self.rate_for_period(p)
            r = annual_pct / Decimal("100") / Decimal("12")
            beginning = balance
            interest = (beginning * r).quantize(quant, rounding=ROUND_HALF_UP)

            if p == n:
                princ = beginning.quantize(quant, rounding=ROUND_HALF_UP)
            elif repayment_mode == RepaymentMode.EQUAL_PRINCIPAL:
                princ = base_principal
            else:  # ANNUITY
                remaining = n - p + 1
                if r == 0:
                    princ = (beginning / Decimal(remaining)).quantize(
                        quant, rounding=ROUND_HALF_UP
                    )
                else:
                    factor = (Decimal(1) + r) ** remaining
                    installment = beginning * r * factor / (factor - Decimal(1))
                    princ = (
                        installment.quantize(quant, rounding=ROUND_HALF_UP)
                        - interest
                    )

            princ = princ.quantize(quant, rounding=ROUND_HALF_UP)
            installment = (princ + interest).quantize(quant, rounding=ROUND_HALF_UP)
            ending = (beginning - princ).quantize(quant, rounding=ROUND_HALF_UP)
            if ending < 0:
                ending = Decimal("0")

            payment_date = (
                self._add_month(effective_start, p)
                if effective_start is not None
                else None
            )
            rows.append(
                AmortizationPeriod(
                    period=p,
                    payment_date=payment_date,
                    annual_rate=annual_pct,
                    beginning_balance=beginning.quantize(
                        quant, rounding=ROUND_HALF_UP
                    ),
                    installment=installment,
                    principal=princ,
                    interest=interest,
                    ending_balance=ending,
                )
            )
            balance = ending
            logger.debug(
                "期次 %s: 年利率=%s%% 期初=%s 月供=%s 本金=%s 利息=%s 期末=%s",
                p,
                annual_pct,
                beginning,
                installment,
                princ,
                interest,
                ending,
            )

        total_principal = sum((r.principal for r in rows), Decimal("0"))
        total_interest = sum((r.interest for r in rows), Decimal("0"))
        logger.info(
            "build_schedule 输出: 期数=%s 本金合计=%s 利息合计=%s",
            len(rows),
            total_principal,
            total_interest,
        )
        logger.info(
            "本金+利息列表(前 %s 期 [期次, 年利率, 本金, 利息]): %s",
            min(12, len(rows)),
            [
                (r.period, str(r.annual_rate), str(r.principal), str(r.interest))
                for r in rows[:12]
            ],
        )
        return rows

    @staticmethod
    def _add_month(day: date, months: int) -> date:
        """从 ``day`` 起顺延 ``months`` 个月，自动处理月末（如 1/31 -> 2/28）。"""
        total = day.month - 1 + months
        year = day.year + total // 12
        month = total % 12 + 1
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(day.day, last_day))

    @staticmethod
    def format_schedule(rows: Sequence[AmortizationPeriod]) -> str:
        """把还款计划表排成对齐的文本表格，方便直接查看每期数据。"""
        header = (
            f"{'期次':>4} {'还款日':<12} {'年利率%':>8} {'期初本金':>16} "
            f"{'月供':>14} {'本金':>14} {'利息':>14} {'期末本金':>16}"
        )
        lines = [header]
        for row in rows:
            lines.append(
                f"{row.period:>4} {str(row.payment_date or '-'):<12} "
                f"{row.annual_rate:>8,.2f} "
                f"{row.beginning_balance:>16,.2f} {row.installment:>14,.2f} "
                f"{row.principal:>14,.2f} {row.interest:>14,.2f} "
                f"{row.ending_balance:>16,.2f}"
            )
        return "\n".join(lines)

    @staticmethod
    def to_dataframe(rows: Sequence[AmortizationPeriod]):
        """把 :meth:`build_schedule` 生成的计划表转成 ``pandas.DataFrame``。

        - 惰性导入 pandas，保证核心计算模块不强依赖 pandas。
        - 金额列保留 ``Decimal``，``payment_date`` 保留 ``datetime.date``，
          便于后续再做汇总、导出或绘图。
        """
        import pandas as pd
        pd.set_option('display.max_columns', None)  # 显示所有列
        pd.set_option('display.width', None)  # 不限制显示宽度
        pd.set_option('display.max_colwidth', None)  # 不限制列宽

        data = [
            {
                "period": r.period,
                "payment_date": r.payment_date,
                "annual_rate": r.annual_rate,
                "beginning_balance": r.beginning_balance,
                "installment": r.installment,
                "principal": r.principal,
                "interest": r.interest,
                "ending_balance": r.ending_balance,
            }
            for r in rows
        ]
        return pd.DataFrame(data)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def quantize_money(value: RateInput) -> Money:
        """把金额量化到分（四舍五入），用于对外展示。"""
        return Decimal(str(value)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # ------------------------------------------------------------------
    # 魔术方法
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"InterestCalculator(principal={self._principal}, "
            f"annual_rate={self._annual_rate}%, periods={self._periods}, "
            f"rate_mode={self._rate_mode})"
        )


# ===========================================================================
# 内部辅助（用于测试与解耦）
# ===========================================================================


class _PeriodStub:
    """测试用最小期次对象，模拟真实 Period dataclass。"""

    __slots__ = ("period", "payment_date", "principal", "interest", "balance")

    def __init__(
        self,
        period: int,
        payment_date: date,
        principal: Decimal,
        interest: Decimal,
        balance: Decimal,
    ) -> None:
        self.period = period
        self.payment_date = payment_date
        self.principal = principal
        self.interest = interest
        self.balance = balance

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"_PeriodStub(p={self.period}, "
            f"principal={self.principal}, interest={self.interest})"
        )
