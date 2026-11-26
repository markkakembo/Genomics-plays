"""Verify the two finite coverage claims for Erdős 287. Standard library only."""

from argparse import ArgumentParser
from bisect import bisect_left
from itertools import pairwise
import json
from math import isqrt
from pathlib import Path

LIMIT = 10**100
DYADIC_EXCEPTIONS = (1, 6, 14, 15, 16, 17, 18, 74, 75, 76, 77, 78)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prime_by_division(n):
    return n >= 2 and all(n % d != 0 for d in range(2, isqrt(n) + 1))


def check_proth(n, a):
    """Proth's theorem is sufficient under the two checked shape conditions."""
    require(n >= 3 and n % 2 == 1, "Proth candidate must be odd and at least 3")
    power_of_two = (n - 1) & -(n - 1)
    odd_part = (n - 1) // power_of_two
    require(odd_part % 2 == 1 and odd_part < power_of_two, f"Invalid Proth form for {n}")
    require(1 < a < n and pow(a, (n - 1) // 2, n) == n - 1, f"Bad Proth base for {n}")


def verify(path):
    rows = json.loads(path.read_text())
    primes = []
    for row in rows:
        require(isinstance(row, list) and len(row) in (1, 3), "Invalid row shape")
        require(all(type(x) is int and x > 0 for x in row), "Expected positive integers")
        p = row[0]
        require(p % 2 == 1 and (not primes or p > primes[-1]), "Unsorted or even witness")
        q = (p + 1) // 2
        if len(row) == 1:
            require(p <= 10**9 and prime_by_division(p) and prime_by_division(q), f"Bad pair at {p}")
        else:
            check_proth(q, row[1])
            check_proth(p, row[2])
        primes.append(p)
    require(primes and primes[-1] >= LIMIT, "Certificate ends early")

    # Exhaust all possible p for N <= 317, including the upper endpoint 2N.
    small = [p for p in range(2, 2 * 317 + 1)
             if prime_by_division(p) and prime_by_division((p + 1) // 2)]
    missing = [n for n in range(1, 318) if not any(n <= p <= 2*n for p in small)]
    require(tuple(missing) == DYADIC_EXCEPTIONS, f"Unexpected dyadic exceptions: {missing}")
    require(not any(317 <= p and 4*p <= 5*317 for p in small), "317 should be an exception")

    # Starting with 318, each new witness covers every integer after the previous one.
    start = bisect_left(primes, 318)
    require(start < len(primes) and 4*primes[start] <= 5*318, "Initial interval uncovered")
    for p, nxt in pairwise(primes[start:]):
        require(4*nxt <= 5*(p + 1), f"Gap after {p}")
    return primes


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--at", type=int, metavar="N", help="show a certified witness at N")
    args = parser.parse_args()
    primes = verify(Path(__file__).with_name("certificate.json"))
    print(f"Verified {len(primes)} prime pairs. Every N from 318 to 10^100 has N <= p <= 5N/4.")
    print("Every N from 79 to 10^100 has N <= p <= 2N. Positive dyadic exceptions:",
          ", ".join(map(str, DYADIC_EXCEPTIONS)))
    if args.at is not None:
        if not 1 <= args.at <= LIMIT:
            parser.error("N must be between 1 and 10^100 inclusive.")
        p = primes[bisect_left(primes, args.at)]
        if p > 2*args.at:
            print(f"No dyadic witness at N={args.at}.")
        else:
            print(f"N={args.at}\np={p}\nq=(p+1)/2={(p+1)//2}")


if __name__ == "__main__":
    main()
