"""Step 5 - Content Refinement Agent (paper Sec. 4 Step 5) with an AgentReview-style reviewer.

Loop (max N iterations): review current PDF -> revise LaTeX -> compile -> re-review.
Accept if Overall increases, or ties with sum(sub-axis gains) >= sum(drops); otherwise revert and stop.
Then an optional single VLM formatting pass (needs a vision-capable model).
"""
from __future__ import annotations

import json
import os
import shutil
from statistics import mean
from typing import Dict, Tuple

from ..latex import compile_latex, pdf_text, pdf_to_pngs
from ..parsing import parse_json, parse_json_and_latex, parse_latex
from .. import prompts as P

AXES = ["Originality", "Quality", "Clarity", "Significance", "Soundness", "Presentation", "Contribution", "Overall", "Confidence"]
LIMITS = {"Overall": (1, 10), "Confidence": (1, 5)}


def review_paper(llm, paper_text: str, ensemble: int = 3) -> Dict:
    system = P.agentreview_system_prompt()
    prompt = P.AGENTREVIEW_INSTRUCTIONS + f"\nHere is the paper you are asked to review:\n```\n{paper_text}\n```"
    reviews = []
    for i in range(max(1, ensemble)):
        r = parse_json(llm.complete(prompt, system=system, task="review", ctx={"paper_text": paper_text, "i": i},
                                    temperature=0.75))
        if isinstance(r, dict):
            reviews.append(r)
    if not reviews:
        return {"Overall": 0, "Error": "no parsable review"}
    if len(reviews) == 1:
        return reviews[0]
    meta_prompt = P.AGENTREVIEW_INSTRUCTIONS + "".join(
        f"\nReview {i+1}/{len(reviews)}:\n```\n{json.dumps(r)}\n```\n" for i, r in enumerate(reviews))
    meta = parse_json(llm.complete(meta_prompt, system=P.META_REVIEWER_SYSTEM.format(reviewer_count=len(reviews)),
                                   task="meta_review", ctx={"reviews": reviews}, temperature=0.75)) or dict(reviews[0])
    for ax in AXES:
        lo, hi = LIMITS.get(ax, (1, 4))
        vals = []
        for r in reviews:
            try:
                v = int(r.get(ax))
                if lo <= v <= hi:
                    vals.append(v)
            except (TypeError, ValueError):
                pass
        if vals:
            meta[ax] = int(round(mean(vals)))
    meta["_ensemble_size"] = len(reviews)
    return meta


WORD_SCORES = {"low": 1, "poor": 1, "medium": 2, "fair": 2, "high": 3, "good": 3, "very high": 4, "excellent": 4,
               "absolute": 5}


def _scores(review: Dict) -> Dict[str, float]:
    """Numeric axis scores. Some models answer with the rubric words ("high", "good"); map those to numbers."""
    out = {}
    for ax in AXES:
        v = review.get(ax, 0)
        try:
            out[ax] = float(v)
        except (TypeError, ValueError):
            out[ax] = float(WORD_SCORES.get(str(v).strip().lower(), 0))
    return out


