"""Turing machines in the bbchallenge "standard text format" and two simulators.

A machine with n states (A, B, C, ...) and 2 symbols (0, 1) is written as n
groups separated by "_"; each group holds the transition on reading 0, then on
reading 1, each as three characters: symbol written, move (L/R), next state.
"Z" as the next state means halt; "---" means an undefined transition, which
is also treated as halting.

Example (the BB(5) champion, Marxen & Buntrock 1989):
    1RB1LC_1RC1RB_1RD0LE_1LA1LD_1RZ0LA

Step-count convention (the one used by Rado and by bbchallenge): every
transition executed counts as one step, including the final halting one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

HALT = -1  # next-state value meaning "halt"

# A transition: (write, move, next_state). move is +1 for R, -1 for L.
Transition = Tuple[int, int, int]


@dataclass(frozen=True)
class Machine:
    """A 2-symbol Turing machine. table[state][symbol] is a Transition or None."""

    table: Tuple[Tuple[Optional[Transition], Optional[Transition]], ...]

    @property
    def n_states(self) -> int:
        return len(self.table)

    @classmethod
    def parse(cls, text: str) -> "Machine":
        groups = text.strip().split("_")
        n = len(groups)
        if n == 0 or n > 26:
            raise ValueError("expected between 1 and 26 states")
        rows = []
        for g in groups:
            if len(g) != 6:
                raise ValueError(f"bad state group {g!r}: need 6 characters")
            row = []
            for t in (g[:3], g[3:]):
                if t == "---":
                    row.append(None)
                    continue
                w, d, q = t
                if w not in "01" or d not in "LR":
                    raise ValueError(f"bad transition {t!r}")
                if q == "Z":
                    nq = HALT
                else:
                    nq = ord(q) - ord("A")
                    if not 0 <= nq < n:
                        raise ValueError(f"transition {t!r} names a missing state")
                row.append((int(w), 1 if d == "R" else -1, nq))
            rows.append(tuple(row))
        return cls(tuple(rows))

    def to_text(self) -> str:
        out = []
        for row in self.table:
            g = ""
            for t in row:
                if t is None:
                    g += "---"
                else:
                    w, d, q = t
                    g += f"{w}{'R' if d == 1 else 'L'}{'Z' if q == HALT else chr(65 + q)}"
            out.append(g)
        return "_".join(out)


@dataclass
class Result:
    halted: bool          # True if a halting (or undefined) transition was executed
    steps: int            # transitions executed (halting one included)
    ones: int             # number of 1s on the tape at the end
    head: int             # head position at the end (start position is 0)
    state: int            # state at the end (HALT if halted)
    tape: Dict[int, int]  # position -> 1, for every cell holding a 1
    infinite: bool = False  # True if a provably endless sweep into blank tape was detected


def simulate_naive(m: Machine, max_steps: int) -> Result:
    """Plain one-step-at-a-time simulation on a growable bytearray.

    This is the reference implementation: no shortcuts, easy to audit.
    """
    flat: List[Optional[Transition]] = [t for row in m.table for t in row]
    size = 1024
    tape = bytearray(size)
    origin = size // 2
    pos = origin
    state = 0
    steps = 0
    halted = False
    while steps < max_steps:
        t = flat[2 * state + tape[pos]]
        steps += 1
        if t is None:  # undefined transition: halt without writing
            halted = True
            state = HALT
            break
        w, d, q = t
        tape[pos] = w
        if q == HALT:
            pos += d
            halted = True
            state = HALT
            break
        pos += d
        state = q
        if pos < 0 or pos >= size:
            # grow the tape on both sides
            tape = bytearray(size) + tape + bytearray(size)
            pos += size
            origin += size
            size *= 3
    cells = {i - origin: 1 for i, v in enumerate(tape) if v}
    return Result(halted, steps, len(cells), pos - origin, state, cells)


def _push(stack: List[List[int]], sym: int, cnt: int) -> None:
    if cnt <= 0:
        return
    if stack and stack[-1][0] == sym:
        stack[-1][1] += cnt
    else:
        stack.append([sym, cnt])


def _pop_one(stack: List[List[int]]) -> int:
    if not stack:
        return 0
    top = stack[-1]
    top[1] -= 1
    if top[1] == 0:
        stack.pop()
    return top[0]


def simulate_fast(m: Machine, max_steps: int) -> Result:
    """Run-length-encoded simulation with exact "sweep" acceleration.

    The tape is two stacks of (symbol, count) runs. The head sits on the top
    cell of ``right``; ``left`` holds the cells to its left, nearest on top.

    Acceleration rule (exact, not heuristic): if in state q reading s the
    transition is (w, d, q) -- same state again -- the machine will keep
    applying that transition across the whole run of s in direction d. We do
    the whole run in one move and add its length to the step count. Every
    other transition is executed one step at a time. The result is identical,
    cell for cell and step for step, to ``simulate_naive`` (see the tests).
    """
    table = m.table
    left: List[List[int]] = []
    right: List[List[int]] = []
    head = 0
    state = 0
    steps = 0
    while steps < max_steps:
        s = right[-1][0] if right else 0
        t = table[state][s]
        if t is None:
            steps += 1
            return _finish(left, right, head, steps, True, HALT)
        w, d, q = t
        remaining = max_steps - steps
        if q == state:
            if d == 1:
                # sweep right across the run of s under the head
                if not right:  # s == 0 and only blanks ahead: endless
                    return _finish(left, right, head, steps, False, state, infinite=True)
                cnt = right[-1][1]
                if s == 0 and len(right) == 1:
                    return _finish(left, right, head, steps, False, state, infinite=True)
                k = min(cnt, remaining)
                right[-1][1] -= k
                if right[-1][1] == 0:
                    right.pop()
                _push(left, w, k)
                head += k
                steps += k
            else:
                # sweep left: the head cell plus the run of s just to its left
                k_left = left[-1][1] if (left and left[-1][0] == s) else 0
                if s == 0 and len(left) == (1 if k_left else 0):
                    return _finish(left, right, head, steps, False, state, infinite=True)
                k = min(1 + k_left, remaining)
                _pop_one(right)  # head cell
                if k > 1:  # take k-1 cells from the run of s on the left
                    left[-1][1] -= k - 1
                    if left[-1][1] == 0:
                        left.pop()
                _push(right, w, k)
                # move the head one cell left of the swept block
                x = _pop_one(left)
                _push(right, x, 1)
                head -= k
                steps += k
            continue
        # ordinary single step
        _pop_one(right)
        steps += 1
        if d == 1:
            _push(left, w, 1)
            head += 1
        else:
            _push(right, w, 1)
            x = _pop_one(left)
            _push(right, x, 1)
            head -= 1
        if q == HALT:
            return _finish(left, right, head, steps, True, HALT)
        state = q
    return _finish(left, right, head, steps, False, state)


def _finish(left, right, head, steps, halted, state, infinite=False) -> Result:
    cells: Dict[int, int] = {}
    pos = head - 1
    for sym, cnt in reversed(left):
        if sym:
            for i in range(cnt):
                cells[pos - i] = 1
        pos -= cnt
    pos = head
    for sym, cnt in reversed(right):
        if sym:
            for i in range(cnt):
                cells[pos + i] = 1
        pos += cnt
    return Result(halted, steps, len(cells), head, state, cells, infinite)


def count_ones_fast(m: Machine, max_steps: int) -> Tuple[bool, int, int]:
    """(halted, steps, ones) without building the cell dictionary."""
    r = simulate_fast(m, max_steps)
    return r.halted, r.steps, r.ones
