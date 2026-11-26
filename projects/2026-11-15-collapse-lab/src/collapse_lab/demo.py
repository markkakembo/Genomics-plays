"""Print simulation-versus-theory tables for all three toy models."""
from __future__ import annotations

import argparse

import numpy as np

from . import discrete, gaussian, linear, theory


def gaussian_table(M: int, chains: int, seed: int) -> str:
    gens = [1, 10, 100, 1000]
    rep = gaussian.simulate(max(gens), M, chains, "replace", seed=seed)
    acc = gaussian.simulate(max(gens), M, chains, "accumulate", seed=seed + 1)
    w_rep = rep.w2sq()
    drift = theory.expected_log_var_drift(M)
    lines = [
        f"1-D Gaussian N(0,1), M={M} samples per generation, {chains} chains",
        "gen | E[log s^2] sim/theory | E[s^2] sim/theory* | E[W2^2] sim/theory* | median s replace | median s accumulate",
    ]
    for n in gens:
        lines.append(
            f"{n:4d} | {np.mean(np.log(rep.sigma[n] ** 2)):8.3f}/{n * drift:8.3f}"
            f" | {np.mean(rep.sigma[n] ** 2):6.3f}/{theory.expected_var_replace(n, M):6.3f}"
            f" | {np.mean(w_rep[n]):7.3f}/{theory.expected_w2sq_replace(n, M):7.3f}"
            f" | {np.median(rep.sigma[n]):10.3g} | {np.median(acc.sigma[n]):8.3f}"
        )
    lines.append(
        "* exact expectations, but at large n they are carried by a vanishing fraction of chains, so a\n"
        "  finite Monte Carlo average undershoots them. log s^2 is a random walk with negative drift, so\n"
        "  the typical chain collapses (s -> 0) even though E[s^2] = 1 for every generation."
    )
    return "\n".join(lines)


def discrete_table(K: int, M: int, chains: int, seed: int) -> str:
    p0 = discrete.zipf(K)
    gens = [1, 10, 50, 200]
    rep = discrete.simulate(p0, max(gens), M, chains, "replace", seed=seed)
    acc = discrete.simulate(p0, max(gens), M, chains, "accumulate", seed=seed + 1)
    H0 = float(theory.heterozygosity(p0))
    lines = [
        f"Categorical Zipf(a=1.1), K={K} tokens, M={M} samples per generation, {chains} chains",
        "gen | E[H] sim/theory (replace) | tokens alive replace/accumulate | median rare-half mass replace/accumulate"
        f" (true {float(discrete.tail_mass(p0, p0)):.3f}) | chains with rare half extinct, replace",
    ]
    for n in gens:
        lines.append(
            f"{n:4d} | {np.mean(theory.heterozygosity(rep[n])):.4f}/{theory.expected_heterozygosity(n, H0, M):.4f}"
            f" | {np.mean(discrete.support_size(rep[n])):6.1f}/{np.mean(discrete.support_size(acc[n])):6.1f}"
            f" | {np.median(discrete.tail_mass(rep[n], p0)):.4f}/{np.median(discrete.tail_mass(acc[n], p0)):.4f}"
            f" | {np.mean(discrete.tail_mass(rep[n], p0) == 0):.2f}"
        )
    lines.append(
        "Each token's expected probability is conserved (a martingale), but in a typical chain the rare\n"
        "tokens die out. Tokens absent from the M real samples are missing under both regimes."
    )
    return "\n".join(lines)


def linear_table(d: int, T: int, chains: int, seed: int) -> str:
    its = [1, 5, 20, 50]
    rep = linear.simulate(max(its), d, T, chains, "replace", seed=seed)
    acc = linear.simulate(max(its), d, T, chains, "accumulate", seed=seed)
    lines = [
        f"Linear regression d={d}, T={T}, noise sigma=1, {chains} chains",
        "iter | replace sim/theory | accumulate sim/theory",
    ]
    for n in its:
        lines.append(
            f"{n:4d} | {np.mean(rep[n - 1]):7.3f}/{theory.linear_test_error_replace(n, d, T):7.3f}"
            f" | {np.mean(acc[n - 1]):6.4f}/{theory.linear_test_error_accumulate(n, d, T):6.4f}"
        )
    lines.append(f"accumulate upper bound pi^2/6 * d/(T-d-1) = {np.pi ** 2 / 6 * d / (T - d - 1):.4f}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m collapse_lab", description=__doc__)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--quick", action="store_true", help="fewer chains, for a fast look")
    a = ap.parse_args(argv)
    c = 200 if a.quick else 2000
    print(gaussian_table(M=20, chains=c, seed=a.seed))
    print()
    print(discrete_table(K=50, M=100, chains=max(c // 4, 50), seed=a.seed))
    print()
    print(linear_table(d=10, T=50, chains=max(c // 4, 50), seed=a.seed))
    return 0
