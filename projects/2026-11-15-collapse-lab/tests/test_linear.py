import numpy as np
import pytest

from collapse_lab import linear, theory


def test_stacked_ols_equals_mean_of_per_copy_fits():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((12, 3))
    ys = [rng.standard_normal(12) for _ in range(4)]
    stacked, *_ = np.linalg.lstsq(np.vstack([X] * 4), np.concatenate(ys), rcond=None)
    mean_fit = np.mean([np.linalg.pinv(X) @ y for y in ys], axis=0)
    np.testing.assert_allclose(stacked, mean_fit, rtol=1e-10)


@pytest.mark.parametrize("mode", ["replace", "accumulate"])
def test_matches_theory(mode):
    d, T = 5, 30
    err = linear.simulate(30, d, T, chains=3000, mode=mode, seed=1)
    f = theory.linear_test_error_replace if mode == "replace" else theory.linear_test_error_accumulate
    for n in (1, 10, 30):
        e = err[n - 1]
        se = e.std(ddof=1) / np.sqrt(e.size)
        assert abs(e.mean() - f(n, d, T)) < 4 * se, (n, e.mean(), f(n, d, T))


def test_replace_grows_accumulate_bounded():
    d, T = 5, 30
    rep = linear.simulate(100, d, T, chains=300, mode="replace", seed=2).mean(axis=1)
    acc = linear.simulate(100, d, T, chains=300, mode="accumulate", seed=2).mean(axis=1)
    bound = np.pi ** 2 / 6 * d / (T - d - 1)
    assert rep[-1] > 10 * acc[-1]
    assert acc.max() < 1.2 * bound


def test_validation():
    with pytest.raises(ValueError):
        linear.simulate(1, 10, 11)
    with pytest.raises(ValueError):
        linear.simulate(1, 2, 10, mode="x")
