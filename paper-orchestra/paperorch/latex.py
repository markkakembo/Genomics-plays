"""LaTeX compilation and PDF helpers."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import List, Optional

import pymupdf as fitz  # PyMuPDF


def pick_engine(pref: str = "auto") -> str:
    if pref != "auto":
        return pref
    for eng in ("latexmk", "pdflatex", "tectonic"):
        if shutil.which(eng):
            return eng
    raise SystemExit("No LaTeX engine found. Install TeX Live (latexmk/pdflatex) or tectonic "
                     "(https://tectonic-typesetting.github.io).")


def compile_latex(cwd: str, tex_name: str, engine: str = "auto", timeout: int = 300) -> Optional[str]:
    """Compile <cwd>/<tex_name>.tex -> <cwd>/<tex_name>.pdf. Returns the pdf path or None."""
    engine = pick_engine(engine)
    pdf = os.path.join(cwd, f"{tex_name}.pdf")
    if os.path.exists(pdf):
        os.remove(pdf)
    env = {k: v for k, v in os.environ.items() if k not in ("TEXINPUTS", "TEXMFHOME")}
    if engine == "tectonic":
        cmds = [["tectonic", "-X", "compile", f"{tex_name}.tex", "--keep-logs", "--keep-intermediates"]]
    elif engine == "latexmk":
        cmds = [["latexmk", "-pdf", "-interaction=nonstopmode", "-f", f"{tex_name}.tex"]]
    else:
        cmds = [["pdflatex", "-interaction=nonstopmode", f"{tex_name}.tex"], ["bibtex", tex_name],
                ["pdflatex", "-interaction=nonstopmode", f"{tex_name}.tex"],
                ["pdflatex", "-interaction=nonstopmode", f"{tex_name}.tex"]]
    log = []
    for c in cmds:
        try:
            r = subprocess.run(c, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
            log.append(f"$ {' '.join(c)}\n[exit {r.returncode}]\n{r.stdout[-4000:]}\n{r.stderr[-4000:]}")
        except subprocess.TimeoutExpired:
            log.append(f"$ {' '.join(c)}\n[timeout]")
    with open(os.path.join(cwd, f"{tex_name}.compile.log"), "w") as f:
        f.write("\n\n".join(log))
    return pdf if os.path.exists(pdf) and os.path.getsize(pdf) > 0 else None


def pdf_text(pdf_path: str, max_chars: int = 200000) -> str:
    with fitz.open(pdf_path) as doc:
        return "\n".join(p.get_text() for p in doc)[:max_chars]


def pdf_to_pngs(pdf_path: str, out_dir: str, scale: float = 1.5, max_pages: int = 12) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            p = os.path.join(out_dir, f"page_{i+1:02d}.png")
            page.get_pixmap(matrix=fitz.Matrix(scale, scale)).save(p)
            paths.append(p)
    return paths


def pdf_page_count(pdf_path: str) -> int:
    with fitz.open(pdf_path) as doc:
        return len(doc)


def sanitize_citations(tex: str, valid_keys: set) -> tuple[str, List[str]]:
    """Drop \\cite keys that are not in the verified bibliography (guards against hallucinated refs)."""
    removed: List[str] = []

    def fix(m):
        cmd, opt, keys = m.group(1), m.group(2) or "", m.group(3)
        ks = [k.strip() for k in keys.split(",") if k.strip()]
        good = [k for k in ks if k in valid_keys]
        removed.extend(k for k in ks if k not in valid_keys)
        return f"\\{cmd}{opt}{{{','.join(good)}}}" if good else ""

    tex = re.sub(r"\\(cite[tp]?|citeauthor|citeyear)(\[[^\]]*\])?\{([^}]*)\}", fix, tex)
    return tex, removed


def looks_complete(tex: str) -> bool:
    return bool(tex) and "\\documentclass" in tex and "\\end{document}" in tex
