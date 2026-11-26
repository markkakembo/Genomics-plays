"""Recursive refitting of a 1-D Gaussian, under 'replace' or 'accumulate' data regimes."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class GaussianChains:
    """Fitted parameters of R independent chains for generations 0..n.

    mu[k, r], sigma[k, r] are the fitted mean and std of chain r at generation k.
    Row 0 is the true distribution.
    """

    mu: np.ndarray
    sigma: np.ndarray

    def w2sq(self, mu0: float = 0.0, sigma0: float = 1.0) -> np.ndarray:
        """Squared 2-Wasserstein distance of each fitted model to the truth."""
        return (self.mu - mu0) ** 2 + (self.sigma - sigma0) ** 2


def simulate(
    generations: int,
    M: int,
    chains: int = 1000,
    mode: str = "replace",
    ddof: int = 1,
    mu0: float = 0.0,
    sigma0: float = 1.0,
    seed: int | None = 0,
) -> GaussianChains:
    """Run `chains` independent copies of the recursive-training loop.

    Generation 1 is fitted to M real samples. Each later generation draws M new
    samples from the current model and refits.

    mode='replace':    fit only on the M newest samples (old data discarded).
    mode='accumulate': fit on every sample ever drawn, the real ones included.
    """
    if mode not in ("replace", "accumulate"):
        raise ValueError("mode must be 'replace' or 'accumulate'")
    if M < 2:
        raise ValueError("need M >= 2")
    rng = np.random.default_rng(seed)
    mu = np.empty((generations + 1, chains))
    sd = np.empty((generations + 1, chains))
    mu[0], sd[0] = mu0, sigma0
    # Running sufficient statistics for the accumulate regime.
    count = 0
    s1 = np.zeros(chains)
    s2 = np.zeros(chains)
    for k in range(1, generations + 1):
        x = rng.standard_normal((M, chains)) * sd[k - 1] + mu[k - 1]
        if mode == "replace":
            mu[k] = x.mean(axis=0)
            sd[k] = x.std(axis=0, ddof=ddof)
        else:
            count += M
            s1 += x.sum(axis=0)
            s2 += (x * x).sum(axis=0)
            m = s1 / count
            ss = np.maximum(s2 - count * m * m, 0.0)
            mu[k] = m
            sd[k] = np.sqrt(ss / (count - ddof))
    return GaussianChains(mu=mu, sigma=sd)
