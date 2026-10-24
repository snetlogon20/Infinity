"""按不同组合演示利息计算：固定/浮动利率 × 等额本息/等额本金 × 不同起息日。

既可作为脚本直接运行（``python interest_calculator_test.py``）看到 DataFrame 输出，
也可被 pytest 收集执行（此时输入/输出会写入日志）。
"""
import logging
from datetime import date

from dataIntegrator.modelService.loans.interest_calculator import (
    InterestCalculator,
    RateScheduleEntry,
    RepaymentMode,
)
from dataIntegrator.modelService.loans.rate_mode import RateMode

logger = logging.getLogger(__name__)

class TestInterestCalculatorTest:
    # ------------------------------------------------------------------
    # 组合一：固定利率
    # ------------------------------------------------------------------

    def test_calculate_interest(self):
        """固定利率 + 等额本息（默认组合）。"""
        calc = InterestCalculator(
            1_000_000,
            4.9,
            240,
            rate_mode=RateMode.FIXED,
            start_date=date(2026, 11, 1),
        )
        self.log_dataframe(calc, RepaymentMode.ANNUITY, "固定利率·等额本息")

    def test_fixed_equal_principal(self):
        """固定利率 + 等额本金。"""
        calc = InterestCalculator(
            1_000_000,
            4.9,
            240,
            rate_mode=RateMode.FIXED,
            start_date=date(2026, 11, 1),
        )
        self.log_dataframe(
            calc, RepaymentMode.EQUAL_PRINCIPAL, "固定利率·等额本金"
        )

    # ------------------------------------------------------------------
    # 组合二：浮动利率（LPR 重定价：第 13 期、第 25 期分段下调）
    # ------------------------------------------------------------------

    def _make_floating_calc(self) -> InterestCalculator:
        """构造带分段利率表的浮动利率计算器。"""
        calc = InterestCalculator(
            1_000_000,
            4.9,
            36,
            rate_mode=RateMode.FLOATING,
            start_date=date(2026, 11, 1),
        )
        # 第 1 期 4.9%；第 13 期重定价为 4.5%；第 25 期为 4.0%
        calc.set_rate_schedule(
            [
                RateScheduleEntry(1, 4.9),
                RateScheduleEntry(13, 4.5),
                RateScheduleEntry(25, 4.0),
            ]
        )
        return calc

    def test_floating_annuity(self):
        """浮动利率 + 等额本息。"""
        self.log_dataframe(
            self._make_floating_calc(),
            RepaymentMode.ANNUITY,
            "浮动利率·等额本息",
            preview=36,
        )

    def test_floating_equal_principal(self):
        """浮动利率 + 等额本金。"""
        self.log_dataframe(
            self._make_floating_calc(),
            RepaymentMode.EQUAL_PRINCIPAL,
            "浮动利率·等额本金",
            preview=36,
        )

    # ------------------------------------------------------------------
    # 组合三：不同起息日（含月末裁剪）对还款日的影响
    # ------------------------------------------------------------------

    def test_various_start_dates(self):
        """不同起息日：普通月初 / 月末(1-31 裁剪) / 月中。"""
        anchors = [date(2026, 11, 1), date(2026, 1, 31), date(2026, 2, 15)]
        for start in anchors:
            calc = InterestCalculator(
                500_000,
                3.85,
                6,
                rate_mode=RateMode.FIXED,
                start_date=start,
            )
            self.log_dataframe(
                calc, RepaymentMode.ANNUITY, f"等额本息·起息日 {start.isoformat()}"
            )

    # ------------------------------------------------------------------
    # 通用输出：把计划表转成 DataFrame 并写入日志
    # ------------------------------------------------------------------

    def log_dataframe(
        self,
        calc: InterestCalculator,
        repayment_mode: str = RepaymentMode.ANNUITY,
        title: str = "",
        preview: int = 12,
    ):
        rows = calc.build_schedule(repayment_mode)
        df = InterestCalculator.to_dataframe(rows)
        logger.info("===== %s =====", title or repayment_mode)
        if len(df) <= preview + 3:
            logger.info("\n%s", df.to_string(index=False))
        else:
            logger.info("\n%s", df.head(preview).to_string(index=False))
            logger.info("...（共 %d 期，中间省略）...", len(df))
            logger.info("\n%s", df.tail(3).to_string(index=False))
        return rows


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    t = TestInterestCalculatorTest()
    t.test_calculate_interest()
    t.test_fixed_equal_principal()
    t.test_floating_annuity()
    t.test_floating_equal_principal()
    t.test_various_start_dates()
