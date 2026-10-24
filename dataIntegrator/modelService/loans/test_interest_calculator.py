"""
InterestCalculator 单元测试
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

校验维度
--------
1. 构造与输入归一化：百分比 / 小数两种写法、类型转换、校验拒绝非法值
2. 月利率换算：与手工算式精确比对
3. 单期利息：基准值、四舍五入精度、余额为零、余额为负
4. 固定利率模式：全期利率一致
5. 浮动利率 + 分段表：按期次命中不同利率、越界查表、期次越界
6. 汇总方法：总利息、按日期累计、InterestSummary 各字段
7. 边界与异常：零利率、大本金、极值四舍五入、bool 被拒

运行
----
    cd /data/workspace
    pytest test_interest_calculator.py -v
"""

from __future__ import annotations

from datetime import date

import pytest

from dataIntegrator.modelService.loans.interest_calculator import (
    InterestCalculator,
    InterestSummary,
    RateMode,
    RateScheduleEntry,
    RepaymentMode,
    _PeriodStub,
)

# 测试约定：所有金额比较使用 Decimal 精确匹配，量化到 0.01
D = "0.01"


# ===========================================================================
# 1. 构造与输入归一化
# ===========================================================================


class TestConstruction:
    def test_basic_construction(self):
        calc = InterestCalculator(
            principal="1000000", annual_rate="4.9", periods=360
        )
        assert calc.principal == 1000000
        assert calc.annual_rate == Decimal("4.9")
        assert calc.periods == 360
        assert calc.rate_mode == RateMode.FIXED

    def test_rate_input_as_percent(self):
        """传入 4.9（百分比数值）应原样保留。"""
        calc = InterestCalculator(100000, 4.9, 120)
        assert calc.annual_rate == Decimal("4.9")

    def test_rate_input_as_decimal_fraction(self):
        """传入 0.049（小数形态）应归一化为 4.9。"""
        calc = InterestCalculator(100000, 0.049, 120)
        assert calc.annual_rate == Decimal("4.9")

    def test_rate_input_as_string(self):
        calc = InterestCalculator("500000", "3.85", 240)
        assert calc.annual_rate == Decimal("3.85")
        assert calc.principal == 500000

    def test_rate_input_exactly_one_is_treated_as_percent(self):
        """边界：等于阈值的 1 视为百分比数值。"""
        calc = InterestCalculator(100000, 1, 12)
        assert calc.annual_rate == Decimal("1")

    def test_zero_rate_allowed(self):
        """零利率合法，后续计算利息应全为 0。"""
        calc = InterestCalculator(100000, 0, 12)
        assert calc.annual_rate == 0

    def test_repr_format(self):
        calc = InterestCalculator(100000, 4.9, 360)
        text = repr(calc)
        assert "annual_rate=4.9%" in text
        assert "periods=360" in text


# ===========================================================================
# 2. 校验拒绝非法值
# ===========================================================================


class TestValidation:
    def test_negative_principal_rejected(self):
        with pytest.raises(ValueError, match="本金"):
            InterestCalculator(-100000, 4.9, 360)

    def test_zero_principal_rejected(self):
        with pytest.raises(ValueError, match="本金"):
            InterestCalculator(0, 4.9, 360)

    def test_negative_rate_rejected(self):
        with pytest.raises(ValueError, match="利率"):
            InterestCalculator(100000, -1.5, 360)

    def test_zero_periods_rejected(self):
        with pytest.raises(ValueError, match="期数"):
            InterestCalculator(100000, 4.9, 0)

    def test_negative_periods_rejected(self):
        with pytest.raises(ValueError, match="期数"):
            InterestCalculator(100000, 4.9, -12)

    def test_invalid_rate_mode_rejected(self):
        with pytest.raises(ValueError, match="不支持"):
            InterestCalculator(100000, 4.9, 360, rate_mode="UNKNOWN")

    def test_bool_input_rejected(self):
        """bool 是 int 子类，必须被显式排除。"""
        with pytest.raises(TypeError):
            InterestCalculator(True, 4.9, 360)

    def test_non_numeric_input_rejected(self):
        with pytest.raises(TypeError):
            InterestCalculator("not-a-number", 4.9, 360)


