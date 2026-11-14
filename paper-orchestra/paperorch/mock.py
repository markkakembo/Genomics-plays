"""Offline Mock LLM: deterministic, input-grounded responses for every agent task.

Purpose: prove the pipeline (file hand-offs, parallelism, real literature verification, plotting,
LaTeX compilation, review/accept/revert logic) runs end to end without an API key. The prose it writes
is template-like and NOT a substitute for a real model. It never invents numbers: tables and plots are
built only from markdown tables in the experimental log.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

MOCK_NOTE = r"\textit{[Mock-mode draft: generated offline without an LLM, from the provided sample materials.]}"


# ----------------------------------------------------------------- markdown helpers
def md_title(text: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else "Untitled Project"


def md_sections(text: str) -> Dict[str, str]:
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            if cur:
                out[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1).strip(), []
        elif cur:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out


def sec(secs: Dict[str, str], *keys: str) -> str:
    for k in keys:
        for name, body in secs.items():
            if k.lower() in name.lower():
                return body
    return ""


def bullets(body: str) -> List[str]:
    return [re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", l).strip() for l in body.splitlines()
            if re.match(r"^\s*(?:[-*]|\d+\.)\s+", l)]


def md_tables(text: str) -> List[Dict[str, Any]]:
    tables, lines, name = [], text.splitlines(), "Results"
    i = 0
    while i < len(lines):
        h = re.match(r"^#{2,4}\s+(.+)$", lines[i])
        if h:
            name = h.group(1).strip()
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            tables.append({"name": name, "header": header, "rows": rows})
            i = j
            continue
        i += 1
    return tables


def num(s: str):
    try:
        return float(str(s).replace(",", ""))
    except ValueError:
        return None


def tex_esc(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("~", r"\textasciitilde{}"),
                 ("^", r"\^{}"), ("{", r"\{"), ("}", r"\}")]:
        s = s.replace(a, b)
    return s.replace("\\textbackslash\\{\\}", r"\textbackslash{}")


def fill(tex: str, marker: str, content: str) -> str:
    pat = re.compile(rf"(%+ {re.escape(marker)} %+\n)(.*?)(\n%+ {re.escape(marker)} %+)", re.S)
    if pat.search(tex):
        return pat.sub(lambda m: m.group(1) + content + m.group(3), tex, count=1)
    return tex


def strip_num(t: str) -> str:
    return re.sub(r"^\s*[\d.]+\s*", "", t or "").strip()


# ----------------------------------------------------------------- tasks
def _outline(ctx) -> Dict:
    idea, log = ctx["idea"], ctx["log"]
    secs, lsecs = md_sections(idea), md_sections(log)
    title = md_title(idea)
    problem = sec(secs, "problem").split("\n\n")[0]
    tables = md_tables(log)
    setup = bullets(sec(lsecs, "setup"))
    related = bullets(sec(secs, "positioning", "related"))
    plan = []
    if tables:
        main_t = next((x for x in tables if "ablation" not in x["name"].lower()), tables[0])
        abl_t = next((x for x in tables if "ablation" in x["name"].lower()), None)
        plan.append({"figure_id": "fig_main_results", "title": f"Main results: {main_t['name']}", "plot_type": "plot",
                     "data_source": "experimental_log.md", "aspect_ratio": "16:9",
                     "objective": f"Grouped Bar Chart comparing methods on the metrics in '{main_t['name']}'."})
    plan.append({"figure_id": "fig_framework_overview", "title": f"Overview of {title}", "plot_type": "diagram",
                 "data_source": "idea.md", "aspect_ratio": "21:9",
                 "objective": "Conceptual pipeline diagram of the proposed method's stages."})
    if tables and abl_t:
        plan.append({"figure_id": "fig_ablation", "title": abl_t["name"], "plot_type": "plot",
                     "data_source": "experimental_log.md", "aspect_ratio": "4:3",
                     "objective": f"Grouped Bar Chart for the ablation table '{abl_t['name']}'."})
    hints = []
    for b in setup:
        m = re.match(r"(Models|Datasets|Retriever|Baselines|Metrics)\s*:\s*(.+)", b)
        if m:
            for item in re.split(r",| and ", m.group(2)):
                item = re.sub(r"\(.*?\)|\d[\d,]*\s+test questions each|top-\d+ passages|over a .*", "", item).strip(" .")
                if 2 < len(item) < 60 and not item.lower().startswith(("exact match", "retrieval rate", "mean latency", "closed-book", "always")):
                    hints.append(f"research paper or technical report introducing '{item}'")
    rw = [{"subsection_title": f"2.{i+1} {r}", "methodology_cluster": r,
           "sota_investigation_mission": f"Find representative work on {r.lower()}.",
           "limitation_hypothesis": "Existing approaches in this cluster do not target the cost/accuracy trade-off studied here.",
           "limitation_search_queries": [r], "bridge_to_our_method": f"{title} addresses this setting directly."}
          for i, r in enumerate(related[:4])]
    return {
        "plotting_plan": plan,
        "intro_related_work_plan": {
            "introduction_strategy": {"hook_hypothesis": problem[:300], "problem_gap_hypothesis": sec(secs, "hypothesis")[:300],
                                      "search_directions": [f"{related[0] if related else title} survey", title]},
            "related_work_strategy": {"overview": "Position the method against the listed related directions.", "subsections": rw},
        },
        "section_plan": [
            {"section_title": "Abstract", "subsections": [{"subsection_title": "Abstract Content", "content_bullets": ["Problem, method, key results."]}]},
            {"section_title": "Methodology", "subsections": [{"subsection_title": "Method", "content_bullets": bullets(sec(secs, "method"))}]},
            {"section_title": "Experiments", "subsections": [{"subsection_title": "Setup", "content_bullets": setup, "citation_hints": hints}]},
            {"section_title": "Conclusion", "subsections": [{"subsection_title": "Summary", "content_bullets": bullets(sec(secs, "contribution"))}]},
        ],
    }


CITE_CMD = {"cmd": "cite"}


def _cite(keys: List[str]) -> str:
    return f"~\\{CITE_CMD['cmd']}{{{','.join(keys)}}}" if keys else ""


def _set_cite_cmd(tex: str) -> None:
    CITE_CMD["cmd"] = "citep" if re.search(r"\\usepackage\{(iclr|natbib|neurips|icml)", tex) else "cite"


def _lit_write(ctx) -> str:
    tex, outline, papers = ctx["template"], ctx["outline"], ctx["papers"]
    _set_cite_cmd(tex)
    secs = md_sections(ctx["idea"])
    title = md_title(ctx["idea"])
    plan = outline.get("intro_related_work_plan", {})
    intro_keys = [p["citation_key"] for p in papers if p["found_in_section"] == "Introduction"]
    used = set(intro_keys)
    hyp = sec(secs, "hypothesis").replace("\n", " ")
    intro = (f"{tex_esc(sec(secs, 'problem').split(chr(10)*2)[0])} Prior work spans several related directions"
             f"{_cite(intro_keys[:6])}.\n\n"
             f"{tex_esc(hyp)}{_cite(intro_keys[6:12])}\n\n"
             f"In this paper we present {tex_esc(title)}. Our contributions are:\n\\begin{{itemize}}\n"
             + "\n".join(f"  \\item {tex_esc(b)}" for b in bullets(sec(secs, "contribution"))) + "\n\\end{itemize}\n")
    rw = []
    for sub in plan.get("related_work_strategy", {}).get("subsections", []):
        sec_name = f"Related Work: {sub.get('subsection_title')}"
        ps = [p for p in papers if p["found_in_section"] == sec_name]
        used |= {p["citation_key"] for p in ps}
        body = f"\\paragraph{{{tex_esc(strip_num(sub['subsection_title']))}.}} "
        body += " ".join(f"{tex_esc(p['title'])}{_cite([p['citation_key']])}." for p in ps[:8])
        body += f" {tex_esc(sub.get('bridge_to_our_method', ''))}"
        rw.append(body)
    rest = [p["citation_key"] for p in papers if p["citation_key"] not in used]
    if rest:
        rw.append(f"\\paragraph{{Resources.}} Our experiments build on established models, datasets and tools{_cite(rest)}.")
    tex = fill(tex, "INTRODUCTION", intro)
    return fill(tex, "RELATED WORK", "\n\n".join(rw) or "No verified related work was retrieved.")


def _plot_code(ctx) -> str:
    plan = ctx["plan"]
    tables = md_tables(ctx["log"])
    want_ablation = "ablation" in plan.get("figure_id", "")
    pick = [x for x in tables if ("ablation" in x["name"].lower()) == want_ablation]
    t = (pick or tables or [None])[0]
    if not t:
        return "import matplotlib.pyplot as plt\nplt.figure(); plt.text(0.5,0.5,'no table found',ha='center')"
    labels = [r[0] for r in t["rows"]]
    cols = [(i, h) for i, h in enumerate(t["header"][1:], 1)
            if all(num(r[i]) is not None for r in t["rows"] if i < len(r))]
    main = [(i, h) for i, h in cols if not re.search(r"latency|rate|time|\(ms\)|\(%\)", h, re.I)] or cols
    extra = [(i, h) for i, h in cols if (i, h) not in main]
    data = {h: [num(r[i]) for r in t["rows"]] for i, h in main}
    extra_data = {h: [num(r[i]) for r in t["rows"]] for i, h in extra}
    return f'''import matplotlib.pyplot as plt
import numpy as np
labels = {labels!r}
data = {data!r}
extra = {extra_data!r}
colors = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]
extra = dict(list(extra.items())[:2])
ncols = 1 + len(extra)
fig, axes = plt.subplots(1, ncols, figsize=(6.5 + 2.6 * len(extra), 3.3), squeeze=False,
                         gridspec_kw={{"width_ratios": [2.4] + [1] * len(extra)}})
ax = axes[0][0]
x = np.arange(len(data)); w = 0.8 / max(1, len(labels))
for j, lab in enumerate(labels):
    vals = [data[k][j] for k in data]
    bars = ax.bar(x + (j - (len(labels) - 1) / 2) * w, vals, w, label=lab, color=colors[j % len(colors)])
    ax.bar_label(bars, fmt="%.1f", fontsize=6.5, padding=1)
ax.set_xticks(x); ax.set_xticklabels(list(data), fontsize=9)
ax.set_ylabel("Score", fontsize=9); ax.grid(axis="y", alpha=0.3); ax.set_axisbelow(True)
ax.set_ylim(0, 1.18 * max(max(v) for v in data.values()))
ax.spines[["top", "right"]].set_visible(False)
fig.legend(*ax.get_legend_handles_labels(), loc="upper center", ncol=len(labels), fontsize=8, frameon=False,
           bbox_to_anchor=(0.5, 1.06))
for k, (name, vals) in enumerate(extra.items(), start=1):
    a = axes[0][k]
    a.barh(labels, vals, color=[colors[j % len(colors)] for j in range(len(labels))])
    for yy, v in enumerate(vals):
        a.text(v, yy, f" {{v:g}}", va="center", fontsize=7)
    a.set_xlabel(name, fontsize=9); a.invert_yaxis(); a.grid(axis="x", alpha=0.3); a.set_axisbelow(True)
    a.set_xlim(0, 1.25 * max(vals) if max(vals) > 0 else 1)
    a.tick_params(labelsize=8); a.spines[["top", "right"]].set_visible(False)
    if k > 1:
        a.set_yticklabels([])
fig.tight_layout()
'''


def _diagram_tikz(ctx) -> str:
    secs = md_sections(ctx["idea"])
    steps = []
    for b in bullets(sec(secs, "method")):
        m = re.match(r"\*\*(.+?)\*\*", b)
        steps.append(m.group(1) if m else " ".join(b.split()[:3]))
    steps = steps[:6] or ["Input", "Method", "Output"]
    nodes, prev = [], "in"
    nodes.append(r"\node[io] (in) {Input};")
    for i, s in enumerate(steps):
        nodes.append(rf"\node[box, right=7mm of {prev}] (s{i}) {{\textbf{{{i+1}.}} {tex_esc(s)}}};")
        prev = f"s{i}"
    nodes.append(rf"\node[io, right=7mm of {prev}] (out) {{Output}};")
    chain = ["in"] + [f"s{i}" for i in range(len(steps))] + ["out"]
    edges = " ".join(rf"\draw[arr] ({a}) -- ({b});" for a, b in zip(chain, chain[1:]))
    return r"""\documentclass[tikz,border=6pt]{standalone}
