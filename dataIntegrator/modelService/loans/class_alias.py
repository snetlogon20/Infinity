# ---------------------------------------------------------------------------
# 类型别名
# ---------------------------------------------------------------------------
from decimal import Decimal
from typing import Union

from dataIntegrator.modelService.loans.rate_mode import RateMode

RateInput = Union[Decimal, float, int, str]
Money = Decimal
# RateMode = str  # "FIXED" | "FLOATING"

# 识别"已经是小数形态"的阈值：<= 该值的输入视为 0.049 写法，否则视为 4.9 写法
_PERCENT_THRESHOLD = Decimal("1")
