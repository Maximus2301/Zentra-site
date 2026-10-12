"""Stage 2: Format-Specific Generation Specialists (Static, Story, Reel, Status)."""
from __future__ import annotations

import logging
from typing import Any
from ..models.state import (
    AccountContext,
    CoreNarrative,
    StaticPostDraft,
    StorySlide,
    ReelDraft,
    ReelScene,
    StatusDraft,
)
from .llm_client import call_structured_gemini

logger = logging.getLogger("instagram_adk.formats")


# --- 2A: Static Post Specialist ---

def run_static_post_agent(ctx: Any) -> str:
    """Stage 2A: Creates high-converting Instagram Feed Post (Caption, 3-tier Hashtags, 4:5 Visual Prompt)."""
    state = ctx.state
    active_formats = state.get("active_formats") or ["static_post", "story", "reel", "status"]
    if "static_post" not in active_formats and "all" not in active_formats:
        logger.info("Static post not in active_formats; skipping.")
        return "skipped"

    account = AccountContext.model_validate(state.get("account"))
    narrative = CoreNarrative.model_validate(state.get("narrative"))

    system_instruction = f"""You are the Master Instagram Feed Copywriter for {account.name} ({account.handle}).
MISSION: {account.mission}
TARGET AUDIENCE: {narrative.cohort_name}
TARGET EMOTION: {narrative.target_emotion}
DISCLAIMERS: {'; '.join(account.mandatory_disclaimers)}

Write an Instagram Feed post adhering to:
- Hook in the very first sentence (must stop the scroll)
- Clean whitespace separation between short punchy paragraphs
- 3 clear bullet points
- Relatable emotional resonance matching {narrative.target_emotion}
- Mandatory disclaimer included if required
- 10-15 hashtags categorized into niche, community, and broad tags
- High-concept 4:5 visual art generation prompt reflecting the account's color palette: {account.color_palette}
"""

    prompt = f"""Evolved Core Narrative:
Hook: {narrative.hook}
Insight: {narrative.core_insight}
Takeaways: {', '.join(narrative.actionable_takeaways)}
CTA: {narrative.call_to_action}

Generate a structured StaticPostDraft."""

    def fallback_generator() -> StaticPostDraft:
        bullets_text = "\n".join([f"• {pt}" for pt in narrative.actionable_takeaways])
        disclaimer_text = f"\n\n📌 {account.mandatory_disclaimers[0]}" if account.mandatory_disclaimers else ""
        caption = (
            f"{narrative.hook}\n\n"
            f"Here is what most companies hope you never find out:\n\n"
            f"{narrative.core_insight}\n\n"
            f"Key steps you must take right now:\n"
            f"{bullets_text}\n\n"
            f"{narrative.call_to_action}"
            f"{disclaimer_text}"
        )
        tags = [
            f"#{account.account_id.replace('_', '')}",
            "#knowyourrights",
            "#corporatelife",
            "#careeradvice",
            "#workplacedignity",
            "#laborlaw",
            "#fairpay",
            "#legalawareness",
            "#techworkers",
            "#careerempowerment",
        ]
        return StaticPostDraft(
            caption=caption,
            hashtags=tags,
            visual_prompt=f"Bold editorial graphic, typography-driven poster, color palette {account.color_palette[:2]}, clean minimalist aesthetic, 4:5 portrait ratio",
            aspect_ratio="4:5",
            overlay_title=narrative.hook[:45] + "...",
            key_bullet_points=narrative.actionable_takeaways,
        )

    draft = call_structured_gemini(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=StaticPostDraft,
        fallback_factory=fallback_generator,
    )

    state["static_post"] = draft.model_dump()

    logger.info(f"✓ Static Post Generated: Caption length {len(draft.caption)} chars | Tags: {len(draft.hashtags)}")
    return "static_ready"


# --- 2B: Story Architect Specialist ---

def run_story_agent(ctx: Any) -> str:
    """Stage 2B: Designs a 4-Slide Interactive Vertical Story Arc (9:16) with Sticker Placements."""
    state = ctx.state
    active_formats = state.get("active_formats") or ["static_post", "story", "reel", "status"]
    if "story" not in active_formats and "all" not in active_formats:
        logger.info("Story not in active_formats; skipping.")
        return "skipped"

    account = AccountContext.model_validate(state.get("account"))
    narrative = CoreNarrative.model_validate(state.get("narrative"))

    def fallback_generator() -> list[StorySlide]:
        return [
            StorySlide(
                slide_index=1,
                headline="Stop scrolling if you recently resigned.",
                subtext="Has your HR delayed your FnF past 30 days?",
                sticker_type="Poll",
                sticker_prompt="Did your employer delay your settlement? [Yes, >30 days] / [On time]",
                background_mood="Urgent, dark mode alert",
            ),
            StorySlide(
                slide_index=2,
                headline="The Corporate Myth vs Legal Reality",
                subtext=narrative.core_insight,
                sticker_type="Slider",
                sticker_prompt="Rate how stressful exit processes are: 🔥",
                background_mood="Informative, stark contrast",
            ),
            StorySlide(
                slide_index=3,
                headline="3 Steps to Take Before Signing Waivers",
                subtext="\n".join([f"{i+1}. {t}" for i, t in enumerate(narrative.actionable_takeaways)]),
                sticker_type=None,
                sticker_prompt=None,
                background_mood="Empowering, clean hierarchy",
            ),
            StorySlide(
                slide_index=4,
                headline="Don't leave your hard-earned money behind.",
                subtext="Tap below or comment 'RIGHTS' to get the statutory legal notice draft.",
                sticker_type="Link / Question Box",
                sticker_prompt="Ask your exit question here anonymously 👇",
                background_mood="Action-oriented, high contrast CTA",
            ),
        ]

    slides = fallback_generator()
    state["story_sequence"] = [s.model_dump() for s in slides]

    logger.info(f"✓ Story Sequence Generated: {len(slides)} vertical slides with interactive stickers")
    return "story_ready"


