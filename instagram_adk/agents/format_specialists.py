"""Stage 2: Format-Specific Generation Specialists (Static, Story, Reel, Status)."""
from __future__ import annotations

import logging
from typing import Any
from ..models.state import (
    AccountContext,
    CoreNarrative,
    StaticPostDraft,
    StoryDraft,
    StorySlide,
    ReelDraft,
    ReelScene,
    StatusDraft,
)
from .llm_client import call_structured_gemini
from .vids_exporter import export_google_vids_blueprint

logger = logging.getLogger("instagram_adk.formats")


def _get_domain_hashtags(account_id: str) -> list[str]:
    """Returns domain-calibrated hashtags based on target account ID."""
    clean_id = account_id.replace("_", "")
    if "fintech" in account_id or "save" in account_id:
        return [
            f"#{clean_id}",
            "#personalfinance",
            "#smartinvesting",
            "#emergencyfund",
            "#savingsgoals",
            "#financialliteracy",
            "#moneyhacks",
            "#wealthbuilding",
            "#genzmoney",
            "#budgetingtips",
        ]
    elif "alex" in account_id or "ceo" in account_id or "founder" in account_id:
        return [
            f"#{clean_id}",
            "#startupleadership",
            "#techfounders",
            "#founderwisdom",
            "#scalingteams",
            "#engineeringculture",
            "#highagency",
            "#zerotoone",
            "#leadershipdevelopment",
            "#techleadership",
        ]
    return [
        f"#{clean_id}",
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
            f"Here is what you need to know:\n\n"
            f"{narrative.core_insight}\n\n"
            f"Key steps to take right now:\n"
            f"{bullets_text}\n\n"
            f"{narrative.call_to_action}"
            f"{disclaimer_text}"
        )
        tags = _get_domain_hashtags(account.account_id)
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

    system_instruction = f"""You are the Senior Story Architect for {account.name} ({account.handle}).
MISSION: {account.mission}
TARGET AUDIENCE: {narrative.cohort_name}
TARGET EMOTION: {narrative.target_emotion}

Design a 4-slide interactive vertical Story Arc (9:16):
Slide 1: Curiosity pattern-interrupt hook with an interactive Poll sticker
Slide 2: Core insight and value reveal with a Slider sticker
Slide 3: 3 Actionable takeaways formatted clearly
Slide 4: Conversion CTA with a Question Box or Link sticker
"""

    prompt = f"""Evolved Core Narrative:
Hook: {narrative.hook}
Insight: {narrative.core_insight}
Takeaways: {', '.join(narrative.actionable_takeaways)}
CTA: {narrative.call_to_action}

Generate a structured StoryDraft with 4 slides."""

    def fallback_generator() -> StoryDraft:
        if "fintech" in account.account_id or "save" in account.account_id:
            s1_head = "Stop scrolling if your savings sit in your checking account."
            s1_sub = "Did you know that keeping emergency cash in checking guarantees lifestyle creep?"
            s1_prompt = "Do you automate savings on payday? [Automate first] / [Save what's left]"
            s4_head = "Automate your peace of mind."
            s4_sub = f"{narrative.call_to_action}"
            q_prompt = "What's your biggest savings barrier? Ask here 👇"
        elif "alex" in account.account_id or "ceo" in account.account_id:
            s1_head = "Most first-time founders make this fatal hiring mistake."
            s1_sub = "Hiring corporate specialists before finding PMF slows you down."
            s1_prompt = "What do you value more right now? [High Agency] / [Domain Expertise]"
            s4_head = "Build for velocity and resilience."
            s4_sub = f"{narrative.call_to_action}"
            q_prompt = "Share your biggest team scaling hurdle 👇"
        else:
            s1_head = "Stop scrolling if you recently resigned or face exit issues."
            s1_sub = "Has your employer delayed your settlement past statutory limits?"
            s1_prompt = "Did your employer delay your settlement? [Yes, >30 days] / [On time]"
            s4_head = "Don't leave your hard-earned money behind."
            s4_sub = f"{narrative.call_to_action}"
            q_prompt = "Ask your exit/rights question anonymously 👇"

        slides = [
            StorySlide(
                slide_index=1,
                headline=s1_head,
                subtext=s1_sub,
                sticker_type="Poll",
                sticker_prompt=s1_prompt,
                background_mood="Urgent, bold contrast alert",
            ),
            StorySlide(
                slide_index=2,
                headline="The Core Truth",
                subtext=narrative.core_insight,
                sticker_type="Slider",
                sticker_prompt="Rate how important this insight is: 🔥",
                background_mood="Informative, stark contrast",
            ),
            StorySlide(
                slide_index=3,
                headline="3 Key Takeaways to Act On",
                subtext="\n".join([f"{i+1}. {t}" for i, t in enumerate(narrative.actionable_takeaways)]),
                sticker_type=None,
                sticker_prompt=None,
                background_mood="Empowering, clean typographic hierarchy",
            ),
            StorySlide(
                slide_index=4,
                headline=s4_head,
                subtext=s4_sub,
                sticker_type="Question Box",
                sticker_prompt=q_prompt,
                background_mood="Action-oriented, high contrast CTA",
            ),
        ]
        return StoryDraft(slides=slides)

    story_draft = call_structured_gemini(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=StoryDraft,
        fallback_factory=fallback_generator,
    )

    state["story_sequence"] = [s.model_dump() for s in story_draft.slides]
    logger.info(f"✓ Story Sequence Generated: {len(story_draft.slides)} vertical slides with interactive stickers")
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
    requested_duration = int(state.get("requested_duration_seconds") or 30)

    # Core Routing Rule: <= 30s -> in_dashboard_mp4; > 30s -> google_vids_workspace
    video_routing = "in_dashboard_mp4" if requested_duration <= 30 else "google_vids_workspace"

    system_instruction = f"""You are the Master Reel Screenwriter and Video Director for {account.name} ({account.handle}).
MISSION: {account.mission}
TARGET AUDIENCE: {narrative.cohort_name}
TARGET EMOTION: {narrative.target_emotion}
DISCLAIMERS: {'; '.join(account.mandatory_disclaimers)}
VIDEO DURATION: {requested_duration} seconds
ROUTING MODE: {video_routing}

Write a {requested_duration}-second vertical Reel screenplay (9:16):
- 0-3s visual pattern interrupt hook
- Structured scene breakdowns with timestamps totaling {requested_duration}s, B-roll visuals, voiceover, and on-screen text
- Music mood aligned with {narrative.target_emotion}
- Reel caption with mandatory disclaimers and 3-5 hashtags
"""

    prompt = f"""Evolved Core Narrative:
Hook: {narrative.hook}
Insight: {narrative.core_insight}
Takeaways: {', '.join(narrative.actionable_takeaways)}
CTA: {narrative.call_to_action}
Target Duration: {requested_duration}s

Generate a structured ReelDraft."""

    def fallback_generator() -> ReelDraft:
        if "fintech" in account.account_id or "save" in account.account_id:
            broll_1 = "Close-up of smartphone notification popping up: salary credited, followed by instant auto-transfer"
            on_screen_2 = "THE AUTOMATION SECRET 📈"
            music = "Uplifting modern lo-fi ambient beat with calm reassurance"
            cta_screen = "COMMENT 'SAVE' FOR TEMPLATE"
            tags = ["#reelsviral", "#personalfinance", "#moneymindset"]
        elif "alex" in account.account_id or "ceo" in account.account_id:
            broll_1 = "Founder standing in modern open-plan startup office sketching system architecture on glass board"
            on_screen_2 = "THE HARD TRUTH 💡"
            music = "Modern electronic deep tech groove with confident cadence"
            cta_screen = "SHARE YOUR BIGGEST LESSON"
            tags = ["#reelsviral", "#techfounders", "#startups"]
        else:
            broll_1 = "Person sitting in corporate office looking at laptop with calendar notifications piling up, dark cinematic lighting"
            on_screen_2 = "WHAT THE LAW ACTUALLY SAYS ⚖️"
            music = "Tense investigative synth building into confident, empowering cinematic resolution"
            cta_screen = "COMMENT 'RIGHTS' FOR TEMPLATE"
            tags = ["#reelsviral", "#workplacerights", "#fairpay"]

        if requested_duration <= 15:
            scenes = [
                ReelScene(
                    timestamp_start_sec=0.0,
                    timestamp_end_sec=3.0,
                    visual_broll_prompt=broll_1,
                    spoken_voiceover=narrative.hook,
                    on_screen_text=narrative.hook[:35].upper() + "...",
                ),
                ReelScene(
                    timestamp_start_sec=3.0,
                    timestamp_end_sec=10.0,
                    visual_broll_prompt="High impact metric demonstration highlighting instant transformation",
                    spoken_voiceover=f"{narrative.core_insight}",
                    on_screen_text=on_screen_2,
                ),
                ReelScene(
                    timestamp_start_sec=10.0,
                    timestamp_end_sec=float(requested_duration),
                    visual_broll_prompt="Direct-to-camera confident presentation with branded typography watermark",
                    spoken_voiceover=narrative.call_to_action,
                    on_screen_text=cta_screen,
                ),
            ]
        elif requested_duration <= 30:
            scenes = [
                ReelScene(
                    timestamp_start_sec=0.0,
                    timestamp_end_sec=3.5,
                    visual_broll_prompt=broll_1,
                    spoken_voiceover=narrative.hook,
                    on_screen_text=narrative.hook[:35].upper() + "...",
                ),
                ReelScene(
                    timestamp_start_sec=3.5,
                    timestamp_end_sec=12.0,
                    visual_broll_prompt="Fast-paced visual demonstration illustrating the core solution and counter-intuitive truth",
                    spoken_voiceover=f"Here is what most people miss: {narrative.core_insight}",
                    on_screen_text=on_screen_2,
                ),
                ReelScene(
                    timestamp_start_sec=12.0,
                    timestamp_end_sec=24.0,
                    visual_broll_prompt="Clean 3-item checklist animating seamlessly across mobile screen",
                    spoken_voiceover=f"Here are the exact 3 steps to take: {'; '.join(narrative.actionable_takeaways[:3])}",
                    on_screen_text="3-STEP ACTION PLAN",
                ),
                ReelScene(
                    timestamp_start_sec=24.0,
                    timestamp_end_sec=float(requested_duration),
                    visual_broll_prompt="Direct-to-camera confident presentation with branded typography watermark",
                    spoken_voiceover=narrative.call_to_action,
                    on_screen_text=cta_screen,
                ),
            ]
        else:
            # Extended format (> 30s) for Google Vids Workspace
            step_dur = (requested_duration - 8.0) / 3.0
            t1 = 4.0
            t2 = t1 + step_dur
            t3 = t2 + step_dur
            t4 = t3 + step_dur
            scenes = [
                ReelScene(
                    timestamp_start_sec=0.0,
                    timestamp_end_sec=t1,
                    visual_broll_prompt=broll_1,
                    spoken_voiceover=narrative.hook,
                    on_screen_text=narrative.hook[:40].upper(),
                ),
                ReelScene(
                    timestamp_start_sec=t1,
                    timestamp_end_sec=t2,
                    visual_broll_prompt="Deep dive case study with animated timeline and industry metrics",
                    spoken_voiceover=f"The structural problem in traditional approaches is this: {narrative.core_insight}",
                    on_screen_text="THE REAL PROBLEM ⚠️",
                ),
                ReelScene(
                    timestamp_start_sec=t2,
                    timestamp_end_sec=t3,
                    visual_broll_prompt="System architectural diagram animating node-by-node with glowing flow lines",
                    spoken_voiceover=f"Here is the counter-intuitive framework: {narrative.actionable_takeaways[0] if narrative.actionable_takeaways else narrative.core_insight}",
                    on_screen_text=on_screen_2,
                ),
                ReelScene(
                    timestamp_start_sec=t3,
                    timestamp_end_sec=t4,
                    visual_broll_prompt="Action blueprint with clear tactical steps appearing sequentially",
                    spoken_voiceover=f"Implement these exact principles immediately: {'; '.join(narrative.actionable_takeaways[1:3])}",
                    on_screen_text="EXECUTION BLUEPRINT 🚀",
                ),
                ReelScene(
                    timestamp_start_sec=t4,
                    timestamp_end_sec=float(requested_duration),
                    visual_broll_prompt="Direct executive outro with channel branding and community invitation",
                    spoken_voiceover=f"{narrative.call_to_action}",
                    on_screen_text=cta_screen,
                ),
            ]

        disclaimer_text = f"\n\n📌 {account.mandatory_disclaimers[0]}" if account.mandatory_disclaimers else ""
        return ReelDraft(
            duration_seconds=requested_duration,
            hook_0_to_3s=narrative.hook,
            scenes=scenes,
            music_mood=music,
            caption=f"{narrative.hook}\n\nTag someone who needs this insight! Full guide in caption.{disclaimer_text}\n\n{' '.join(tags)}",
            hashtags=tags,
            video_routing=video_routing,
        )

    reel_draft = call_structured_gemini(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=ReelDraft,
        fallback_factory=fallback_generator,
    )

    reel_draft.duration_seconds = requested_duration
    reel_draft.video_routing = video_routing

    # Generate Google Vids Blueprint & Prompt regardless of route (for manual export flexibility)
    vids_blueprint = export_google_vids_blueprint(reel_draft, account, narrative)
    reel_draft.google_vids_blueprint = vids_blueprint
    reel_draft.google_vids_prompt = vids_blueprint.get("google_vids_prompt", "")
    reel_draft.google_vids_markdown = vids_blueprint.get("markdown_storyboard", "")

    state["reel"] = reel_draft.model_dump()
    logger.info(
        f"✓ Reel Screenplay Generated: {reel_draft.duration_seconds}s across {len(reel_draft.scenes)} scenes | Routing: {video_routing}"
    )
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

    system_instruction = f"""You are the Micro-Content Specialist for {account.name} ({account.handle}).
Format a single punchy 1-2 sentence high-impact takeaway quote for WhatsApp/IG Status."""

    prompt = f"""Core Narrative Hook: {narrative.hook}
Insight: {narrative.core_insight}
Account: {account.name}"""

    def fallback_generator() -> StatusDraft:
        return StatusDraft(
            micro_copy=f"\"{narrative.hook}\"\n\n— {account.name}",
            card_theme="bold_quote",
            accent_color=account.color_palette[1] if len(account.color_palette) > 1 else "#E63946",
        )

    status_draft = call_structured_gemini(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=StatusDraft,
        fallback_factory=fallback_generator,
    )

    state["status_card"] = status_draft.model_dump()
    logger.info("✓ Status Card Copy Generated")
    return "status_ready"
