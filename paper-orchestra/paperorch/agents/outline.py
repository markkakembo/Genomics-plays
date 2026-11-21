"""Step 1 - Outline Agent (paper Sec. 4, Step 1). One LLM call -> outline.json with
plotting_plan, intro_related_work_plan and section_plan."""
from __future__ import annotations

import json

from ..parsing import parse_json
from ..prompts import OUTLINE_SYSTEM


def run_outline(llm, materials, template_tex: str, guidelines: str, cutoff: str, out_path: str) -> dict:
    print("[1/5] Outline Agent: planning figures, literature search strategy and sections ...")
    system = OUTLINE_SYSTEM.format(cutoff_date=cutoff)
    prompt = (f"'idea.md':\n{materials.idea}\n\n'experimental_log.md':\n{materials.experimental_log}\n\n"
              f"'template.tex':\n{template_tex}\n\n'conference_guidelines.md':\n{guidelines}")
    ctx = {"idea": materials.idea, "log": materials.experimental_log, "template": template_tex, "cutoff": cutoff}
    outline = None
    for _ in range(3):
        outline = parse_json(llm.complete(prompt, system=system, task="outline", ctx=ctx))
        if isinstance(outline, dict) and {"plotting_plan", "intro_related_work_plan", "section_plan"} <= set(outline):
            break
        print("   ! outline missing required keys, retrying")
    if not isinstance(outline, dict):
        raise RuntimeError("Outline Agent did not return valid JSON")
    with open(out_path, "w") as f:
        json.dump(outline, f, indent=2)
    print(f"   -> {len(outline.get('plotting_plan', []))} planned figures, "
          f"{len(outline.get('section_plan', []))} planned sections; saved {out_path}")
    return outline
