"""Gaussian simulations against exact expectations (tolerances are ~4 standard errors)."""
import numpy as np
import pytest

from collapse_lab import gaussian, theory


def _close(samples, target, k=4.0):
    se = samples.std(ddof=1) / np.sqrt(samples.size)
    assert abs(samples.mean() - target) < k * se + 1e-12, (samples.mean(), target, se)


@pytest.fixture(scope="module")
def rep():
    return gaussian.simulate(300, M=20, chains=20_000, mode="replace", seed=1)


def test_unbiased_variance_is_preserved_in_expectation(rep):
    for n in (1, 5, 10):
        _close(rep.sigma[n] ** 2, theory.expected_var_replace(n, 20))


def test_mle_variance_shrinks_geometrically():
    ch = gaussian.simulate(10, M=10, chains=20_000, mode="replace", ddof=0, seed=2)
    for n in (1, 5, 10):
        _close(ch.sigma[n] ** 2, theory.expected_var_replace(n, 10, ddof=0))


def test_expected_std_decays_as_cM_power(rep):
    for n in (1, 10, 30):
        _close(rep.sigma[n], theory.expected_std_replace(n, 20))


def test_log_variance_random_walk_drift(rep):
    for n in (10, 100, 300):
        _close(np.log(rep.sigma[n] ** 2), n * theory.expected_log_var_drift(20))


def test_marginal_variance_and_w2(rep):
    n = 10
    marginal = np.mean(rep.sigma[n] ** 2) + np.var(rep.mu[n])
    assert marginal == pytest.approx(theory.marginal_var_replace(n, 20), rel=0.03)
    _close(rep.w2sq()[n], theory.expected_w2sq_replace(n, 20))


def test_replace_collapses_accumulate_does_not():
    rep = gaussian.simulate(1000, M=20, chains=500, mode="replace", seed=3)
    acc = gaussian.simulate(1000, M=20, chains=500, mode="accumulate", seed=3)
    assert np.median(rep.sigma[-1]) < 1e-6
    assert np.median(acc.sigma[-1]) > 0.8
    # accumulate: fitted std barely moves between generation 100 and 1000
    assert np.median(np.abs(acc.sigma[-1] - acc.sigma[100])) < 0.05


def test_seed_reproducibility_and_validation():
    a = gaussian.simulate(5, 4, 3, seed=7)
    b = gaussian.simulate(5, 4, 3, seed=7)
    assert np.array_equal(a.sigma, b.sigma) and np.array_equal(a.mu, b.mu)
    with pytest.raises(ValueError):
        gaussian.simulate(5, 1)
    with pytest.raises(ValueError):
        gaussian.simulate(5, 4, mode="mix")


def test_accumulate_pooled_stats_match_direct_computation():
    # Re-derive the accumulate fit from raw samples with the same RNG stream.
    M, G, R, seed = 5, 4, 3, 11
    ch = gaussian.simulate(G, M, R, mode="accumulate", seed=seed)
    rng = np.random.default_rng(seed)
    pool = [[] for _ in range(R)]
    mu, sd = np.zeros(R), np.ones(R)
    for k in range(1, G + 1):
        x = rng.standard_normal((M, R)) * sd + mu
        for r in range(R):
            pool[r].extend(x[:, r])
        mu = np.array([np.mean(p) for p in pool])
        sd = np.array([np.std(p, ddof=1) for p in pool])
        np.testing.assert_allclose(ch.mu[k], mu, rtol=1e-10)
        np.testing.assert_allclose(ch.sigma[k], sd, rtol=1e-8)
