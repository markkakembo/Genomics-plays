"""Small-scale re-creation of the bbchallenge method: enumerate, then decide.

This is the same *shape* of argument the BB(5) proof uses, at a size a laptop
can do in seconds (2 and 3 states):

1. Enumerate machines in Tree Normal Form (TNF): start from a machine with
   every transition undefined, run it from a blank tape, and only when it
   reaches an undefined transition branch on what that transition could be.
   States are introduced in order (A, then B, then C...), which removes
   machines that differ only by renaming states.
2. Each leaf machine either halts (we record its step count), or runs past a
   step limit and is handed to *deciders* that try to prove it never halts.
3. Machines no decider handles are *holdouts*. If there are no holdouts, the
   largest halting step count is BB(n) -- given correct deciders. If there
   are holdouts, the largest step count is only a lower bound.

Two deciders are implemented, both with a proof sketch in their docstrings:
cyclers (an exact configuration repeats) and translated cyclers (the machine
reaches a new tape record in the same state with the same nearby tape
contents, so it repeats forever while drifting). The real BB(5) proof needed
far stronger deciders (finite-automata reduction, CPS, and others) plus
hand-written Coq proofs for a few machines; none of those are here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .machine import HALT, Machine

Table = List[List[Optional[Tuple[int, int, int]]]]


@dataclass
class Census:
    n_states: int
    step_limit: int
    halting: int = 0
    cyclers: int = 0
    translated_cyclers: int = 0
    holdouts: List[str] = field(default_factory=list)
    max_steps: int = 0
    max_steps_machine: str = ""
    max_ones: int = 0
    max_ones_machine: str = ""

    @property
    def leaves(self) -> int:
        return self.halting + self.cyclers + self.translated_cyclers + len(self.holdouts)

    @property
    def proved(self) -> bool:
        return not self.holdouts


def _text(table: Table) -> str:
    return Machine(tuple(tuple(r) for r in table)).to_text()


def _run(table: Table, limit: int):
    """Run from blank tape for at most ``limit`` steps, keeping full history.

    Returns ("undefined", steps, ones, (q, s)) if an undefined transition is
    reached (steps = transitions executed before it), or
    ("limit", history) where history[t] = (state, head, tape-dict copy) for
    t = 0..limit.
    """
    tape: Dict[int, int] = {}
    head = 0
    state = 0
    history = [(state, head, dict(tape))]
    for steps in range(limit):
        s = tape.get(head, 0)
        t = table[state][s]
        if t is None:
            return ("undefined", steps, sum(tape.values()), (state, s))
        w, d, q = t
        if w:
            tape[head] = 1
        else:
            tape.pop(head, None)
        head += d
        state = q
        history.append((state, head, dict(tape)))
    return ("limit", history)


def is_cycler(history) -> bool:
    """True if some full configuration (state, head, tape) occurs twice.

    A Turing machine is deterministic, so a repeated configuration means the
    run loops between the two occurrences forever and never halts.
    """
    seen = set()
    for state, head, tape in history:
        key = (state, head, frozenset(tape.items()))
        if key in seen:
            return True
        seen.add(key)
    return False


def is_translated_cycler(history) -> bool:
    """True if the run provably repeats forever while drifting along the tape.

    Look at "record" times, when the head reaches a cell further right than
    ever before (and, mirrored, further left). Take two records t1 < t2 in
    the same state, at positions p1 < p2, and let m be the leftmost head
    position during [t1, t2]. Between t1 and t2 the machine only looked at
    cells >= m. If the tape on [m, p1] at t1 equals the tape on
    [m + (p2 - p1), p2] at t2 (everything right of a record is blank), then
    from t2 the machine faces exactly a shifted copy of what it faced at t1.
    It therefore repeats the same moves, reaches the next record in the same
    state with the same pattern, and so on forever: it never halts.
    """
    for direction in (1, -1):
        heads = [h * direction for _, h, _ in history]
        records: List[int] = [0]  # time indices of records; t=0 counts
        best = heads[0]
        for t in range(1, len(heads)):
            h = heads[t]
            if h > best:
                best = h
                state = history[t][0]
                for t1 in records:
                    if history[t1][0] != state:
                        continue
                    p1, p2 = heads[t1], h
                    if p2 <= p1:
                        continue
                    m = min(heads[t1 : t + 1])
                    delta = p2 - p1
                    tape1 = history[t1][2]
                    tape2 = history[t][2]
                    ok = True
                    for x in range(m, p1 + 1):
                        if tape1.get(x * direction, 0) != tape2.get((x + delta) * direction, 0):
                            ok = False
                            break
                    if ok:
                        return True
                records.append(t)
    return False


def census(n_states: int, step_limit: int) -> Census:
    """Enumerate every TNF machine with ``n_states`` states and classify it."""
    c = Census(n_states, step_limit)
    root: Table = [[None, None] for _ in range(n_states)]
    stack = [root]
    while stack:
        table = stack.pop()
        out = _run(table, step_limit)
        if out[0] == "undefined":
            _, steps, ones, (q, s) = out
            # Leaf: make this undefined transition the halting one (write 1).
            halt_steps = steps + 1
            halt_ones = ones + (0 if s == 1 else 1)
            hal = [list(r) for r in table]
            hal[q][s] = (1, 1, HALT)
            c.halting += 1
            if halt_steps > c.max_steps:
                c.max_steps, c.max_steps_machine = halt_steps, _text(hal)
            if halt_ones > c.max_ones:
                c.max_ones, c.max_ones_machine = halt_ones, _text(hal)
            defined = sum(t is not None for r in table for t in r)
            if defined == 2 * n_states - 1:
                continue  # filling the last slot with a non-halt cannot halt
            used = max([0] + [t[2] for r in table for t in r if t is not None and t[2] != HALT])
            for nq in range(min(used + 1, n_states - 1) + 1):
                for w in (0, 1):
                    for d in (1, -1):
                        child = [list(r) for r in table]
                        child[q][s] = (w, d, nq)
                        stack.append(child)
            continue
        history = out[1]
        if is_cycler(history):
            c.cyclers += 1
        elif is_translated_cycler(history):
            c.translated_cyclers += 1
        else:
            c.holdouts.append(_text(table))
    return c
