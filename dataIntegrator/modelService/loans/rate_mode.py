# ===========================================================================
# 枚举替代：利率模式
# ===========================================================================
from typing import Tuple


class RateMode:
    """利率模式常量。"""

    FIXED = "FIXED"
    FLOATING = "FLOATING"

    @classmethod
    def all(cls) -> Tuple[str, ...]:
        return (cls.FIXED, cls.FLOATING)
