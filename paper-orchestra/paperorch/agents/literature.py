"""Step 3 - Literature Review Agent (paper Sec. 4 Step 3, App. B and D.3).

Phase 1a  parallel candidate discovery (10 workers): LLM + web search when the provider has it
          (Gemini Google-Search grounding as in the paper / OpenAI or Anthropic web search),
          optionally LLM recall, plus direct keyword search on OpenAlex/arXiv.
Phase 1b  sequential verification (~1 query/s) against Semantic Scholar (fallback arXiv, OpenAlex):
          fuzzy title ratio > 70 (+10 year bonus), abstract required, strictly before cutoff.
Phase 2   dedupe -> citation registry -> references.bib + citation_map.json; inject keys into outline.
Phase 3   one LLM call writes Introduction + Related Work, citing >= 90% of the verified pool.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from .. import scholar
from ..latex import looks_complete, sanitize_citations
from ..parsing import parse_json, parse_latex
from ..prompts import LIT_WRITER_SYSTEM

DISCOVERY_SCHEMA = ('{"section_name": "string", "candidates": [{"title": "exact paper title", '
                    '"year": 2020, "reason": "why it is relevant"}]}')


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def collect_search_tasks(outline: Dict) -> List[Dict]:
    """Same task construction as upstream HybridLiteratureAgent._collect_search_tasks."""
    tasks = []
    plan = outline.get("intro_related_work_plan", {})
    intro = plan.get("introduction_strategy", {})
    for d in intro.get("search_directions", []):
        tasks.append({"section": "Introduction", "focus": d, "search_type": "exploration",
                      "context": f"Hook: {intro.get('hook_hypothesis', '')}. Gap: {intro.get('problem_gap_hypothesis', '')}"})
    for sub in plan.get("related_work_strategy", {}).get("subsections", []):
        qs = sub.get("limitation_search_queries") or [f"{sub.get('subsection_title', '')} {sub.get('methodology_cluster', '')}"]
        for q in qs:
            tasks.append({"section": f"Related Work: {sub.get('subsection_title', 'General')}", "focus": q,
                          "search_type": "exploration",
                          "context": f"Mission: {sub.get('sota_investigation_mission', '')}. Hypothesis: {sub.get('limitation_hypothesis', '')}"})
    for sec in outline.get("section_plan", []):
        st = sec.get("section_title", "Unknown Section")
        for sub in sec.get("subsections", []):
            for hint in sub.get("citation_hints", []):
                tasks.append({"section": f"{st} - {sub.get('subsection_title', 'General')}", "focus": hint,
                              "search_type": "targeted",
                              "context": "Must-have citation for section covering: " + " ".join(sub.get("content_bullets", []))})
    return tasks


def _discovery_prompt(task, core_problem, cutoff, web: bool) -> str:
    how = "Use web search to find" if web else "From your own knowledge, list only papers you are certain exist, giving"
    if task["search_type"] == "targeted":
        return f"""
Identify the SPECIFIC academic paper described by this hint: "{task['focus']}".

CONTEXT: {task['context']}
CUTOFF DATE: Published BEFORE {cutoff}

INSTRUCTIONS:
1. {how} the EXACT title and year of this paper.
2. If the hint refers to a dataset, model architecture, or baseline (e.g., "research paper introducing..."), you MUST find the primary, original paper that introduced it.
3. Return EXACTLY 1 candidate paper that matches best.

YOU MUST return the results in json format (```json content```) following this schema:
{DISCOVERY_SCHEMA}
"""
    return f"""
Find 10-15 highly relevant, influential academic papers matching the search task. Do not force results; only return strictly relevant papers.

SEARCH TASK: {task['focus']}
CONTEXT FOR TASK: {task['context']}
BROADER PROJECT PROBLEM: {core_problem}
CUTOFF DATE: Published BEFORE {cutoff}

INSTRUCTIONS:
1. {how} REAL papers (ArXiv, CVPR, NeurIPS, ICML, ICLR, etc.) with exact titles.
2. Only return papers published in top-tier conferences or journals, or highly-cited works, or the exact state-of-the-art relevant to the task.

