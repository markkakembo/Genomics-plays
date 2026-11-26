"""Linear regression trained on its own predictions (setup of Gerstgrasser et al. 2024).

A fixed design X (T x d, rows ~ N(0, I_d)) is reused every iteration. Iteration
1 labels are real: y = X w* + noise. Iteration i > 1 labels come from the
previous model: y = X w_{i-1} + noise. Ordinary least squares is refit either
on the newest labels only (replace) or on all labelled copies so far
(accumulate).
"""
from __future__ import annotations

import numpy as np


def simulate(
    iterations: int,
    d: int,
    T: int,
    chains: int = 500,
    mode: str = "replace",
    sigma: float = 1.0,
    seed: int | None = 0,
) -> np.ndarray:
    """Return excess test error ||w_n - w*||^2 with shape (iterations, chains).

    For test inputs x ~ N(0, I_d) the expected excess squared error of w is
    exactly ||w - w*||^2, so no test set has to be sampled.
    """
    if mode not in ("replace", "accumulate"):
        raise ValueError("mode must be 'replace' or 'accumulate'")
    if T < d + 2:
        raise ValueError("need T >= d + 2")
    rng = np.random.default_rng(seed)
    err = np.empty((iterations, chains))
    for r in range(chains):
        X = rng.standard_normal((T, d))
        w_star = rng.standard_normal(d)
        pinv = np.linalg.pinv(X)  # (X^T X)^{-1} X^T for full-rank X
        w_prev = w_star
        mean_target = np.zeros(d)  # running mean of per-copy OLS fits
        for i in range(1, iterations + 1):
            y = X @ w_prev + sigma * rng.standard_normal(T)
            w_fit = pinv @ y
            if mode == "replace":
                w = w_fit
            else:
                # OLS on [X; X; ...; X] stacked i times equals the mean of the
                # i per-copy OLS solutions, because every copy shares X.
                mean_target += (w_fit - mean_target) / i
                w = mean_target
            err[i - 1, r] = np.sum((w - w_star) ** 2)
            w_prev = w
    return err
