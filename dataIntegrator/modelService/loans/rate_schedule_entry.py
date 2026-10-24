# ===========================================================================
# 数据类
# ===========================================================================
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class RateScheduleEntry:
    """分段利率表的一项。

    Attributes
    ----------
    start_period : int
        生效起始期次（1-based，含）。
    end_period : int | None
        生效结束期次（1-based，含）；``None`` 表示一直生效到贷款结束。
    annual_rate : Decimal
        该段采用的**年化百分比**数值，如 ``Decimal("4.9")``。
    """

    start_period: int
    annual_rate: Decimal
    end_period: Optional[int] = None