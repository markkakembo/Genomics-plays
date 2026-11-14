"""Step 2 - Plotting Agent (paper Sec. 4 Step 2; PaperBanana-style closed loop).

For each item of outline["plotting_plan"] (in parallel):
  planner -> stylist -> visualizer -> render -> VLM critic (<= N rounds, re-render on change) -> caption.
  * plot    : the LLM writes matplotlib code, executed in a sandboxed subprocess (timeout) -> PNG.
  * diagram : the paper uses an image-generation model (gemini-3-pro-image); here the LLM writes a
              standalone TikZ picture compiled with the LaTeX engine (Graphviz DOT as fallback) -> PDF+PNG.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from ..latex import compile_latex, pdf_to_pngs
from ..parsing import parse_code, parse_json
from .. import prompts as P

HARNESS_PRE = "import matplotlib\nmatplotlib.use('Agg')\n"
HARNESS_POST = """
import matplotlib.pyplot as _plt
if _plt.get_fignums():
    _plt.savefig(__OUT__, dpi=300, bbox_inches='tight')
"""


def run_plot_code(code: str, out_png: str, timeout: int = 120) -> Optional[str]:
    code = re.sub(r"plt\.show\(\s*\)", "", code)
    code = re.sub(r"(plt|fig)\.savefig\([^\n]*\)", "pass", code)
    script = HARNESS_PRE + code + HARNESS_POST.replace("__OUT__", repr(os.path.abspath(out_png)))
    with tempfile.TemporaryDirectory() as td:
        sp = os.path.join(td, "plot.py")
        with open(sp, "w") as f:
            f.write(script)
        try:
            r = subprocess.run([sys.executable, sp], cwd=td, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        if r.returncode != 0:
            print(f"   ! plot code failed: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.returncode}")
    return out_png if os.path.exists(out_png) else None


def render_tikz(code: str, out_base: str, engine: str) -> Optional[str]:
    work = os.path.dirname(out_base)
    name = os.path.basename(out_base) + "_tikz"
    with open(os.path.join(work, name + ".tex"), "w") as f:
        f.write(code)
    pdf = compile_latex(work, name, engine)
    if not pdf:
        return None
    shutil.move(pdf, out_base + ".pdf")
    tmpdir = out_base + "_pages"
    pngs = pdf_to_pngs(out_base + ".pdf", tmpdir, scale=4.0, max_pages=1)
    if pngs:
        shutil.move(pngs[0], out_base + ".png")
    shutil.rmtree(tmpdir, ignore_errors=True)
    return out_base + ".png" if os.path.exists(out_base + ".png") else None


def render_dot(code: str, out_base: str) -> Optional[str]:
    if not shutil.which("dot"):
        return None
    with open(out_base + ".dot", "w") as f:
        f.write(code)
    r = subprocess.run(["dot", "-Tpng", "-Gdpi=300", out_base + ".dot", "-o", out_base + ".png"], capture_output=True)
    return out_base + ".png" if r.returncode == 0 and os.path.exists(out_base + ".png") else None


def _raw_content(materials, data_source: str) -> str:
    ds = (data_source or "").lower()
    parts = []
    if "idea" in ds or "both" in ds:
        parts.append("--- idea.md ---\n" + materials.idea)
    if "experiment" in ds or "both" in ds:
        parts.append("--- experimental_log.md ---\n" + materials.experimental_log)
    return "\n".join(parts) or ("--- experimental_log.md ---\n" + materials.experimental_log)


class PlottingAgent:
    def __init__(self, llm, cfg, materials, figures_dir: str):
        self.llm, self.cfg, self.m, self.dir = llm, cfg, materials, figures_dir
        os.makedirs(figures_dir, exist_ok=True)

    def _render(self, kind, desc, out_base, ctx) -> Optional[str]:
        if kind == "plot":
            prompt = (f"Use python matplotlib to generate a statistical plot based on the following detailed description: "
                      f"{desc}\n Only provide the code without any explanations. Code:")
            code = parse_code(self.llm.complete(prompt, system=P.PLOT_VISUALIZER, task="plot_code", ctx=ctx), "python")
            with open(out_base + ".py", "w") as f:
                f.write(code)
            return run_plot_code(code, out_base + ".png")
        prompt = (f"Draw the following diagram as TikZ: {desc}\nNote that do not include figure titles in the image. "
                  f"Diagram (```latex standalone document):")
        code = parse_code(self.llm.complete(prompt, system=P.DIAGRAM_TIKZ_VISUALIZER, task="diagram_tikz", ctx=ctx), "latex")
        png = render_tikz(code, out_base, self.cfg.latex_engine) if "\\documentclass" in code else None
        if not png and self.llm.provider != "mock":  # Graphviz fallback
            dot = parse_code(self.llm.complete("Express this diagram as a Graphviz DOT graph (rankdir=LR, clean academic "
                                               f"style). Return only ```dot code.\n{desc}", task="diagram_dot", ctx=ctx), "dot")
            png = render_dot(dot, out_base)
        return png

    def _one(self, plan: Dict) -> Dict:
        fid = re.sub(r"[^a-zA-Z0-9_]+", "_", plan.get("figure_id", "figure")).lower().strip("_")
        kind = "plot" if "plot" in (plan.get("plot_type", "") or "").lower() or "chart" in (plan.get("plot_type", "") or "").lower() else "diagram"
        if (plan.get("plot_type") or "").lower() == "diagram":
            kind = "diagram"
        raw = _raw_content(self.m, plan.get("data_source", ""))
        intent = f"Title: {plan.get('title', '')}\nObjective: {plan.get('objective', '')}"
        ctx = {"plan": plan, "raw": raw, "kind": kind, "idea": self.m.idea, "log": self.m.experimental_log}
        print(f"   [{fid}] {kind}: planning")
        planner, stylist, critic = ((P.PLOT_PLANNER, P.PLOT_STYLIST, P.PLOT_CRITIC) if kind == "plot"
                                    else (P.DIAGRAM_PLANNER, P.DIAGRAM_STYLIST, P.DIAGRAM_CRITIC))
        labels = (("Plot Raw Data", "Visual Intent of the Desired Plot") if kind == "plot"
                  else ("Methodology Section", "Diagram Caption"))
        desc = self.llm.complete(f"Now, based on the following {labels[0].lower()} and {labels[1].lower()}, provide a detailed "
                                 f"description for the figure to be generated.\n{labels[0]}: {raw}\n{labels[1]}: {intent}\n"
                                 "Detailed description of the target figure to be generated:", system=planner,
                                 task="figure_plan", ctx=ctx).strip()
        desc = self.llm.complete(f"Detailed Description: {desc}\nStyle Guidelines: (NeurIPS-style, colour-blind safe palette)\n"
                                 f"{labels[0]}: {raw}\n{labels[1]}: {intent}\nYour Output:", system=stylist,
                                 task="figure_style", ctx=ctx).strip() or desc
        base = os.path.join(self.dir, fid)
        img = self._render(kind, desc, base, ctx)
        history = []
        for r in range(self.cfg.plotting_max_critic_rounds):
            target = [img] if img else []
            notice = "" if img else ("\n[SYSTEM NOTICE] The image could not be generated based on the current description "
                                     "(likely due to invalid code). Please check the description for errors and provide a revised version.")
            resp = self.llm.complete(f"Target for Critique:{notice}\nDetailed Description: {desc}\n{labels[0]}: {raw}\n"
                                     f"{'Visual Intent' if kind == 'plot' else 'Figure Caption'}: {intent}\nYour Output:",
                                     system=critic, images=target, task="figure_critic", ctx={**ctx, "rendered": bool(img)})
            ev = parse_json(resp) or {}
            sugg = str(ev.get("critic_suggestions", "No changes needed.")) if isinstance(ev, dict) else "No changes needed."
            rev = str(ev.get("revised_description", "No changes needed.")) if isinstance(ev, dict) else "No changes needed."
            history.append({"round": r, "suggestions": sugg})
            if sugg.strip() == "No changes needed." and img:
                break
            if rev.strip() != "No changes needed.":
                desc = rev
            new = self._render(kind, desc, base, ctx)
            img = new or img
        cap_prompt = f"""
    ## INPUT DATA
    -   Task Type: {kind}
    -   Contextual Section: {raw}
    -   Overall Figure Intent: {intent}
    -   Detailed Figure Description: {desc}

    Please provide the final caption for this figure based on the system instructions.
    Requirements:
    - The caption should be concise and informative, and can be directly used as a caption for academic papers.
    - The caption MUST NOT contain a "Figure X:" or "Caption X:" prefix, as the latex template will add it automatically.
    - The caption MUST NOT contain any markdown formatting (like bold, italics, etc), it should be plain text.

    Respond with the plain text caption only.
    """
        caption = self.llm.complete(cap_prompt, images=[img] if img else [], task="figure_caption", ctx=ctx,
                                    temperature=0.5).strip()
        caption = re.sub(r"^(\*\*)?Caption:(\*\*)?\s*", "", caption)
        res = {"figure_id": fid, "title": plan.get("title", ""), "task_name": kind, "description": desc,
               "caption": caption, "aspect_ratio": plan.get("aspect_ratio"), "critic_history": history}
        if img:
            res["image_path"] = f"figures/{os.path.basename(img)}"
            print(f"   [{fid}] done -> {img}")
        else:
            print(f"   [{fid}] FAILED to render; it will be left out of the paper")
        return res

    def run(self, outline: Dict, out_json: str) -> List[Dict]:
        plans = outline.get("plotting_plan", [])
        print(f"[2/5] Plotting Agent: {len(plans)} figures ...")
        results = []
        with ThreadPoolExecutor(max_workers=5) as ex:
            futs = [ex.submit(self._one, p) for p in plans]
            for f in as_completed(futs):
                try:
                    results.append(f.result())
                except Exception as e:  # noqa: BLE001
                    print(f"   ! figure failed: {e}")
        with open(out_json, "w") as f:
            json.dump(results, f, indent=2)
        return results
