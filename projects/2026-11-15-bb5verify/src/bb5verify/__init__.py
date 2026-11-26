"""bb5verify: re-run the BB(5) champion and re-create the enumerate-and-decide method at small scale."""

from .machine import HALT, Machine, Result, simulate_fast, simulate_naive

__all__ = ["HALT", "Machine", "Result", "simulate_fast", "simulate_naive"]
__version__ = "0.1.0"

# Champion machines from the literature (standard text format).
CHAMPIONS = {
    2: ("1RB1LB_1LA1RZ", 6, 4),
    3: ("1RB1RZ_1LB0RC_1LC1LA", 21, 5),
    4: ("1RB1LB_1LA0LC_1RZ1LD_1RD0RA", 107, 13),
    5: ("1RB1LC_1RC1RB_1RD0LE_1LA1LD_1RZ0LA", 47_176_870, 4098),
}
