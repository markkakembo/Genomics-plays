"""Command line: python -m bb5verify {champion,run,census}."""

from __future__ import annotations

import argparse
import time

from . import CHAMPIONS
from .enumerate import census
from .machine import Machine, simulate_fast, simulate_naive


def _report(label: str, r, secs: float) -> None:
    span = (max(r.tape) - min(r.tape) + 1) if r.tape else 0
    status = "halted" if r.halted else ("runs forever (endless sweep)" if r.infinite else "did not halt within limit")
    print(f"{label}: {status}; steps={r.steps:,}; ones={r.ones:,}; span of 1s={span:,} cells; {secs:.2f}s")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bb5verify", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("champion", help="run the BB(n) champion machine (default n=5)")
    c.add_argument("-n", type=int, default=5, choices=sorted(CHAMPIONS))
    c.add_argument("--naive", action="store_true", help="also run the plain one-step simulator (about 10 s for n=5)")

    r = sub.add_parser("run", help="run any machine given in standard text format")
    r.add_argument("machine")
    r.add_argument("--max-steps", type=int, default=10**8)

    e = sub.add_parser("census", help="enumerate and classify all TNF machines with n states")
    e.add_argument("-n", type=int, default=3, choices=[1, 2, 3])
    e.add_argument("--limit", type=int, default=200, help="steps before handing a machine to the deciders")
    e.add_argument("--recheck", type=int, default=0, help="re-run each holdout for this many steps and report whether any halt")

    a = p.parse_args(argv)
    if a.cmd == "champion":
        text, exp_steps, exp_ones = CHAMPIONS[a.n]
        m = Machine.parse(text)
        print(f"BB({a.n}) champion {text}; literature: {exp_steps:,} steps, {exp_ones:,} ones")
        t = time.time(); res = simulate_fast(m, 10**9); _report("fast (run-length) simulator", res, time.time() - t)
        ok = res.halted and res.steps == exp_steps and res.ones == exp_ones
        if a.naive:
            t = time.time(); res2 = simulate_naive(m, 10**9); _report("naive one-step simulator", res2, time.time() - t)
            same = (res2.steps, res2.ones, res2.head, res2.tape) == (res.steps, res.ones, res.head, res.tape)
            print(f"simulators agree cell for cell: {same}")
            ok = ok and same
        print("MATCHES LITERATURE" if ok else "MISMATCH")
        return 0 if ok else 1
    if a.cmd == "run":
        m = Machine.parse(a.machine)
        t = time.time(); res = simulate_fast(m, a.max_steps); _report(m.to_text(), res, time.time() - t)
        return 0
    t = time.time(); cs = census(a.n, a.limit)
    print(f"{a.n}-state TNF census, step limit {a.limit}: {cs.leaves:,} leaves in {time.time() - t:.1f}s")
    print(f"  halting leaves:      {cs.halting:,}")
    print(f"  cyclers:             {cs.cyclers:,}")
    print(f"  translated cyclers:  {cs.translated_cyclers:,}")
    print(f"  holdouts (undecided):{len(cs.holdouts):,}")
    print(f"  most steps: {cs.max_steps} by {cs.max_steps_machine}")
    print(f"  most ones:  {cs.max_ones} by {cs.max_ones_machine}")
    if cs.proved:
        print(f"  no holdouts: S({a.n}) = {cs.max_steps} and Sigma({a.n}) = {cs.max_ones}, given the deciders are correct")
    else:
        print(f"  holdouts remain: {cs.max_steps} steps is only a LOWER BOUND for S({a.n})")
    if a.recheck and cs.holdouts:
        halted = [h for h in cs.holdouts if simulate_fast(Machine.parse(h), a.recheck).halted]
        print(f"  holdouts that halt within {a.recheck:,} steps: {len(halted)}")
    return 0
