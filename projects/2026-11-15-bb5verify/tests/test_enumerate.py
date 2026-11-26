import random

from bb5verify.enumerate import _run, census, is_cycler, is_translated_cycler
from bb5verify.machine import Machine, simulate_fast


def _table(text):
    return [list(r) for r in Machine.parse(text).table]


def test_one_state():
    c = census(1, 20)
    assert c.proved and c.max_steps == 1 and c.max_ones == 1


def test_two_states_fully_decided_matches_rado():
    # Rado (1962): S(2) = 6, Sigma(2) = 4.
    c = census(2, 50)
    assert c.proved
    assert c.max_steps == 6
    assert c.max_ones == 4
    assert c.leaves == c.halting + c.cyclers + c.translated_cyclers


def test_three_states_lower_bounds_match_lin_rado():
    # Lin & Rado (1965): S(3) = 21, Sigma(3) = 6. Our simple deciders leave
    # holdouts, so here these are lower bounds that must equal the known values.
    c = census(3, 200)
    assert c.max_steps == 21
    assert c.max_ones == 6
    assert not c.proved and len(c.holdouts) > 0
    # no holdout halts within 10^4 further steps (evidence, not proof)
    assert not any(simulate_fast(Machine.parse(h), 10**4).halted for h in c.holdouts)


def test_cycler_decider_on_known_cycler():
    out = _run(_table("0RB---_0LA---"), 100)  # steps right, left, right... on blank tape
    assert out[0] == "limit"
    assert is_cycler(out[1])


def test_translated_cycler_decider_on_known_example():
    out = _run(_table("1RA---"), 50)  # writes 1s rightwards forever
    assert out[0] == "limit"
    assert not is_cycler(out[1])
    assert is_translated_cycler(out[1])


def test_deciders_reject_halting_machine_prefix():
    # The BB(4) champion, run for fewer steps than it needs to halt, must not
    # be classified as non-halting by either decider (soundness check).
    out = _run(_table("1RB1LB_1LA0LC_1RZ1LD_1RD0RA"), 100)
    assert out[0] == "limit"
    assert not is_cycler(out[1]) and not is_translated_cycler(out[1])


def test_deciders_are_sound_on_sample():
    # Every machine a decider calls non-halting must indeed not halt in a
    # much longer run.
    rng = random.Random(5)
    seen = 0
    # random 3-state machines with one undefined (halting) slot
    for _ in range(400):
        rows = [[(rng.randrange(2), rng.choice((1, -1)), rng.randrange(3)) for _ in range(2)] for _ in range(3)]
        rows[rng.randrange(3)][rng.randrange(2)] = None
        out = _run(rows, 150)
        if out[0] != "limit":
            continue
        if is_cycler(out[1]) or is_translated_cycler(out[1]):
            seen += 1
            m = Machine(tuple(tuple(r) for r in rows))
            assert not simulate_fast(m, 20_000).halted, m.to_text()
    assert seen > 50
