"""Prompts. The agent prompts are imported VERBATIM from the official code in ./upstream
(Apache-2.0) so this implementation stays faithful to the paper's App. F.1. Constants living
in modules that require Gemini credentials at import time are read with `ast` instead of import.
"""
from __future__ import annotations

import ast
import os
import sys
from typing import Any, Dict

from .config import UPSTREAM_DIR

if UPSTREAM_DIR not in sys.path:
    sys.path.insert(0, UPSTREAM_DIR)

import warnings  # noqa: E402

with warnings.catch_warnings():
    warnings.simplefilter("ignore", SyntaxWarning)
    from methods.prompts.outline_agent import outline_agent_system_prompt as OUTLINE_SYSTEM  # noqa: E402
    from methods.prompts.literature_review_agent import literature_review_agent_writter_prompt as LIT_WRITER_SYSTEM  # noqa: E402
    from methods.prompts.section_writing_agent import section_writing_agent_prompt as SECTION_WRITER_SYSTEM  # noqa: E402
    from methods.prompts.content_refinement_agent import content_refinement_agent_system_prompt as REFINEMENT_SYSTEM  # noqa: E402
    from utils.prompt_utils import UNIVERSAL_NO_LEAKAGE_PROMPT  # noqa: E402,F401


def _literals(relpath: str) -> Dict[str, Any]:
    src = open(os.path.join(UPSTREAM_DIR, relpath), encoding="utf-8").read()
    out: Dict[str, Any] = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                pass
    return out


_PB = _literals("utils/paper_banana_utils.py")          # PaperBanana-derived plotting prompts
PLOT_PLANNER = _PB["PLOT_PLANNER_AGENT_SYSTEM_PROMPT"]
PLOT_STYLIST = _PB["PLOT_STYLIST_AGENT_SYSTEM_PROMPT"]
PLOT_VISUALIZER = _PB["PLOT_VISUALIZER_AGENT_SYSTEM_PROMPT"]
PLOT_CRITIC = _PB["PLOT_CRITIC_AGENT_SYSTEM_PROMPT"]
DIAGRAM_PLANNER = _PB["DIAGRAM_PLANNER_AGENT_SYSTEM_PROMPT"]
DIAGRAM_STYLIST = _PB["DIAGRAM_STYLIST_AGENT_SYSTEM_PROMPT"]
DIAGRAM_CRITIC = _PB["DIAGRAM_CRITIC_AGENT_SYSTEM_PROMPT"]

_AR = _literals("autoraters/agent_review.py")            # AgentReview reviewer used in Step 5
SCORE_CALCULATION = _AR["SCORE_CALCULATION"]
AGENTREVIEW_INSTRUCTIONS = _AR["AGENTREVIEW_INSTRUCTIONS"]
META_REVIEWER_SYSTEM = _AR["meta_reviewer_system_prompt"]


def agentreview_system_prompt() -> str:
    """'Best case' reviewer persona (knowledgeable, responsible, benign), as in upstream."""
    rub = "".join(f"* {k}: {v};\n" for k, v in SCORE_CALCULATION.items()).rstrip(";\n") + ". "
    return (
        "You are a reviewer. You write peer review of academic papers by evaluating their technical quality, originality, and clarity.\n\n"
        "Knowledgeability: You are knowledgeable, with a strong background and a PhD degree in the subject areas related to this paper. You possess the expertise necessary to scrutinize and provide insightful feedback to this paper.\n\n"
        "Responsibility: As a responsible reviewer, you highly responsibly write paper reviews. You meticulously assess a research paper's technical accuracy, innovation, and relevance. You thoroughly read the paper, critically analyze the methodologies, and carefully consider the paper's contribution to the field.\n\n"
        "Intention: As a benign reviewer, your approach to reviewing is guided by a genuine intention to aid authors in enhancing their work. You provide detailed, constructive feedback, aimed at both validating robust research and guiding authors to refine and improve their work. You are also critical of technical flaws in the paper.\n\n"
        f"## Rubrics for Overall Rating\n{rub}"
    )


# --- Prompts added by this re-implementation (not in upstream) ------------------------
DIAGRAM_TIKZ_VISUALIZER = (
    "You are an expert scientific diagram illustrator who draws with TikZ. Produce a single, "
    "self-contained LaTeX document using \\documentclass[tikz,border=6pt]{standalone} that renders the "
    "described diagram. Use only standard TikZ libraries (arrows.meta, positioning, shapes, fit, calc, "
    "backgrounds). Keep text short, use a clean academic palette, no figure title. Return only the code "
    "in a ```latex block."
)

FORMAT_REVIEW_PROMPT = """
Analyze the provided page images of a research paper for formatting issues.
You must strictly follow the provided formatting guidelines and examples. Do not create rules based on your own assumptions or general knowledge if they are not explicitly supported by the guidelines or contradicted by the examples.

You must output the status for EVERY SINGLE figure and table found in the paper, and then list any other text content or layout issues.
Pay attention to column margins and page edges. Only report issues if a figure or table clearly overflows into the gutter or margin. Do not flag figures or tables that are simply filling the column width fully.

Formatting Guidelines:
{guidelines}

Respond in JSON format: {{"figure_and_tables": {{"Figure 1": {{"detected_issue": "...", "suggested_fix": "..."}}}}, "other_issues": [{{"page": 1, "element": "...", "detected_issue": "...", "suggested_fix": "..."}}]}}
Use "None" for detected_issue when there is no problem.
"""
