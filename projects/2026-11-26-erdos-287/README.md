# Erdős 287 · Certified prime pairs in short intervals

For every integer **318 ≤ N ≤ 10¹⁰⁰**, there is a prime **p** between **N and 5N/4**, inclusive, for which **(p+1)/2 is also prime**. The certificate contains 1,188 prime pairs. At N = 318, for example, the pair is p = 397 and q = 199. At N = 317, the first qualifying p is still 397, above the upper limit of 396.25.

For the original **[N, 2N]** interval, the certificate works for every **79 ≤ N ≤ 10¹⁰⁰**. Among all positive integers through that bound, the complete exception list is **1, 6, 14–18, and 74–78**. At the last exception, 2 × 78 = 156 falls one short of the next qualifying prime, 157. At 79 the pair (157, 79) works.

## The question

The prime-pair variant of Erdős Problem 287 asks whether [N, 2N] contains such a prime for *every sufficiently large N*. The original problem is about gaps between denominators in Egyptian fraction representations of 1. The cited upstream statement explains their connection. This repository gives an independent finite computation for the prime-pair variant. The argument ends at the stated bound. Earlier work has also used chains of primes to study Erdős 287, so no priority or record claim is made.

- [Exact variant in the pinned formal-conjectures source](https://github.com/google-deepmind/formal-conjectures/blob/9097e2f90e66d2f6244209cb1c07f7120d17ec53/FormalConjectures/ErdosProblems/287.lean#L92)
- [Erdős Problems entry and discussion](https://www.erdosproblems.com/forum/thread/287)

## Run the checks

From this directory, run the following with Python 3.10 or newer. The Python programs use only the standard library.

```sh
python3 verify.py
python3 verify.py --at 318
```

To check the interval coverage of the actual chain with Lean 4.33.1, place that version of Lean on PATH and run the command below. Alternatively, set the LEAN environment variable to the executable path.

```sh
python3 check_lean.py
```

To regenerate certificate.json, run `python3 search.py`. The verifier reads the certificate independently of the search program.

## How 1,188 pairs cover the range

A prime p with prime partner (p+1)/2 certifies all integer N from ceil(4p/5) through p. If p has covered up to p, the next witness s leaves no gap whenever 4s ≤ 5(p+1). The first and last witnesses anchor the interval. Checking one inequality between successive witnesses therefore covers every intervening integer. Replacing 4 and 5 by 1 and 2 gives the dyadic version.

The verifier also enumerates every possible prime candidate up to 634 by exact trial division. This suffices to classify all N ≤ 317 in the dyadic case and confirm the narrower interval fails at 317.

## How primality is certified

Each row in certificate.json is either [p] or [p, a, b]. In both formats, q = (p+1)/2. The 213 one-entry rows use exact trial division on p and q. For each of the other 975 rows the verifier applies Proth's theorem to q with base a and to p with base b.

For an odd candidate x, write x−1 = h·2ᵉ with h odd. The verifier requires h < 2ᵉ and checks that the supplied base raised to (x−1)/2 is congruent to −1 modulo x. To see why this proves primality, take any prime divisor r of x. The base raised to h has multiplicative order exactly 2ᵉ modulo r, so 2ᵉ divides r−1. Hence every prime divisor is at least 2ᵉ+1, larger than the square root of x. A composite x would have a smaller prime divisor. [Proth's theorem](https://mathworld.wolfram.com/ProthPrime.html)

The search makes this test available for both members of a pair by choosing q = h·2ᵉ+1 and p = h·2ᵉ⁺¹+1. It filters small factors before searching for bases. A rejected candidate has no bearing on the result. Every claimed positive witness is rechecked from scratch.

## Verification scope

**Python** proves the finite primality claims by deterministic arithmetic, checks all coverage inequalities, and verifies the low-end exceptions. **Lean** checks a general interval-coverage lemma and the two concrete coverage statements for the actual list of candidate values. The translation from JSON to the Lean list is in check_lean.py. Primality is certified by the Python verifier and Proth's theorem. This is a public finite certificate, with no submission as a solution of the unrestricted problem.
