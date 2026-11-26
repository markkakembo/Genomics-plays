"""Recompute every value in VALIDATION.md (run from the project root).

Hand values and closed forms use the same inputs as tests/test_theory.py.
Simulated values use the same settings and seeds as tests/test_gaussian.py,
tests/test_discrete.py and tests/test_linear.py, so each 'got' here is the
number the corresponding test asserts on.
"""
import itertools
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from collapse_lab import discrete, gaussian, linear, theory  # noqa: E402

G = 0.5772156649015329


def mc(x):
    x = np.asarray(x, dtype=float)
    return x.mean(), x.std(ddof=1) / np.sqrt(x.size)


def multinomial(p, M):
    for c in itertools.product(range(M + 1), repeat=len(p)):
        if sum(c) == M:
            pr = math.factorial(M)
            for ci, pi in zip(c, p):
                pr *= pi ** ci / math.factorial(ci)
            yield np.array(c), pr


rows = []


def row(q, exp, got, src):
    rows.append((q, exp, got, src))


# --- closed forms vs hand values --------------------------------------------
row("c_M(2)", f"{math.sqrt(2/math.pi):.10f}", f"{theory.c_M(2):.10f}", "hand: E[abs(Z)] = sqrt(2/pi), Z ~ N(0,1)")
row("c_M(3)", f"{math.sqrt(math.pi)/2:.10f}", f"{theory.c_M(3):.10f}", "hand: Gamma(1.5) = sqrt(pi)/2")
row("digamma(1)", f"{-G:.10f}", f"{theory._digamma(1.0):.10f}", "known value: psi(1) = -gamma")
row("digamma(0.5)", f"{-G-2*math.log(2):.10f}", f"{theory._digamma(0.5):.10f}", "known value: psi(1/2) = -gamma - 2 ln 2")
row("digamma(10)", "2.2517525891", f"{theory._digamma(10.0):.10f}", "known value: psi(10) = H_9 - gamma (comment in test_digamma_known_values)")
row("E[log Q], M=3", f"{-G:.10f}", f"{theory.expected_log_var_drift(3):.10f}", "hand: Q ~ Exp(1), E[log Q] = -gamma")
row("E[s_2^2], MLE, M=10", "0.81", f"{theory.expected_var_replace(2, 10, ddof=0):.6f}", "hand: ((M-1)/M)^n = 0.9^2")
row("E[W2^2], n=3, M=10000", f"{1.5*3/10000:.6f}", f"{theory.expected_w2sq_replace(3, 10000):.6f}",
    "Shumailov et al. arXiv:2305.17493v3 Eq. 4 leading term (3/2) n/M (rel. tol 1e-3)")
row("Var(X_10), M=20", "1.5", f"{theory.marginal_var_replace(10, 20):.6f}", "arXiv:2305.17493v3 Sec. 4.2: sigma^2 (1 + n/M)")
p, M = np.array([0.5, 0.3, 0.2]), 4
ex = sum(pr * theory.heterozygosity(c / M) for c, pr in multinomial(p, M))
row("E[H_1], p=(.5,.3,.2), M=4", f"{ex:.10f}", f"{theory.expected_heterozygosity(1, float(theory.heterozygosity(p)), M):.10f}",
    "exact multinomial enumeration vs Wright-Fisher H0 (1-1/M)")
p, M = np.array([0.6, 0.3, 0.1]), 5
ex = sum(pr * np.count_nonzero(c) for c, pr in multinomial(p, M))
row("E[support_1], p=(.6,.3,.1), M=5", f"{ex:.10f}", f"{theory.expected_support_after_one_step(p, M):.10f}",
    "exact multinomial enumeration vs sum 1-(1-p_i)^M")
