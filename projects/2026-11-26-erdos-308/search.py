"""Find one exact Egyptian-fraction witness. Run 'python3 search.py --help'."""

import argparse
import json
from collections import defaultdict
from math import gcd


def subset_bits(denominators, scale):
    reachable = 1  # Bit zero represents the empty subset.
    for d in denominators:
        reachable |= reachable << (scale // d)
    return reachable


def best_multiple(denominators, scale, q):
    if len(denominators) < 11:
        sums = {0}
        for d in denominators:
            weight = scale // d
            sums |= {v + weight for v in sums}
        return max(v for v in sums if v % q == 0)

    bits = subset_bits(denominators, scale)
    largest = bits.bit_length() - 1
    for value in range(largest - largest % q, -1, -q):
        if (bits >> value) & 1:
            return value
    raise ArithmeticError("The empty subset should be reachable")


def recover(denominators, scale, target):
    layers = [1]
    for d in denominators:
        previous = layers[-1]
        layers.append(previous | (previous << (scale // d)))
    picked = []
    for d, previous in zip(reversed(denominators), reversed(layers[:-1])):
        if not (previous >> target) & 1:
            picked.append(d)
            target -= scale // d
    if target != 0:
        raise ArithmeticError("Backtracking failed")
    return picked


def find_witness(n, k, scale):
    groups = defaultdict(list)
    for d in range(1, n + 1):
        q = d // gcd(d, scale)
        groups[q].append(d)

    core = groups.pop(1)
    remaining = k * scale
    blocks = []
    for q, denominators in groups.items():
        # A singleton outside the core cannot contribute a multiple of 1/scale.
        if len(denominators) == 1:
            continue
        chosen = best_multiple(denominators, scale * q, q)
        if 0 < chosen <= remaining * q:
            blocks.append((q, denominators, chosen))
            remaining -= chosen // q

    if not (subset_bits(core, scale) >> remaining) & 1:
        return None
    result = recover(core, scale, remaining)
    for q, denominators, chosen in blocks:
        result.extend(recover(denominators, scale * q, chosen))
    return sorted(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("k", type=int, help="integer to represent")
    parser.add_argument("N", type=int, help="maximum permitted denominator")
    parser.add_argument("--scale", type=int, default=720720)
    args = parser.parse_args()
    if min(args.k, args.N, args.scale) < 1:
        parser.error("All three inputs must be positive.")
    result = find_witness(args.N, args.k, args.scale)
    if result is None:
        raise SystemExit("This search found no witness at these parameters.")
    print(json.dumps(result))
