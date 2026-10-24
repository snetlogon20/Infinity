from dataclasses import dataclass

from dataIntegrator.modelService.loans.class_alias import Money

@dataclass
class InterestSummary:
    """利息汇总结果。"""

    total_interest: Money = Money("0")
    principal: Money = Money("0")
    total_payment: Money = Money("0")
    interest_ratio: Money = Money("0")  # 总利息 / 本金

    def to_dict(self) -> dict:
        return {
            "total_interest": str(self.total_interest),
            "principal": str(self.principal),
            "total_payment": str(self.total_payment),
            "interest_ratio": str(self.interest_ratio),
        }