row("P(token p=0.1 lost), M=5", "0.59049", f"{theory.one_step_loss_prob(0.1, 5):.6f}", "hand: 0.9^5")
row("linear replace, n=1, d=10, T=50", f"{10/39:.6f}", f"{theory.linear_test_error_replace(1, 10, 50):.6f}", "hand: sigma^2 d n/(T-d-1) = 10/39")
row("linear replace, n=4, d=10, T=50", f"{40/39:.6f}", f"{theory.linear_test_error_replace(4, 10, 50):.6f}", "hand: 40/39")
row("linear accumulate, n=2, d=10, T=50", f"{10/39*1.25:.6f}", f"{theory.linear_test_error_accumulate(2, 10, 50):.6f}",
    "Gerstgrasser et al. arXiv:2404.01413 Thm 2: d/(T-d-1) (1 + 1/4)")

# --- simulations vs closed forms (test settings and seeds) ------------------
rep = gaussian.simulate(300, M=20, chains=20_000, mode="replace", seed=1)
for n in (1, 10):
    m, se = mc(rep.sigma[n] ** 2)
    row(f"Gaussian E[s_{n}^2], M=20 (sim)", "1.000", f"{m:.4f} +/- {se:.4f}", "theory.py: E[Q]=1 for unbiased variance")
for n in (10, 30):
    m, se = mc(rep.sigma[n])
    row(f"Gaussian E[s_{n}], M=20 (sim)", f"{theory.expected_std_replace(n, 20):.4f}", f"{m:.4f} +/- {se:.4f}", "theory.py: sigma c_M^n")
for n in (100, 300):
    m, se = mc(np.log(rep.sigma[n] ** 2))
    row(f"Gaussian E[log s_{n}^2], M=20 (sim)", f"{n*theory.expected_log_var_drift(20):.4f}", f"{m:.4f} +/- {se:.4f}",
        "theory.py: n (psi((M-1)/2) + log(2/(M-1)))")
m, se = mc(rep.w2sq()[10])
row("Gaussian E[W2^2], n=10, M=20 (sim)", f"{theory.expected_w2sq_replace(10, 20):.4f}", f"{m:.4f} +/- {se:.4f}",
    "theory.py: sigma^2 (n/M + 2 - 2 c_M^n)")
marg = np.mean(rep.sigma[10] ** 2) + np.var(rep.mu[10])
row("Gaussian Var(X_10), M=20 (sim)", "1.5000", f"{marg:.4f}", "arXiv:2305.17493v3 Sec. 4.2: sigma^2 (1 + n/M)")

p0 = discrete.zipf(20)
sim = discrete.simulate(p0, 20, M=50, chains=4000, seed=1)
H0 = float(theory.heterozygosity(p0))
for t in (10, 20):
    m, se = mc(theory.heterozygosity(sim[t]))
    row(f"Categorical E[H_{t}], Zipf K=20, M=50 (sim)", f"{theory.expected_heterozygosity(t, H0, 50):.4f}", f"{m:.4f} +/- {se:.4f}",
        "Wright-Fisher: H0 (1-1/M)^t")
p0 = np.array([0.5, 0.3, 0.2])
fin = discrete.simulate(p0, 400, M=20, chains=3000, seed=3)[-1]
frac = np.bincount(fin.argmax(axis=1), minlength=3) / fin.shape[0]
row("Fixation probabilities, p=(.5,.3,.2) (sim)", "0.500 / 0.300 / 0.200", " / ".join(f"{f:.3f}" for f in frac),
    "neutral drift: P(fix i) = p_i")

for mode, f in (("replace", theory.linear_test_error_replace), ("accumulate", theory.linear_test_error_accumulate)):
    err = linear.simulate(30, 5, 30, chains=3000, mode=mode, seed=1)
    for n in (10, 30):
        m, se = mc(err[n - 1])
        src = "hand: sigma^2 d n/(T-d-1)" if mode == "replace" else "Gerstgrasser et al. Thm 2: d/(T-d-1) sum 1/i^2"
        row(f"Linear {mode}, n={n}, d=5, T=30 (sim)", f"{f(n, 5, 30):.4f}", f"{m:.4f} +/- {se:.4f}", src)

print("| quantity | expected | got | source |")
print("|---|---|---|---|")
for r in rows:
    print("| " + " | ".join(r) + " |")
