import random

import pytest

from bb5verify import CHAMPIONS
from bb5verify.machine import HALT, Machine, simulate_fast, simulate_naive

BB5 = "1RB1LC_1RC1RB_1RD0LE_1LA1LD_1RZ0LA"


def test_parse_roundtrip():
    m = Machine.parse(BB5)
    assert m.n_states == 5
    assert m.to_text() == BB5
    assert m.table[4][0] == (1, 1, HALT)
    assert Machine.parse("1RB---_1LA1RZ").table[0][1] is None


@pytest.mark.parametrize("bad", ["1RB1L", "1RB1LC", "2RB1LB_1LA1RZ", "1XB1LB_1LA1RZ"])
def test_parse_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        Machine.parse(bad)


def test_hand_calculated_two_state_trace():
    # 1RB1LB_1LA1RZ traced by hand from a blank tape (head starts at 0):
    # t1 A0->1RB @1, t2 B0->1LA @0, t3 A1->1LB @-1, t4 B0->1LA @-2,
    # t5 A0->1RB @-1, t6 B1->1RZ @0 halt. Ones at -2..1 => 4.
    r = simulate_naive(Machine.parse("1RB1LB_1LA1RZ"), 100)
    assert (r.halted, r.steps, r.ones, r.head) == (True, 6, 4, 0)
    assert r.tape == {-2: 1, -1: 1, 0: 1, 1: 1}


@pytest.mark.parametrize("n", [2, 3, 4])
def test_small_champions_match_literature(n):
    text, steps, ones = CHAMPIONS[n]
    for sim in (simulate_naive, simulate_fast):
        r = sim(Machine.parse(text), 10**6)
        assert (r.halted, r.steps, r.ones) == (True, steps, ones)


def test_bb5_champion_fast():
    r = simulate_fast(Machine.parse(BB5), 10**8)
    assert r.halted
    assert r.steps == 47_176_870
    assert r.ones == 4098


def test_bb5_champion_naive_agrees_cell_for_cell():
    # The audit-friendly simulator, no shortcuts: about 10 s.
    m = Machine.parse(BB5)
    a = simulate_naive(m, 10**8)
    b = simulate_fast(m, 10**8)
    assert (a.halted, a.steps, a.ones) == (True, 47_176_870, 4098)
    assert (a.head, a.tape) == (b.head, b.tape)


def test_bb5_does_not_halt_one_step_early():
    r = simulate_fast(Machine.parse(BB5), 47_176_869)
    assert not r.halted and r.steps == 47_176_869


def _random_machine(rng, n):
    rows = []
    for _ in range(n):
        row = []
        for _ in range(2):
            if rng.random() < 0.08:
                row.append(None)
            else:
                q = HALT if rng.random() < 0.05 else rng.randrange(n)
                row.append((rng.randrange(2), rng.choice((1, -1)), q))
        rows.append(tuple(row))
    return Machine(tuple(rows))


def test_fast_equals_naive_on_random_machines_at_exact_step_counts():
    rng = random.Random(20240702)
    for _ in range(1500):
        m = _random_machine(rng, rng.randint(1, 5))
        limit = rng.randint(1, 3000)
        a = simulate_naive(m, limit)
        b = simulate_fast(m, limit)
        if b.infinite:
            # fast sim proved an endless sweep into blank tape; naive must not halt
            assert not a.halted
            continue
        assert (a.halted, a.steps, a.ones, a.head, a.state, a.tape) == (
            b.halted, b.steps, b.ones, b.head, b.state, b.tape), m.to_text()


def test_infinite_sweep_detection():
    r = simulate_fast(Machine.parse("1RA1RZ"), 10**9)  # marches right forever
    assert r.infinite and not r.halted
    r = simulate_fast(Machine.parse("0LA1RZ"), 10**9)
    assert r.infinite and not r.halted
