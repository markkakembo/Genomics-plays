"""Scholarly-API access for citation discovery and verification (paper App. D.3).

Verification order: Semantic Scholar (as in the paper) -> arXiv -> OpenAlex (fallbacks added here
because the unauthenticated Semantic Scholar pool is frequently rate-limited). A candidate is accepted
only if (1) a fuzzy title match ratio > 70 (+10 bonus for exact year), (2) it has an abstract, and
(3) it strictly predates the research cutoff (first day of the cutoff month).
"""
from __future__ import annotations

import datetime as dt
import os
import re
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

import requests
from thefuzz import fuzz

UA = {"User-Agent": "paperorch/0.1 (research prototype; https://github.com/google-research/paper-orchestra)"}
_MIN_GAP = {"s2": 1.1, "arxiv": 3.1, "openalex": 0.2}
_last: Dict[str, float] = {}
_lock = threading.Lock()


def _throttle(host: str) -> None:
    with _lock:
        gap = _MIN_GAP[host] - (time.time() - _last.get(host, 0))
        if gap > 0:
            time.sleep(gap)
        _last[host] = time.time()


def _get(host: str, url: str, params=None, headers=None, tries: int = 3, timeout: int = 20):
    for i in range(tries):
        _throttle(host)
        try:
            r = requests.get(url, params=params, headers={**UA, **(headers or {})}, timeout=timeout)
        except requests.RequestException:
            r = None
        if r is not None and r.status_code == 200:
            return r
        if r is not None and r.status_code not in (429, 500, 502, 503, 504):
            return None
        time.sleep(2 * (i + 1))
    return None


# ---------------------------------------------------------------- cutoff logic
def is_allowed(pub_date: Optional[str], year: Optional[int], cutoff: Optional[str]) -> bool:
    if not cutoff:
        return True
    cy, cm = (int(x) for x in cutoff.split("-")[:2])
    cdt = dt.date(cy, cm, 1)
    if pub_date:
        try:
            parts = [int(x) for x in str(pub_date).split("-")]
            p = dt.date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
            if len(parts) >= 3:
                return p < cdt
            year = parts[0]
        except Exception:  # noqa: BLE001
            pass
    if year:
        return int(year) < cy or (int(year) == cy and cm > 1)
    return True


def _best(title: str, year_hint: Optional[int], recs: List[Dict], cutoff: Optional[str]) -> Optional[Dict]:
    best, hi = None, 0
    for r in recs:
        if not r.get("title") or not is_allowed(r.get("publicationDate"), r.get("year"), cutoff):
            continue
        ratio = fuzz.ratio(title.lower(), r["title"].lower())
        if year_hint and r.get("year") == year_hint:
            ratio += 10
        if ratio > hi:
            best, hi = r, ratio
    return best if hi > 70 else None


# ---------------------------------------------------------------- Semantic Scholar
S2_FIELDS = "paperId,title,authors,venue,year,abstract,citationCount,journal,publicationDate,externalIds"


def s2_search(query: str, limit: int = 3) -> List[Dict]:
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    r = _get("s2", "https://api.semanticscholar.org/graph/v1/paper/search",
             params={"query": query, "limit": limit, "fields": S2_FIELDS},
             headers={"x-api-key": key} if key else None)
    if not r:
        return []
    out = []
    for d in r.json().get("data", []) or []:
        d["source"] = "semantic_scholar"
        out.append(d)
    return out


# ---------------------------------------------------------------- arXiv
_NS = {"a": "http://www.w3.org/2005/Atom"}


def arxiv_search(query: str, limit: int = 5, title_only: bool = False) -> List[Dict]:
    if title_only:
        clean = re.sub(r"[^A-Za-z0-9 \-]", " ", query)
        q = 'ti:"' + " ".join(clean.split()) + '"'
    else:
        q = " AND ".join("all:" + w for w in re.findall(r"[A-Za-z0-9\-]+", query)[:8])
    r = _get("arxiv", "https://export.arxiv.org/api/query",
             params={"search_query": q, "max_results": limit, "sortBy": "relevance"})
    if not r:
        return []
    out = []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []
    for e in root.findall("a:entry", _NS):
        title = " ".join((e.findtext("a:title", "", _NS) or "").split())
        pub = (e.findtext("a:published", "", _NS) or "")[:10]
        aid = (e.findtext("a:id", "", _NS) or "").rsplit("/abs/", 1)[-1]
        out.append({
            "paperId": f"arXiv:{aid}", "title": title,
            "authors": [{"name": a.findtext("a:name", "", _NS)} for a in e.findall("a:author", _NS)],
            "venue": "arXiv", "year": int(pub[:4]) if pub else None, "publicationDate": pub or None,
            "abstract": " ".join((e.findtext("a:summary", "", _NS) or "").split()),
            "citationCount": None, "journal": None, "source": "arxiv",
            "url": f"https://arxiv.org/abs/{aid}",
        })
    return out


# ---------------------------------------------------------------- OpenAlex
def _undo_inverted(inv: Optional[Dict[str, List[int]]]) -> str:
    if not inv:
        return ""
    pos = sorted((i, w) for w, idx in inv.items() for i in idx)
    return " ".join(w for _, w in pos)


def openalex_search(query: str, limit: int = 5, cutoff: Optional[str] = None) -> List[Dict]:
    params = {"search": query, "per-page": limit}
    if cutoff:
        cy, cm = (int(x) for x in cutoff.split("-")[:2])
        last = dt.date(cy, cm, 1) - dt.timedelta(days=1)
        params["filter"] = f"to_publication_date:{last.isoformat()}"
    mail = os.environ.get("OPENALEX_EMAIL")
    if mail:
        params["mailto"] = mail
    r = _get("openalex", "https://api.openalex.org/works", params=params)
    if not r:
        return []
    out = []
    for w in r.json().get("results", []):
        src = ((w.get("primary_location") or {}).get("source") or {})
        out.append({
            "paperId": w.get("id"), "title": w.get("display_name") or w.get("title"),
            "authors": [{"name": a["author"]["display_name"]} for a in w.get("authorships", []) if a.get("author")],
            "venue": src.get("display_name") or "", "year": w.get("publication_year"),
            "publicationDate": w.get("publication_date"),
            "abstract": _undo_inverted(w.get("abstract_inverted_index")),
            "citationCount": w.get("cited_by_count"), "journal": None, "source": "openalex",
            "url": w.get("doi") or w.get("id"),
        })
    return out


# ---------------------------------------------------------------- public API
def verify_title(title: str, year_hint: Optional[int], cutoff: Optional[str],
                 fallbacks: List[str] = ("arxiv", "openalex")) -> Optional[Dict]:
    """Resolve a candidate title to a real paper record (or None)."""
    m = _best(title, year_hint, s2_search(title, 3), cutoff)
    if m and m.get("abstract"):
        return m
    for fb in fallbacks:
        recs = arxiv_search(title, 5, title_only=True) if fb == "arxiv" else openalex_search(title, 5, cutoff)
        m2 = _best(title, year_hint, recs, cutoff)
        if m2 and m2.get("abstract"):
            return m2
    return m if (m and m.get("abstract")) else None


def keyword_search(query: str, limit: int, cutoff: Optional[str]) -> List[Dict]:
    """Direct keyword search (used when the LLM has no web-search tool, and in mock mode)."""
    recs = openalex_search(query, limit, cutoff)
    if len(recs) < limit:
        recs += arxiv_search(query, limit - len(recs))
    return [r for r in recs if r.get("title") and r.get("abstract")
            and is_allowed(r.get("publicationDate"), r.get("year"), cutoff)]
