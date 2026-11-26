import numpy as np
import pytest

from collapse_lab import discrete, theory


def test_zipf_is_a_distribution():
    p = discrete.zipf(30)
    assert p.sum() == pytest.approx(1.0) and np.all(np.diff(p) < 0)


def test_heterozygosity_decay_matches_wright_fisher():
    p0 = discrete.zipf(20)
    sim = discrete.simulate(p0, 20, M=50, chains=4000, seed=1)
    H0 = float(theory.heterozygosity(p0))
    for t in (1, 10, 20):
        h = theory.heterozygosity(sim[t])
        se = h.std(ddof=1) / np.sqrt(h.size)
        assert abs(h.mean() - theory.expected_heterozygosity(t, H0, 50)) < 4 * se


def test_one_step_support_matches_formula():
    p0 = discrete.zipf(40)
    sim = discrete.simulate(p0, 1, M=60, chains=4000, seed=2)
    s = discrete.support_size(sim[1])
    se = s.std(ddof=1) / np.sqrt(s.size)
    assert abs(s.mean() - theory.expected_support_after_one_step(p0, 60)) < 4 * se


def test_absorbing_state_and_fixation_probability():
    # Neutral drift: P(category i takes over) = p_i.
    p0 = np.array([0.5, 0.3, 0.2])
    sim = discrete.simulate(p0, 400, M=20, chains=3000, seed=3)
    final = sim[-1]
    assert np.all(np.isclose(final.max(axis=1), 1.0))  # every chain absorbed in a delta
    frac = np.bincount(final.argmax(axis=1), minlength=3) / final.shape[0]
    se = np.sqrt(p0 * (1 - p0) / final.shape[0])
    assert np.all(np.abs(frac - p0) < 4 * se)


def test_tails_lost_under_replace_kept_under_accumulate():
    p0 = discrete.zipf(50)
    rep = discrete.simulate(p0, 200, M=100, chains=200, mode="replace", seed=4)
    acc = discrete.simulate(p0, 200, M=100, chains=200, mode="accumulate", seed=4)
    # replace: support only shrinks; accumulate: support fixed after the real sample
    assert np.all(np.diff(discrete.support_size(rep), axis=0) <= 0)
    assert np.all(discrete.support_size(acc[1:]) == discrete.support_size(acc[1]))
    assert np.mean(discrete.tail_mass(rep[-1], p0) == 0) > 0.5
    assert np.mean(discrete.tail_mass(acc[-1], p0) == 0) == 0.0
    # expectation of each token's probability is conserved (martingale) under replace
    m = rep[-1].mean(axis=0)
    assert abs(discrete.tail_mass(m, p0) - discrete.tail_mass(p0, p0)) < 0.05


def test_validation():
    with pytest.raises(ValueError):
        discrete.simulate(np.array([0.5, 0.6]), 1, 10)
    with pytest.raises(ValueError):
        discrete.simulate(np.array([0.5, 0.5]), 1, 10, mode="x")
