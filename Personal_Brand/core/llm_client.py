"""
Zero-Cost Multi-Provider LLM Client for Personal Brand Engine.
Supports free-tier text/JSON providers (Gemini Flash Free Tier, Groq Free Tier,
OpenRouter Free Tier, or local Ollama) with Pydantic structured output validation.
Does NOT use paid Anthropic APIs.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Optional, Type, TypeVar

import requests
from pydantic import BaseModel

from ..config.settings import BrandSettings, settings

logger = logging.getLogger("personal_brand.llm_client")
T = TypeVar("T", bound=BaseModel)

# Circuit breaker so repeated Gemini 503/timeout spikes skip straight to Groq for 5 mins
_GEMINI_COOLDOWN_UNTIL: float = 0.0


class LLMNotConfiguredError(RuntimeError):
    """Raised when no free-tier LLM provider is configured or reachable."""


def _extract_json_payload(raw_text: str) -> str:
    """Strips markdown code fences and isolates the JSON object from LLM text."""
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]
    return text


def _call_gemini(
    api_key: str,
    prompt: str,
    system_instruction: str,
    response_schema: Optional[Type[T]],
    temperature: float,
    history: Optional[list[dict[str, str]]] = None,
) -> Any:
    """Calls Google Gemini Flash free tier (structured JSON or plain text)."""
    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=11000),
    )
    primary = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")
    candidates = [primary, "gemini-3.8-flash"]
    models = list(dict.fromkeys(candidates))

    contents: Any = prompt
    if history:
        turns = [
            types.Content(
                role="model" if m.get("role") == "assistant" else "user",
                parts=[types.Part.from_text(text=m.get("content", ""))],
            )
            for m in history[-6:]
            if m.get("content")
        ]
        turns.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
        contents = turns

    cfg: dict[str, Any] = {
        "system_instruction": system_instruction,
        "temperature": temperature,
    }
    if response_schema is not None:
        cfg["response_mime_type"] = "application/json"
        cfg["response_schema"] = response_schema

    last_err: Optional[Exception] = None
    for model_name in models:
        try:
            logger.info(f"Calling Gemini ({model_name})...")
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=cfg,
            )
            if response.text:
                if response_schema is not None:
                    data = json.loads(_extract_json_payload(response.text))
                    return response_schema.model_validate(data)
                return response.text.strip()
        except Exception as e:
            last_err = e
            logger.warning(f"Gemini model {model_name} failed: {e}")
    raise RuntimeError(f"Gemini generation failed: {last_err}")


def _call_openai_compatible(
    endpoint: str,
    api_key: Optional[str],
    model: str,
    prompt: str,
    system_instruction: str,
    response_schema: Optional[Type[T]],
    temperature: float,
    extra_headers: Optional[dict[str, str]] = None,
    history: Optional[list[dict[str, str]]] = None,
) -> Any:
    """Calls Groq, OpenRouter, or Ollama OpenAI-compatible endpoints (JSON or plain text)."""
    full_system = system_instruction
    if response_schema is not None:
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        full_system = (
            f"{system_instruction}\n\n"
            f"You MUST reply with ONLY a valid JSON object matching this exact JSON Schema "
            f"(never return null for lists or required strings):\n"
            f"{schema_json}"
        )

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)

    messages: list[dict[str, str]] = [{"role": "system", "content": full_system}]
    if history:
        for m in history[-6:]:
            if m.get("content"):
                messages.append({"role": m.get("role", "user"), "content": m["content"]})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_schema is not None:
        payload["response_format"] = {"type": "json_object"}

    logger.info(f"Calling {endpoint} ({model})...")
    res = requests.post(endpoint, headers=headers, json=payload, timeout=35)
    res.raise_for_status()
    content = res.json()["choices"][0]["message"]["content"]
    if response_schema is not None:
        data = json.loads(_extract_json_payload(content))
        return response_schema.model_validate(data)
    return content.strip()


def has_llm_provider() -> bool:
    """Returns True if at least one free-tier cloud or local LLM provider is configured."""
    return bool(
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GROQ_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OLLAMA_MODEL")
    )


def _dispatch_llm(
    prompt: str,
    system_instruction: str,
    response_schema: Optional[Type[T]],
    temperature: float,
    history: Optional[list[dict[str, str]]] = None,
) -> Any:
    """Executes free-tier LLM call with automatic provider failover and Gemini circuit breaker."""
    global _GEMINI_COOLDOWN_UNTIL
    errors: list[str] = []
    has_groq = bool(os.getenv("GROQ_API_KEY", ""))

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if gemini_key and (not has_groq or time.time() >= _GEMINI_COOLDOWN_UNTIL):
        try:
            return _call_gemini(
                gemini_key, prompt, system_instruction, response_schema, temperature, history=history
            )
        except Exception as e:
            errors.append(f"Gemini: {e}")
            if has_groq:
                _GEMINI_COOLDOWN_UNTIL = time.time() + 300.0
                logger.info("Gemini unavailable; activating 5-min failover to Groq.")

    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        groq_models = list(
            dict.fromkeys([
                os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                "openai/gpt-oss-120b",
                "qwen/qwen3.8-27b",
            ])
        )
        for gm in groq_models:
            try:
                return _call_openai_compatible(
                    "https://api.groq.com/openai/v1/chat/completions",
                    groq_key,
                    gm,
                    prompt,
                    system_instruction,
                    response_schema,
                    temperature,
                    history=history,
                )
            except Exception as e:
                errors.append(f"Groq({gm}): {e}")

    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key:
        try:
            model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
            return _call_openai_compatible(
                "https://openrouter.ai/api/v1/chat/completions",
                openrouter_key,
                model,
                prompt,
                system_instruction,
                response_schema,
                temperature,
                extra_headers={"HTTP-Referer": "https://zentraai.in", "X-Title": "Personal Brand Engine"},
                history=history,
            )
        except Exception as e:
            errors.append(f"OpenRouter: {e}")

    ollama_model = os.getenv("OLLAMA_MODEL", "")
    if ollama_model:
        try:
            base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
            return _call_openai_compatible(
                f"{base}/v1/chat/completions",
                None,
                ollama_model,
                prompt,
                system_instruction,
                response_schema,
                temperature,
                history=history,
            )
        except Exception as e:
            errors.append(f"Ollama: {e}")

    if errors:
        raise LLMNotConfiguredError(f"All configured LLM providers failed: {' | '.join(errors)}")

    raise LLMNotConfiguredError(
        "No free-tier LLM key configured. Set GEMINI_API_KEY (free at aistudio.google.com), "
        "GROQ_API_KEY (free at console.groq.com), OPENROUTER_API_KEY, or OLLAMA_MODEL in .env."
    )


def call_structured_llm(
    prompt: str,
    system_instruction: str,
    response_schema: Type[T],
    temperature: float = 0.75,
) -> T:
    """Calls the zero-cost LLM provider and returns a validated Pydantic object."""
    return _dispatch_llm(prompt, system_instruction, response_schema, temperature)


def call_text_llm(
    prompt: str,
    system_instruction: str,
    history: Optional[list[dict[str, str]]] = None,
    temperature: float = 0.6,
) -> str:
    """Calls the zero-cost LLM provider for conversational plain-text responses."""
    return str(_dispatch_llm(prompt, system_instruction, None, temperature, history=history))


SEO_AEO_META_RULES = """=== SEO, AEO & META REACH OPTIMIZATION RULES ===
1. 125-Character Natural SEO Fold Rule: The very first sentence of `caption` (<=125 chars) MUST weave the `primary_search_keyword` (or its exact terms) organically into a natural human hook before '...more'. NEVER write robotic prefixes like 'keyword:' or 'SEO:'.
2. Natural AEO Direct Answer: Populate `aeo_direct_answer` with a crisp 40-60 word factual answer to `aeo_question` with entity attribution (creator name, role/credentials, niche/city). In `caption`, weave that direct answer naturally WITHOUT labeling it 'AEO Direct Answer:'.
3. Meta Distribution Signals: Engineer the post to drive (a) Saves ("Bookmark this..."), (b) DM Shares ("Send this to someone who..."), and (c) Comment velocity (ask a specific, low-friction debate or experience question).
4. Multimodal Keyword Lock: Ensure the `primary_search_keyword` (or exact core topic entity) appears across the visual headline, caption opener, and ALT text (and spoken script for Reels).
5. ALT Text (`alt_text`): Write a clear 15-30 word accessibility & search description describing what is visually on the slide/image plus the primary topic keyword.
6. Focused Hashtags: Provide 3 to 5 hyper-relevant semantic search hashtags (never dump 15+ generic spam tags)."""


def build_brand_context_block(brand: Optional[BrandSettings] = None) -> str:
    """
    Constructs a comprehensive, non-hardcoded persona prompt block from the creator's
    profile, niche/genre, target audience, voice DNA, and virality objectives.
    """
    b = brand or settings
    creator = b.creator
    voice = b.voice
    audience = b.target_audience
    virality = b.virality_strategy

    pillars_desc = "\n".join(
        f"  - {p.get('name')} ({p.get('id', '')}): {p.get('description') or ', '.join(p.get('core_themes', []))}"
        for p in (b.pillars or [])
    ) or "  - General Personal Authority"

    tone_attrs = ", ".join(voice.get("tone_attributes", [])) or voice.get("writing_style", "Authentic and clear")
    encouraged = ", ".join(voice.get("vocabulary", {}).get("encouraged", []))
    forbidden = ", ".join(voice.get("vocabulary", {}).get("forbidden", []))
    contrarian = "\n".join(f"  - {r}" for r in voice.get("contrarian_rules", []))
    hook_styles = "\n".join(f"  - {h}" for h in voice.get("hook_archetypes", []))
    pain_points = ", ".join(audience.get("pain_points", []))
    outcomes = ", ".join(audience.get("desired_outcomes", []))
    location_str = creator.get("city") or ""

    return f"""=== CREATOR BRAND IDENTITY ===
