"""Validate the bounded Erdős 308 certificate using only Python's standard library."""

import json
from fractions import Fraction
from math import gcd
from pathlib import Path

# This is a convenient scale for grouping fractions, not a bound on denominators.
SCALE = 720720
ROUNDING_SCALE = 10**15


def reciprocal_sum(denominators):
    # For q = d/gcd(d,SCALE), SCALE*q is a common denominator inside group q.
    groups = {}
    for d in denominators:
        q = d // gcd(d, SCALE)
        groups[q] = groups.get(q, 0) + SCALE * q // d
    return sum((Fraction(weight, SCALE*q) for q, weight in groups.items()), Fraction())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify():
    base = Path(__file__).resolve().parent
    witnesses = json.loads((base / "witnesses.json").read_text())
    limit = int((base / "bound.txt").read_text())
    maxima = []
    for k in range(1, len(witnesses) + 1):
        ds = witnesses[str(k)]
        require(ds and all(type(d) is int and d > 0 for d in ds), f"Invalid denominator for {k}")
        require(len(set(ds)) == len(ds), f"Duplicate denominator for {k}")
        require(reciprocal_sum(ds) == k, f"Incorrect sum for {k}")
        maxima.append(max(ds))
    require(maxima[0] == 1 and maxima == sorted(set(maxima)), "Invalid witness intervals")
    require(limit >= maxima[-1], "Final interval ends before the last witness")

    # H_b <= sum of termwise round-ups. All comparisons use integers.
    numerator = 0
    last = 0
    for r, (start, stop) in enumerate(zip(maxima, [d-1 for d in maxima[1:]] + [limit]), 1):
        require(start == last + 1, "Gap in interval coverage")
        for d in range(start, stop + 1):
            numerator += (ROUNDING_SCALE + d - 1) // d
        require(numerator < (r + 3) * ROUNDING_SCALE, f"Harmonic bound failed at {stop}")
        print(f"{start:>8,} .. {stop:>9,}   witnesses 1..{r:<2}   H(end) < {r+3}")
        last = stop
    print(f"Verified interval criterion for every integer N from 1 through {last:,}.")


if __name__ == "__main__":
    verify()
