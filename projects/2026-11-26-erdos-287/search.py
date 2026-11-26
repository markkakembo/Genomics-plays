"""Build a deterministic chain of prime-pair certificates for Erdős 287."""

import json
from math import gcd, isqrt, prod
from pathlib import Path

LIMIT = 10**100
SMALL = 20_000
WHEEL = prod(p for p in range(3, 250, 2) if all(p % d for d in range(3, isqrt(p) + 1, 2)))


def trial(n):
    return n >= 2 and (n == 2 or n % 2 == 1 and all(n % d for d in range(3, isqrt(n) + 1, 2)))


def proth_base(n):
    """A returned base proves primality. None only rejects this candidate."""
    for base in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47):
        residue = pow(base, (n - 1) // 2, n)
        if residue == n - 1:
            return base
        if residue != 1:
            return None
    return None


def next_pair(previous):
    # The next limit needing coverage is previous+1.
    upper = 5 * (previous + 1) // 4
    max_q = (upper + 1) // 2
    exponent = (max_q.bit_length() + 1) // 2
    step = 1 << exponent
    k = (max_q - 1) // step
    if k % 2 == 0:
        k -= 1
    while k > 0:
        q = k * step + 1
        p = 2 * q - 1
        if p <= previous:
            break
        if gcd(p * q, WHEEL) == 1:
            a = proth_base(q)
            if a is not None:
                b = proth_base(p)
                if b is not None:
                    return [p, a, b]
        k -= 2

    # At small sizes the restricted Proth search can miss an entire window.
    if upper <= 10**9:
        for p in range(upper, previous, -1):
            if trial(p) and trial((p + 1) // 2):
                return [p]
    raise RuntimeError(f"No certified pair found after {previous}")


def main():
    # All small pairs give exactly the low-end exceptions.
    small_pairs = [p for p in range(3, SMALL + 1, 2) if trial(p) and trial((p + 1) // 2)]
    rows = [[p] for p in small_pairs]
    while rows[-1][0] < LIMIT:
        rows.append(next_pair(rows[-1][0]))
    output = Path(__file__).with_name("certificate.json")
    output.write_text(json.dumps(rows, separators=(",", ":")) + "\n")
    print(f"Wrote {len(rows)} prime pairs through {rows[-1][0]}")


if __name__ == "__main__":
    main()