# ===========================================================================
# 3. 月利率换算
# ===========================================================================


class TestMonthlyRate:
    def test_standard_rate(self):
        calc = InterestCalculator(100000, 4.9, 360)
        # 4.9% / 12 = 0.408333...%
        assert calc.monthly_rate() == Decimal("4.9") / 100 / 12

    def test_zero_rate(self):
        calc = InterestCalculator(100000, 0, 12)
        assert calc.monthly_rate() == 0

    def test_high_rate(self):
        calc = InterestCalculator(100000, 18.0, 60)
        assert calc.monthly_rate() == Decimal("18") / 100 / 12

    def test_period_rate_matches_monthly(self):
        """period_rate 在月付约定下应与 monthly_rate 一致。"""
        calc = InterestCalculator(100000, 5.88, 240)
        assert calc.period_rate() == calc.monthly_rate()


# ===========================================================================
# 4. 单期利息
# ===========================================================================


class TestInterestForPeriod:
    def test_basic_interest(self):
        """100000 元，年利率 4.9%，第一期利息 = 100000 × 4.9 / 1200"""
        calc = InterestCalculator(100000, 4.9, 360)
        interest = calc.interest_for_period(100000, 1)
        assert interest == Decimal("408.33333333")  # 保留 8 位内部精度

    def test_interest_quantize_to_fen(self):
        """对外展示时量化到分。"""
        calc = InterestCalculator(100000, 4.9, 360)
        interest = calc.interest_for_period(100000, 1)
        assert calc.quantize_money(interest) == Decimal("408.33")

    def test_interest_scales_with_balance(self):
        calc = InterestCalculator(100000, 4.9, 360)
        # 余额减半，利息应减半
        half = calc.interest_for_period(50000, 1)
        full = calc.interest_for_period(100000, 1)
        assert calc.quantize_money(half * 2) == calc.quantize_money(full)

    def test_zero_balance_yields_zero_interest(self):
        calc = InterestCalculator(100000, 4.9, 360)
        assert calc.interest_for_period(0, 1) == 0

    def test_zero_rate_yields_zero_interest(self):
        calc = InterestCalculator(100000, 0, 12)
        assert calc.interest_for_period(100000, 1) == 0

    def test_negative_balance_rejected(self):
        calc = InterestCalculator(100000, 4.9, 360)
        with pytest.raises(ValueError, match="剩余本金"):
            calc.interest_for_period(-100, 1)

    def test_string_balance_accepted(self):
        calc = InterestCalculator(100000, 4.9, 360)
        assert calc.interest_for_period("100000", 1) == Decimal("408.33333333")

    def test_override_rate(self):
        """临时覆盖利率应直接生效。"""
        calc = InterestCalculator(100000, 4.9, 360)
        base = calc.interest_for_period(100000, 1)
        override = calc.interest_for_period(100000, 1, annual_rate=3.85)
        # 3.85 < 4.9，利息应更少
        assert override < base
        # 100000 × 3.85 / 1200 = 320.8333...
        assert override == Decimal("320.83333333")


# ===========================================================================
# 5. 固定利率模式
# ===========================================================================


class TestFixedRateMode:
    def test_all_periods_use_same_rate(self):
        calc = InterestCalculator(100000, 4.9, 360)
        rates = [calc.rate_for_period(i) for i in range(1, 361)]
        assert all(r == Decimal("4.9") for r in rates)

    def test_rate_for_period_out_of_range(self):
        calc = InterestCalculator(100000, 4.9, 360)
        with pytest.raises(IndexError):
            calc.rate_for_period(0)
        with pytest.raises(IndexError):
            calc.rate_for_period(361)


# ===========================================================================
# 6. 浮动利率与分段表
# ===========================================================================


