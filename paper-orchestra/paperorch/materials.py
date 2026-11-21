"""Loading the pre-writing materials folder (paper Sec. 3.1: I, E, T, G, F)."""
from __future__ import annotations

import csv
import glob
import os
from dataclasses import dataclass, field
from typing import List

IDEA_CANDIDATES = ["idea.md", "idea_dense.md", "idea_sparse.md"]


@dataclass
class Materials:
    root: str
    idea_path: str
    idea: str
    experimental_log: str          # experimental_log.md + any tables/*.csv rendered as markdown
    extra_notes: str = ""
    figures: List[str] = field(default_factory=list)   # optional pre-existing figures (F)


def csv_to_markdown(path: str) -> str:
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.reader(f) if r]
    if not rows:
        return ""
    head, body = rows[0], rows[1:]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(lines)


def load_materials(raw_dir: str, idea_filename: str | None = None,
                   log_filename: str = "experimental_log.md") -> Materials:
    if not os.path.isdir(raw_dir):
        raise SystemExit(f"Raw materials directory not found: {raw_dir}")
    names = [idea_filename] if idea_filename else IDEA_CANDIDATES
    idea_path = next((os.path.join(raw_dir, n) for n in names if n and os.path.exists(os.path.join(raw_dir, n))), None)
    if not idea_path:
        raise SystemExit(f"No idea file found in {raw_dir} (looked for {names})")
    log_path = os.path.join(raw_dir, log_filename)
    if not os.path.exists(log_path):
        raise SystemExit(f"No experimental log found at {log_path}")
    idea = open(idea_path, encoding="utf-8").read()
    log = open(log_path, encoding="utf-8").read()

    tables = sorted(glob.glob(os.path.join(raw_dir, "tables", "*.csv")))
    if tables:
        log += "\n\n## Results Tables (auto-imported from tables/*.csv)\n"
        for t in tables:
            name = os.path.splitext(os.path.basename(t))[0].replace("_", " ").title()
            log += f"\n### {name}\n\n{csv_to_markdown(t)}\n"

    notes = ""
    for n in sorted(glob.glob(os.path.join(raw_dir, "notes", "*.md"))):
        notes += f"\n\n--- {os.path.basename(n)} ---\n" + open(n, encoding="utf-8").read()
    if notes:
        idea += "\n\n## Additional Notes\n" + notes

    figs = sorted(f for f in glob.glob(os.path.join(raw_dir, "figures", "*"))
                  if f.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")))
    return Materials(root=raw_dir, idea_path=idea_path, idea=idea, experimental_log=log,
                     extra_notes=notes, figures=figs)