# --- 2C: Reel Screenwriter Specialist ---

def run_reel_agent(ctx: Any) -> str:
    """Stage 2C: Formulates 30-45s Reel Production Screenplay (Visual B-roll, Voiceover, Music Mood)."""
    state = ctx.state
    active_formats = state.get("active_formats") or ["static_post", "story", "reel", "status"]
    if "reel" not in active_formats and "all" not in active_formats:
        logger.info("Reel not in active_formats; skipping.")
        return "skipped"

    account = AccountContext.model_validate(state.get("account"))
    narrative = CoreNarrative.model_validate(state.get("narrative"))

    def fallback_generator() -> ReelDraft:
        scenes = [
            ReelScene(
                timestamp_start_sec=0.0,
                timestamp_end_sec=3.5,
                visual_broll_prompt="Person sitting in corporate office looking at laptop with calendar notifications piling up, dark cinematic lighting",
                spoken_voiceover=narrative.hook,
                on_screen_text=narrative.hook[:35].upper() + "...",
            ),
            ReelScene(
                timestamp_start_sec=3.5,
                timestamp_end_sec=12.0,
                visual_broll_prompt="Quick cuts of email inbox with unanswered threads, followed by legal document highlighted in amber neon",
                spoken_voiceover=f"Most people think they just have to wait politely. But the law is crystal clear: {narrative.core_insight}",
                on_screen_text="WHAT THE LAW ACTUALLY SAYS ⚖️",
            ),
            ReelScene(
                timestamp_start_sec=12.0,
                timestamp_end_sec=24.0,
                visual_broll_prompt="Close up checklist appearing on smartphone screen with smooth tactile animations",
                spoken_voiceover=f"Here are the exact steps you need to take right now: {'; '.join(narrative.actionable_takeaways[:3])}",
                on_screen_text="3-STEP ACTION PLAN",
            ),
            ReelScene(
                timestamp_start_sec=24.0,
                timestamp_end_sec=30.0,
                visual_broll_prompt="Direct to camera confident posture, clean modern typography overlay",
                spoken_voiceover=f"{narrative.call_to_action}",
                on_screen_text="COMMENT 'RIGHTS' FOR THE TEMPLATE",
            ),
        ]
        disclaimer_text = f"\n\n📌 {account.mandatory_disclaimers[0]}" if account.mandatory_disclaimers else ""
        return ReelDraft(
            duration_seconds=30,
            hook_0_to_3s=narrative.hook,
            scenes=scenes,
            music_mood="Tense investigative synth building into confident, empowering cinematic resolution",
            caption=f"{narrative.hook}\n\nTag someone who needs to see this! Full guide in caption.{disclaimer_text}\n\n#reels #workplacerights #fairpay",
            hashtags=["#reelsviral", "#corporateawareness", "#fairwages"],
        )

    reel_draft = fallback_generator()
    state["reel"] = reel_draft.model_dump()

    logger.info(f"✓ Reel Screenplay Generated: {reel_draft.duration_seconds}s across {len(reel_draft.scenes)} scenes")
    return "reel_ready"


# --- 2D: Status Specialist ---

def run_status_agent(ctx: Any) -> str:
    """Stage 2D: Formats punchy micro-takeaway card for WhatsApp/IG/FB Status."""
    state = ctx.state
    active_formats = state.get("active_formats") or ["static_post", "story", "reel", "status"]
    if "status" not in active_formats and "all" not in active_formats:
        logger.info("Status not in active_formats; skipping.")
        return "skipped"

    narrative = CoreNarrative.model_validate(state.get("narrative"))
    account = AccountContext.model_validate(state.get("account"))

    status_draft = StatusDraft(
        micro_copy=f"\"{narrative.hook}\"\n\n— {account.name}",
        card_theme="bold_quote",
        accent_color=account.color_palette[1] if len(account.color_palette) > 1 else "#E63946",
    )

    state["status_card"] = status_draft.model_dump()

    logger.info("✓ Status Card Copy Generated")
    return "status_ready"
