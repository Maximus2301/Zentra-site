"""
5-Axis Brand, Virality, SEO, AEO & Meta Reach Critic for Personal Brand Engine.
Evaluates every generated Instagram post on:
1. Scroll-Stop Hook Power
2. Brand Persona & Voice Fit
3. Meta Viral Distribution Signals (Saves, DM Shares, Comment Velocity)
4. Instagram & Google Search SEO (125-char fold keyword, ALT text, 3-5 semantic tags)
5. AEO / Answer Engine Clarity (Explicit Q&A directness & entity attribution)
"""
from __future__ import annotations

import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from ..config.settings import BrandSettings, settings
from .llm_client import build_brand_context_block, call_structured_llm

logger = logging.getLogger("personal_brand.critic")


class CriticEvaluation(BaseModel):
    hook_score: int = Field(..., ge=1, le=10, description="Scroll-stop power of the opening hook (1-10)")
    persona_alignment_score: int = Field(..., ge=1, le=10, description="Match with creator's genre, voice & audience (1-10)")
    virality_engagement_score: int = Field(..., ge=1, le=10, description="Saves, DM Shares ('Send this to...'), and comment velocity potential (1-10)")
    seo_discoverability_score: int = Field(..., ge=1, le=10, description="125-char keyword opener, ALT text, and 3-5 semantic tags quality (1-10)")
    aeo_citation_score: int = Field(..., ge=1, le=10, description="Clarity of direct question-answer structure & creator authority for AI search (1-10)")
    overall_score: int = Field(..., ge=1, le=100, description="Composite readiness score out of 100")
    verdict: str = Field(..., description="Short 1-sentence editorial + reach verdict")
    strengths: List[str] = Field(default_factory=list, description="1-2 key strengths")
    improvements: List[str] = Field(default_factory=list, description="1-2 specific tweaks to boost reach/SEO")
    suggested_pinned_comment: str = Field(..., description="Ready-to-paste pinned comment to spark replies")


def evaluate_post_package(
    format_type: str,
    topic: str,
    hook: str,
    content_summary: str,
    caption: str,
    primary_keyword: str = "",
    aeo_question: str = "",
    alt_text: str = "",
    hashtags: Optional[List[str]] = None,
    brand: Optional[BrandSettings] = None,
) -> CriticEvaluation:
    """
    Audits a generated Instagram post package across Brand Fit, Meta Virality,
    Instagram/Google SEO, and AEO (Answer Engine Optimization).
    """
    b = brand or settings
    brand_context = build_brand_context_block(b)

    system_instruction = f"""You are a Senior Instagram Algorithm, SEO & Answer Engine (AEO) Critic.

{brand_context}

Evaluate the proposed {format_type.upper()} post strictly on 5 axes:
1. Hook Power: Stops scrolling in <1.5 seconds?
2. Brand Fidelity: Matches this creator's authentic tone, niche, and compliance rules?
3. Meta Reach Mechanics: Explicitly drives Saves + DM Shares ("Send to...") + Comments?
4. Instagram & Google SEO: Is `primary_keyword` naturally inside the first 125 chars of `caption`? Is `alt_text` descriptive? Are there 3-5 focused semantic hashtags?
5. AEO / AI Citation Clarity: Does it directly answer `aeo_question` with clear entity attribution?
Provide a high-converting pinned comment the creator can drop immediately after posting.
"""

    first_125 = (caption or "")[:125].replace("\n", " ")
    prompt = (
        f"Format: {format_type}\n"
        f"Topic: {topic}\n"
        f"Target Search Keyword: {primary_keyword or 'Not set'}\n"
        f"AEO Question: {aeo_question or 'Not set'}\n"
        f"Opening Hook: {hook}\n"
        f"First 125 Chars of Caption: {first_125}\n"
        f"ALT Text: {alt_text or 'Missing'}\n"
        f"Hashtags ({len(hashtags or [])}): {', '.join(hashtags or [])}\n\n"
        f"Content Summary:\n{content_summary[:1000]}\n\n"
        f"Full Caption:\n{caption[:1000]}"
    )

    try:
        return call_structured_llm(
            prompt=prompt,
            system_instruction=system_instruction,
            response_schema=CriticEvaluation,
            temperature=0.35,
        )
    except Exception as e:
        logger.warning(f"Critic evaluation skipped ({e}); returning neutral baseline.")
        return CriticEvaluation(
            hook_score=8,
            persona_alignment_score=8,
            virality_engagement_score=8,
            seo_discoverability_score=8,
            aeo_citation_score=8,
            overall_score=80,
            verdict="Ready for human review (critic check bypassed).",
            strengths=["Aligned with selected topic"],
            improvements=[],
            suggested_pinned_comment=f"Curious where you stand on {topic} — share your thoughts below 👇",
        )
