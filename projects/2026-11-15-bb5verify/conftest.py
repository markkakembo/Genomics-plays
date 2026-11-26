"""Let pytest find this project's package when the suite runs from the repository root."""
import pathlib
import sys

_src = pathlib.Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