class TestFloatingRate:
    def _make_calc(self):
        calc = InterestCalculator(
            100000, annual_rate=4.9, periods=360, rate_mode=RateMode.FLOATING
        )
        return calc

    def test_set_schedule(self):
        calc = self._make_calc()
        calc.set_rate_schedule(
            [
                RateScheduleEntry(1, 4.9),
                RateScheduleEntry(13, 4.5),
                RateScheduleEntry(25, 4.0),
            ]
        )
        # 第 1~12 期用 4.9
        assert calc.rate_for_period(1) == Decimal("4.9")
        assert calc.rate_for_period(12) == Decimal("4.9")
        # 第 13~24 期用 4.5
        assert calc.rate_for_period(13) == Decimal("4.5")
        assert calc.rate_for_period(24) == Decimal("4.5")
        # 第 25 期起用 4.0
        assert calc.rate_for_period(25) == Decimal("4.0")
        assert calc.rate_for_period(360) == Decimal("4.0")

    def test_schedule_rate_affects_interest(self):
        """分段利率变化应反映在单期利息上。"""
        calc = self._make_calc()
        calc.set_rate_schedule(
            [
                RateScheduleEntry(1, 4.9),
                RateScheduleEntry(13, 4.5),
            ]
        )
        bal = 80000
        i1 = calc.interest_for_period(bal, 1)
        i13 = calc.interest_for_period(bal, 13)
        assert i13 < i1
        # i13 应为 80000 × 4.5 / 1200 = 300
        assert i13 == Decimal("300")

    def test_duplicate_start_period_rejected(self):
        calc = self._make_calc()
        with pytest.raises(ValueError, match="递增"):
            calc.set_rate_schedule(
                [
                    RateScheduleEntry(1, 4.9),
                    RateScheduleEntry(1, 4.5),  # 重复 start
                ]
            )

    def test_set_schedule_on_fixed_mode_rejected(self):
        calc = InterestCalculator(100000, 4.9, 360, rate_mode=RateMode.FIXED)
        with pytest.raises(RuntimeError, match="仅"):
            calc.set_rate_schedule([RateScheduleEntry(1, 4.9)])

    def test_floating_without_schedule_uses_initial_rate(self):
        """未设分段表时，浮动利率退化为全程使用初始年利率。"""
        calc = InterestCalculator(
            100000, 4.9, 360, rate_mode=RateMode.FLOATING
        )
        assert calc.rate_for_period(1) == Decimal("4.9")
        assert calc.rate_for_period(360) == Decimal("4.9")

    def test_schedule_accepts_decimal_fraction(self):
        """分段记录内的利率同样支持小数形态。"""
        calc = self._make_calc()
        calc.set_rate_schedule(
            [
                RateScheduleEntry(1, 4.9),
                RateScheduleEntry(13, 0.045),  # 0.045 -> 4.5
            ]
        )
        assert calc.rate_for_period(13) == Decimal("4.5")


# ===========================================================================
# 7. 汇总方法
# ===========================================================================


def _build_schedule(items):
    """由 (principal, interest) 元组构造 _PeriodStub 列表。"""
    balance = Decimal("100000")
    stub = []
    d = date(2026, 11, 1)
    for i, (p, ip) in enumerate(items, start=1):
        p = Decimal(str(p))
        ip = Decimal(str(ip))
        balance -= p
        stub.append(
            _PeriodStub(
                period=i,
                payment_date=d.replace(month=(d.month + i - 1) % 12 + 1),
                principal=p,
                interest=ip,
                balance=max(balance, Decimal("0")),
            )
        )
    return stub


