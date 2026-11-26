# Validation

Every row below was produced by running `python3 scripts/validation_values.py`
from the project root (NumPy, seeds fixed). The first block checks the closed
forms in `src/collapse_lab/theory.py` against hand calculations, known
constants or exact multinomial enumeration, with the same inputs as
`tests/test_theory.py` (the baseline test is `test_digamma_known_values`).
The second block checks the simulations against those closed forms, with the
same settings and seeds as `tests/test_gaussian.py`, `tests/test_discrete.py`
and `tests/test_linear.py`; "got" is the Monte Carlo mean +/- one standard
error. The tests pass a simulated row when it is within 4 standard errors
(3% relative for the marginal variance). `pytest -q`: 29 passed.

| quantity | expected | got | source |
|---|---|---|---|
| c_M(2) | 0.7978845608 | 0.7978845608 | hand: E[abs(Z)] = sqrt(2/pi), Z ~ N(0,1) |
| c_M(3) | 0.8862269255 | 0.8862269255 | hand: Gamma(1.5) = sqrt(pi)/2 |
| digamma(1) | -0.5772156649 | -0.5772156649 | known value: psi(1) = -gamma |
| digamma(0.5) | -1.9635100260 | -1.9635100260 | known value: psi(1/2) = -gamma - 2 ln 2 |
| digamma(10) | 2.2517525891 | 2.2517525891 | known value: psi(10) = H_9 - gamma (comment in test_digamma_known_values) |
| E[log Q], M=3 | -0.5772156649 | -0.5772156649 | hand: Q ~ Exp(1), E[log Q] = -gamma |
| E[s_2^2], MLE, M=10 | 0.81 | 0.810000 | hand: ((M-1)/M)^n = 0.9^2 |
| E[W2^2], n=3, M=10000 | 0.000450 | 0.000450 | Shumailov et al. arXiv:2305.17493v3 Eq. 4 leading term (3/2) n/M (rel. tol 1e-3) |
| Var(X_10), M=20 | 1.5 | 1.500000 | arXiv:2305.17493v3 Sec. 4.2: sigma^2 (1 + n/M) |
| E[H_1], p=(.5,.3,.2), M=4 | 0.4650000000 | 0.4650000000 | exact multinomial enumeration vs Wright-Fisher H0 (1-1/M) |
| E[support_1], p=(.6,.3,.1), M=5 | 2.2312000000 | 2.2312000000 | exact multinomial enumeration vs sum 1-(1-p_i)^M |
| P(token p=0.1 lost), M=5 | 0.59049 | 0.590490 | hand: 0.9^5 |
| linear replace, n=1, d=10, T=50 | 0.256410 | 0.256410 | hand: sigma^2 d n/(T-d-1) = 10/39 |
| linear replace, n=4, d=10, T=50 | 1.025641 | 1.025641 | hand: 40/39 |
| linear accumulate, n=2, d=10, T=50 | 0.320513 | 0.320513 | Gerstgrasser et al. arXiv:2404.01413 Thm 2: d/(T-d-1) (1 + 1/4) |
| Gaussian E[s_1^2], M=20 (sim) | 1.000 | 0.9959 +/- 0.0023 | theory.py: E[Q]=1 for unbiased variance |
| Gaussian E[s_10^2], M=20 (sim) | 1.000 | 0.9908 +/- 0.0091 | theory.py: E[Q]=1 for unbiased variance |
| Gaussian E[s_10], M=20 (sim) | 0.8768 | 0.8738 +/- 0.0034 | theory.py: sigma c_M^n |
| Gaussian E[s_30], M=20 (sim) | 0.6740 | 0.6712 +/- 0.0052 | theory.py: sigma c_M^n |
| Gaussian E[log s_100^2], M=20 (sim) | -5.3554 | -5.3580 +/- 0.0235 | theory.py: n (psi((M-1)/2) + log(2/(M-1))) |
| Gaussian E[log s_300^2], M=20 (sim) | -16.0662 | -15.9976 +/- 0.0404 | theory.py: n (psi((M-1)/2) + log(2/(M-1))) |
| Gaussian E[W2^2], n=10, M=20 (sim) | 0.7465 | 0.7329 +/- 0.0075 | theory.py: sigma^2 (n/M + 2 - 2 c_M^n) |
| Gaussian Var(X_10), M=20 (sim) | 1.5000 | 1.4805 | arXiv:2305.17493v3 Sec. 4.2: sigma^2 (1 + n/M) |
| Categorical E[H_10], Zipf K=20, M=50 (sim) | 0.6993 | 0.7009 +/- 0.0017 | Wright-Fisher: H0 (1-1/M)^t |
| Categorical E[H_20], Zipf K=20, M=50 (sim) | 0.5714 | 0.5755 +/- 0.0025 | Wright-Fisher: H0 (1-1/M)^t |
| Fixation probabilities, p=(.5,.3,.2) (sim) | 0.500 / 0.300 / 0.200 | 0.504 / 0.301 / 0.195 | neutral drift: P(fix i) = p_i |
| Linear replace, n=10, d=5, T=30 (sim) | 2.0833 | 2.1040 +/- 0.0283 | hand: sigma^2 d n/(T-d-1) |
| Linear replace, n=30, d=5, T=30 (sim) | 6.2500 | 6.3281 +/- 0.0882 | hand: sigma^2 d n/(T-d-1) |
| Linear accumulate, n=10, d=5, T=30 (sim) | 0.3229 | 0.3352 +/- 0.0044 | Gerstgrasser et al. Thm 2: d/(T-d-1) sum 1/i^2 |
| Linear accumulate, n=30, d=5, T=30 (sim) | 0.3359 | 0.3477 +/- 0.0047 | Gerstgrasser et al. Thm 2: d/(T-d-1) sum 1/i^2 |

## Where this demo departs from the paper

* **Only the theory sections are reproduced.** Shumailov et al. (Nature 2024;
  arXiv:2305.17493v3) also run Gaussian-mixture, VAE and OPT-125m language-model
  experiments. None of those is reproduced here.
* **Exact formulas in place of the paper's bounds.** E[W2^2] = sigma^2 (n/M + 2 - 2 c_M^n)
  is derived in this project; only its small-n/M leading term, (3/2) sigma^2 n/M,
  is compared with the paper's Eq. 4. E[s_n] = sigma c_M^n and the log-variance
  drift are this project's derivations, not equations from the paper.
* **The categorical model is plain Wright-Fisher drift**, a textbook result, used
  as a stand-in for the paper's Markov-chain argument (Sec. 4.1 of the preprint).
* **The accumulate regime** follows Gerstgrasser et al. (arXiv:2404.01413), not
  Shumailov et al. Only the linear-regression accumulate value has a theorem
  behind it (their Theorem 2); the Gaussian and categorical accumulate results
  in the demo are empirical and have no row here.
* **Large-n averages are not validated.** At large n, Monte Carlo averages of
  E[s_n^2] and E[W2^2] undershoot the exact values because a vanishing fraction of
  chains carries them (see the starred rows in the README). The tests check
  log-variance, medians and extinction counts there instead.
