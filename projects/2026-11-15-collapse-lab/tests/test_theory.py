"""Closed forms checked against hand calculation or exact enumeration."""
import itertools
import math

import numpy as np
import pytest

from collapse_lab import theory

EULER_GAMMA = 0.5772156649015329


def test_c_M_hand_values():
    # M=2: E|Z| = sqrt(2/pi)
    assert theory.c_M(2) == pytest.approx(math.sqrt(2 / math.pi), rel=1e-12)
    # M=3: E[sqrt(chi2_2/2)] = Gamma(1.5) = sqrt(pi)/2
    assert theory.c_M(3) == pytest.approx(math.sqrt(math.pi) / 2, rel=1e-12)
    # large M: c4 ~ 1 - 1/(4M)
    assert theory.c_M(1000) == pytest.approx(1 - 1 / 4000, abs=1e-6)
    with pytest.raises(ValueError):
        theory.c_M(1)


def test_digamma_known_values():
    # Standard digamma identities: psi(1) = -gamma, psi(1/2) = -gamma - 2 ln 2,
    # psi(n) = -gamma + sum_{k=1}^{n-1} 1/k, so psi(10) = H_9 - gamma = 2.2517525890667...
    assert theory._digamma(1.0) == pytest.approx(-EULER_GAMMA, abs=1e-10)
    assert theory._digamma(0.5) == pytest.approx(-EULER_GAMMA - 2 * math.log(2), abs=1e-10)
    assert theory._digamma(10.0) == pytest.approx(2.251752589066721, abs=1e-10)


def test_log_variance_drift_negative_and_matches_hand_value():
    # M=3: Q ~ chi2_2/2 ~ Exp(1), E[log Q] = -gamma
    assert theory.expected_log_var_drift(3) == pytest.approx(-EULER_GAMMA, abs=1e-10)
    for M in (2, 5, 20, 200):
        assert theory.expected_log_var_drift(M) < 0


def test_expected_variance_both_estimators():
    assert theory.expected_var_replace(50, 10, ddof=1) == 1.0
    assert theory.expected_var_replace(2, 10, ddof=0) == pytest.approx(0.81)
    with pytest.raises(ValueError):
        theory.expected_var_replace(1, 10, ddof=2)


def test_w2_small_n_matches_paper_leading_term():
    # Shumailov et al. Eq. 4 leading term: (3/2) sigma^2 n / M for n << M
    M, n = 10_000, 3
    assert theory.expected_w2sq_replace(n, M) == pytest.approx(1.5 * n / M, rel=1e-3)
    assert theory.expected_w2sq_replace(0, M) == 0.0


def test_marginal_variance():
    assert theory.marginal_var_replace(10, 20) == pytest.approx(1.5)


def _multinomial_outcomes(p, M):
    K = len(p)
    for counts in itertools.product(range(M + 1), repeat=K):
        if sum(counts) != M:
            continue
        prob = math.factorial(M)
        for c, pi in zip(counts, p):
            prob *= pi ** c / math.factorial(c)
        yield np.array(counts), prob


def test_heterozygosity_one_step_exact_enumeration():
    p, M = np.array([0.5, 0.3, 0.2]), 4
    exact = sum(prob * theory.heterozygosity(c / M) for c, prob in _multinomial_outcomes(p, M))
    H0 = float(theory.heterozygosity(p))
    assert exact == pytest.approx(theory.expected_heterozygosity(1, H0, M), rel=1e-12)
    # hand case: p=(1/2,1/2), M=2 -> E[H'] = 0.5 * 0.5 = 0.25
    assert theory.expected_heterozygosity(1, 0.5, 2) == 0.25


def test_support_and_loss_exact_enumeration():
    p, M = np.array([0.6, 0.3, 0.1]), 5
    exact_support = sum(prob * np.count_nonzero(c) for c, prob in _multinomial_outcomes(p, M))
    assert exact_support == pytest.approx(theory.expected_support_after_one_step(p, M), rel=1e-12)
    exact_loss = sum(prob for c, prob in _multinomial_outcomes(p, M) if c[2] == 0)
    assert exact_loss == pytest.approx(theory.one_step_loss_prob(0.1, M), rel=1e-12)
    assert theory.one_step_loss_prob(0.1, 5) == pytest.approx(0.59049)


def test_linear_formulas_hand_values():
    assert theory.linear_test_error_replace(1, 10, 50) == pytest.approx(10 / 39)
    assert theory.linear_test_error_replace(4, 10, 50) == pytest.approx(40 / 39)
    assert theory.linear_test_error_accumulate(2, 10, 50) == pytest.approx(10 / 39 * 1.25)
    bound = 10 / 39 * math.pi ** 2 / 6
    assert theory.linear_test_error_accumulate(10_000, 10, 50) < bound
    with pytest.raises(ValueError):
        theory.linear_test_error_replace(1, 10, 11)