\usetikzlibrary{arrows.meta,positioning,shapes,fit,backgrounds}
\begin{document}
\begin{tikzpicture}[
  box/.style={draw=blue!60!black, fill=blue!7, rounded corners=3pt, minimum height=12mm, text width=24mm, align=center, font=\small},
  io/.style={draw=gray!70, fill=gray!10, rounded corners=6pt, minimum height=10mm, font=\small},
  arr/.style={-{Stealth[length=2.5mm]}, thick, gray!70!black}]
""" + "\n".join(nodes) + "\n" + edges + r"""
\begin{scope}[on background layer]
\node[draw=blue!30, dashed, rounded corners=6pt, fit=(s0) (s""" + str(len(steps) - 1) + r"""), inner sep=4mm, label={[font=\footnotesize\itshape]above:proposed pipeline}] {};
\end{scope}
\end{tikzpicture}
\end{document}
"""


def _booktabs(t: Dict, label: str) -> str:
    n = len(t["header"])
    head = " & ".join(tex_esc(h) for h in t["header"]) + r" \\"
    body = "\n".join(" & ".join(tex_esc(c) for c in r) + r" \\" for r in t["rows"])
    return (f"\\begin{{table}}[t]\n\\centering\n\\caption{{{tex_esc(t['name'])} (values copied verbatim from the experimental log).}}\n"
            f"\\label{{{label}}}\n\\small\n\\resizebox{{\\ifdim\\width>\\linewidth\\linewidth\\else\\width\\fi}}{{!}}{{%\n\\begin{{tabular}}{{l{'c' * (n - 1)}}}\n\\toprule\n{head}\n"
            f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}}}\n\\end{{table}}\n")


def _section_write(ctx) -> str:
    tex, idea, log = ctx["template"], ctx["idea"], ctx["log"]
    _set_cite_cmd(tex)
    secs, lsecs = md_sections(idea), md_sections(log)
    title = md_title(idea)
    cmap = ctx.get("cmap", {})
    exp_keys = []
    for s in ctx["outline"].get("section_plan", []):
        for sub in s.get("subsections", []):
            exp_keys += sub.get("citation_candidates", [])
    tables = md_tables(log)
    figs = ctx.get("figures", [])
    if "\\usepackage{booktabs}" not in tex:
        tex = tex.replace("\\begin{document}", "\\usepackage{booktabs}\n\\usepackage{graphicx}\n\\begin{document}", 1)
    tex = re.sub(r"\\title\{[^}]*\}", lambda m: "\\title{" + tex_esc(title) + "}", tex, count=1)
    abstract = (f"{tex_esc(sec(secs, 'problem').split(chr(10)*2)[0])} We propose {tex_esc(title)}. "
                f"{tex_esc(sec(secs, 'hypothesis').replace(chr(10), ' '))} {MOCK_NOTE}")
    figtex = {f["name"]: (f"\\begin{{figure}}[t]\n\\centering\n\\includegraphics[width=\\linewidth]{{figures/{f['name']}}}\n"
                          f"\\caption{{{tex_esc(f.get('caption', ''))}}}\n\\label{{fig:{f['name'].rsplit('.', 1)[0]}}}\n\\end{{figure}}\n")
              for f in figs}
    diag = [n for n in figtex if "framework" in n or "overview" in n]
    method = "\\subsection{Problem Setting}\n" + tex_esc(sec(secs, "problem")) + "\n\n\\subsection{Approach}\n"
    if diag:
        method += f"Figure~\\ref{{fig:{diag[0].rsplit('.', 1)[0]}}} summarises the pipeline.\n" + figtex[diag[0]]
    method += "\\begin{enumerate}\n" + "\n".join(f"  \\item {tex_esc(b)}" for b in bullets(sec(secs, "method"))) + "\n\\end{enumerate}\n"
    setup = bullets(sec(lsecs, "setup"))
    exp = "\\subsection{Experimental Setup}\n\\begin{itemize}\n"
    for b in setup:
        if b.lower().startswith(("hardware", "calibration")):
            continue  # left for the refinement step to surface (mock reviewer asks for it)
        exp += f"  \\item {tex_esc(b)}\n"
    exp += "\\end{itemize}\n"
    if exp_keys:
        exp += f"Models, datasets and baselines follow their original papers{_cite(sorted(set(exp_keys)))}.\n"
    exp += "\n\\subsection{Results}\n"
    for k, t in enumerate(tables):
        exp += f"Table~\\ref{{tab:t{k}}} reports {tex_esc(t['name'].lower())}.\n" + _booktabs(t, f"tab:t{k}")
    for n, ft in figtex.items():
        if n not in diag:
            exp += f"Figure~\\ref{{fig:{n.rsplit('.', 1)[0]}}} visualises these numbers.\n" + ft
    obs = bullets(sec(lsecs, "observation"))
    if obs:
        exp += "\n\\subsection{Analysis}\n\\begin{itemize}\n" + "\n".join(f"  \\item {tex_esc(o)}" for o in obs) + "\n\\end{itemize}\n"
    concl = (f"We presented {tex_esc(title)}. " + " ".join(tex_esc(b) for b in bullets(sec(secs, "contribution"))))
    for m, c in [("ABSTRACT", abstract), ("METHOD", method), ("EXPERIMENTS", exp), ("CONCLUSION", concl)]:
        tex = fill(tex, m, c)
    return tex


def _review(ctx) -> Dict:
    t = ctx["paper_text"]
    has_impl = "Implementation details" in t
    n_fig = len(set(re.findall(r"Figure\s+(\d+)", t)))
    n_tab = len(set(re.findall(r"Table\s+(\d+)", t)))
    words = len(t.split())
    weak = []
    if not has_impl:
        weak.append("Implementation details (hardware, calibration split, decoding settings) are not reported, hurting reproducibility.")
    if n_fig < 2:
        weak.append("Few figures; results would be easier to digest visually.")
    weak.append("The method section is high-level; a formal definition of the confidence score would help.")
    overall = 3 + int(has_impl) + int(n_fig >= 2) + int(n_tab >= 2)
    return {"Summary": "[mock heuristic reviewer] The paper proposes a method and evaluates it on the logged experiments.",
            "Strengths": ["Results tables are reported with exact numbers from the experimental log."],
            "Weaknesses": weak, "Originality": 3, "Quality": 2 + int(has_impl), "Clarity": 3 if words > 1200 else 2,
            "Significance": 2, "Questions": ["What hardware and calibration data were used?"],
            "Limitations": ["Synthetic sample data."], "Ethical Concerns": False, "Soundness": 2 + int(has_impl),
            "Presentation": 2 + int(n_fig >= 2), "Contribution": 2 + int(n_tab >= 2), "Overall": overall,
            "Confidence": 2, "Decision": "Accept" if overall >= 6 else "Reject"}


def _refine(ctx) -> str:
    tex = ctx["tex"]
    lsecs = md_sections(ctx["log"])
    hidden = [b for b in bullets(sec(lsecs, "setup")) if b.lower().startswith(("hardware", "calibration"))]
    if "Implementation details" not in tex and hidden:
        para = "\n\\paragraph{Implementation details.} " + " ".join(tex_esc(h) for h in hidden) + "\n"
        tex = fill(tex, "EXPERIMENTS", re.search(r"%+ EXPERIMENTS %+\n(.*?)\n%+ EXPERIMENTS %+", tex, re.S).group(1)
                   .replace("\n\\subsection{Results}", para + "\n\\subsection{Results}", 1))
        log = {"addressed_weaknesses": ["Reported hardware and calibration details (reviewer question 1)"],
               "integrated_answers": ["Added an Implementation details paragraph using values from experimental_log.md"],
               "actions_taken": ["Inserted paragraph in Experimental Setup"]}
    else:
        log = {"addressed_weaknesses": [], "integrated_answers": [], "actions_taken": ["No further grounded changes possible in mock mode"]}
    return "```json\n" + json.dumps(log, indent=2) + "\n```\n\n```latex\n" + tex + "\n```"


def respond(task: str, ctx: Dict[str, Any], prompt: str) -> str:
    if task == "outline":
        return "```json\n" + json.dumps(_outline(ctx), indent=2) + "\n```"
    if task == "discover":
        return '```json\n{"section_name": "", "candidates": []}\n```'
    if task == "lit_write":
        return "```latex\n" + _lit_write(ctx) + "\n```"
    if task in ("figure_plan", "figure_style"):
        p = ctx["plan"]
        return f"{p.get('title', '')}. {p.get('objective', '')}"
    if task == "plot_code":
        return "```python\n" + _plot_code(ctx) + "\n```"
    if task == "diagram_tikz":
        return "```latex\n" + _diagram_tikz(ctx) + "\n```"
    if task == "figure_critic":
        return '```json\n{"critic_suggestions": "No changes needed.", "revised_description": "No changes needed."}\n```'
    if task == "figure_caption":
        p = ctx["plan"]
        return f"{p.get('title', '')}. {p.get('objective', '')}".replace("Grouped Bar Chart", "Grouped bar chart")
    if task == "section_write":
        return "```latex\n" + _section_write(ctx) + "\n```"
    if task == "review":
        return "THOUGHT:\nHeuristic mock review.\n\nREVIEW JSON:\n```json\n" + json.dumps(_review(ctx)) + "\n```"
    if task == "meta_review":
        return "```json\n" + json.dumps(ctx["reviews"][0]) + "\n```"
    if task == "refine":
        return _refine(ctx)
    if task in ("format_fix",):
        return "```latex\n" + ctx["tex"] + "\n```"
    return ""
