"""
Status / Quote / Contrarian Card Generator & Renderer for Personal Brand Engine.
Creates single-slide 1080x1350 high-engagement Instagram status posts (tweet-style
takes, bold quotes, and contrarian opinions) at $0 media cost.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Literal, Optional
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field

from ..config.settings import BrandSettings, settings
from ..core.llm_client import SEO_AEO_META_RULES, build_brand_context_block, call_structured_llm
from .render_utils import (
    apply_subtle_radial_glow,
    draw_author_header,
    load_circular_avatar,
    resolve_font,
    wrap_text,
)

logger = logging.getLogger("personal_brand.status_generator")


class StatusCard(BaseModel):
    """Structured single-slide status / quote / contrarian Instagram post."""
    topic: str
    pillar: str
    primary_search_keyword: str = Field(
        default="",
        description="2-5 word target search phrase front-loaded into the caption opener",
    )
    aeo_question: str = Field(
        default="",
        description="Explicit user question answered by this post",
    )
    aeo_direct_answer: str = Field(
        default="",
        description="Citation-ready 40-60 word direct factual answer with entity attribution",
    )
    style_variant: Literal["tweet_card", "bold_quote", "contrarian_take"] = Field(
        default="tweet_card",
        description="Visual card style suited for the message",
    )
    badge: str = Field(..., description="Short top category tag, e.g. UNPOPULAR OPINION or DAILY NOTE")
    headline_statement: str = Field(
        ...,
        description="Punchy, high-contrast core statement (15-40 words max) that stops the scroll",
    )
    supporting_punchline: Optional[str] = Field(
        None,
        description="Short 1-sentence kicker or mic-drop takeaway underneath",
    )
    alt_text: str = Field(
        default="",
        description="15-30 word descriptive ALT text for Instagram search & accessibility",
    )
    caption: str = Field(
        ...,
        description="SEO/AEO-optimized Instagram caption: <=125-char keyword hook opener, direct answer takeaway, DM share trigger, comment question",
    )
    hashtags: List[str] = Field(default_factory=list, description="3-5 hyper-relevant semantic search hashtags")


def generate_status_card(
    topic: str,
    pillar_id: Optional[str] = None,
    brand: Optional[BrandSettings] = None,
    hook_override: Optional[str] = None,
    angle_summary: Optional[str] = None,
    primary_search_keyword: Optional[str] = None,
    aeo_question: Optional[str] = None,
    alternate_hook: bool = False,
) -> StatusCard:
    """Generates a persona-calibrated, SEO/AEO/Meta-optimized Status Card."""
    b = brand or settings
    brand_context = build_brand_context_block(b)

    system_instruction = f"""You are the Lead Social Copywriter & Search Strategist for {b.name or 'the creator'} ({b.handle or '@creator'}).

{brand_context}

{SEO_AEO_META_RULES}

