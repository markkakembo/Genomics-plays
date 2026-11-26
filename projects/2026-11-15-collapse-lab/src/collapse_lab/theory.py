"""Closed-form results used as baselines for the simulations.

Every function here is a hand-derivable formula; the derivations are written
out in the docstrings so they can be checked without trusting the code.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np


# ---------------------------------------------------------------------------
# 1-D Gaussian, "replace" regime
# ---------------------------------------------------------------------------
# Generation 0 is N(mu, sigma^2). Generation k+1 draws M samples from the
# generation-k model and refits (mean, variance). Write s_k^2 for the fitted
# variance at generation k (s_0 = sigma).
#
# With the unbiased estimator (ddof=1), (M-1) s_{k+1}^2 / s_k^2 ~ chi^2_{M-1},
# independently of everything earlier, so s_n^2 = sigma^2 * prod_k Q_k with
# Q_k iid chi^2_{M-1}/(M-1).


def c_M(M: int) -> float:
    """E[sqrt(chi^2_{M-1} / (M-1))] = sqrt(2/(M-1)) * Gamma(M/2) / Gamma((M-1)/2).

    This is the familiar c4 bias constant of the sample standard deviation.
    Hand check: M=2 gives sqrt(2)/sqrt(pi) = 0.79788...
    """
    if M < 2:
        raise ValueError("need M >= 2 samples per generation")
    return math.sqrt(2.0 / (M - 1)) * math.exp(math.lgamma(M / 2) - math.lgamma((M - 1) / 2))


def expected_var_replace(n: int, M: int, sigma2: float = 1.0, ddof: int = 1) -> float:
    """E[s_n^2].

    ddof=1 (unbiased): E[Q]=1, so E[s_n^2] = sigma^2 for every n.
    ddof=0 (MLE):      E[s^2_{k+1} | s_k] = s_k^2 (M-1)/M, so sigma^2 ((M-1)/M)^n.
    """
    if ddof == 1:
        return sigma2
    if ddof == 0:
        return sigma2 * ((M - 1) / M) ** n
    raise ValueError("ddof must be 0 or 1")


def expected_std_replace(n: int, M: int, sigma: float = 1.0) -> float:
    """E[s_n] = sigma * c_M^n (ddof=1). Decays geometrically: the collapse."""
    return sigma * c_M(M) ** n


def expected_log_var_drift(M: int) -> float:
    """E[log Q] for Q ~ chi^2_{M-1}/(M-1): digamma((M-1)/2) + log(2/(M-1)) < 0.

    log s_n^2 is a random walk with this (negative) drift, so s_n -> 0 almost
    surely even though E[s_n^2] stays equal to sigma^2 under ddof=1.
    """
    k = (M - 1) / 2
    return _digamma(k) + math.log(2.0 / (M - 1))


def marginal_var_replace(n: int, M: int, sigma2: float = 1.0) -> float:
    """Var(X_n) for one draw X_n from the generation-n model (ddof=1).

    Var(X_n) = E[s_n^2] + Var(mu_n) and mu_{k+1} = mu_k + s_k Z/sqrt(M), so
    Var(mu_n) = sum_k E[s_k^2]/M = n sigma^2/M. Hence sigma^2 (1 + n/M), the
    formula stated in Shumailov et al. (arXiv:2305.17493v3, Sec. 4.2).
    """
    return sigma2 * (1.0 + n / M)


def expected_w2sq_replace(n: int, M: int, sigma: float = 1.0) -> float:
    """E[W2^2(N(mu, sigma^2), N(mu_n, s_n^2))] exactly (ddof=1).

    For 1-D Gaussians W2^2 = (mu_n-mu)^2 + (s_n-sigma)^2. Taking expectations:
    n sigma^2/M + sigma^2 + sigma^2 - 2 sigma E[s_n]
      = sigma^2 (n/M + 2 - 2 c_M^n).
    For small n/M this is about (3/2) sigma^2 n/M, matching the leading term
    of Eq. 4 in Shumailov et al. (arXiv:2305.17493v3).
    """
    return sigma ** 2 * (n / M + 2.0 - 2.0 * c_M(M) ** n)


# ---------------------------------------------------------------------------
# Discrete distributions: resampling == neutral Wright-Fisher drift
# ---------------------------------------------------------------------------


def heterozygosity(p: np.ndarray) -> np.ndarray:
    """H = 1 - sum_i p_i^2 (Gini-Simpson diversity), along the last axis."""
    p = np.asarray(p, dtype=float)
    return 1.0 - np.sum(p * p, axis=-1)


def expected_heterozygosity(t: int, H0: float, M: int) -> float:
    """Wright-Fisher result E[H_t] = H_0 (1 - 1/M)^t.

    One step: counts ~ Multinomial(M, p), p' = counts/M.
    E[p_i'^2] = p_i^2 + p_i(1-p_i)/M, so E[H'] = H (1 - 1/M).
    """
    return H0 * (1.0 - 1.0 / M) ** t


def one_step_loss_prob(p_i: float, M: int) -> float:
    """P(category with probability p_i gets zero samples) = (1 - p_i)^M."""
    return (1.0 - p_i) ** M


def expected_support_after_one_step(p: Sequence[float], M: int) -> float:
    """E[# categories still present after one resampling] = sum_i 1-(1-p_i)^M."""
    p = np.asarray(p, dtype=float)
    return float(np.sum(1.0 - (1.0 - p) ** M))


# ---------------------------------------------------------------------------
# Linear regression (Gerstgrasser et al., arXiv:2404.01413v2)
# ---------------------------------------------------------------------------


def linear_test_error_replace(n: int, d: int, T: int, sigma2: float = 1.0) -> float:
    """Excess test error after n fits when each fit sees only the previous model's labels.

    w_n = w* + A sum_{i<=n} E_i with A = (X^T X)^{-1} X^T, E_i ~ N(0, sigma^2 I_T).
    With x ~ N(0, I_d) and E[(X^T X)^{-1}] = I_d/(T-d-1) (inverse Wishart):
    sigma^2 d n / (T - d - 1). Grows without bound in n.
    """
    _check_T(d, T)
    return sigma2 * d * n / (T - d - 1)


def linear_test_error_accumulate(n: int, d: int, T: int, sigma2: float = 1.0) -> float:
    """Theorem 2 of Gerstgrasser et al.: sigma^2 d/(T-d-1) * sum_{i=1}^n 1/i^2.

    Bounded above by sigma^2 d/(T-d-1) * pi^2/6 for every n.
    """
    _check_T(d, T)
    return sigma2 * d / (T - d - 1) * sum(1.0 / i ** 2 for i in range(1, n + 1))


def _check_T(d: int, T: int) -> None:
    if T < d + 2:
        raise ValueError("need T >= d + 2 for the inverse-Wishart mean to exist")


def _digamma(x: float) -> float:
    """Digamma via recurrence + asymptotic series (no SciPy dependency)."""
    result = 0.0
    while x < 10.0:
        result -= 1.0 / x
        x += 1.0
    inv = 1.0 / x
    inv2 = inv * inv
    result += math.log(x) - 0.5 * inv - inv2 * (1 / 12 - inv2 * (1 / 120 - inv2 * (1 / 252 - inv2 / 240)))
    return result