Name: {b.name or 'Creator'}
Handle: {b.handle or '@creator'}
Genre / Niche: {creator.get('genre') or 'Not specified — infer carefully from bio and pillars'}
Location / Region: {location_str or 'Global / Not specified'}
Tagline: {creator.get('tagline', '')}
Bio: {creator.get('bio', '')}
Language & Register: {creator.get('language_style', 'Natural, clear English')}

=== TARGET AUDIENCE ===
Primary Audience: {audience.get('primary_audience', 'General audience interested in the creator niche')}
Core Pain Points: {pain_points or 'Infer from niche and topic'}
Desired Outcomes: {outcomes or 'Clarity, actionable insight, transformation'}
Sophistication Level: {audience.get('awareness_level', 'Accessible yet high-value')}

=== VOICE DNA & GUARDRAILS ===
Archetype: {voice.get('archetype', 'Authentic Domain Practitioner')}
Tone Attributes: {tone_attrs}
Cadence: {voice.get('cadence', voice.get('writing_style', 'Direct and engaging'))}
Perspective: {voice.get('perspective', 'First-person authentic voice')}
Real Voice Sample: {voice.get('sample_transcript', '')[:400]}
Encouraged Vocabulary: {encouraged or 'Natural domain language'}
Forbidden Words/Cliches: {forbidden or 'Generic motivational fluff'}
Contrarian / Compliance Rules:
{contrarian or '  - Stay authentic to the creator persona; avoid generic AI cliches.'}
Preferred Hook Styles:
{hook_styles or '  - Curiosity gap, myth-busting, contrarian insight, story-driven hook'}

=== CONTENT PILLARS ===
{pillars_desc}

=== VIRALITY & ENGAGEMENT STRATEGY ===
Primary Growth Objective: {virality.get('primary_goal', 'saves_and_shares')}
CTA / Engagement Style: {virality.get('cta_style', 'Ask a polarizing or relatable question to spark comments')}
DM Automation Keyword (if any): {virality.get('dm_keyword', '')}
Hashtag Strategy: {virality.get('hashtag_strategy', '3-5 focused semantic search tags')}
"""
