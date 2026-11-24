"""
Static Single-Image Post Generator & Renderer for Personal Brand Engine.
Supports both:
1. Photo + Branded Typography Overlay (using user-uploaded photos or optional free stock photos)
2. Designer-Grade $0 Graphic Editorial Layouts (infographic checklist, myth vs fact, stat spotlight)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Literal, Optional
from PIL import Image, ImageDraw, ImageOps
from pydantic import BaseModel, Field

from ..config.settings import BrandSettings, settings
from ..core.llm_client import SEO_AEO_META_RULES, build_brand_context_block, call_structured_llm
from .render_utils import (
    apply_subtle_radial_glow,
    draw_author_header,
    hex_to_rgb,
    load_circular_avatar,
    resolve_font,
    wrap_text,
)

logger = logging.getLogger("personal_brand.static_post_generator")


class StaticPost(BaseModel):
    """Structured single-image Instagram feed post (4:5 portrait)."""
    topic: str
    pillar: str
    primary_search_keyword: str = Field(
        default="",
        description="2-5 word target search phrase front-loaded into the caption opener",
    )
    aeo_question: str = Field(
        default="",
        description="Explicit user question answered by this graphic",
    )
    aeo_direct_answer: str = Field(
        default="",
        description="Citation-ready 40-60 word direct factual answer with entity attribution",
    )
    layout_type: Literal["infographic_checklist", "myth_vs_fact", "stat_spotlight", "photo_overlay"] = Field(
        default="infographic_checklist",
        description="Visual layout type best suited to the content",
    )
    eyebrow_badge: str = Field(..., description="Short uppercase tag, e.g. 01 / QUICK CHEATSHEET")
    headline: str = Field(..., description="Bold scroll-stopping headline (<10 words)")
    subheadline: str = Field(..., description="1-sentence value hook underneath")
    hero_callout: str = Field(
        default="SAVE THIS",
        description="Short bold metric or punchy 2-4 word spotlight (e.g., '3X RETENTION' or 'STOP DOING THIS')",
    )
    key_points: List[str] = Field(
        default_factory=list,
        description="3-4 crisp bullets (for checklist/stat) OR 2-4 'Myth: ... | Fact: ...' pairs (for myth_vs_fact)",
    )
    alt_text: str = Field(
        default="",
        description="15-30 word descriptive ALT text for Instagram search & accessibility",
    )
    caption: str = Field(
        ...,
        description="SEO/AEO-optimized Instagram caption: <=125-char keyword hook, AEO answer, save/share trigger, comment CTA",
    )
    hashtags: List[str] = Field(default_factory=list, description="3-5 hyper-relevant semantic search hashtags")


def generate_static_post(
    topic: str,
    pillar_id: Optional[str] = None,
    brand: Optional[BrandSettings] = None,
    hook_override: Optional[str] = None,
    angle_summary: Optional[str] = None,
    primary_search_keyword: Optional[str] = None,
    aeo_question: Optional[str] = None,
    has_photo: bool = False,
    alternate_hook: bool = False,
) -> StaticPost:
    """Generates a single-image static Instagram post package optimized for SEO/AEO/Meta reach."""
    b = brand or settings
    brand_context = build_brand_context_block(b)

    layout_instruction = (
        "Set layout_type='photo_overlay' because the creator provided a real photo background. Keep key_points to 2 ultra-short punchy tags/bullets."
        if has_photo
        else "Pick the strongest layout_type from ['infographic_checklist', 'myth_vs_fact', 'stat_spotlight']. "
             "If using 'myth_vs_fact', format each entry in key_points as 'Myth: <old belief> | Fact: <truth>'."
    )

    system_instruction = f"""You are the Lead Visual Content & Search Strategist for {b.name or 'the creator'} ({b.handle or '@creator'}).

{brand_context}

{SEO_AEO_META_RULES}

