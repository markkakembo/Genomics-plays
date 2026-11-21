"""Response parsers (logic adapted from upstream utils/gemini_utils.py, Apache-2.0)."""
import json
import re
from typing import Any, Dict, Optional

import json_repair


def parse_json(response: str) -> Optional[Any]:
    if not response or not isinstance(response, str):
        return None
    matches = re.findall(r"```json(.*?)```", response, re.DOTALL)
    if not matches:
        matches = re.findall(r"(\{.*\}|\[.*\])", response, re.DOTALL)
    for s in matches:
        s = s.strip()
        for attempt in (s, _clean(s)):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError:
                pass
        try:
            v = json_repair.loads(s)
            if v:
                return v
        except Exception:
            pass
    return None


def _clean(s: str) -> str:
    s = re.sub(r"[\x00-\x1F\x7F]", "", s)
    s = re.sub(r",\s*([\]}])", r"\1", s)
    return re.sub(r'\\(?![\\"/bfnrtu])', r"\\\\", s)


def parse_latex(response: str) -> str:
    m = re.search(r"```latex\s*(.*?)\s*```", (response or "").strip(), re.DOTALL)
    return m.group(1) if m else (response or "")


def parse_json_and_latex(response: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"json": None, "latex": None}
    jm = re.search(r"```json\s*(.*?)\s*```", response or "", re.DOTALL)
    if jm:
        out["json"] = parse_json("```json\n" + jm.group(1) + "\n```")
    lm = re.search(r"```latex\s*(.*?)\s*```", response or "", re.DOTALL)
    if lm:
        out["latex"] = lm.group(1)
    return out


def parse_code(response: str, lang: str = "python") -> str:
    m = re.search(rf"```{lang}\s*(.*?)```", response or "", re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\w*\s*(.*?)```", response or "", re.DOTALL)
    return (m.group(1) if m else (response or "")).strip()
