"""Let pytest find this project's package when the suite runs from the repository root."""
import pathlib
import sys

_src = pathlib.Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

try:  # NumPy is this project's only dependency; skip its tests where it isn't installed.
    import numpy  # noqa: F401
except ImportError:
    collect_ignore_glob = ["tests/*"]
