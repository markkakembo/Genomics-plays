"""Recursive refitting of a categorical distribution (a token-frequency 'model').

Fitting a categorical by maximum likelihood to M samples drawn from the
previous fit is exactly neutral Wright-Fisher drift with population size M.
Rare categories (the tails) are lost first, and every chain ends in an
absorbing state that puts all mass on one category.
"""
from __future__ import annotations

import numpy as np


def zipf(K: int, a: float = 1.1) -> np.ndarray:
    """A long-tailed reference distribution p_i proportional to i^-a, i = 1..K."""
    w = np.arange(1, K + 1, dtype=float) ** (-a)
    return w / w.sum()


def simulate(
    p0: np.ndarray,
    generations: int,
    M: int,
    chains: int = 1000,
    mode: str = "replace",
    seed: int | None = 0,
) -> np.ndarray:
    """Return fitted probabilities with shape (generations+1, chains, K).

    mode='replace':    refit on the M newest samples only.
    mode='accumulate': refit on all counts so far, the M real samples included.
    """
    if mode not in ("replace", "accumulate"):
        raise ValueError("mode must be 'replace' or 'accumulate'")
    p0 = np.asarray(p0, dtype=float)
    if np.any(p0 < 0) or not np.isclose(p0.sum(), 1.0):
        raise ValueError("p0 must be a probability vector")
    rng = np.random.default_rng(seed)
    K = p0.size
    out = np.empty((generations + 1, chains, K))
    out[0] = p0
    totals = np.zeros((chains, K))
    for k in range(1, generations + 1):
        counts = np.stack([rng.multinomial(M, out[k - 1, r]) for r in range(chains)])
        if mode == "replace":
            out[k] = counts / M
        else:
            totals += counts
            out[k] = totals / totals.sum(axis=1, keepdims=True)
    return out


def support_size(p: np.ndarray) -> np.ndarray:
    """Number of categories with non-zero probability, along the last axis."""
    return np.count_nonzero(p > 0, axis=-1)


def tail_mass(p: np.ndarray, p0: np.ndarray, quantile: float = 0.5) -> np.ndarray:
    """Mass the fitted model gives to the rarest categories of p0.

    The 'tail' is the set of categories whose p0 lies below the given quantile
    of p0's values (by default, the rarer half of the vocabulary).
    """
    p0 = np.asarray(p0, dtype=float)
    tail = p0 < np.quantile(p0, quantile)
    return p[..., tail].sum(axis=-1)