YOU MUST return the results in json format (```json content```) following this schema:
{DISCOVERY_SCHEMA}
"""


def _keyword_query(task) -> str:
    q = task["focus"]
    m = re.search(r"introducing\s+['\"]?([^'\"]+)['\"]?", q)
    if m:
        q = m.group(1)
    q = re.sub(r"^(find|search for|identify)\s+", "", q, flags=re.I)
    return q[:200]


class LiteratureAgent:
    def __init__(self, llm, cfg, materials, template_tex: str, out_dir: str):
        self.llm, self.cfg, self.m, self.template = llm, cfg, materials, template_tex
        self.s = cfg.lit_settings
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.lock = threading.Lock()

    # ---------------------------------------------------------------- phase 1a
    def _discover(self, task, outline, cutoff) -> List[Dict]:
        cands: List[Dict] = []
        core = outline.get("intro_related_work_plan", {}).get("introduction_strategy", {}).get("problem_gap_hypothesis", "N/A")
        use_web = self.s["use_web_search"] and self.llm.supports_web_search
        if self.llm.provider != "mock" and (use_web or self.s["use_llm_recall"]):
            for _ in range(3):
                try:
                    resp = self.llm.complete(_discovery_prompt(task, core, cutoff, use_web), task="discover",
                                             ctx={"task": task}, web_search=use_web,
                                             temperature=0.1 if task["search_type"] == "targeted" else 0.4)
                    parsed = parse_json(resp) or {}
                    got = parsed.get("candidates", []) if isinstance(parsed, dict) else []
                    if got:
                        cands += [c for c in got if isinstance(c, dict) and c.get("title")]
                        break
                except Exception as e:  # noqa: BLE001
                    print(f"   ! discovery failed for '{task['focus'][:40]}': {e}")
                    break
        kw = self.s["use_keyword_search"]
        if kw == "auto":  # paper: LLM + web search only; keyword search fills in when no web search is available
            kw = not self.llm.supports_web_search or self.llm.provider == "mock"  # re-checked: may be disabled mid-run
        if kw:
            n = 1 if task["search_type"] == "targeted" else self.s["keyword_search_results"]
            for rec in scholar.keyword_search(_keyword_query(task), n, cutoff):
                cands.append({"title": rec["title"], "year": rec.get("year"), "reason": f"keyword search: {task['focus']}",
                              "_record": rec})
        return cands

    # ---------------------------------------------------------------- phase 1b
    def _verify(self, cand, task, registry, cutoff, rejected):
        title = cand.get("title", "")
        if _norm(title) in registry:
            return
        rec = cand.get("_record")
        if rec is None:
            time.sleep(self.s["verify_delay_sec"])
            try:
                year = int(cand.get("year")) if cand.get("year") else None
            except (TypeError, ValueError):
                year = None
            rec = scholar.verify_title(title, year, cutoff, self.s["fallback_sources"])
        if not rec or not rec.get("abstract") or not scholar.is_allowed(rec.get("publicationDate"), rec.get("year"), cutoff):
            rejected.append({"title": title, "task": task["focus"], "reason": "unverified / no abstract / after cutoff"})
            return
        key_norm = _norm(rec["title"])
        pid = rec.get("paperId")
        with self.lock:
            if key_norm in registry or any(p.get("paper_id") == pid for p in registry.values() if pid):
                return
            abstract = rec["abstract"]
            registry[key_norm] = {
                "paper_id": pid, "title": rec["title"], "authors": [a["name"] for a in rec.get("authors", []) if a.get("name")],
                "venue": rec.get("venue") or "arXiv", "year": rec.get("year"),
                "abstract": abstract if len(abstract) <= 1500 else abstract[:1500] + "... [Truncated]",
                "citation_count": rec.get("citationCount") or 0, "found_in_section": task["section"],
                "reason": cand.get("reason", ""), "journal": (rec.get("journal") or {}).get("name") if isinstance(rec.get("journal"), dict) else None,
                "publication_date": rec.get("publicationDate"), "verified_via": rec.get("source"), "url": rec.get("url"),
            }

    # ---------------------------------------------------------------- phase 2 helpers
    @staticmethod
    def _key(p) -> str:
        first = (p["authors"][0].split()[-1] if p["authors"] else "Unknown")
        first = re.sub(r"[^a-zA-Z]", "", first).capitalize() or "Anon"
        stop = {"the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "is", "are", "with", "by", "study"}
        words = [w.capitalize() for w in re.sub(r"[^a-zA-Z0-9\s]", "", p["title"].lower()).split() if w not in stop]
        return f"{first}{p.get('year') or 'nd'}{''.join(words[:2]) or 'Paper'}"

    @staticmethod
    def _bibesc(s: str) -> str:
        return re.sub(r"([&%#_$])", r"\\\1", str(s or ""))

    def _bibtex(self, papers) -> str:
        seen, entries = set(), []
        for p in papers:
            k, suf = p["citation_key"], "a"
            while k in seen:
                k = p["citation_key"] + suf
                suf = chr(ord(suf) + 1)
            p["citation_key"] = k
            seen.add(k)
            authors = " and ".join(self._bibesc(a) for a in p["authors"]) or "Unknown"
            if p.get("journal"):
                e = f"@article{{{k},\n  title={{{{{self._bibesc(p['title'])}}}}},\n  author={{{authors}}},\n  journal={{{self._bibesc(p['journal'])}}},\n  year={{{p['year']}}}\n}}"
            else:
                e = f"@inproceedings{{{k},\n  title={{{{{self._bibesc(p['title'])}}}}},\n  author={{{authors}}},\n  booktitle={{{self._bibesc(p['venue'])}}},\n  year={{{p['year']}}}\n}}"
            entries.append(e)
        return "\n\n".join(entries) + "\n"

    @staticmethod
    def _inject(outline, papers) -> Dict:
        by_sec: Dict[str, List[str]] = {}
        for p in papers:
            by_sec.setdefault(p["found_in_section"], []).append(p["citation_key"])
        plan = outline.get("intro_related_work_plan", {})
        plan.get("introduction_strategy", {})["citation_candidates"] = sorted(set(by_sec.get("Introduction", [])))
        for sub in plan.get("related_work_strategy", {}).get("subsections", []):
            sub["citation_candidates"] = by_sec.get(f"Related Work: {sub.get('subsection_title', 'General')}", [])
        for sec in outline.get("section_plan", []):
            for sub in sec.get("subsections", []):
                sub["citation_candidates"] = by_sec.get(f"{sec.get('section_title')} - {sub.get('subsection_title', 'General')}", [])
                sub.pop("citation_hints", None)
        return outline

    # ---------------------------------------------------------------- run
    def run(self, outline: Dict, cutoff: str) -> Dict:
        print(f"[3/5] Literature Review Agent (cutoff {cutoff}) ...")
        tasks = collect_search_tasks(outline)
        cap = self.s["max_search_tasks"]
        if cap and len(tasks) > cap:
            print(f"   (capping {len(tasks)} search tasks to {cap} per config lit.max_search_tasks)")
            tasks = tasks[:cap]
        print(f"   Phase 1a: discovery over {len(tasks)} search tasks ({self.s['discovery_workers']} workers)")
        pooled = []
        with ThreadPoolExecutor(max_workers=self.s["discovery_workers"]) as ex:
            futs = {ex.submit(self._discover, t, outline, cutoff): t for t in tasks}
            for f in as_completed(futs):
                try:
                    pooled += [(c, futs[f]) for c in f.result()]
                except Exception as e:  # noqa: BLE001
                    print(f"   ! discovery error: {e}")
        print(f"   Phase 1b: verifying {len(pooled)} candidates (sequential, rate-limited)")
        registry: Dict[str, Dict] = {}
        rejected: List[Dict] = []
        for c, t in pooled:
            self._verify(c, t, registry, cutoff, rejected)
        papers = list(registry.values())
        for p in papers:
            p["citation_key"] = self._key(p)
        bib = self._bibtex(papers)
        cmap = {p["citation_key"]: {k: p[k] for k in ("citation_key", "title", "authors", "venue", "year", "abstract")}
                for p in papers if p["abstract"]}
        outline = self._inject(json.loads(json.dumps(outline)), papers)
        print(f"   -> {len(papers)} verified unique papers ({len(rejected)} candidates rejected)")

        print("   Phase 3: writing Introduction + Related Work")
        system = LIT_WRITER_SYSTEM.format(paper_count=len(papers),
                                          min_cite_paper_count=int(len(papers) * self.s["min_cite_fraction"]),
                                          cutoff_date=cutoff)
        payload = {"template.tex": self.template, "intro_related_work_plan": outline.get("intro_related_work_plan", {}),
                   "project_idea": self.m.idea, "project_experimental_log": self.m.experimental_log,
                   "citation_checklist": list(cmap), "collected_papers": papers}
        tex = ""
        for _ in range(2):
            tex = parse_latex(self.llm.complete("Generate the LaTeX for Introduction and Related Work sections.\n\n"
                                                + json.dumps(payload), system=system, task="lit_write",
                                                ctx={"template": self.template, "outline": outline, "papers": papers,
                                                     "idea": self.m.idea, "log": self.m.experimental_log}))
            if looks_complete(tex):
                break
        if not looks_complete(tex):
            print("   ! writer did not return a complete LaTeX file; keeping the template unchanged")
            tex = self.template
        tex, removed = sanitize_citations(tex, set(cmap))
        if removed:
            print(f"   ! removed {len(removed)} citation keys not in the verified pool: {sorted(set(removed))[:8]}")
        cited = set(re.findall(r"\\cite[tp]?\{([^}]*)\}", tex))
        cited = {k.strip() for grp in cited for k in grp.split(",")}
        print(f"   -> cited {len(cited & set(cmap))}/{len(cmap)} verified papers in Intro/Related Work")

        files = {"updated_template.tex": tex, "references.bib": bib}
        for n, c in files.items():
            with open(os.path.join(self.out, n), "w", encoding="utf-8") as f:
                f.write(c)
        for n, obj in {"citation_map.json": cmap, "outline_v1.json": outline, "registry.json": papers,
                       "rejected_candidates.json": rejected}.items():
            with open(os.path.join(self.out, n), "w", encoding="utf-8") as f:
                json.dump(obj, f, indent=2)
        return {"outline": outline, "citation_map": cmap, "tex": tex, "bib": bib, "papers": papers}