class RefinementAgent:
    def __init__(self, llm, cfg, materials, cmap: Dict, guidelines: str, work_dir: str):
        self.llm, self.cfg, self.m, self.cmap, self.guidelines, self.dir = llm, cfg, materials, cmap, guidelines, work_dir
        os.makedirs(os.path.join(work_dir, "peer_reviews"), exist_ok=True)
        self.worklog: Dict = {}

    def _review(self, pdf: str, label: str) -> Tuple[Dict, float]:
        rev = review_paper(self.llm, pdf_text(pdf), self.cfg.review_ensemble)
        with open(os.path.join(self.dir, "peer_reviews", f"review_{label}.json"), "w") as f:
            json.dump(rev, f, indent=2)
        score = _scores(rev)["Overall"]
        print(f"   [AgentReview] {label}: Overall {score}/10")
        return rev, score

    def run(self, draft_tex: str) -> Tuple[str, str, Dict]:
        print("[5/5] Content Refinement Agent ...")
        eng = self.cfg.latex_engine
        cur_tex = draft_tex
        with open(os.path.join(self.dir, "initial_draft.tex"), "w") as f:
            f.write(cur_tex)
        cur_pdf = compile_latex(self.dir, "initial_draft", eng)
        if not cur_pdf:
            raise RuntimeError(f"Initial draft failed to compile; see {self.dir}/initial_draft.compile.log")
        cur_rev, cur_score = self._review(cur_pdf, "v0")
        history = {"initial_overall": cur_score, "iterations": []}
        for i in range(self.cfg.max_reflections):
            name = f"refined_paper_v{i+1}"
            prompt = f"""
REFLECTION ITERATION {i+1}.

--- PREVIOUS ITERATION LOG ---
{json.dumps(self.worklog, indent=2) if self.worklog else 'None'}

--- CURRENT REVIEWER FEEDBACK (Score: {cur_score}) ---
{json.dumps(cur_rev, indent=2)}

--- CONFERENCE GUIDELINES ---
{self.guidelines}

--- EXPERIMENTAL LOG (Data Truth) ---
{self.m.experimental_log}

--- CITATION MAP (Reference Truth) ---
{json.dumps(self.cmap, indent=2)}

--- CURRENT LATEX SOURCE ---
{cur_tex}

INSTRUCTION:
1. Your goal is to IMPROVE the reviewer score (Current: {cur_score}).
2. Address the 'Weaknesses' and 'Questions' in the Reviewer Feedback above.
3. Output the JSON Worklog first, then the Full Revised LaTeX.
"""
            pages = pdf_to_pngs(cur_pdf, os.path.join(self.dir, "pdf_screenshots", f"v{i}")) if self.llm.supports_vision else []
            parsed = parse_json_and_latex(self.llm.complete(prompt, system=P.REFINEMENT_SYSTEM, images=pages, task="refine",
                                                            ctx={"tex": cur_tex, "review": cur_rev, "log": self.m.experimental_log,
                                                                 "iteration": i + 1}))
            new_tex = parsed.get("latex")
            if not new_tex:
                print("   ! no LaTeX returned; stopping")
                break
            with open(os.path.join(self.dir, f"{name}.tex"), "w") as f:
                f.write(new_tex)
            new_pdf = compile_latex(self.dir, name, eng)
            if not new_pdf:
                print(f"   ! v{i+1} failed to compile; skipping this iteration")
                history["iterations"].append({"version": i + 1, "outcome": "COMPILE_FAILED"})
                continue
            new_rev, new_score = self._review(new_pdf, f"v{i+1}")
            old, new = _scores(cur_rev), _scores(new_rev)
            deltas = {a: new[a] - old[a] for a in AXES if a not in ("Overall", "Confidence")}
            gain = sum(d for d in deltas.values() if d > 0)
            drop = -sum(d for d in deltas.values() if d < 0)
            entry = {"version": i + 1, "worklog": parsed.get("json"), "overall_before": old["Overall"],
                     "overall_after": new["Overall"], "deltas": deltas, "total_gain": gain, "total_drop": drop}
            if new["Overall"] > old["Overall"]:
                entry["outcome"] = "ACCEPTED_SCORE_INCREASE"
            elif new["Overall"] < old["Overall"]:
                entry["outcome"] = "REJECTED_SCORE_DECREASE"
            elif drop > gain:
                entry["outcome"] = "REJECTED_DEGRADATION"
            else:
                entry["outcome"] = "ACCEPTED_NEUTRAL_IMPROVEMENT"
            print(f"   v{i+1}: Overall {old['Overall']} -> {new['Overall']}, sub-axes +{gain}/-{drop} => {entry['outcome']}")
            history["iterations"].append(entry)
            self.worklog[f"v{i+1}"] = entry
            if entry["outcome"].startswith("REJECTED"):
                break
            cur_tex, cur_pdf, cur_rev, cur_score = new_tex, new_pdf, new_rev, new_score

        if self.cfg.formatting_loop and self.llm.supports_vision:
            cur_tex, cur_pdf = self._format_pass(cur_tex, cur_pdf, history)
        elif self.cfg.formatting_loop:
            history["formatting"] = "skipped (model has no vision input)"

        final_tex = os.path.join(self.dir, "final_refined_paper.tex")
        with open(final_tex, "w") as f:
            f.write(cur_tex)
        final_pdf = os.path.join(self.dir, "final_refined_paper.pdf")
        shutil.copy(cur_pdf, final_pdf)
        history["final_overall"] = cur_score
        with open(os.path.join(self.dir, "content_refinement_worklog.json"), "w") as f:
            json.dump(history, f, indent=2)
        return final_tex, final_pdf, history

    def _format_pass(self, tex, pdf, history):
        pages = pdf_to_pngs(pdf, os.path.join(self.dir, "pdf_screenshots", "format_v0"))
        fb = parse_json(self.llm.complete(P.FORMAT_REVIEW_PROMPT.format(guidelines=self.guidelines), images=pages,
                                          task="format_review", ctx={})) or {}
        issues = [d for d in (fb.get("figure_and_tables") or {}).values()
                  if isinstance(d, dict) and str(d.get("detected_issue", "None")).lower() != "none"]
        issues += [d for d in (fb.get("other_issues") or []) if isinstance(d, dict)
                   and str(d.get("detected_issue", "None")).lower() != "none"]
        if not issues:
            history["formatting"] = "no issues found"
            return tex, pdf
        prompt = f"""You are a LaTeX formatting expert. Your task is to fix the formatting issues identified in the feedback below.
You must STRICTLY follow the provided formatting guidelines.
CRITICAL: You are ONLY allowed to make formatting, layout, and spacing adjustments. You MUST NOT change any content, text, claims, data, or citations in the paper unless explicitly allowed by the feedback.

--- CURRENT FORMATTING FEEDBACK ---
{json.dumps(fb, indent=2)}

--- CONFERENCE GUIDELINES ---
{self.guidelines}

--- CURRENT LATEX SOURCE ---
{tex}

Output the Full Revised LaTeX only, inside a ```latex block."""
        new_tex = parse_latex(self.llm.complete(prompt, task="format_fix", ctx={"tex": tex}))
        with open(os.path.join(self.dir, "formatted_candidate_v1.tex"), "w") as f:
            f.write(new_tex)
        new_pdf = compile_latex(self.dir, "formatted_candidate_v1", self.cfg.latex_engine)
        history["formatting"] = {"issues": len(issues), "outcome": "ACCEPTED_COMPILE_SUCCESS" if new_pdf else "REJECTED_COMPILE_FAILURE"}
        return (new_tex, new_pdf) if new_pdf else (tex, pdf)
