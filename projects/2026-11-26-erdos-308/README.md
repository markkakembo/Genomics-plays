# Erdős 308 · A finite certificate for the all-N question

**Result.** For each integer N between 1 and 1,835,420 inclusive, the positive integers expressible as sums of distinct reciprocals of denominators in {1,…,N} form {1,…,m} for some m. This is an exact finite result. No claim of historical priority or of a proof for every N is made.

## Why twelve witnesses suffice

Let H_N denote the sum of the reciprocals of all positive denominators through N. Let A_N be the set of nonnegative integers attainable with a subset of those denominators. The empty subset contributes zero. Every member of A_N is at most H_N. Each witness remains valid if N increases.

If k>0 is attainable, toggle denominator 1 in its representation. Removing it gives k−1 when present. Adding it gives k+1 when absent. In particular the maximum attainable value has an attainable predecessor.

Suppose 1 through r are attainable and H_N < r+3. No attainable integer exceeds r+2. If r+2 is attainable, its predecessor r+1 is attainable because its successor is too large. Otherwise r+1 is the only optional value above r. In either case, the positive attainable integers form an initial interval.

The file witnesses.json supplies one list of distinct positive denominators for each integer from 1 to 12. On the interval starting at the largest denominator in the r-th witness and ending just before the largest denominator in the next witness, all of 1 through r are attainable. For the last interval, use bound.txt as the endpoint. The verifier checks that the intervals cover the entire asserted range and that H_N < r+3 at every right endpoint. Monotonicity of H_N extends each bound to its interval.

For example, 2 = 1 + 1/2 + 1/3 + 1/6. In the final interval, all integers from 1 to 12 are attainable from N=474,994 onward. At N=1,835,420 the harmonic sum is still strictly less than 15. If 14 occurs anywhere in this interval, toggling 1 forces 13 to occur there too.

## Reproduce

From the extracted directory, run:

```sh
python3 verify.py
lean Interval.lean
```

The Python check needs only the standard library and the supplied witnesses.json and bound.txt. It checks positivity, distinctness, exact reciprocal sums, and the full chain of harmonic bounds. For a fast provable upper bound on H_b, it uses the sum of ceil(10^15/d) over d=1,…,b divided by 10^15. Every comparison uses integers. For reciprocal equality it groups by d/gcd(d,720720) and combines the group totals as exact rational numbers.

The Lean file was checked with Lean 4.33.1 using Std. It proves the interval criterion and the neighbour property for optional inclusion of denominator 1. The concrete witness and harmonic checks run in Python. The complete bounded result has not been formalized against the upstream Erdős 308 definitions. The checker for the unrestricted platform problem has received no submission from this work.

## Witness construction

The generator is optional. For instance, run:

```sh
python3 search.py 3 31 --scale 2520
```

Fix an integer scale L. Put a denominator d in group q=d/gcd(d,L). In group q, all reciprocals have common denominator Lq. A subset whose integer weights sum to a multiple of q therefore contributes an integer multiple of 1/L. The search selects large such contributions, then uses subset-sum dynamic programming on the divisors of L to fill the remaining balance exactly. Failure at a chosen scale or denominator limit is inconclusive.

The witness searches used (integer, search limit, scale):
```text
1   1        direct witness [1]
2   11       2520
3   31       2520
4   83       2520
5   227      2520
6   616      2520
7   1674     55440
8   4900     720720
9   14500    720720
10  48000    720720
11  140000   720720
12  475000   720720
```

## What remains

Croot's asymptotic theorem gives the interval property for sufficiently large N. The bound in this certificate has no proved overlap with that asymptotic range. A useful next milestone is an explicit construction that produces k by the first N with H_N ≥ k+2, for all remaining k. At a given N, this would supply every positive integer through floor(H_N)−2, enough for the toggling lemma. This condition is sufficient for the original question and may be stronger. Another route is extracting a usable explicit threshold from the published argument and closing the finite gap.

- [Pinned formal statement](https://github.com/google-deepmind/formal-conjectures/blob/9097e2f90e66d2f6244209cb1c07f7120d17ec53/FormalConjectures/ErdosProblems/308.lean)
- [Left to Solve problem brief](https://lefttosolve.com/p/Erdos308.erdos_308.variants.all_N/agent.txt)
- [Croot, On Some Questions of Erdős and Graham about Egyptian Fractions](https://ecroot.math.gatech.edu/erdos_graham.pdf)
- [Erdős Problems entry 308](https://www.erdosproblems.com/308)