Create a save-worthy single-image 4:5 Instagram static post tailored strictly to this creator's genre, tone, and audience.
Rules:
1. {layout_instruction}
2. Keep `headline` under 10 words and ultra-punchy.
3. Keep `key_points` concise (max 12 words each) so the single graphic stays clean and readable on mobile.
4. Front-load `primary_search_keyword` in the first 125 chars of `caption`, include the `aeo_direct_answer` block, add a Save + DM Share trigger, and end with 3-5 semantic tags.
"""

    parts = [f"Topic: {topic}", f"Pillar: {pillar_id or 'Core Authority'}"]
    if primary_search_keyword:
        parts.append(f"Primary Search Keyword: {primary_search_keyword}")
    if aeo_question:
        parts.append(f"AEO Question to Answer: {aeo_question}")
    if hook_override:
        parts.append(f"Hook Direction: {hook_override}")
    if angle_summary:
        parts.append(f"Angle Summary: {angle_summary}")
    if alternate_hook:
        parts.append("ALTERNATE HOOK REQUESTED: Rewrite the headline and hero_callout with a sharper, higher-curiosity angle.")

    post = call_structured_llm(
        prompt="\n".join(parts),
        system_instruction=system_instruction,
        response_schema=StaticPost,
        temperature=0.85 if alternate_hook else 0.74,
    )
    if has_photo:
        post.layout_type = "photo_overlay"
    return post


class StaticPostRenderer:
    """Renders 1080x1350 static Instagram posts (photo overlay or designer editorial graphics)."""

    def __init__(self, brand: Optional[BrandSettings] = None):
        self.brand = brand or settings
        self.width = 1080
        self.height = 1350
        self.palette = self.brand.active_palette

        fp = self.brand.font_paths
        self.font_bold = fp.get("headline_bold")
        self.font_reg = fp.get("body_regular")

        self.f_hero = resolve_font(self.font_bold, 66, "bold")
        self.f_title = resolve_font(self.font_bold, 52, "bold")
        self.f_title_sm = resolve_font(self.font_bold, 42, "bold")
        self.f_sub = resolve_font(self.font_reg, 27, "regular")
        self.f_body = resolve_font(self.font_reg, 24, "regular")
        self.f_body_bold = resolve_font(self.font_bold, 24, "bold")
        self.f_badge = resolve_font(self.font_bold, 18, "bold")
        self.f_footer = resolve_font(self.font_bold, 20, "bold")
        self.avatar_img = load_circular_avatar(self.brand, size=64)

    def _render_photo_overlay(self, post: StaticPost, photo_path: Path) -> Image.Image:
        """Applies cover-crop, editorial dark scrims, author pill, and bold headline over a user photo."""
        base = Image.open(photo_path).convert("RGB")
        img = ImageOps.fit(base, (self.width, self.height), method=Image.Resampling.LANCZOS)

        # Create top & bottom readability gradient scrims
        scrim = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(scrim)
        for y in range(260):
            alpha = int(175 * (1 - y / 260))
            sdraw.line((0, y, self.width, y), fill=(8, 10, 16, alpha))
        for y in range(620, self.height):
            progress = (y - 620) / (self.height - 620)
            alpha = int(230 * (progress ** 1.15))
            sdraw.line((0, y, self.width, y), fill=(8, 10, 16, alpha))

        img = Image.alpha_composite(img.convert("RGBA"), scrim).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Top author overlay pill (light text over dark scrim)
        light_palette = {
            **self.palette,
            "text_primary": "#FFFFFF",
            "text_muted": "#CBD5E1",
        }
        draw_author_header(
            img=img,
            draw=draw,
            brand=self.brand,
            palette=light_palette,
            x=64,
            y=48,
            avatar_size=64,
            avatar_img=self.avatar_img,
        )

        # Badge pill bottom-left above headline
        y_cursor = 790
        badge_txt = post.eyebrow_badge.upper()[:28]
        bb = draw.textbbox((0, 0), badge_txt, font=self.f_badge)
        pw = (bb[2] - bb[0]) + 32
        ph = (bb[3] - bb[1]) + 18
        draw.rounded_rectangle((64, y_cursor, 64 + pw, y_cursor + ph), radius=14, fill=self.palette.get("accent", "#10B981"))
        draw.text((80, y_cursor + 7), badge_txt, font=self.f_badge, fill="#0B0F17")
        y_cursor += ph + 24

        hl_font = self.f_title if len(post.headline) <= 46 else self.f_title_sm
        hl_step = 62 if hl_font is self.f_title else 50
        for line in wrap_text(post.headline, hl_font, 952, draw)[:4]:
            draw.text((64, y_cursor), line, font=hl_font, fill="#FFFFFF")
            y_cursor += hl_step
        y_cursor += 14

        for sline in wrap_text(post.subheadline, self.f_sub, 952, draw)[:2]:
            draw.text((64, y_cursor), sline, font=self.f_sub, fill="#E2E8F0")
            y_cursor += 36

        # Bottom cue
        draw.text((64, 1275), f"{self.brand.handle or '@creator'}", font=self.f_footer, fill="#94A3B8")
        save_txt = "SAVE THIS POST →"
        sb = draw.textbbox((0, 0), save_txt, font=self.f_footer)
        draw.text((1016 - (sb[2] - sb[0]), 1275), save_txt, font=self.f_footer, fill=self.palette.get("accent", "#10B981"))
        return img

    def _render_editorial_graphic(self, post: StaticPost) -> Image.Image:
        """Renders a crisp $0 designer-grade infographic/comparison/stat graphic."""
        bg_color = self.palette.get("bg_color", "#0B0F17")
        img = Image.new("RGB", (self.width, self.height), color=bg_color)
        apply_subtle_radial_glow(
            img,
            accent_hex=self.palette.get("accent", "#10B981"),
            bg_hex=bg_color,
            center=(880, 220),
            radius=560,
            intensity=0.14,
        )
        draw = ImageDraw.Draw(img)

        # Header
        draw_author_header(
            img=img,
            draw=draw,
            brand=self.brand,
            palette=self.palette,
            x=70,
            y=52,
            avatar_size=64,
            avatar_img=self.avatar_img,
        )

        # Top right badge
        badge_txt = post.eyebrow_badge.upper()[:26]
        bb = draw.textbbox((0, 0), badge_txt, font=self.f_badge)
        pw = (bb[2] - bb[0]) + 34
        ph = (bb[3] - bb[1]) + 18
        draw.rounded_rectangle(
            (1010 - pw, 64, 1010, 64 + ph),
            radius=14,
            fill=self.palette.get("header_pill_bg", "#1E293B"),
            outline=self.palette.get("card_border", "#334155"),
        )
        draw.text((1010 - pw + 17, 71), badge_txt, font=self.f_badge, fill=self.palette.get("header_pill_text", "#38BDF8"))

        y = 165
        # Optional Hero Callout Banner for stat_spotlight
        if post.layout_type == "stat_spotlight" and post.hero_callout:
            draw.rounded_rectangle(
                (70, y, 1010, y + 132),
                radius=20,
                fill=self.palette.get("highlight_box", "#0F172A"),
                outline=self.palette.get("accent", "#10B981"),
                width=2,
            )
            cb = draw.textbbox((0, 0), post.hero_callout[:22], font=self.f_hero)
            cw = cb[2] - cb[0]
            draw.text(
                (540 - cw // 2, y + 30),
                post.hero_callout[:22],
                font=self.f_hero,
                fill=self.palette.get("accent", "#10B981"),
            )
            y += 160

        # Headline + Subheadline
        hl_font = self.f_title if len(post.headline) <= 48 else self.f_title_sm
        hl_step = 62 if hl_font is self.f_title else 50
        for line in wrap_text(post.headline, hl_font, 940, draw)[:3]:
            draw.text((70, y), line, font=hl_font, fill=self.palette.get("text_primary", "#F8FAFC"))
            y += hl_step
        y += 12

        for sline in wrap_text(post.subheadline, self.f_sub, 940, draw)[:2]:
            draw.text((70, y), sline, font=self.f_sub, fill=self.palette.get("text_secondary", "#94A3B8"))
            y += 36
        y += 28

        # Body cards based on layout_type
        max_y = 1210
        if post.layout_type == "myth_vs_fact":
            for pt in post.key_points[:3]:
                if "|" in pt:
                    left_txt, right_txt = [p.strip() for p in pt.split("|", 1)]
                else:
                    left_txt, right_txt = "Myth: Old conventional advice", pt
                col_w = 455
                l_lines = wrap_text(left_txt, self.f_body, col_w - 40, draw)
                r_lines = wrap_text(right_txt, self.f_body_bold, col_w - 40, draw)
                row_h = max(110, max(len(l_lines), len(r_lines)) * 32 + 44)
                if y + row_h > max_y:
                    break

                # Left card (Myth)
                draw.rounded_rectangle(
                    (70, y, 70 + col_w, y + row_h),
                    radius=16,
                    fill=self.palette.get("card_bg", "#121824"),
                    outline=self.palette.get("card_border", "#1E293B"),
                )
                ly = y + 20
                for ll in l_lines:
                    draw.text((90, ly), ll, font=self.f_body, fill=self.palette.get("text_muted", "#64748B"))
                    ly += 32

                # Right card (Reality / Fact)
                rx = 70 + col_w + 30
                draw.rounded_rectangle(
                    (rx, y, rx + col_w, y + row_h),
                    radius=16,
                    fill=self.palette.get("highlight_box", "#0F172A"),
                    outline=self.palette.get("accent", "#10B981"),
                    width=2,
                )
                ry = y + 20
                for rl in r_lines:
                    draw.text((rx + 20, ry), rl, font=self.f_body_bold, fill=self.palette.get("text_primary", "#F8FAFC"))
                    ry += 32

                y += row_h + 18
        else:
            # Infographic checklist / cards
            for idx, pt in enumerate(post.key_points[:4], 1):
                pt_lines = wrap_text(pt, self.f_body, 830, draw)
                card_h = max(78, len(pt_lines) * 32 + 36)
                if y + card_h > max_y:
                    break
                draw.rounded_rectangle(
                    (70, y, 1010, y + card_h),
                    radius=16,
                    fill=self.palette.get("card_bg", "#121824"),
                    outline=self.palette.get("card_border", "#1E293B"),
                )
                draw.rounded_rectangle(
                    (92, y + 20, 134, y + 60),
                    radius=10,
                    fill=self.palette.get("accent", "#10B981"),
                )
                draw.text((104, y + 28), f"{idx}", font=self.f_body_bold, fill="#0B0F17")

                ty = y + 20
                for pl in pt_lines:
                    draw.text((156, ty), pl, font=self.f_body, fill=self.palette.get("text_primary", "#F8FAFC"))
                    ty += 32
                y += card_h + 16

        # Footer
        draw.line((70, 1236, 1010, 1236), fill=self.palette.get("card_border", "#1E293B"), width=1)
        draw.text((70, 1265), f"FOLLOW {self.brand.handle or '@creator'}", font=self.f_footer, fill=self.palette.get("text_muted", "#64748B"))
        cue = "BOOKMARK THIS →"
        cb = draw.textbbox((0, 0), cue, font=self.f_footer)
        draw.text((1010 - (cb[2] - cb[0]), 1265), cue, font=self.f_footer, fill=self.palette.get("accent", "#10B981"))
        return img

    def render(self, post: StaticPost, output_dir: Path, photo_path: Optional[Path] = None) -> Path:
        """Renders the static post to output_dir/static_01.png and saves metadata."""
        output_dir.mkdir(parents=True, exist_ok=True)
        if photo_path and photo_path.exists():
            img = self._render_photo_overlay(post, photo_path)
        else:
            img = self._render_editorial_graphic(post)

        out_path = output_dir / "static_01.png"
        img.save(out_path, "PNG", optimize=True)

        meta_path = output_dir / "static_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(post.model_dump_json(indent=2))

        return out_path
