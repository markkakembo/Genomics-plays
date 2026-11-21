"""Configuration loading. API keys are NEVER stored in config; they are read from env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM_DIR = os.path.join(PROJECT_ROOT, "upstream")

# API keys live in <project>/.env (never in config files or logs). Existing env vars take precedence.
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=False)

# provider -> env var that must hold the key
KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "mock": None,
}

DEFAULT_MODELS = {
    "openai": {"writer": "gpt-5", "reflection": "gpt-5", "plotting": "gpt-5", "discovery": "gpt-5-mini"},
    "anthropic": {"writer": "claude-sonnet-4-5", "reflection": "claude-sonnet-4-5", "plotting": "claude-sonnet-4-5", "discovery": "claude-haiku-4-5"},
    # Gemini models used in the paper (App. D.1)
    # Paper used gemini-3.1-pro-preview / gemini-3-flash-preview; those are not available to every key.
    # gemini-3.5-flash was verified with models.list() + a test call on 2026-11-14.
    "gemini": {"writer": "gemini-3.5-flash", "reflection": "gemini-3.5-flash", "plotting": "gemini-3.5-flash", "discovery": "gemini-3.5-flash"},
    "mock": {"writer": "mock", "reflection": "mock", "plotting": "mock", "discovery": "mock"},
}


@dataclass
class Config:
    provider: str = "gemini"
    models: Dict[str, str] = field(default_factory=dict)
    template: str = "iclr2025"
    research_cutoff: str | None = None          # "YYYY-MM"; defaults to current month
    use_plotting: bool = True
    plotting_max_critic_rounds: int = 3
    max_reflections: int = 3                    # content-refinement iterations (paper: 3)
    review_ensemble: int = 3                    # AgentReview ensemble size (upstream default: 3)
    formatting_loop: bool = True                # VLM layout check after refinement (needs a vision model)
    lit: Dict[str, Any] = field(default_factory=dict)
    latex_engine: str = "auto"                  # auto | tectonic | latexmk | pdflatex
    temperature: float = 0.7

    @property
    def lit_settings(self) -> Dict[str, Any]:
        d = {
            "max_search_tasks": 0,              # 0 = no cap (paper behaviour)
            "discovery_workers": 10,            # paper: 10 concurrent discovery workers
            "verify_delay_sec": 1.0,            # paper: 1 query/sec to Semantic Scholar
            "min_cite_fraction": 0.9,           # paper: cite >=90% of the verified pool
            "keyword_search_results": 8,        # results per direct scholarly-API keyword query
            "use_llm_recall": True,             # ask the LLM to propose candidate titles
            "use_web_search": True,             # use provider web search if available (Gemini grounding / OpenAI web_search)
            "use_keyword_search": "auto",       # true | false | auto (= only when the model has no web search, or mock)
            "fallback_sources": ["arxiv", "openalex"],
        }
        d.update(self.lit or {})
        return d

    def model(self, role: str) -> str:
        m = dict(DEFAULT_MODELS.get(self.provider, {}))
        m.update(self.models or {})
        return m[role]

    def check_keys(self) -> None:
        env = KEY_ENV.get(self.provider, "missing")
        if env == "missing":
            raise SystemExit(f"Unknown provider '{self.provider}'. Use one of: {', '.join(KEY_ENV)}")
        if env and not os.environ.get(env):
            if self.provider == "gemini" and os.environ.get("VERTEX_AI_PROJECT"):
                return
            raise SystemExit(
                f"Provider '{self.provider}' needs the {env} environment variable. "
                f"Run `export {env}=...` (or use --provider mock for a dry run)."
            )


def load_config(path: str | None, overrides: Dict[str, Any] | None = None) -> Config:
    data: Dict[str, Any] = {}
    if path and os.path.exists(path):
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    for k, v in (overrides or {}).items():
        if v is not None:
            data[k] = v
    known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    return Config(**known)
