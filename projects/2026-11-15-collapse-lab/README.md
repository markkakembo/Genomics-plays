# collapse-lab

Small, theory-checked simulations of **model collapse**: what happens when each
generation of a model is trained on samples from the previous generation. Every
simulated number is printed beside an exact formula, so you can see where the
toy models agree with the mathematics, and where Monte Carlo can't show it.

Part of the *Da Vinci's Poet* series. Code is MIT-licensed. All data is synthetic.

## What happened?

On 24 July 2024 *Nature* published Shumailov, Shumaylov, Zhao, Papernot, Anderson
and Gal, "AI models collapse when trained on recursively generated data",
*Nature* 631, 755–759, doi:10.1038/s41586-024-07566-y. It is a peer-reviewed
version of the preprint arXiv:2305.17493 (first posted 27 May 2023, v3 14 April 2024).
The authors argue that when models are trained on data produced by earlier
models, and that data replaces the original, the tails of the original
distribution disappear and the models converge on a narrow, wrong distribution.
They show this in theory for discrete distributions and Gaussians, and in
experiments with Gaussian mixtures, VAEs and fine-tuned OPT-125m language models.

The question is contested. Gerstgrasser et al., "Is Model Collapse Inevitable?
Breaking the Curse of Recursion by Accumulating Real and Synthetic Data"
(arXiv:2404.01413, v1 1 April 2024, v2 29 April 2024, a preprint that was not
peer-reviewed at the time), argue that collapse depends on synthetic data
*replacing* real data. When data *accumulates*, they prove that test error stays
bounded for linear regression, and they report the same pattern for language
models, diffusion models and VAEs.

## Why does it matter?

Web text, images and code increasingly include model outputs. If future models
are trained on that web, these results say the outcome turns on the data
pipeline: whether old human data is kept, how much of the new data is
synthetic, and whether rare content survives filtering. The rare cases (rare
diseases, minority dialects, unusual chemistry) are the first to go, and they
are often the ones that matter most.

## How does it work?

Three toy models, each run under two regimes:

* **replace**: generation *k+1* is fitted only to *M* fresh samples from generation *k*;
* **accumulate**: generation *k+1* is fitted to every sample so far, including the original real ones.

| Module | Model | Exact baseline used |
|---|---|---|
| `gaussian.py` | 1-D Gaussian refit by sample mean and variance | E[s_n²] = σ² (unbiased) or σ²((M−1)/M)ⁿ (MLE); E[s_n] = σ c_Mⁿ; E[log s_n²] = n·(ψ((M−1)/2) + log(2/(M−1))); Var(X_n) = σ²(1 + n/M); E[W₂²] = σ²(n/M + 2 − 2c_Mⁿ) (ψ is the digamma function, c_M the c₄ constant) |
| `discrete.py` | Categorical ("token frequencies") refit by counts | E[H_t] = H₀(1 − 1/M)ᵗ for H = 1 − Σp²; P(token lost in one step) = (1 − p)ᴹ; P(token takes over) = p |
| `linear.py` | OLS regression refit on its own predicted labels | replace: σ²dn/(T − d − 1); accumulate: σ²d/(T − d − 1)·Σ1/i² ≤ σ²d/(T − d − 1)·π²/6 |

The derivations are in the docstrings of `src/collapse_lab/theory.py`. In short:

* **Gaussian.** With the unbiased variance estimator, s²_{k+1}/s²_k ~ χ²_{M−1}/(M−1).
  Its mean is 1, so E[s_n²] never changes, but its logarithm has a negative mean.
  So log s_n² is a random walk that drifts downward and every chain eventually
  collapses to a spike. The expectation stays at σ² only because ever fewer
  chains carry it. The variance formula σ²(1 + n/M) is the one stated in
  Section 4.2 of arXiv:2305.17493v3. The exact E[W₂²] here reduces to the
  (3/2)σ²n/M leading term of that paper's Eq. 4 when n ≪ M.
* **Discrete.** Refitting a categorical distribution to M samples from itself is
  exactly neutral **Wright–Fisher genetic drift** with population size M. This is
  a textbook result, not a new finding. Diversity decays at rate 1/M per
  generation. Rare tokens are lost first. Each chain ends in an absorbing state
  with all mass on one token, which is the paper's Markov-chain argument
  (Sec. 4.1 of the preprint).
* **Linear.** This follows the setup of Gerstgrasser et al. (Theorems 1–2): the
  design X is fixed, labels come from the previous model plus N(0, σ²) noise, and
  test inputs are drawn from N(0, I). The replace formula is the linear growth
  that Gerstgrasser et al. attribute to Dohmatob et al. (2024). It follows from
  E[(XᵀX)⁻¹] = I/(T − d − 1).