class TestSummarize:
    def test_total_interest(self):
        calc = InterestCalculator(100000, 4.9, 360)
        schedule = _build_schedule([(1000, 408.33), (1000, 407.92)])
        assert calc.total_interest(schedule) == Decimal("816.25")

    def test_total_interest_with_dict_like(self):
        """测试 __getitem__ 路径。"""
        calc = InterestCalculator(100000, 4.9, 360)
        schedule = [
            {"principal": Decimal("1000"), "interest": Decimal("408.33")},
            {"principal": Decimal("1000"), "interest": Decimal("407.92")},
        ]
        assert calc.total_interest(schedule) == Decimal("816.25")

    def test_total_interest_empty(self):
        calc = InterestCalculator(100000, 4.9, 360)
        assert calc.total_interest([]) == 0

    def test_summarize_fields(self):
        calc = InterestCalculator(100000, 4.9, 360)
        schedule = _build_schedule([(1000, 400), (1000, 300)])
        result = calc.summarize(schedule)
        assert isinstance(result, InterestSummary)
        assert result.total_interest == 700
        assert result.principal == 2000
        assert result.total_payment == 2700
        # 利息/本金 = 700/2000 = 0.35
        assert result.interest_ratio == Decimal("0.35")

    def test_summarize_full_repayment(self):
        """本金全部还清时，principal 合计应等于初始本金。"""
        calc = InterestCalculator(100000, 4.9, 360)
        # 构造一份 3 期还清的计划
        schedule = [
            _PeriodStub(1, date(2026, 11, 1), Decimal("60000"),
                        Decimal("408.33"), Decimal("40000")),
            _PeriodStub(2, date(2026, 12, 1), Decimal("40000"),
                        Decimal("163.33"), Decimal("0")),
        ]
        result = calc.summarize(schedule)
        assert result.principal == 100000
        assert result.total_interest == Decimal("571.66")
        assert result.total_payment == Decimal("100571.66")

    def test_interest_to_date(self):
        calc = InterestCalculator(100000, 4.9, 360)
        schedule = [
            _PeriodStub(1, date(2026, 10, 15), Decimal("1000"),
                        Decimal("408.33"), Decimal("99000")),
            _PeriodStub(2, date(2026, 11, 15), Decimal("1000"),
                        Decimal("404.58"), Decimal("98000")),
            _PeriodStub(3, date(2026, 12, 15), Decimal("1000"),
                        Decimal("400.83"), Decimal("97000")),
        ]
        # 截止到 11 月底：计入第 1、2 期
        total = calc.interest_to_date(schedule, date(2026, 11, 30))
        assert total == Decimal("812.91")

        # 截止到 12 月底：三期全计
        total = calc.interest_to_date(schedule, date(2026, 12, 31))
        assert total == Decimal("1213.74")

        # 截止到 10 月初：一期都不计
        total = calc.interest_to_date(schedule, date(2026, 10, 1))
        assert total == 0

    def test_interest_to_date_exact_match(self):
        """还款日等于截止日时应计入。"""
        calc = InterestCalculator(100000, 4.9, 360)
        schedule = [
            _PeriodStub(1, date(2026, 11, 15), Decimal("1000"),
                        Decimal("408.33"), Decimal("99000")),
            _PeriodStub(2, date(2026, 12, 15), Decimal("1000"),
                        Decimal("404.58"), Decimal("98000")),
        ]
        total = calc.interest_to_date(schedule, date(2026, 11, 15))
        assert total == Decimal("408.33")

    def test_missing_field_raises(self):
        calc = InterestCalculator(100000, 4.9, 360)
        bad = [object()]
        with pytest.raises(AttributeError):
            calc.total_interest(bad)


# ===========================================================================
# 8. 精度与量化
# ===========================================================================


class TestPrecision:
    def test_no_float_contamination(self):
        """结果是 Decimal 而非 float。"""
        calc = InterestCalculator(100000, 4.9, 360)
        interest = calc.interest_for_period(100000, 1)
        assert isinstance(interest, Decimal)
        assert not isinstance(interest, float)

    def test_quantize_half_up(self):
        """验证银行家舍入之外的正确半调上入。"""
        # 408.335 -> 应入到 408.34
        assert InterestCalculator.quantize_money("408.335") == Decimal("408.34")
        # 408.334 -> 应舍到 408.33
        assert InterestCalculator.quantize_money("408.334") == Decimal("408.33")

    def test_large_principal_precision(self):
        """大本金下的单期利息仍精确。"""
        calc = InterestCalculator("1000000000", 4.9, 360)  # 10 亿
        interest = calc.interest_for_period("1000000000", 1)
        assert interest == Decimal("4083333.33333333")

    def test_tiny_rate_precision(self):
        # 阈值边界：传入 1 等于阈值，应视为百分比数值 → 1%
        calc = InterestCalculator(100000, "1", 360)
        interest = calc.interest_for_period(100000, 1)
        # 1% / 12 * 100000 = 83.3333...
        assert interest == Decimal("83.33333333")

    def test_repeated_accumulation_no_drift(self):
        """多次累加单期利息不应产生浮点漂移。"""
        calc = InterestCalculator(100000, 4.9, 360)
        total = Decimal("0")
        bal = Decimal("100000")
        for i in range(1, 361):
            bal -= Decimal("138.47")
            if bal <= 0:
                bal = Decimal("0")
            total += calc.interest_for_period(bal if bal > 0 else "100000", i)
        # 验证结果是干净的 Decimal
        assert total == total.quantize(Decimal("0.0000001"))


