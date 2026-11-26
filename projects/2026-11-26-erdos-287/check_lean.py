"""Check interval coverage of the concrete certificate with a local Lean 4 binary."""

import json
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parent
rows = json.loads((root / "certificate.json").read_text())
points = [r[0] for r in rows]
if not all(type(p) is int and p > 0 for p in points):
    raise ValueError("Expected positive integer witnesses")
source = (root / "Coverage.lean").read_text()
source += "\nnamespace Erdos287Certificate\nset_option maxRecDepth 20000\nset_option maxHeartbeats 8000000\n"
for name, start, num, den in (("dyadic", 79, 2, 1), ("narrow", 318, 5, 4)):
    seq = ",\n".join(str(p) for p in points if p >= start)
    source += f"""
def {name}Points : List Nat := [{seq}]

theorem {name}_range (n : Nat) (lo : {start} ≤ n) (hi : n ≤ 10^100) :
    ∃ p ∈ {name}Points, n ≤ p ∧ {den} * p ≤ {num} * n :=
  covers_sound {num} {den} (10^100) {name}Points {start} (by decide +kernel) n lo hi

#print axioms {name}_range
"""
source += "end Erdos287Certificate\n"
with tempfile.TemporaryDirectory() as work:
    artifact = Path(work) / "Checked.lean"
    artifact.write_text(source)
    subprocess.run([os.environ.get("LEAN", "lean"), str(artifact)], check=True)