## What can we demonstrate?

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
python -m collapse_lab            # full tables (~4 s); add --quick for a fast look
pytest -q                         # 29 tests (~10 s)
```

Output of `python -m collapse_lab` (seed 0):

```
1-D Gaussian N(0,1), M=20 samples per generation, 2000 chains
gen | E[log s^2] sim/theory | E[s^2] sim/theory* | E[W2^2] sim/theory* | median s replace | median s accumulate
   1 |   -0.048/  -0.054 |  1.006/ 1.000 |   0.075/  0.076 |      0.987 |    0.976
  10 |   -0.504/  -0.536 |  1.017/ 1.000 |   0.754/  0.746 |      0.783 |    0.944
 100 |   -5.391/  -5.355 |  0.615/ 1.000 |   7.681/  6.463 |     0.0671 |    0.938
1000 |  -53.416/ -53.554 |  0.000/ 1.000 |  12.123/ 52.000 |   2.03e-12 |    0.936

Categorical Zipf(a=1.1), K=50 tokens, M=100 samples per generation, 500 chains
gen | E[H] sim/theory (replace) | tokens alive replace/accumulate | median rare-half mass replace/accumulate (true 0.125) | chains with rare half extinct, replace
   1 | 0.8911/0.8898 |   29.7/  29.7 | 0.1200/0.1300 | 0.00
  10 | 0.8163/0.8129 |   10.6/  29.7 | 0.1100/0.1260 | 0.11
  50 | 0.5498/0.5438 |    3.6/  29.7 | 0.0000/0.1240 | 0.55
 200 | 0.1270/0.1204 |    1.4/  29.7 | 0.0000/0.1245 | 0.83

Linear regression d=10, T=50, noise sigma=1, 500 chains
iter | replace sim/theory | accumulate sim/theory
   1 |   0.249/  0.256 | 0.2493/0.2564
   5 |   1.278/  1.282 | 0.3680/0.3753
  20 |   5.100/  5.128 | 0.3993/0.4093
  50 |  12.727/ 12.821 | 0.4078/0.4167
accumulate upper bound pi^2/6 * d/(T-d-1) = 0.4218
```

What to read from it:

1. **Under replace, collapse happens in the typical chain.** The median fitted
   standard deviation falls to about 2×10⁻¹² after 1000 generations, and in 83%
   of categorical chains the rarer half of the vocabulary is gone by generation 200.
2. **Under accumulate, the toy models don't collapse.** The fitted std stays near
   0.94, the vocabulary stays the same size, and linear test error approaches its
   π²/6 ceiling.
3. **Averages can hide collapse.** E[s²] is exactly 1 in every generation, and
   each token's expected probability is conserved, because both are martingales.
   The rows marked * show a finite simulation falling short of the true
   expectation at large n, because only a vanishing fraction of chains carries it.
   That is why the tests check log-variance, medians and extinction counts.
4. **Accumulating doesn't recover data that was never seen.** About 20 of the 50
   tokens are missing from the first 100 real samples, and they stay missing
   under both regimes.

The tests (`tests/`) check every closed form against hand values or exact
multinomial enumeration. They check every simulation against theory within about
4 Monte Carlo standard errors. They also check that the faster code paths
(running sums, mean-of-fits OLS) match a direct recomputation.

## What remains uncertain?

* **The toy models don't show what happens to LLMs.** They show the statistical
  mechanism. Whether frontier-scale training collapses depends on data mixing,
  filtering, curation and how much human data is kept, none of which is modelled here.
* **The paper's LLM evidence is small-scale:** OPT-125m fine-tuning, with example
  outputs shown for about ten generations. This project doesn't reproduce it.
* **Replace versus accumulate is the main point of dispute.** Shumailov et al.
  study replacement, and Gerstgrasser et al. study accumulation. Real pipelines are probably in
  between, with a growing share of synthetic data. The behaviour of that middle
  regime isn't settled by either paper or by this project.
* **The accumulate result for the Gaussian here is empirical.** This project
  doesn't derive its limit; only the linear-regression accumulate result is a
  proven theorem (Gerstgrasser et al., Theorem 2).
* **The primary article page wasn't reachable** when this was built. Paper details
  come from the bibliographic record (RePEc/IDEAS) and from the arXiv preprint
  2305.17493v3, so the published version may differ from the preprint in details.

## Sources

* Shumailov I., Shumaylov Z., Zhao Y., Papernot N., Anderson R., Gal Y. (2024). AI models collapse when trained on recursively generated data. *Nature* 631(8022), 755–759. Published 24 July 2024. doi:10.1038/s41586-024-07566-y
* Shumailov I. et al. The Curse of Recursion: Training on Generated Data Makes Models Forget. arXiv:2305.17493 (v1 27 May 2023; v3 14 April 2024). Preprint of the work above.
* Gerstgrasser M., Schaeffer R., Dey A., Rafailov R., Sleight H., Hughes J., Korbak T., Agrawal R., Pai D., Gromov A., Roberts D. A., Yang D., Donoho D. L., Koyejo S. Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data. arXiv:2404.01413 (v1 1 April 2024; v2 29 April 2024). Preprint.

## License

MIT, see `LICENSE`. No third-party data or code is included.
