# Validation

Every "got" value below was produced by this package's own code on 2026-11-15 (Python 3.13,
`PYTHONPATH=src`), by the same calls the tests in `tests/` make. Each row names the test that
asserts it. "Expected" values are published values or a hand calculation already written into
the tests or the README; the sources are listed in README.md under Sources.

| quantity | expected | got | source |
|---|---|---|---|
| BB(5) champion `1RB1LC_1RC1RB_1RD0LE_1LA1LD_1RZ0LA`: steps to halt (fast simulator) | 47,176,870 | 47,176,870 | Marxen and Buntrock, Bull. EATCS 40 (Feb 1990), Table 1; bbchallenge announcement, 2 Jul 2024 (`test_bb5_champion_fast`) |
| BB(5) champion: ones left on tape (fast simulator) | 4,098 | 4,098 | Marxen and Buntrock, Bull. EATCS 40 (Feb 1990), Table 1 (`test_bb5_champion_fast`) |
| BB(5) champion: steps and ones (naive one-step simulator) | 47,176,870 / 4,098 | 47,176,870 / 4,098 | same as above (`test_bb5_champion_naive_agrees_cell_for_cell`) |
| BB(5) champion: halted after 47,176,869 steps? | no | no (not halted, 47,176,869 steps run) | follows from the exact count 47,176,870 above (`test_bb5_does_not_halt_one_step_early`) |
| BB(4) champion `1RB1LB_1LA0LC_1RZ1LD_1RD0RA`: steps / ones, both simulators | 107 / 13 | 107 / 13 | Brady, Math. Comp. 40(162), Apr 1983: S(4) = 107, Σ(4) = 13 (`test_small_champions_match_literature`) |
| BB(3) step champion `1RB1RZ_1LB0RC_1LC1LA`: steps / ones, both simulators | 21 / 5 | 21 / 5 | Lin and Radó, J. ACM 12(2), Apr 1965: S(3) = 21; this machine's 21 steps and 5 ones as listed on the bbchallenge wiki BB(3) page (`test_small_champions_match_literature`) |
| BB(2) champion `1RB1LB_1LA1RZ`: steps / ones, both simulators | 6 / 4 | 6 / 4 | Radó, Bell Syst. Tech. J. 41, May 1962: S(2) = 6, Σ(2) = 4 (`test_small_champions_match_literature`) |
| `1RB1LB_1LA1RZ` from blank tape: halted, steps, ones, final head position | True, 6, 4, 0 | True, 6, 4, 0 | hand trace written in the test comment (`test_hand_calculated_two_state_trace`) |
| `1RB1LB_1LA1RZ` final tape | 1s at cells -2, -1, 0, 1 | 1s at cells -2, -1, 0, 1 | same hand trace (`test_hand_calculated_two_state_trace`) |
| 2-state TNF census (limit 50): max steps of a halting machine, with 0 holdouts | 6 | 6 (0 holdouts) | Radó 1962: S(2) = 6 (`test_two_states_fully_decided_matches_rado`) |
| 2-state TNF census: max ones of a halting machine | 4 | 4 | Radó 1962: Σ(2) = 4 (`test_two_states_fully_decided_matches_rado`) |
| 3-state TNF census (limit 200): max steps found (lower bound only, 184 holdouts) | 21 | 21 | Lin and Radó 1965: S(3) = 21 (`test_three_states_lower_bounds_match_lin_rado`) |
| 3-state TNF census: max ones found (lower bound only) | 6 | 6 | Lin and Radó 1965: Σ(3) = 6 (`test_three_states_lower_bounds_match_lin_rado`) |

## Checks with no external reference value

These are tested, but there is no published number to compare them with, so they are not in
the table above.

- The fast (run-length) and naive simulators agree on halted flag, steps, ones, head, state
  and full tape for 1,500 random 1- to 5-state machines at random step limits
  (`test_fast_equals_naive_on_random_machines_at_exact_step_counts`), and cell for cell on the
  BB(5) champion.
- Census counts: 1 state gives 5 TNF leaves (1 halting, 0 cyclers, 4 translated cyclers, 0
  holdouts); 2 states give 121 (37, 12, 72, 0); 3 states give 10,833 (3,543, 1,052, 6,054, 184).
  These are this program's own outputs under its own TNF conventions and step limits. They
  have not been compared with an independent enumeration.
- Decider soundness: on 400 random 3-state machines, every machine called non-halting runs
  20,000 steps without halting (`test_deciders_are_sound_on_sample`), and a too-short prefix
  of the halting BB(4) champion is not called non-halting
  (`test_deciders_reject_halting_machine_prefix`). This is sampling evidence, not a proof.

## Where the demo departs from the BB(5) result

- It checks only the lower bound S(5) ≥ 47,176,870, by running the champion. The upper bound,
  that no other 5-state machine halts later, comes from the Coq proof, which was not compiled
  or re-checked here.
- The enumerate-and-decide part runs only for 1 to 3 states, with two simple deciders
  (cyclers and translated cyclers). The BB(5) proof used much stronger deciders on about 180
  million machines. For 3 states this demo leaves 184 holdouts, so its 21 and 6 are lower
  bounds that happen to equal the known values, not a re-derivation.
- Marxen and Buntrock print the champion in a different table notation that is the
  left-right mirror of the bbchallenge text used here; mirroring a machine does not change its
  step count or number of ones.
