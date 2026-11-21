"""Step 4 - Section Writing Agent (paper Sec. 4 Step 4). A single multimodal call that completes
abstract, method, experiments (tables from the experimental log), conclusion, and inserts figures."""
from __future__ import annotations

import json
import os

from ..latex import looks_complete, sanitize_citations
from ..parsing import parse_latex
from ..prompts import SECTION_WRITER_SYSTEM


def _figs_ctx(figs):
    if not figs:
        return "No figures available."
    return "\n".join(f"- Filename: figures/{f['name']}\n  Caption: {f.get('caption', '')}" for f in figs)


def _cites_ctx(cmap):
    if not cmap:
        return "No citations available."
    return "\n\n".join(f"Key: {k}\nTitle: {v['title']}\nYear: {v.get('year')}\nAbstract: {v['abstract'][:600]}"
                       for k, v in cmap.items())


def run_section_writer(llm, materials, outline, template_tex, cmap, figures, guidelines, figures_dir, out_path) -> str:
    print("[4/5] Section Writing Agent: drafting abstract, method, experiments, conclusion ...")
    user = f"""
Here are the input materials for the paper.

--- INPUT: outline.json (Structure & Citation Candidates) ---
{json.dumps(outline, indent=2)}

--- INPUT: citation_map.json (Reference Library) ---
{_cites_ctx(cmap)}

--- INPUT: idea.md (Technical Method Details) ---
{materials.idea}

--- INPUT: experimental_log.md (Raw Data for Tables) ---
{materials.experimental_log}

--- INPUT: figures_list (Available Figure Files) ---
{_figs_ctx(figures)}

--- INPUT: conference_guidelines.md ---
{guidelines}

--- INPUT: template.tex (DO NOT CHANGE EXISTING TEXT. FILL MISSING SECTIONS.) ---
{template_tex}

**INSTRUCTION**:
1. Identify missing sections in `template.tex`.
2. Generate LaTeX content for those sections based on `outline.json`.
3. Construct tables using data from `experimental_log.md`.
4. Insert figures using the filenames from the 'figures_list' input.
5. Use citations from the Reference Library.
6. Return the **full** compilable LaTeX file.
"""
    images = [os.path.join(figures_dir, f["name"]) for f in figures
              if f["name"].lower().endswith((".png", ".jpg", ".jpeg"))]
    ctx = {"template": template_tex, "outline": outline, "idea": materials.idea, "log": materials.experimental_log,
           "figures": figures, "cmap": cmap}
    tex = ""
    for _ in range(2):
        tex = parse_latex(llm.complete(user, system=SECTION_WRITER_SYSTEM, images=images, task="section_write",
                                       ctx=ctx, temperature=0.7))
        if looks_complete(tex):
            break
        print("   ! incomplete LaTeX returned, retrying")
    tex, removed = sanitize_citations(tex, set(cmap))
    if removed:
        print(f"   ! removed {len(removed)} unverified citation keys")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(tex)
    print(f"   -> draft saved to {out_path}")
    return tex
