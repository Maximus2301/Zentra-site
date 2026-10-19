"""State models and schemas for the Instagram ADK 2.0 Agent System."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class AudienceCohort(BaseModel):
    segment_id: str
    name: str
    core_fears: list[str] = Field(default_factory=list)
    tone_resonance: str = ""
    key_triggers: list[str] = Field(default_factory=list)


class VisualIdentity(BaseModel):
    theme: str = "investigative_legal"
    theme_label: str = "Investigative Legal High-Contrast"
    channel_icon: str = "⚖️"
    iconography_style: str = "line"  # line, glassmorphism, tech_terminal, editorial_serif, vibrant_emoji
    primary_color: str = "#E63946"
    accent_color: str = "#38BDF8"
    bg_color: str = "#0B0F19"
    text_color: str = "#F8FAFC"
    color_palette: list[str] = Field(
        default_factory=lambda: ["#0B0F19", "#E63946", "#38BDF8", "#F1FAEE", "#334155"]
    )
    headline_font: str = "Plus Jakarta Sans"
    body_font: str = "Inter"
    font_weight: str = "bold"
    letter_spacing: str = "tracked"


class AccountContext(BaseModel):
    account_id: str
    handle: str
    name: str
    category: str = "General"
    mission: str = ""
    tone_rules: list[str] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)
    mandatory_disclaimers: list[str] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=lambda: ["#1A1A24", "#FFFFFF"])
    instagram_business_id: str = ""
    access_token_env: str = ""
    audience_cohorts: list[AudienceCohort] = Field(default_factory=list)
    linked_accounts: dict[str, Any] = Field(default_factory=dict)
    visual_identity: VisualIdentity | None = None


class CoreNarrative(BaseModel):
    selected_cohort_id: str = ""
    cohort_name: str = ""
    target_emotion: str = ""
    hook: str = ""
    core_insight: str = ""
    actionable_takeaways: list[str] = Field(default_factory=list)
    call_to_action: str = ""
    emotional_arc: str = ""


class StaticPostDraft(BaseModel):
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    visual_prompt: str = ""
    aspect_ratio: str = "4:5"
    overlay_title: str = ""
    key_bullet_points: list[str] = Field(default_factory=list)


class StorySlide(BaseModel):
    slide_index: int
    headline: str = ""
    subtext: str = ""
    sticker_type: str | None = None  # e.g., "Poll", "Quiz", "Question Box", "Link"
    sticker_prompt: str | None = None
    background_mood: str = ""


class StoryDraft(BaseModel):
    slides: list[StorySlide] = Field(default_factory=list)


class ReelScene(BaseModel):
    timestamp_start_sec: float
    timestamp_end_sec: float
    visual_broll_prompt: str
    spoken_voiceover: str
    on_screen_text: str


class ReelDraft(BaseModel):
    duration_seconds: int = 30
    hook_0_to_3s: str = ""
    scenes: list[ReelScene] = Field(default_factory=list)
    music_mood: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    video_routing: Literal["in_dashboard_mp4", "google_vids_workspace"] = "in_dashboard_mp4"
    video_file: str | None = None
    video_url: str | None = None
    google_vids_prompt: str = ""
    google_vids_blueprint: dict[str, Any] = Field(default_factory=dict)
    google_vids_markdown: str = ""


class StatusDraft(BaseModel):
    micro_copy: str = ""
    card_theme: str = "bold_quote"
    accent_color: str = "#E63946"


class CriticReview(BaseModel):
    score: float = 0.0
    eq_score: float = 0.0
    passed: bool = False
    feedback: str = ""
    checklist_results: dict[str, bool] = Field(default_factory=dict)
    suggested_revisions: list[str] = Field(default_factory=list)


class InstagramCampaignState(BaseModel):
    # Stage 0: Account Context (Locked)
    account: AccountContext | None = None
    account_id: str = ""

    # User Inputs & Intent
    raw_user_script: str | None = None
    requested_topic: str | None = None
    requested_emotion: str | None = None
    requested_duration_seconds: int = 30
    active_formats: list[str] = Field(
        default_factory=lambda: ["static_post", "story", "reel", "status"]
    )
    visual_identity: VisualIdentity | None = None

    # Stage 1: Strategy & Evolved Narrative
    narrative: CoreNarrative | None = None

    # Stage 2: Format Deliverables
    static_post: StaticPostDraft | None = None
    story_sequence: list[StorySlide] | None = None
    reel: ReelDraft | None = None
    status_card: StatusDraft | None = None

    # Stage 3: Media Asset References (local file paths or URLs)
    media_assets: dict[str, str] = Field(default_factory=dict)
    video_specs: dict[str, Any] = Field(default_factory=dict)

    # Stage 4: Aggregated Draft Bundle
    campaign_bundle: dict[str, Any] = Field(default_factory=dict)

    # Stage 5: Quality, EQ & Safety Critique
    critic: CriticReview | None = None
    revision_count: int = 0
    max_revisions: int = 2
    status: Literal[
        "initialized",
        "account_locked",
        "drafting",
        "narrative_evolved",
        "critique_pending",
        "revision_needed",
        "approved",
        "rejected",
        "published",
        "discarded",
    ] = "drafting"

    # Stage 6: Publish Results
    published_media_ids: dict[str, str] = Field(default_factory=dict)
    preview_html_path: str = ""
