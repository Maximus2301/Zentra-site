"""
AI-Powered Content Ideation & SEO/AEO/Meta Reach Strategist for Personal Brand Engine.
Generates persona-grounded, search-intent & algorithm-aligned Instagram content angles across:
- status (Quote / Contrarian / Micro-Thought Card)
- static (Single-Image Graphic / Photo Overlay Post)
- carousel (5-7 Slide Authority & Save-Worthy Deck)
- reel (9:16 Retention-Engineered Kinetic Video)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from ..config.settings import BrandSettings, OUTPUT_DIR, settings
from .llm_client import build_brand_context_block, call_structured_llm
from .search_intel import fetch_autocomplete_queries

logger = logging.getLogger("personal_brand.ideator")

ANGLES_CACHE_DIR = OUTPUT_DIR / "angles_cache"
ANGLES_CACHE_DIR.mkdir(parents=True, exist_ok=True)

InstagramFormat = Literal["status", "static", "carousel", "reel"]


class ContentAngle(BaseModel):
    id: int
    uid: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    tenant_id: str = ""
    brand_slug: str = "default"
    pillar: str
    format: InstagramFormat = Field(
        ...,
        description="One of: status, static, carousel, reel",
    )
    format_label: str = Field(
        default="6-Slide Authority Carousel (4:5)",
        description="Human-readable format label",
    )
    topic: str = Field(..., description="Specific, concrete topic title tailored to the creator's genre")
    primary_search_keyword: str = Field(
        default="",
        description="Exact high-intent 2-5 word phrase users search on Instagram & Google",
    )
    aeo_question: str = Field(
        default="",
        description="Explicit real-world question this post answers clearly for AI Answer Engines & social search",
    )
    hook: str = Field(..., description="Scroll-stopping opening hook (<12 words) engineered for the target audience")
    angle_summary: str = Field(..., description="2-sentence creative direction and core insight")
    why_it_works: str = Field(..., description="Meta algorithm & viral psychology (Saves, DM Shares, Search Intent)")
    cta_trigger: str = Field(default="Save & send to a friend", description="Specific engagement/share call-to-action")


class ContentRoadmap(BaseModel):
    creator_name: str
    creator_handle: str
    angles: List[ContentAngle]
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )


class _LLMContentAngles(BaseModel):
    angles: List[ContentAngle]


def save_angles_cache(roadmap: ContentRoadmap) -> None:
    """Persists full ContentAngle payloads by short UID so callbacks never truncate context."""
    for angle in roadmap.angles:
        if not angle.uid:
            angle.uid = uuid.uuid4().hex[:8]
        cache_path = ANGLES_CACHE_DIR / f"{angle.uid}.json"
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(angle.model_dump_json(indent=2))


def load_angle_from_cache(uid: str, expected_tenant_id: Optional[str] = None) -> Optional[ContentAngle]:
    """Retrieves a cached ContentAngle by UID, enforcing tenant ownership."""
    safe_uid = "".join(c for c in uid if c.isalnum())
    cache_path = ANGLES_CACHE_DIR / f"{safe_uid}.json"
    if not cache_path.exists():
        return None
    with open(cache_path, "r", encoding="utf-8") as f:
        angle = ContentAngle.model_validate_json(f.read())
    if expected_tenant_id is not None and angle.tenant_id and angle.tenant_id != str(expected_tenant_id):
        return None
    return angle


def generate_content_overview(
    brand: Optional[BrandSettings] = None,
    seed_thought: Optional[str] = None,
    requested_format: Optional[str] = None,
    viral_goal: Optional[str] = None,
    tenant_id: str = "",
    brand_slug: str = "default",
) -> ContentRoadmap:
    """
    Uses search autocomplete intelligence + free-tier LLM to generate 4 deeply customized,
    SEO/AEO/Meta-reach optimized Instagram content angles.
    """
    b = brand or settings
    brand_context = build_brand_context_block(b)

    # Fetch live search autocomplete hints ($0.00)
    search_seed = (seed_thought or "").strip() or (
        b.pillars[0].get("name", "") if b.pillars else b.creator.get("genre", "")
    )
    live_queries = fetch_autocomplete_queries(search_seed, max_results=6)
    search_hints_str = (
        "\nReal-World Search Autocomplete Signals (use to anchor keywords & questions):\n"
        + "\n".join(f"  - {q}" for q in live_queries)
        if live_queries
        else ""
    )

    format_directive = (
        f"ALL 4 angles MUST be tailored specifically for the Instagram format '{requested_format}'."
        if requested_format and requested_format in ("status", "static", "carousel", "reel")
        else (
            "Generate a balanced 4-format Instagram mix:\n"
            "  - Angle 1: format='carousel' (high-save educational/framework breakdown)\n"
            "  - Angle 2: format='reel' (high-reach 9:16 hook + direct search answer)\n"
            "  - Angle 3: format='static' (single-image bold graphic / visual comparison)\n"
            "  - Angle 4: format='status' (punchy contrarian quote / tweet-style debate & DM-share starter)"
        )
    )

    goal_line = f"Primary Engagement Goal Override: {viral_goal}" if viral_goal else ""

    if seed_thought:
        user_prompt = (
            f"The creator shared this raw thought/topic/voice memo:\n"
            f"\"{seed_thought.strip()}\"\n"
            f"{search_hints_str}\n\n"
            f"Transform this input into 4 distinct, SEO + AEO + Meta-algorithm optimized Instagram post angles "
            f"tailored to their exact brand persona, genre, and target audience.\n"
            f"{format_directive}\n{goal_line}"
        )
    else:
        user_prompt = (
            f"Generate a fresh weekly batch of 4 high-reach Instagram content angles covering the creator's "
            f"configured content pillars, grounded in real search demand and target audience pain points.\n"
            f"{search_hints_str}\n\n"
            f"{format_directive}\n{goal_line}"
        )

    system_instruction = f"""You are an Elite Instagram Growth, SEO & AEO Strategist.

{brand_context}

Rules for Maximum Reach, Search & Answer Engine Visibility:
1. NEVER write generic corporate fluff or assume a tech/engineering niche unless the creator's profile is actually tech/engineering.
2. Each angle MUST include a concrete `primary_search_keyword` (2-5 words people actually type into Instagram/Google search) and an explicit `aeo_question` (a real user question AI Answer Engines cite).
3. Optimize every hook for Meta ranking signals: curiosity gap for Watch/Dwell Time, utility for Saves, and relatability/emotion for DM Shares ("Send this to...").
4. Ensure each angle has a unique integer `id` (1..4) and a valid `format` in ["status", "static", "carousel", "reel"].
"""

    result = call_structured_llm(
        prompt=user_prompt,
        system_instruction=system_instruction,
        response_schema=_LLMContentAngles,
        temperature=0.78,
    )

    format_labels = {
        "status": "Status / Quote Card (4:5)",
        "static": "Static Single-Image Post (4:5)",
        "carousel": "Authority Carousel (5–7 Slides)",
        "reel": "Kinetic 9:16 Reel Video",
    }

    cleaned_angles: List[ContentAngle] = []
    for idx, angle in enumerate(result.angles[:4], 1):
        angle.id = idx
        angle.uid = uuid.uuid4().hex[:8]
        angle.tenant_id = str(tenant_id)
        angle.brand_slug = brand_slug
        angle.format_label = format_labels.get(angle.format, angle.format_label)
        cleaned_angles.append(angle)

    roadmap = ContentRoadmap(
        creator_name=b.name or "Creator",
        creator_handle=b.handle or "@creator",
        angles=cleaned_angles,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    save_angles_cache(roadmap)
    return roadmap
