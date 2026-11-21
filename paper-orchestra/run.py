#!/usr/bin/env python3
"""CLI entry point for the PaperOrchestra re-implementation.

Examples:
  python run.py --raw_materials examples/sample_project/raw_materials --out outputs/demo --provider mock
  export OPENAI_API_KEY=...;    python run.py --raw_materials my_project/raw_materials --provider openai
  export ANTHROPIC_API_KEY=...; python run.py --raw_materials my_project/raw_materials --provider anthropic
  export GEMINI_API_KEY=...;    python run.py --raw_materials my_project/raw_materials --provider gemini   # closest to the paper
"""
import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paperorch.config import load_config  # noqa: E402
from paperorch.pipeline import write_paper  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="PaperOrchestra: raw research materials -> LaTeX paper + PDF")
    ap.add_argument("--raw_materials", required=True, help="folder with idea.md, experimental_log.md, optional tables/, figures/, notes/")
    ap.add_argument("--out", default=None, help="output folder (default outputs/run_<timestamp>)")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--provider", choices=["mock", "openai", "anthropic", "gemini"])
    ap.add_argument("--template", help="iclr2025 | cvpr2025 | path to a template folder (template.tex + guidelines.md + style files)")
    ap.add_argument("--cutoff", dest="research_cutoff", help="research cutoff YYYY-MM (papers must predate this month)")
    ap.add_argument("--idea_file", default=None, help="idea filename inside raw_materials (default: idea.md / idea_dense.md / idea_sparse.md)")
    ap.add_argument("--no_plotting", action="store_true", help="PlotOff: use figures/ from raw_materials instead of generating")
    ap.add_argument("--max_reflections", type=int)
    ap.add_argument("--max_search_tasks", type=int, help="cap literature search tasks (0 = no cap)")
    a = ap.parse_args()
    over = {"provider": a.provider, "template": a.template, "research_cutoff": a.research_cutoff,
            "max_reflections": a.max_reflections}
    if a.no_plotting:
        over["use_plotting"] = False
    cfg = load_config(a.config, over)
    if a.max_search_tasks is not None:
        cfg.lit = {**(cfg.lit or {}), "max_search_tasks": a.max_search_tasks}
    out = a.out or os.path.join("outputs", "run_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
    write_paper(cfg, a.raw_materials, out, a.idea_file)


if __name__ == "__main__":
    main()
