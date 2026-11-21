"""Provider-agnostic LLM wrapper: OpenAI, Anthropic, Gemini, or an offline Mock.

Every agent calls `llm.complete(prompt, system=..., images=..., task=..., ctx=...)`.
Real providers ignore `task`/`ctx`; the Mock provider uses them to produce deterministic,
input-grounded outputs so the whole pipeline can run end to end without any API key.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import threading
import time
from typing import Any, Dict, List, Optional

from .config import Config

_LOG_LOCK = threading.Lock()


class BaseLLM:
    provider = "base"
    supports_vision = True
    supports_web_search = False

    def __init__(self, model: str, call_log: Optional[str] = None, max_retries: int = 5):
        self.model = model
        self.call_log = call_log
        self.max_retries = max_retries

    # --- public -----------------------------------------------------------
    def complete(self, prompt: str, system: Optional[str] = None, images: Optional[List[str]] = None,
                 task: str = "generic", ctx: Optional[Dict[str, Any]] = None,
                 temperature: Optional[float] = None, web_search: bool = False,
                 max_tokens: int = 32000) -> str:
        images = [p for p in (images or []) if p and os.path.exists(p)] if self.supports_vision else []
        t0 = time.time()
        last = None
        for attempt in range(self.max_retries):
            try:
                out = self._complete(prompt, system, images, task, ctx or {}, temperature,
                                     web_search and self.supports_web_search, max_tokens)
                self._log(task, prompt, system, images, out, time.time() - t0)
                return out or ""
            except Exception as e:  # noqa: BLE001
                last = e
                if "PerDay" in str(e) or "insufficient_quota" in str(e):
                    raise RuntimeError(f"{self.provider}:{self.model} daily quota exhausted; not retrying. "
                                       "Use another model in config.yaml or wait for the quota to reset.") from None
                wait = min(60, 5 * (2 ** attempt)) if attempt else 2
                print(f"   ! {self.provider}:{self.model} call failed ({task}, attempt {attempt+1}): {e}. Retrying in {wait}s")
                time.sleep(wait)
        raise RuntimeError(f"LLM call failed after {self.max_retries} attempts: {last}")

    # --- internals --------------------------------------------------------
    def _complete(self, prompt, system, images, task, ctx, temperature, web_search, max_tokens) -> str:
        raise NotImplementedError

    def _log(self, task, prompt, system, images, out, dt):
        if not self.call_log:
            return
        rec = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "provider": self.provider, "model": self.model,
               "task": task, "prompt_chars": len(prompt or "") + len(system or ""), "n_images": len(images),
               "output_chars": len(out or ""), "seconds": round(dt, 2)}
        with _LOG_LOCK, open(self.call_log, "a") as f:
            f.write(json.dumps(rec) + "\n")


def _b64(path: str) -> tuple[str, str]:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        return mime, base64.b64encode(f.read()).decode()


class OpenAILLM(BaseLLM):
    provider = "openai"
    supports_web_search = True

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ.get("OPENAI_BASE_URL") or None)

    def _complete(self, prompt, system, images, task, ctx, temperature, web_search, max_tokens):
        if web_search:
            try:  # Responses API with the hosted web search tool
                content = [{"type": "input_text", "text": prompt}]
                r = self.client.responses.create(model=self.model, instructions=system or None,
                                                 tools=[{"type": "web_search"}],
                                                 input=[{"role": "user", "content": content}])
                return r.output_text
            except Exception as e:  # noqa: BLE001
                print(f"   ! OpenAI web_search unavailable ({e}); disabling it and falling back to plain completion")
                self.supports_web_search = False
        content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
        for p in images:
            mime, data = _b64(p)
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": content})
        # GPT-5 / o-series reject custom temperature, mirroring upstream we omit it.
        r = self.client.chat.completions.create(model=self.model, messages=msgs)
        return r.choices[0].message.content


class AnthropicLLM(BaseLLM):
    provider = "anthropic"
    supports_web_search = True

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.max_out = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "32000"))

    def _complete(self, prompt, system, images, task, ctx, temperature, web_search, max_tokens):
        content: List[Dict[str, Any]] = []
        for p in images:
            mime, data = _b64(p)
            if mime not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
                continue
            content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}})
        content.append({"type": "text", "text": prompt})
        kw: Dict[str, Any] = dict(model=self.model, max_tokens=min(max_tokens, self.max_out),
                                  messages=[{"role": "user", "content": content}])
        if system:
            kw["system"] = system
        if temperature is not None:
            kw["temperature"] = temperature
        if web_search:
            kw["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}]
        try:
            with self.client.messages.stream(**kw) as s:
                msg = s.get_final_message()
        except Exception as e:  # noqa: BLE001
            if web_search:
                print(f"   ! Anthropic web search unavailable ({e}); retrying without it")
                kw.pop("tools", None)
                with self.client.messages.stream(**kw) as s:
                    msg = s.get_final_message()
            else:
                raise
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


class GeminiLLM(BaseLLM):
    provider = "gemini"
    supports_web_search = True  # Google Search grounding, as in the paper
    _rpm_lock = threading.Lock()
    _last_call: Dict[str, float] = {}

    def _throttle(self):
        """Respect a requests-per-minute cap (free tier: 5 RPM per model). Set GEMINI_MAX_RPM=0 to disable."""
        rpm = float(os.environ.get("GEMINI_MAX_RPM", "5"))
        if rpm <= 0:
            return
        with GeminiLLM._rpm_lock:
            wait = 60.0 / rpm - (time.time() - GeminiLLM._last_call.get(self.model, 0))
            if wait > 0:
                time.sleep(wait)
            GeminiLLM._last_call[self.model] = time.time()

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        from google import genai
        if os.environ.get("VERTEX_AI_PROJECT") and os.environ.get("VERTEX_AI_LOCATION"):
            self.client = genai.Client(vertexai=True, project=os.environ["VERTEX_AI_PROJECT"],
                                       location=os.environ["VERTEX_AI_LOCATION"])
        else:
            self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def _complete(self, prompt, system, images, task, ctx, temperature, web_search, max_tokens):
        from google.genai import types
        parts = []
        for p in images:
            mime, _ = _b64(p)
            with open(p, "rb") as f:
                parts.append(types.Part.from_bytes(data=f.read(), mime_type=mime))
        parts.append(types.Part.from_text(text=prompt))
        cfg: Dict[str, Any] = {}
        if system:
            cfg["system_instruction"] = system
        if temperature is not None:
            cfg["temperature"] = temperature
        if web_search:
            cfg["tools"] = [types.Tool(google_search=types.GoogleSearch())]
        self._throttle()
        try:
            r = self.client.models.generate_content(model=self.model, contents=parts,
                                                    config=types.GenerateContentConfig(**cfg))
        except Exception as e:  # noqa: BLE001
            if not web_search or "PerDay" in str(e):
                raise
            # Google Search grounding is quota-limited on some keys: disable it for the rest of the run.
            print(f"   ! Gemini Google Search grounding unavailable ({str(e)[:60]}...); disabling it, using plain calls")
            self.supports_web_search = False
            cfg.pop("tools", None)
            self._throttle()
            r = self.client.models.generate_content(model=self.model, contents=parts,
                                                    config=types.GenerateContentConfig(**cfg))
        if not r.text:
            fr = r.candidates[0].finish_reason if r.candidates else "no candidates"
            print(f"   ! Gemini returned empty text (finish_reason={fr})")
        return r.text


class MockLLM(BaseLLM):
    """Offline, deterministic stand-in. Produces outputs grounded in the inputs (no invented numbers)."""
    provider = "mock"
    supports_vision = False
    supports_web_search = False

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.max_retries = 1  # deterministic: retrying cannot help

    def _complete(self, prompt, system, images, task, ctx, temperature, web_search, max_tokens):
        from . import mock
        return mock.respond(task, ctx, prompt)


def make_llm(cfg: Config, role: str, call_log: Optional[str] = None) -> BaseLLM:
    cls = {"openai": OpenAILLM, "anthropic": AnthropicLLM, "gemini": GeminiLLM, "mock": MockLLM}[cfg.provider]
    return cls(cfg.model(role), call_log=call_log)