# ===========================================================================
# 9. 手工基准比对
# ===========================================================================


class TestHandBaseline:
    """与手工纸面算式交叉验证，确保核心公式无误。"""

    def test_first_period_of_equal_installment(self):
        """等额本息首期：利息 = 本金 × 月利率。

        贷款 100 万，年利率 4.9%，30 年(360期)：
        首期利息应为 1000000 × 4.9% / 12 = 4083.33...
        """
        calc = InterestCalculator(1000000, 4.9, 360)
        interest = calc.interest_for_period(1000000, 1)
        expected = Decimal("1000000") * Decimal("4.9") / Decimal("1200")
        assert interest == expected.quantize(Decimal("0.00000001"))

    def test_two_decimal_places_display(self):
        """验证量化到分的展示值。"""
        calc = InterestCalculator(1000000, 4.9, 360)
        interest = calc.interest_for_period(1000000, 1)
        assert calc.quantize_money(interest) == Decimal("4083.33")

    def test_known_rate_schedule(self):
        """手工给定三段利率，逐期核对命中结果。"""
        calc = InterestCalculator(
            100000, 4.9, 24, rate_mode=RateMode.FLOATING
        )
        calc.set_rate_schedule(
            [
                RateScheduleEntry(1, 4.9),
                RateScheduleEntry(7, 4.3),
                RateScheduleEntry(13, 3.8),
            ]
        )
        assert calc.rate_for_period(1) == Decimal("4.9")
        assert calc.rate_for_period(6) == Decimal("4.9")
        assert calc.rate_for_period(7) == Decimal("4.3")
        assert calc.rate_for_period(12) == Decimal("4.3")
        assert calc.rate_for_period(13) == Decimal("3.8")
        assert calc.rate_for_period(24) == Decimal("3.8")

    def test_summary_ratio_rounding(self):
        """利息/本金比率保留 4 位小数。"""
        calc = InterestCalculator(100000, 4.9, 360)
        schedule = _build_schedule([(20000, 1234.56), (80000, 3456.78)])
        result = calc.summarize(schedule)
        # 4691.34 / 100000 = 0.0469134 -> 0.0469
        assert result.interest_ratio == Decimal("0.0469")


# 为了被 _build_schedule 用到
from decimal import Decimal  # noqa: E402


# ===========================================================================
# 10. 还款计划表生成（build_schedule）
# ===========================================================================


