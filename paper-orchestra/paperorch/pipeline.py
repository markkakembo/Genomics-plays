"""Orchestrator: Step 1 -> (Step 2 || Step 3) -> Step 4 -> Step 5, mirroring
upstream methods/paper_writer_with_plotting.py.write_single_paper."""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

from .agents.literature import LiteratureAgent
from .agents.outline import run_outline
from .agents.plotting import PlottingAgent
from .agents.refinement import RefinementAgent
from .agents.section_writer import run_section_writer
from .config import Config, UPSTREAM_DIR
from .latex import pdf_page_count, pick_engine
from .llm import make_llm
from .materials import load_materials


def resolve_template(name_or_path: str) -> str:
    if os.path.isdir(name_or_path):
        return os.path.abspath(name_or_path)
    p = os.path.join(UPSTREAM_DIR, "templates", name_or_path)
    if os.path.isdir(p):
        return p
    raise SystemExit(f"Template '{name_or_path}' not found (looked in {p}).")


def write_paper(cfg: Config, raw_dir: str, out_dir: str, idea_filename: str | None = None) -> dict:
    cfg.check_keys()
    cutoff = cfg.research_cutoff or dt.date.today().strftime("%Y-%m")
    engine = pick_engine(cfg.latex_engine)
    cfg.latex_engine = engine
    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(out_dir, "llm_calls.jsonl")
    open(log_path, "w").close()
    writer = make_llm(cfg, "writer", log_path)
    reflect = make_llm(cfg, "reflection", log_path)
    plotter = make_llm(cfg, "plotting", log_path)
    discover = make_llm(cfg, "discovery", log_path)
    # Discovery uses the cheaper model (paper: Gemini-3-Flash); intro/related-work writing uses the writer model.
    print(f"PaperOrchestra | provider={cfg.provider} writer={writer.model} discovery={discover.model} "
          f"cutoff={cutoff} latex={engine} out={out_dir}")

    mats = load_materials(raw_dir, idea_filename)
    dst_raw = os.path.join(out_dir, "raw_materials")
    if os.path.abspath(dst_raw) != os.path.abspath(raw_dir):
        shutil.rmtree(dst_raw, ignore_errors=True)
        shutil.copytree(raw_dir, dst_raw)

    tdir = resolve_template(cfg.template)
    wdir = os.path.join(out_dir, "latex_writeup")
    shutil.rmtree(wdir, ignore_errors=True)
    shutil.copytree(tdir, wdir)
    figures_dir = os.path.join(wdir, "figures")
    os.makedirs(figures_dir, exist_ok=True)
    template_tex = open(os.path.join(wdir, "template.tex"), encoding="utf-8").read()
    guidelines = open(os.path.join(wdir, "guidelines.md"), encoding="utf-8").read()

    t: dict = {}
    t0 = time.time()
    outline_path = os.path.join(out_dir, "outline.json")
    outline = run_outline(writer, mats, template_tex, guidelines, cutoff, outline_path)
    t["OutlineAgent"] = round(time.time() - t0, 1)

    # ---- Steps 2 & 3 in parallel
    t1 = time.time()

    class _LitLLM:  # discovery calls -> discovery model, writing call -> writer model
        def __init__(self):
            self.provider, self.supports_vision, self.model = discover.provider, writer.supports_vision, writer.model

        @property
        def supports_web_search(self):
            return discover.supports_web_search

        def complete(self, *a, **k):
            return (discover if k.get("task") == "discover" else writer).complete(*a, **k)

    lit_agent = LiteratureAgent(_LitLLM(), cfg, mats, template_tex, os.path.join(out_dir, "literature_agent_output"))
    plot_out = os.path.join(out_dir, "plotting_results.json")
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_lit = ex.submit(lit_agent.run, outline, cutoff)
        f_plot = ex.submit(PlottingAgent(plotter, cfg, mats, figures_dir).run, outline, plot_out) if cfg.use_plotting else None
        lit = f_lit.result()
        plots = f_plot.result() if f_plot else []
    t["Parallel_Lit_and_Plot"] = round(time.time() - t1, 1)

    figures = []
    if cfg.use_plotting:
        figures = [{"name": os.path.basename(p["image_path"]), "caption": p.get("caption", "")} for p in plots if p.get("image_path")]
    else:  # PlotOff: use the user-provided figures (F)
        for fp in mats.figures:
            shutil.copy(fp, figures_dir)
            figures.append({"name": os.path.basename(fp), "caption": ""})
    with open(os.path.join(figures_dir, "info.json"), "w") as f:
        json.dump(figures, f, indent=2)
    shutil.copy(os.path.join(lit_agent.out, "outline_v1.json"), outline_path)
    with open(os.path.join(wdir, "template.tex"), "w") as f:
        f.write(lit["tex"])
    with open(os.path.join(wdir, "references.bib"), "w") as f:
        f.write(lit["bib"])

    t2 = time.time()
    draft = run_section_writer(writer, mats, lit["outline"], lit["tex"], lit["citation_map"], figures, guidelines,
                               figures_dir, os.path.join(wdir, "raw_draft_paper.tex"))
    t["SectionWritingAgent"] = round(time.time() - t2, 1)

    rdir = os.path.join(out_dir, "content_refinement_workdir")
    shutil.rmtree(rdir, ignore_errors=True)
    shutil.copytree(wdir, rdir)
    t3 = time.time()
    final_tex, final_pdf, hist = RefinementAgent(reflect, cfg, mats, lit["citation_map"], guidelines, rdir).run(draft)
    t["ContentRefinementAgent"] = round(time.time() - t3, 1)
    t["Total"] = round(time.time() - t0, 1)

    shutil.copy(final_tex, os.path.join(out_dir, "final_paper.tex"))
    shutil.copy(final_pdf, os.path.join(out_dir, "final_paper.pdf"))
    n_calls = sum(1 for _ in open(log_path))
    summary = {"provider": cfg.provider, "models": {r: cfg.model(r) for r in ("writer", "reflection", "plotting", "discovery")},
               "cutoff": cutoff, "latex_engine": engine, "verified_papers": len(lit["citation_map"]),
               "figures": [f["name"] for f in figures], "llm_calls": n_calls, "timing_sec": t,
               "review_initial_overall": hist.get("initial_overall"), "review_final_overall": hist.get("final_overall"),
               "refinement_iterations": [(i["version"], i["outcome"]) for i in hist.get("iterations", [])],
               "final_pdf": os.path.join(out_dir, "final_paper.pdf"), "final_pdf_pages": pdf_page_count(final_pdf)}
    with open(os.path.join(out_dir, "run_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("\nDONE ->", summary["final_pdf"])
    print(json.dumps(summary, indent=2))
    return summary
