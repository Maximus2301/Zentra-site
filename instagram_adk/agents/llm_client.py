"""Robust LLM client supporting Google Gemini with intelligent offline fallback."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Type, TypeVar
from pydantic import BaseModel
from ..config.settings import GEMINI_API_KEY

logger = logging.getLogger("instagram_adk.llm_client")
T = TypeVar("T", bound=BaseModel)


def get_genai_client() -> Any | None:
    """Returns a Google GenAI Client if API key is configured."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or GEMINI_API_KEY
    if not key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except Exception as e:
        logger.warning(f"Could not initialize Google GenAI Client: {e}")
        return None


def call_structured_gemini(
    prompt: str,
    system_instruction: str,
    response_schema: Type[T],
    model: str = "gemini-2.5-flash",
    fallback_factory: Any | None = None,
) -> T:
    """Calls Gemini with structured response_schema. Falls back to generator if no key."""
    client = get_genai_client()
    if client:
        try:
            logger.info(f"Calling Gemini ({model}) for structured generation...")
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                    "temperature": 0.7,
                },
            )
            if response.text:
                return response_schema.model_validate_json(response.text)
        except Exception as e:
            logger.warning(f"Gemini API call failed ({e}). Using intelligent fallback generation.")

    if fallback_factory:
        logger.info("Using account-calibrated intelligent generator fallback.")
        return fallback_factory()
    raise RuntimeError("No Gemini API key available and no fallback provided.")
