"""
Persona-Driven Carousel Generator for Personal Brand Engine.
Produces structured 5-7 slide high-retention Instagram carousels grounded 100% in the
creator's brand DNA, genre, target audience, and virality goals.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from ..config.settings import BrandSettings, settings
from ..core.llm_client import SEO_AEO_META_RULES, build_brand_context_block, call_structured_llm

logger = logging.getLogger("personal_brand.carousel_generator")


class CarouselSlide(BaseModel):
    """Schema for an individual carousel slide."""
    slide_number: int = Field(..., ge=1, le=10, description="1-indexed slide number")
    slide_type: str = Field(..., description="hook, agitation, framework, tactics, cheatsheet, or cta")
    badge: str = Field(..., description="Top pill badge, e.g. 01 / THE REALITY CHECK")
    headline: str = Field(..., description="High-impact bold headline (<12 words on Slide 1)")
    subheadline: Optional[str] = Field(None, description="Supporting context or lead-in sentence")
    body_points: List[str] = Field(default_factory=list, description="2 to 4 concise, punchy bullet points")
    highlight_box: Optional[str] = Field(None, description="Key takeaway, myth-buster, or rule callout")
    footer_cue: str = Field(default="SWIPE ➔", description="Bottom action prompt, e.g. SWIPE ➔ or SAVE 📌")


class CarouselDeck(BaseModel):
    """Complete carousel package including SEO/AEO/Meta-optimized Instagram caption."""
    topic: str
    pillar: str
    primary_search_keyword: str = Field(
        default="",
        description="2-5 word target search phrase front-loaded into caption opener",
    )
    aeo_question: str = Field(
        default="",
        description="Explicit user question answered by this carousel",
    )
    aeo_direct_answer: str = Field(
        default="",
        description="Citation-ready 40-60 word direct factual answer with entity attribution",
    )
    title: str
    slides: List[CarouselSlide]
    alt_text: str = Field(
        default="",
        description="15-30 word descriptive ALT text summarizing the carousel visual & primary keyword",
    )
    caption: str = Field(
        ...,
        description="SEO/AEO-optimized Instagram caption: <=125-char keyword hook, direct answer, save/DM-share CTA",
    )
    hashtags: List[str] = Field(default_factory=list, description="3-5 hyper-relevant semantic search hashtags")
    estimated_read_time: str = Field(default="60s")


def _build_system_prompt(brand: BrandSettings, slide_count: int) -> str:
    """Builds a dynamic system instruction tailored strictly to the creator's brand DNA."""
    brand_context = build_brand_context_block(brand)
    slide_blueprint = brand.carousel_specs.get("slide_blueprint")
    blueprint_str = ""
    if slide_blueprint:
        blueprint_str = "\nCustom Slide Blueprint:\n" + "\n".join(
            f"  Slide {s.get('slide')}: {s.get('name')} — {s.get('guidance')}"
            for s in slide_blueprint
        )

    return f"""You are the Lead Instagram Ghostwriter & Search Growth Strategist for {brand.name or 'the creator'} ({brand.handle or '@creator'}).

{brand_context}
{blueprint_str}

{SEO_AEO_META_RULES}

Your goal is to write a viral, high-retention {slide_count}-slide Instagram Carousel Deck tailored strictly to this creator's niche, language style, voice DNA, and target audience.

Critical Rules:
1. NEVER inject software engineering, AI agent, or unrelated jargon unless the creator's genre is actually tech.
2. Slide 1 MUST be a scroll-stopping hook under 12 words with high curiosity gap or emotional resonance for the target audience.
3. Slide 2 addresses the relatable pain point, myth, or hidden mistake.
4. Middle slides deliver concrete, structured, actionable value (framework, breakdown, steps, or comparison) with concise bullets (max 14 words per bullet so slides stay super readable on mobile).
5. Penultimate slide provides a save-worthy summary or checklist.
6. Final slide wraps up in the creator's authentic voice and includes BOTH a DM-share trigger ("Send this to someone who...") and a Save/Follow CTA.
7. Caption MUST open with `primary_search_keyword` naturally within the first 125 chars, include the `aeo_direct_answer` block, end with a comment question + 3–5 semantic search hashtags.
"""


def generate_carousel(
    topic: str,
    pillar_id: Optional[str] = None,
    brand: Optional[BrandSettings] = None,
    hook_override: Optional[str] = None,
    angle_summary: Optional[str] = None,
    primary_search_keyword: Optional[str] = None,
    aeo_question: Optional[str] = None,
    slide_count: Optional[int] = None,
    alternate_hook: bool = False,
) -> CarouselDeck:
    """
    Generates a structured, persona-calibrated Instagram CarouselDeck using the free-tier LLM.
    Raises LLMNotConfiguredError if no free-tier LLM key is configured.
    """
    brand_inst = brand or settings
    target_slides = slide_count or int(brand_inst.carousel_specs.get("default_slide_count", 6))
    target_slides = max(4, min(8, target_slides))

    prompt_parts = [
        f"Topic: {topic}",
        f"Content Pillar: {pillar_id or 'Core Authority'}",
        f"Slide Count: Exactly {target_slides} slides",
    ]
    if primary_search_keyword:
        prompt_parts.append(f"Primary Search Keyword: {primary_search_keyword}")
    if aeo_question:
        prompt_parts.append(f"AEO Question to Answer: {aeo_question}")
    if hook_override:
        prompt_parts.append(f"Selected Opening Hook Direction: {hook_override}")
    if angle_summary:
        prompt_parts.append(f"Creative Angle Summary: {angle_summary}")
    if alternate_hook:
        prompt_parts.append(
            "IMPORTANT: The creator requested an ALTERNATE HOOK. Write a completely fresh, bolder, "
            "more intriguing Slide 1 headline and caption opener than before, approaching the topic from a sharper contrarian or curiosity angle."
        )

    prompt = "\n".join(prompt_parts)
    system_instruction = _build_system_prompt(brand_inst, target_slides)

    logger.info(f"Generating {target_slides}-slide customized carousel for '{topic}'...")
    deck = call_structured_llm(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=CarouselDeck,
        temperature=0.85 if alternate_hook else 0.72,
    )

    # Normalize slide numbers sequentially
    for idx, slide in enumerate(deck.slides, 1):
        slide.slide_number = idx

    return deck
