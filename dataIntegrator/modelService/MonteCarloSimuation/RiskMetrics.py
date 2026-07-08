"""
RiskMetrics – VAR and ES calculations on simulated return distributions.
"""

import numpy as np
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class RiskMetrics:
    """Compute Value-at-Risk (VAR) and Expected Shortfall (ES) from simulated values."""

    @staticmethod
    def _var_lower(values: np.ndarray, alpha: float) -> float:
        """Lower VAR bound = alpha-th percentile."""
        return float(np.percentile(values, alpha * 100))

    @staticmethod
    def _var_upper(values: np.ndarray, alpha: float) -> float:
        """Upper VAR bound = (1-alpha)-th percentile."""
        return float(np.percentile(values, (1 - alpha) * 100))

    @staticmethod
    def _es_lower(values: np.ndarray, alpha: float) -> float:
        """Expected Shortfall (CVaR) for the lower tail."""
        var_low = RiskMetrics._var_lower(values, alpha)
        tail = values[values <= var_low]
        if len(tail) == 0:
            return var_low
        return float(np.mean(tail))

    @staticmethod
    def _es_upper(values: np.ndarray, alpha: float) -> float:
        """Expected Shortfall for the upper tail."""
        var_high = RiskMetrics._var_upper(values, alpha)
        tail = values[values >= var_high]
        if len(tail) == 0:
            return var_high
        return float(np.mean(tail))

    @classmethod
    def calculate_var(cls, simulated_values: np.ndarray, alpha: float) -> Tuple[float, float]:
        """
        Calculate two-sided VAR bounds.

        Args:
            simulated_values: 1-D array of simulated returns.
            alpha: significance level (e.g. 0.05).

        Returns:
            (var_lower_bound, var_upper_bound)
        """
        var_low, var_high = cls._var_lower(simulated_values, alpha), cls._var_upper(simulated_values, alpha)
        logger.debug(f"VAR: lower={var_low:.6f}, upper={var_high:.6f}, alpha={alpha}, n={len(simulated_values)}")
        return var_low, var_high

    @classmethod
    def calculate_es(cls, simulated_values: np.ndarray, alpha: float) -> Tuple[float, float]:
        """
        Calculate two-sided Expected Shortfall.

        Args:
            simulated_values: 1-D array of simulated returns.
            alpha: significance level.

        Returns:
            (es_lower_bound, es_upper_bound)
        """
        es_low, es_high = cls._es_lower(simulated_values, alpha), cls._es_upper(simulated_values, alpha)
        logger.debug(f"ES: lower={es_low:.6f}, upper={es_high:.6f}, alpha={alpha}")
        return es_low, es_high

    @classmethod
    def calculate_all_stats(cls, simulated_values: np.ndarray, alpha: float) -> dict:
        """
        Compute all risk & summary statistics from simulated value distribution.

        Returns dict with keys:
            var_lower_bound, var_upper_bound,
            es_lower_bound, es_upper_bound,
            average, median_value
        """
        var_low, var_high = cls.calculate_var(simulated_values, alpha)
        es_low, es_high = cls.calculate_es(simulated_values, alpha)
        avg = float(np.mean(simulated_values))
        med = float(np.median(simulated_values))
        logger.debug(f"Risk stats: VAR=[{var_low:.6f}, {var_high:.6f}], "
                      f"ES=[{es_low:.6f}, {es_high:.6f}], avg={avg:.6f}, median={med:.6f}")
        return {
            'var_lower_bound': var_low,
            'var_upper_bound': var_high,
            'es_lower_bound': es_low,
            'es_upper_bound': es_high,
            'average': avg,
            'median_value': med,
        }