Create a viral single-slide Instagram Status / Quote Card tailored to this creator's exact niche, tone, and audience.
Rules:
1. `headline_statement` must be 12–38 words, readable in 3 seconds, emotionally resonant, and unmistakably in this creator's authentic voice.
2. `style_variant` should match the message: 'tweet_card' for sharp observations, 'contrarian_take' for myth-busting, 'bold_quote' for inspirational/mindset truths.
3. Front-load `primary_search_keyword` inside the first 125 chars of `caption`, include the crisp `aeo_direct_answer` takeaway, add a DM-share nudge ("Send this to someone who..."), and end with a debate/comment question + 3-5 semantic tags.
"""

    parts = [f"Topic: {topic}", f"Pillar: {pillar_id or 'Core Perspective'}"]
    if primary_search_keyword:
        parts.append(f"Primary Search Keyword: {primary_search_keyword}")
    if aeo_question:
        parts.append(f"AEO Question to Answer: {aeo_question}")
    if hook_override:
        parts.append(f"Hook Direction: {hook_override}")
    if angle_summary:
        parts.append(f"Angle Context: {angle_summary}")
    if alternate_hook:
        parts.append("ALTERNATE HOOK REQUESTED: Craft a significantly sharper, bolder, more share-worthy statement.")

    return call_structured_llm(
        prompt="\n".join(parts),
        system_instruction=system_instruction,
        response_schema=StatusCard,
        temperature=0.88 if alternate_hook else 0.78,
    )


class StatusRenderer:
    """Renders 1080x1350 status / tweet-style / bold quote PNG cards."""

    def __init__(self, brand: Optional[BrandSettings] = None):
        self.brand = brand or settings
        self.width = 1080
        self.height = 1350
        self.palette = self.brand.active_palette

        fp = self.brand.font_paths
        self.font_bold = fp.get("headline_bold")
        self.font_reg = fp.get("body_regular")

        self.f_quote_lg = resolve_font(self.font_bold, 54, "bold")
        self.f_quote_md = resolve_font(self.font_bold, 44, "bold")
        self.f_sub = resolve_font(self.font_reg, 30, "regular")
        self.f_badge = resolve_font(self.font_bold, 20, "bold")
        self.f_name = resolve_font(self.font_bold, 28, "bold")
        self.f_handle = resolve_font(self.font_reg, 22, "regular")
        self.f_footer = resolve_font(self.font_bold, 20, "bold")
        self.avatar_img = load_circular_avatar(self.brand, size=84)

    def render(self, card: StatusCard, output_dir: Path) -> Path:
        """Renders the status card to output_dir/status_01.png and saves metadata."""
        output_dir.mkdir(parents=True, exist_ok=True)
        bg_color = self.palette.get("bg_color", "#0B0F17")
        img = Image.new("RGB", (self.width, self.height), color=bg_color)
        apply_subtle_radial_glow(
            img,
            accent_hex=self.palette.get("accent", "#10B981"),
            bg_hex=bg_color,
            center=(540, 520),
            radius=640,
            intensity=0.13,
        )
        draw = ImageDraw.Draw(img)

        # Outer editorial card container
        card_x1, card_y1 = 76, 170
        card_x2, card_y2 = 1004, 1180
        draw.rounded_rectangle(
            (card_x1, card_y1, card_x2, card_y2),
            radius=28,
            fill=self.palette.get("card_bg", "#121824"),
            outline=self.palette.get("card_border", "#1E293B"),
            width=2,
        )

        # Top badge pill inside card
        badge_text = card.badge.upper()[:28]
        bb = draw.textbbox((0, 0), badge_text, font=self.f_badge)
        pw = (bb[2] - bb[0]) + 36
        ph = (bb[3] - bb[1]) + 20
        px = card_x1 + 56
        py = card_y1 + 56
        draw.rounded_rectangle(
            (px, py, px + pw, py + ph),
            radius=16,
            fill=self.palette.get("header_pill_bg", "#1E293B"),
        )
        draw.text(
            (px + 18, py + 8),
            badge_text,
            font=self.f_badge,
            fill=self.palette.get("header_pill_text", "#38BDF8"),
        )

        # Author identity block
        draw_author_header(
            img=img,
            draw=draw,
            brand=self.brand,
            palette=self.palette,
            x=card_x1 + 56,
            y=py + ph + 44,
            avatar_size=84,
            avatar_img=self.avatar_img,
            name_font=self.f_name,
            handle_font=self.f_handle,
        )

        # Accent divider bar
        div_y = py + ph + 158
        draw.rounded_rectangle(
            (card_x1 + 56, div_y, card_x1 + 160, div_y + 6),
            radius=3,
            fill=self.palette.get("accent", "#10B981"),
        )

        # Main statement
        max_text_w = (card_x2 - card_x1) - 112
        q_font = self.f_quote_lg if len(card.headline_statement) <= 120 else self.f_quote_md
        q_step = 68 if q_font is self.f_quote_lg else 56
        lines = wrap_text(card.headline_statement, q_font, max_text_w, draw)

        text_y = div_y + 42
        for line in lines[:8]:
            draw.text((card_x1 + 56, text_y), line, font=q_font, fill=self.palette.get("text_primary", "#F8FAFC"))
            text_y += q_step

        # Supporting punchline box
        if card.supporting_punchline and text_y < card_y2 - 180:
            text_y += 28
            sub_lines = wrap_text(card.supporting_punchline, self.f_sub, max_text_w - 44, draw)
            box_h = (len(sub_lines) * 40) + 36
            draw.rounded_rectangle(
                (card_x1 + 56, text_y, card_x2 - 56, text_y + box_h),
                radius=14,
                fill=self.palette.get("highlight_box", "#0F172A"),
            )
            draw.rounded_rectangle(
                (card_x1 + 56, text_y, card_x1 + 64, text_y + box_h),
                radius=4,
                fill=self.palette.get("accent", "#10B981"),
            )
            sy = text_y + 18
            for sline in sub_lines[:3]:
                draw.text(
                    (card_x1 + 84, sy),
                    sline,
                    font=self.f_sub,
                    fill=self.palette.get("accent_secondary", "#38BDF8"),
                )
                sy += 40

        # Card footer interaction cue
        foot_y = card_y2 - 72
        draw.line((card_x1 + 56, foot_y - 20, card_x2 - 56, foot_y - 20), fill=self.palette.get("card_border", "#1E293B"), width=1)
        draw.text((card_x1 + 56, foot_y), "AGREE OR DISAGREE?", font=self.f_footer, fill=self.palette.get("text_muted", "#64748B"))
        save_txt = "SAVE & SHARE →"
        sb = draw.textbbox((0, 0), save_txt, font=self.f_footer)
        draw.text((card_x2 - 56 - (sb[2] - sb[0]), foot_y), save_txt, font=self.f_footer, fill=self.palette.get("accent", "#10B981"))

        out_path = output_dir / "status_01.png"
        img.save(out_path, "PNG", optimize=True)

        meta_path = output_dir / "status_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(card.model_dump_json(indent=2))

        return out_path
