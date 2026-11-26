# bb5verify

Part of the *Da Vinci's Poet* series. Code is MIT-licensed.

A small, dependency-free Python package that

1. re-runs the fifth Busy Beaver champion machine and checks that it halts after exactly
   **47,176,870** steps, using two independent simulators that must agree cell for cell; and
2. rebuilds the *enumerate-then-decide* method behind the BB(5) proof at a size a laptop can
   handle (1 to 3 states), so you can see how it works and where its limits are.

It does **not** re-check the BB(5) proof itself. See "What remains uncertain" below.

## What happened?

On **2 July 2024** the Busy Beaver Challenge (bbchallenge), an online collaboration, announced
that it had proved **BB(5) = 47,176,870**
([announcement, 2 Jul 2024](https://discuss.bbchallenge.org/t/july-2nd-2024-we-have-proved-bb-5-47-176-870/237)).
Here BB(5) is the largest number of steps that any 5-state, 2-symbol Turing machine can run
from a blank tape and still halt. The proof is written in the Coq proof assistant
([ccz181078/Coq-BB5](https://github.com/ccz181078/Coq-BB5), by the contributor mxdys). The
announcement says it compiles in about 10 hours on a standard laptop, and that Coq experts
Yannick Forster and Théo Zimmermann reviewed its formal statement.

The value itself was not new. The champion machine `1RB1LC_1RC1RB_1RD0LE_1LA1LD_1RZ0LA` was
found by Heiner Marxen and Jürgen Buntrock in 1989 (published as "Attacking the Busy Beaver 5",
*Bulletin of the EATCS* 40, 1990). What was new was the proof that **no** 5-state machine that
halts runs longer.

## Why does it matter?

- Tibor Radó defined the Busy Beaver function in 1962 ("On non-computable functions",
  *Bell System Technical Journal* 41, May 1962). It grows faster than any computable function, so
  each new value has to be fought for. The values before this were S(2) = 6 (Radó 1962),
  S(3) = 21 (Lin and Radó, *J. ACM* 12(2), 1965) and S(4) = 107 (Brady, *Mathematics of
  Computation* 40(162), 1983). S(5) had been open since then.
- It is a clear example of a result settled by an open online collaboration and backed by a machine-checked proof rather than by trust in a large
  unchecked computer search.

## How does it work?

**Machine format.** A machine is written in bbchallenge's standard text format. There is one
6-character group per state (A, B, C, ...). Each group holds the action on reading 0 and then
on reading 1, each as *write, move, next state*. `Z` means halt and `---` means undefined.

**Two simulators** (`src/bb5verify/machine.py`):

- `simulate_naive` executes one transition at a time on a growable `bytearray`. It is the
  reference: there are no shortcuts, it is easy to audit, and it takes about 8 s for BB(5).
- `simulate_fast` stores the tape as runs of equal symbols. When a transition sends the
  machine back into the same state (for example the champion's `B1 -> 1RB` and `D1 -> 1LD`),
  the machine must sweep across the whole run, so the simulator does that sweep in one move.
  This is exact, not a heuristic. It runs BB(5) in about 0.05 s and is tested against the
  naive simulator on 1,500 random machines at exact step counts.

The step count includes the final halting transition, which is the convention used by Radó
and by bbchallenge.

**Enumerate and decide** (`src/bb5verify/enumerate.py`) is the same shape of argument the
BB(5) proof uses:

1. Enumerate machines in *Tree Normal Form*. Run a partly defined machine from a blank tape,
   and branch on an undefined transition only when the machine actually reaches it,
   introducing states in order. This skips machines that differ only by renaming states and
   transitions that are never used.
2. Each leaf machine either halts or runs past a step limit. Past the limit it goes to
   *deciders* that try to prove it never halts:
   - **cyclers**: the full configuration repeats exactly;
   - **translated cyclers**: the machine reaches a new tape record in the same state, with
     the same tape contents over the region it used since the last record, so it repeats
     forever while drifting.

   Both deciders have a proof sketch in their docstrings.
3. Machines that no decider handles are **holdouts**. If there are none, the largest halting
   step count is S(n), provided the deciders are correct. Otherwise it is only a lower bound.

The real BB(5) proof needed much stronger deciders, among them finite-automata reduction
(FAR), weighted FAR, closed-position-set (CPS) deciders, a shift-overflow counter, and
individual proofs for a few machines. It applied them to about 180 million machines left
after symmetry reductions, per the announcement. None of that is reproduced here.

## What can we demonstrate?

```text
$ bb5verify champion --naive
BB(5) champion 1RB1LC_1RC1RB_1RD0LE_1LA1LD_1RZ0LA; literature: 47,176,870 steps, 4,098 ones
fast (run-length) simulator: halted; steps=47,176,870; ones=4,098; span of 1s=12,289 cells; 0.05s
naive one-step simulator: halted; steps=47,176,870; ones=4,098; span of 1s=12,289 cells; 8.10s
simulators agree cell for cell: True
MATCHES LITERATURE
```

| States | TNF leaves | halting | cyclers | translated cyclers | holdouts | max steps | max ones |
|---|---|---|---|---|---|---|---|
| 1 | 5 | 1 | 0 | 4 | 0 | 1 | 1 |
| 2 | 121 | 37 | 12 | 72 | **0** | **6** (= S(2)) | **4** (= Σ(2)) |
| 3 | 10,833 | 3,543 | 1,052 | 6,054 | **184** | 21 (lower bound; equals S(3)) | 6 (lower bound; equals Σ(3)) |

The step limit was 50 for 2 states and 200 for 3 states.

- For **2 states** our two deciders close every case, so this little program re-derives
  S(2) = 6 and Σ(2) = 4 on its own (provided the deciders are correct).
- For **3 states**, 184 holdouts remain. These are machines whose non-halting needs stronger
  arguments, such as "bouncers" that sweep back and forth over a growing tape. So 21 is only a
  lower bound here, although it equals the known value. None of the 184 halts within
  1,000,000 steps (`bb5verify census -n 3 --recheck 1000000`, about 1 minute). That is
  evidence, not proof.

This is the BB(5) story in miniature. Finding the champion was easy; the hard part was
proving that every holdout never halts.

The BB(2), BB(3) and BB(4) champions (6/4, 21/5 and 107/13 steps/ones) are reproduced in the
tests as well.

## Install and run

Requires Python 3.9 or later and has no runtime dependencies.

```bash
pip install .                     # or: pip install -e ".[test]"
bb5verify champion                # BB(5) with the fast simulator
bb5verify champion --naive        # also the plain simulator, ~10 s
bb5verify champion -n 4           # any of n = 2..5
bb5verify run 1RB1LB_1LA1RZ       # any machine in standard text format
bb5verify census -n 3 --limit 200 # enumerate and classify all 3-state TNF machines
python -m pytest -q               # 21 tests, ~20 s (includes the 47M-step naive run)
```

Without installing, run `PYTHONPATH=src python -m bb5verify champion`.

## What remains uncertain?

- **This package does not verify that BB(5) = 47,176,870.** It verifies only the easy half:
  the champion halts after exactly that many steps, so S(5) ≥ 47,176,870. The hard half, that
  every other 5-state machine either halts sooner or never halts, rests on the Coq proof. We
  did not compile that proof in this run.
- **The result's status.** In July 2024 it was a machine-checked proof plus a community
  announcement, with a human-readable write-up still in progress. That write-up is now the
  preprint "Determination of the fifth Busy Beaver value" by the bbchallenge Collaboration
  (arXiv:2509.12337, first submitted 15 September 2025, v2 23 March 2026), which reports
  enumerating 181,385,789 five-state machines. As of 24 November 2026 the arXiv listing shows no
  journal reference. Trust rests on the Coq kernel and on the formal statement matching the
  informal claim.
- **"BB(5)" can mean different things.** The announcement notes that the notation is
  historically ambiguous. Here it means the maximum step count S(5). The champion leaves 4,098
  ones (we reproduce this), but this package makes no claim about whether Σ(5) = 4,098 was
  part of what was proved.
- **Our deciders.** They are argued for in the docstrings and tested for soundness on samples,
  but they are not formally verified. The 2-state result "S(2) = 6" depends on them being
  correct and on the TNF enumeration being complete.

## Sources

All links below were opened on 2026-11-15 (the Lin and Radó DOI was not reachable from here; its
bibliographic record was opened instead).

- bbchallenge, "July 2nd 2024: We have proved BB(5) = 47,176,870", posted 2 July 2024 (primary
  source), https://discuss.bbchallenge.org/t/july-2nd-2024-we-have-proved-bb-5-47-176-870/237
- mxdys et al., Coq-BB5 proof repository, https://github.com/ccz181078/Coq-BB5, linked from the
  announcement of 2 July 2024; accessed 2026-11-15 (the live page shows later content than July 2024).
- The bbchallenge Collaboration et al., "Determination of the fifth Busy Beaver value",
  arXiv:2509.12337 (submitted 15 September 2025; v2 23 March 2026), opened 2026-11-24,
  https://arxiv.org/abs/2509.12337
- T. Radó, "On non-computable functions", *Bell System Technical Journal* 41, pp. 877–884,
  May 1962, doi:10.1002/j.1538-7305.1962.tb00480.x
- S. Lin and T. Radó, "Computer studies of Turing machine problems", *J. ACM* 12(2), pp. 196–212,
  April 1965, doi:10.1145/321264.321270 (record: https://projects.csail.mit.edu/jacm/References/linr1965:196.html)
- A. H. Brady, "The determination of the value of Rado's noncomputable function Σ(k) for
  four-state Turing machines", *Mathematics of Computation* 40(162), pp. 647–665, April 1983,
  doi:10.1090/S0025-5718-1983-0689479-6
- H. Marxen and J. Buntrock, "Attacking the Busy Beaver 5", *Bulletin of the EATCS* 40,
  pp. 247–251, February 1990, https://docs.bbchallenge.org/papers/MarxenAndBuntrock1990.html
- bbchallenge wiki, "BB(3)" (champion 1RB1RZ_1LB0RC_1LC1LA: 21 steps, 5 ones), accessed
  2026-11-15, https://wiki.bbchallenge.org/wiki/BB%283%29

The champion machines are published mathematical facts. No third-party code or data is
included. The licence is MIT (see `LICENSE`).