class TestBuildSchedule:
    def test_annuity_schedule(self):
        """等额本息：期数、本金合计、末期归零、首期数值。"""
        calc = InterestCalculator(
            1_000_000, 4.9, 240, rate_mode=RateMode.FIXED
        )
        rows = calc.build_schedule(
            RepaymentMode.ANNUITY, start_date=date(2026, 11, 1)
        )

        df = InterestCalculator.to_dataframe(rows)  # 或 calc.to_dataframe(rows)
        print(df)

        assert len(rows) == 240
        assert rows[-1].ending_balance == Decimal("0")
        # 本金逐期偿还，合计恰好等于贷款本金
        assert sum(r.principal for r in rows) == Decimal("1000000.00")
        # 首期：利息 = 1000000 × 4.9 / 1200 = 4083.33；月供恒定为 6544.44
        assert rows[0].interest == Decimal("4083.33")
        assert rows[0].installment == Decimal("6544.44")

        # 输入快照可直接断言（数据同时会写入日志）
        snap = calc.input_snapshot()
        assert snap["principal"] == Decimal("1000000")
        assert snap["annual_rate(%)"] == Decimal("4.9")
        assert snap["periods"] == 240
        assert snap["rate_mode"] == RateMode.FIXED

    def test_equal_principal_schedule(self):
        """等额本金：每期本金固定、利息逐期递减。"""
        calc = InterestCalculator(120000, 4.8, 12, rate_mode=RateMode.FIXED)
        rows = calc.build_schedule(RepaymentMode.EQUAL_PRINCIPAL, start_date=date(2026, 11, 1))

        df = InterestCalculator.to_dataframe(rows)  # 或 calc.to_dataframe(rows)
        print(df)

        assert len(rows) == 12
        # 每期本金 = 120000 / 12 = 10000
        assert rows[0].principal == Decimal("10000.00")
        # 首期利息 = 120000 × 4.8 / 1200 = 480
        assert rows[0].interest == Decimal("480.00")
        assert rows[1].interest < rows[0].interest
        assert sum(r.principal for r in rows) == Decimal("120000.00")

    def test_floating_rate_schedule_uses_segmented_rate(self):
        """浮动利率下，分段表应反映到计划表利息。"""
        calc = InterestCalculator(
            100000, 4.9, 24, rate_mode=RateMode.FLOATING
        )
        calc.set_rate_schedule(
            [RateScheduleEntry(1, 4.9), RateScheduleEntry(13, 3.0)]
        )
        rows = calc.build_schedule(RepaymentMode.EQUAL_PRINCIPAL)

        df = InterestCalculator.to_dataframe(rows)  # 或 calc.to_dataframe(rows)
        print(df)


        # 第 13 期利率降为 3.0，等额本金下利息明显低于第 1 期
        assert rows[0].interest == Decimal("408.33")     # 100000 × 4.9 / 1200
        # 第 13 期初余额 49999.96，利率 3.0：49999.96 × 3.0 / 1200 = 125.00
        assert rows[12].interest == Decimal("125.00")

    def test_start_date_generates_payment_dates(self):
        """构造给定起息日后，build_schedule 不传参也能生成每期还款日。"""
        calc = InterestCalculator(
            100000, 4.9, 3, rate_mode=RateMode.FIXED, start_date="2026-11-01"
        )
        assert calc.start_date == date(2026, 11, 1)
        rows = calc.build_schedule(RepaymentMode.EQUAL_PRINCIPAL)
        # 首期还款日 = 起息日 + 1 个月
        assert [r.payment_date for r in rows] == [
            date(2026, 12, 1),
            date(2027, 1, 1),
            date(2027, 2, 1),
        ]

    def test_start_month_end_is_clamped(self):
        """起息日为月末时，顺延自动裁剪到当月最后一天（1/31 -> 2/28）。"""
        calc = InterestCalculator(100000, 4.9, 2, start_date=date(2026, 1, 31))
        rows = calc.build_schedule(RepaymentMode.EQUAL_PRINCIPAL)
        assert rows[0].payment_date == date(2026, 2, 28)
        assert rows[1].payment_date == date(2026, 3, 31)

    def test_build_schedule_start_date_overrides_ctor(self):
        """build_schedule 传入的起息日优先于构造时的设置。"""
        calc = InterestCalculator(100000, 4.9, 2, start_date="2026-11-01")
        rows = calc.build_schedule(
            RepaymentMode.EQUAL_PRINCIPAL, start_date="2020-01-01"
        )
        assert rows[0].payment_date == date(2020, 2, 1)

    def test_no_start_date_yields_none_payment_dates(self):
        """两处都没给起息日时，不生成还款日（保持向后兼容）。"""
        calc = InterestCalculator(100000, 4.9, 2)
        rows = calc.build_schedule(RepaymentMode.EQUAL_PRINCIPAL)
        assert all(r.payment_date is None for r in rows)

    def test_invalid_repayment_mode_rejected(self):
        calc = InterestCalculator(100000, 4.9, 12)
        with pytest.raises(ValueError, match="不支持的还款方式"):
            calc.build_schedule("WRONG_MODE")
