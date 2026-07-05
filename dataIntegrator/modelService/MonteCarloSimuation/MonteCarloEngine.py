"""
MonteCarloEngine — core simulation engine.
Handles distribution fitting, sigma calculation, and path generation.
"""

import numpy as np
import pandas as pd
import warnings
from typing import Callable, Optional
from scipy import stats
from scipy.special import gammaln
from arch import arch_model
import logging

logger = logging.getLogger(__name__)

# Silence arch's DataScaleWarning — our pct_change values are naturally small percentages
warnings.filterwarnings('ignore', message='.*y is poorly scaled.*', module='arch')
warnings.filterwarnings('ignore', message='.*y is poorly scaled.*', module='arch.univariate')


class MonteCarloEngine:
    """
    Core Monte Carlo simulation engine.

    Supports distribution types:
        - 'normal'      : Gaussian
        - 'student'     : Student's t
        - 'skewed-t'    : Hansen's skewed-t (via arch)
        - 'lognormal'   : Log-normal
        - 'history'     : empirical bootstrap

    Supports sigma calculation types:
        - 'normal'      : rolling standard deviation
        - 'garch'       : GARCH(1,1) conditional volatility
        - 'egarch'      : EGARCH(1,1) conditional volatility
    """

    def __init__(self, returns: pd.Series, params: dict):
        """
        Args:
            returns: time series of historical returns (pct_change).
            params: simulation parameters dict with keys:
                - distribution_type
                - segma_calculation_type
                - series (number of simulation paths)
                - alpha (significance level)
        """
        self.returns = returns.dropna().values.astype(np.float64)
        self.params = params
        self.distribution_type = params.get('distribution_type', 'normal')
        self.sigma_type = params.get('segma_calculation_type', 'normal')
        self.n_series = int(params.get('series', 5000))
        self.alpha = float(params.get('alpha', 0.05))
        self.t_param = float(params.get('t', 0.01))

        # Fitted distribution info
        self.mu: float = 0.0
        self.sigma: float = 0.0
        self.distribution: Optional[Callable] = None
        self.distribution_params: dict = {}

        logger.info(
            f"MonteCarloEngine initialized: returns={len(self.returns)} points, "
            f"distribution_type={self.distribution_type}, sigma_type={self.sigma_type}, "
            f"n_series={self.n_series}, alpha={self.alpha}, t={self.t_param}"
        )

    # ------------------------------------------------------------------
    #  Distribution fitting
    # ------------------------------------------------------------------

    def fit_distribution(self) -> dict:
        """Fit the chosen distribution to historical returns."""
        logger.info(f"Fitting distribution: {self.distribution_type}")
        dist_map = {
            'normal': self._fit_normal,
            'student': self._fit_student,
            'skewed-t': self._fit_skewed_t,
            'lognormal': self._fit_lognormal,
            'history': self._fit_historical,
        }
        fitter = dist_map.get(self.distribution_type)
        if fitter is None:
            raise ValueError(f"Unsupported distribution_type: {self.distribution_type}")
        self.distribution_params = fitter()
        self.mu = self.distribution_params.get('mu', 0.0)
        logger.info(f"Distribution fitted: {self.distribution_params.get('dist_name')}, "
                     f"mu={self.mu:.6f}, sigma={self.distribution_params.get('sigma', 0):.6f}")
        return self.distribution_params

    def _fit_normal(self) -> dict:
        mu = float(np.mean(self.returns))
        std = float(np.std(self.returns, ddof=1))
        self.distribution = lambda size: np.random.normal(mu, std, size)
        logger.debug(f"Normal fit: mu={mu:.6f}, sigma={std:.6f}")
        return {'mu': mu, 'sigma': std, 'dist_name': 'normal'}

    def _fit_student(self) -> dict:
        df, loc, scale = stats.t.fit(self.returns)
        self.distribution = lambda size: stats.t.rvs(df, loc, scale, size=size)
        logger.debug(f"Student-t fit: df={df:.2f}, loc={loc:.6f}, scale={scale:.6f}")
        return {'mu': loc, 'sigma': scale, 'df': df, 'dist_name': 'student-t'}

    def _fit_skewed_t(self) -> dict:
        # Fit via arch's skewed-t distribution on the returns
        try:
            # Fit GARCH(1,1) with skewed-t to extract distribution params
            model = arch_model(self.returns * 100, vol='Garch', p=1, q=1, dist='skewt')
            res = model.fit(disp='off')
            # Extract standardized residuals distribution params
            # arch skewed-t: eta (df), lambda (skew)
            dist_params = res.params
            eta = dist_params.get('eta', 5.0)
            lam = dist_params.get('lambda', 0.0)
            mu = float(np.mean(self.returns))
            cond_vol = np.asarray(res.conditional_volatility)
            sigma = float(cond_vol[-1] / 100.0)

            # Generate Hansen skewed-t by inverse-transform sampling.
            # arch's SkewStudent.simulate() is unreliable when used standalone,
            # so we implement the quantile-based generator here.
            # Hansen (1994) skewed-t: standardized mean=0, variance=1.
            from scipy.stats import t as t_dist

            eta_f = float(eta)
            lam_f = float(lam)
            # Constants for standardized skewed-t
            c = np.exp(
                gammaln((eta_f + 1) / 2)
                - gammaln(eta_f / 2)
            ) / np.sqrt(np.pi * (eta_f - 2))
            a = 4 * lam_f * c * (eta_f - 2) / (eta_f - 1)
            b = np.sqrt(1 + 3 * lam_f**2 - a**2)

            def _gen(size):
                u = np.random.uniform(size=size)
                threshold = (1 - lam_f) / 2
                left = u < threshold
                right = ~left
                result = np.empty(size, dtype=np.float64)
                # Left tail: u -> q = 2u/(1-λ)
                q_left = 2 * u[left] / (1 - lam_f)
                result[left] = (
                    (1 - lam_f) * np.sqrt((eta_f - 2) / eta_f) * t_dist.ppf(q_left, df=eta_f)
                    - a
                )
                # Right tail: u -> q = 2(1-u)/(1+λ)
                q_right = 2 * (1 - u[right]) / (1 + lam_f)
                result[right] = (
                    -(1 + lam_f) * np.sqrt((eta_f - 2) / eta_f) * t_dist.ppf(q_right, df=eta_f)
                    - a
                )
                result = result / b
                return result / 100.0 + mu

            self.distribution = _gen
            logger.debug(f"Skewed-t fit: mu={mu:.6f}, sigma={sigma:.6f}, eta={eta:.2f}, lambda={lam:.4f}")
            return {'mu': mu, 'sigma': sigma, 'eta': eta, 'lambda': lam, 'dist_name': 'skewed-t'}
        except Exception as e:
            logger.warning(f"Skewed-t fit failed ({e}), falling back to Student-t")
            return self._fit_student()

    def _fit_lognormal(self) -> dict:
        # Ensure returns are shifted positive for lognormal fitting
        min_val = self.returns.min()
        shifted = self.returns - min_val + 1e-8
        shape, loc, scale = stats.lognorm.fit(shifted, floc=0)
        mu_log = float(np.log(scale))
        sigma_log = float(shape)
        self.distribution = lambda size: stats.lognorm.rvs(sigma_log, scale=np.exp(mu_log), size=size) + min_val - 1e-8
        logger.debug(f"Lognormal fit: mu_log={mu_log:.6f}, sigma_log={sigma_log:.6f}, shift={min_val:.6f}")
        return {'mu': mu_log, 'sigma': sigma_log, 'shift': min_val, 'dist_name': 'lognormal'}

    def _fit_historical(self) -> dict:
        """Bootstrap from empirical distribution."""
        self.distribution = lambda size: np.random.choice(self.returns, size=size, replace=True)
        mu = float(np.mean(self.returns))
        std = float(np.std(self.returns, ddof=1))
        logger.debug(f"Historical (bootstrap) fit: mu={mu:.6f}, sigma={std:.6f}, n={len(self.returns)}")
        return {'mu': mu, 'sigma': std, 'dist_name': 'history'}

    # ------------------------------------------------------------------
    #  Sigma calculation
    # ------------------------------------------------------------------

    def calculate_sigma(self) -> float:
        """Calculate sigma (volatility) based on segma_calculation_type."""
        logger.info(f"Calculating sigma: method={self.sigma_type}")
        sigma_map = {
            'normal': self._calc_normal_sigma,
            'garch': self._calc_garch_sigma,
            'egarch': self._calc_egarch_sigma,
        }
        calc = sigma_map.get(self.sigma_type)
        if calc is None:
            raise ValueError(f"Unsupported segma_calculation_type: {self.sigma_type}")
        self.sigma = calc()
        logger.info(f"Sigma calculated: {self.sigma:.6f}")
        return self.sigma

    def _calc_normal_sigma(self) -> float:
        return float(np.std(self.returns, ddof=1))

    def _calc_garch_sigma(self) -> float:
        try:
            model = arch_model(self.returns * 100, vol='Garch', p=1, q=1, dist='normal')
            res = model.fit(disp='off')
            cond_vol = np.asarray(res.conditional_volatility)
            last_vol = float(cond_vol[-1])
            result = last_vol / 100.0  # rescale back
            logger.debug(f"GARCH sigma: last_cond_vol={last_vol:.4f}, sigma={result:.6f}")
            return result
        except Exception as e:
            logger.warning(f"GARCH fitting failed ({e}), falling back to normal sigma.")
            return self._calc_normal_sigma()

    def _calc_egarch_sigma(self) -> float:
        try:
            model = arch_model(self.returns * 100, vol='EGARCH', p=1, q=1, dist='normal')
            res = model.fit(disp='off')
            cond_vol = np.asarray(res.conditional_volatility)
            last_vol = float(cond_vol[-1])
            result = last_vol / 100.0
            logger.debug(f"EGARCH sigma: last_cond_vol={last_vol:.4f}, sigma={result:.6f}")
            return result
        except Exception as e:
            logger.warning(f"EGARCH fitting failed ({e}), falling back to normal sigma.")
            return self._calc_normal_sigma()

    # ------------------------------------------------------------------
    #  Conditional volatility series (for rolling-window historical analysis)
    # ------------------------------------------------------------------

    def get_conditional_volatility(self) -> Optional[np.ndarray]:
        """
        Fit GARCH/EGARCH on the returns and return the full conditional volatility series.
        For 'normal' sigma type, returns None (use rolling std externally).
        """
        if self.sigma_type == 'normal':
            return None
        try:
            vol_type = 'Garch' if self.sigma_type == 'garch' else 'EGARCH'
            model = arch_model(self.returns * 100, vol=vol_type, p=1, q=1, dist='normal')
            res = model.fit(disp='off')
            return np.asarray(res.conditional_volatility) / 100.0
        except Exception as e:
            logger.warning(f"Conditional volatility fit failed ({e}), falling back to normal.")
            return None

    # ------------------------------------------------------------------
    #  Simulation
    # ------------------------------------------------------------------

    def simulate_single_step(self) -> np.ndarray:
        """
        Generate `n_series` random samples for a single-step forecast.

        Returns:
            1-D numpy array of simulated returns.
        """
        if self.distribution is None:
            self.fit_distribution()

        logger.debug(f"Simulating single step: n_series={self.n_series}, dist={self.distribution_type}")

        # Use the fitted distribution; scale by sigma if distribution != history/non-parametric
        if self.distribution_type == 'history':
            result = self.distribution(self.n_series)
            logger.debug(f"Single step simulation done: shape=({len(result)},), "
                         f"mean={np.mean(result):.6f}, std={np.std(result):.6f}")
            return result

        base_samples = self.distribution(self.n_series)
        # De-mean, rescale to target sigma, then add mu back
        if self.sigma > 0:
            base_mean = np.mean(base_samples)
            base_std = np.std(base_samples, ddof=1)
            if base_std > 0:
                base_samples = (base_samples - base_mean) * (self.sigma / base_std) + self.mu
        logger.debug(f"Single step simulation done: shape=({len(base_samples)},), "
                     f"mean={np.mean(base_samples):.6f}, min={np.min(base_samples):.6f}, max={np.max(base_samples):.6f}")
        return base_samples

    def simulate_multi_step(self, times: int) -> np.ndarray:
        """
        Generate `n_series` paths, each with `times` steps.

        Args:
            times: number of steps (e.g., next_n_working_days).

        Returns:
            2-D numpy array of shape (times, n_series).
            Row i = simulated values at step i.
        """
        if self.distribution is None:
            self.fit_distribution()
        if self.sigma == 0:
            self.calculate_sigma()

        logger.info(f"Simulating multi-step: times={times}, n_series={self.n_series}, "
                     f"dist={self.distribution_type}, sigma={self.sigma:.6f}")

        if self.distribution_type == 'history':
            sim = np.zeros((times, self.n_series))
            for step in range(times):
                sim[step] = self.distribution(self.n_series)
            return sim

        # Geometric Brownian motion style: dS = mu*dt + sigma*dW
        dt = self.t_param
        drift = self.mu * dt

        sim = np.zeros((times, self.n_series))
        for step in range(times):
            if step == 0:
                # Use distribution shape for initial shock, de-mean then rescale
                shock = self.distribution(self.n_series)
                shock_mean = np.mean(shock)
                shock_std = np.std(shock, ddof=1) or 1.0
                shock = (shock - shock_mean) * (self.sigma * np.sqrt(dt) / shock_std)
                sim[step] = drift + shock
            else:
                shock = np.random.normal(0, self.sigma * np.sqrt(dt), self.n_series)
                sim[step] = sim[step - 1] + drift + shock

        logger.info(f"Multi-step simulation done: shape={sim.shape}, "
                     f"final_step_mean={np.mean(sim[-1]):.6f}, final_step_std={np.std(sim[-1]):.6f}")
        return sim

    # ------------------------------------------------------------------
    #  Convenience: simulate + stats
    # ------------------------------------------------------------------

    def simulate_and_get_stats(self, times: int = None) -> dict:
        """
        Simulate and compute statistics per step.

        Args:
            times: if None, do single-step; if int, do multi-step.

        Returns:
            For single-step: dict of stats.
            For multi-step: list of dicts (one per step).
        """
        from .RiskMetrics import RiskMetrics

        if times is None or times == 1:
            simulated = self.simulate_single_step()
            return RiskMetrics.calculate_all_stats(simulated, self.alpha)

        simulated_matrix = self.simulate_multi_step(times)
        stats_list = []
        for step in range(times):
            step_vals = simulated_matrix[step]
            stats = RiskMetrics.calculate_all_stats(step_vals, self.alpha)
            stats['step_num'] = step + 1
            stats_list.append(stats)
        return stats_list
