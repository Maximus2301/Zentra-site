"""
High-Fidelity 1080x1350 Multi-Slide Pillow Carousel Renderer for Instagram.
Renders structured CarouselDeck slides into crisp 4:5 PNG images with dynamic
overflow protection and custom brand palettes.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw

from .carousel_generator import CarouselDeck, CarouselSlide
from .render_utils import (
    apply_subtle_radial_glow,
    draw_author_header,
    load_circular_avatar,
    resolve_font,
    sanitize_pil_text,
    wrap_text,
)
from ..config.settings import BrandSettings, settings


class CarouselRenderer:
    """Renders 1080x1350 Instagram carousel slides in the creator's active theme."""

    def __init__(self, brand: Optional[BrandSettings] = None):
        self.brand = brand or settings
        self.width = 1080
        self.height = 1350
        self.palette = self.brand.active_palette

        font_paths = self.brand.font_paths
        self.font_bold_path = font_paths.get("headline_bold")
        self.font_reg_path = font_paths.get("body_regular")

        self.font_title = resolve_font(self.font_bold_path, 52, "bold")
        self.font_title_compact = resolve_font(self.font_bold_path, 42, "bold")
        self.font_subtitle = resolve_font(self.font_reg_path, 28, "regular")
        self.font_card_title = resolve_font(self.font_bold_path, 26, "bold")
        self.font_body = resolve_font(self.font_reg_path, 24, "regular")
        self.font_body_compact = resolve_font(self.font_reg_path, 21, "regular")
        self.font_header_name = resolve_font(self.font_bold_path, 24, "bold")
        self.font_header_handle = resolve_font(self.font_reg_path, 20, "regular")
        self.font_badge = resolve_font(self.font_bold_path, 18, "bold")
        self.font_footer = resolve_font(self.font_bold_path, 20, "bold")

        self.avatar_img = load_circular_avatar(self.brand, size=68)

    def _draw_segmented_progress_bar(self, draw: ImageDraw.ImageDraw, current_slide: int, total_slides: int):
        """Draws a sleek segmented progress bar at top."""
        left_m = 70
        right_m = 1010
        total_w = right_m - left_m
        gap = 10
        seg_w = (total_w - (gap * max(0, total_slides - 1))) / max(1, total_slides)
        bar_h = 5
        bar_y = 28

        for i in range(total_slides):
            x1 = left_m + i * (seg_w + gap)
            x2 = x1 + seg_w
            fill_color = (
                self.palette.get("accent", "#10B981")
                if (i + 1) <= current_slide
                else self.palette.get("card_border", "#1E293B")
            )
            draw.rounded_rectangle((x1, bar_y, x2, bar_y + bar_h), radius=3, fill=fill_color)

    def _draw_header(self, img: Image.Image, draw: ImageDraw.ImageDraw, slide: CarouselSlide):
        """Draws the top author banner and category badge."""
        header_y = 54
        left_x = 70

        draw_author_header(
            img=img,
            draw=draw,
            brand=self.brand,
            palette=self.palette,
            x=left_x,
            y=header_y,
            avatar_size=68,
            avatar_img=self.avatar_img,
            name_font=self.font_header_name,
            handle_font=self.font_header_handle,
        )

        # Right category badge pill
        badge_text = sanitize_pil_text(slide.badge).upper()[:32]
        bbox = draw.textbbox((0, 0), badge_text, font=self.font_badge)
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]

        pill_pad_x = 18
        pill_pad_y = 10
        pill_w = bw + (pill_pad_x * 2)
        pill_h = bh + (pill_pad_y * 2)
        pill_x = 1010 - pill_w
        pill_y = header_y + 14

        draw.rounded_rectangle(
            (pill_x, pill_y, pill_x + pill_w, pill_y + pill_h),
            radius=16,
            fill=self.palette.get("header_pill_bg", "#1E293B"),
            outline=self.palette.get("card_border", "#334155"),
            width=1,
        )
        draw.text(
            (pill_x + pill_pad_x, pill_y + pill_pad_y - 2),
            badge_text,
            font=self.font_badge,
            fill=self.palette.get("header_pill_text", "#38BDF8"),
        )

    def _draw_footer(self, draw: ImageDraw.ImageDraw, slide: CarouselSlide, total_slides: int):
        """Draws the bottom divider, slide counter, and swipe cue."""
        foot_y = 1230
        left_x = 70
        right_x = 1010

        draw.line((left_x, foot_y, right_x, foot_y), fill=self.palette.get("card_border", "#1E293B"), width=1)

        counter_str = f"SLIDE {slide.slide_number:02d} / {total_slides:02d}"
        draw.text((left_x, foot_y + 30), counter_str, font=self.font_footer, fill=self.palette.get("text_muted", "#64748B"))

        cue_str = sanitize_pil_text(slide.footer_cue)
        bbox = draw.textbbox((0, 0), cue_str, font=self.font_footer)
        cw = bbox[2] - bbox[0]
        draw.text((right_x - cw, foot_y + 30), cue_str, font=self.font_footer, fill=self.palette.get("accent", "#10B981"))

    def render_slide(self, slide: CarouselSlide, total_slides: int = 6) -> Image.Image:
        """Renders an individual 1080x1350 slide with overflow-safe spacing."""
        bg_color = self.palette.get("bg_color", "#0B0F17")
        img = Image.new("RGB", (self.width, self.height), color=bg_color)
        apply_subtle_radial_glow(
            img,
            accent_hex=self.palette.get("accent", "#10B981"),
            bg_hex=bg_color,
            center=(920, 180),
            radius=480,
            intensity=0.10,
        )
        draw = ImageDraw.Draw(img)

        self._draw_segmented_progress_bar(draw, slide.slide_number, total_slides)
        self._draw_header(img, draw, slide)

        content_y = 170
        content_left = 70
        content_max_w = 940
        max_content_bottom = 1195

        # Auto-select headline font size based on length
        hl_font = self.font_title if len(slide.headline) <= 58 else self.font_title_compact
        hl_step = 62 if hl_font is self.font_title else 50
        headline_lines = wrap_text(slide.headline, hl_font, content_max_w, draw)
        for line in headline_lines[:4]:
            draw.text((content_left, content_y), line, font=hl_font, fill=self.palette.get("text_primary", "#F8FAFC"))
            content_y += hl_step
        content_y += 12

        # Subheadline
        if slide.subheadline:
            sub_lines = wrap_text(slide.subheadline, self.font_subtitle, content_max_w, draw)
            for sline in sub_lines[:3]:
                draw.text((content_left, content_y), sline, font=self.font_subtitle, fill=self.palette.get("text_secondary", "#94A3B8"))
                content_y += 36
            content_y += 20

        # Estimate remaining height for highlight box
        hl_box_reserve = 140 if slide.highlight_box else 0
        body_limit_y = max_content_bottom - hl_box_reserve

        # Body Points (Auto-compact if needed to avoid clipping)
        if slide.body_points:
            body_font = self.font_body if len(slide.body_points) <= 3 else self.font_body_compact
            line_h = 31 if body_font is self.font_body else 27
            card_pad_y = 16 if body_font is self.font_body else 13
            card_gap = 14

            for idx, pt in enumerate(slide.body_points, 1):
                pt_lines = wrap_text(pt, body_font, content_max_w - 92, draw)
                card_h = max(68, (len(pt_lines) * line_h) + (card_pad_y * 2))
                if content_y + card_h > body_limit_y:
                    break

                draw.rounded_rectangle(
                    (content_left, content_y, content_left + content_max_w, content_y + card_h),
                    radius=12,
                    fill=self.palette.get("card_bg", "#121824"),
                    outline=self.palette.get("card_border", "#1E293B"),
                    width=1,
                )

                badge_str = f"{idx:02d}"
                draw.rounded_rectangle(
                    (content_left + 18, content_y + card_pad_y, content_left + 58, content_y + card_pad_y + 34),
                    radius=6,
                    fill=self.palette.get("header_pill_bg", "#1E293B"),
                )
                draw.text(
                    (content_left + 25, content_y + card_pad_y + 6),
                    badge_str,
                    font=self.font_badge,
                    fill=self.palette.get("accent", "#10B981"),
                )

                text_y = content_y + card_pad_y + 2
                for pline in pt_lines:
                    draw.text((content_left + 72, text_y), pline, font=body_font, fill=self.palette.get("text_primary", "#F8FAFC"))
                    text_y += line_h

                content_y += card_h + card_gap

        # Highlight Box
        if slide.highlight_box and content_y < max_content_bottom - 80:
            content_y += 6
            h_pad_x = 26
            h_pad_y = 20
            hl_lines = wrap_text(slide.highlight_box, self.font_card_title, content_max_w - (h_pad_x * 2) - 10, draw)
            box_h = (len(hl_lines) * 34) + (h_pad_y * 2)

            if content_y + box_h <= max_content_bottom:
                draw.rounded_rectangle(
                    (content_left, content_y, content_left + content_max_w, content_y + box_h),
                    radius=14,
                    fill=self.palette.get("highlight_box", "#0F172A"),
                    outline=self.palette.get("card_border", "#1E293B"),
                    width=1,
                )
                draw.rounded_rectangle(
                    (content_left, content_y, content_left + 8, content_y + box_h),
                    radius=4,
                    fill=self.palette.get("accent", "#10B981"),
                )
                hy = content_y + h_pad_y
                for hline in hl_lines:
                    draw.text(
                        (content_left + h_pad_x + 6, hy),
                        hline,
                        font=self.font_card_title,
                        fill=self.palette.get("accent_secondary", "#38BDF8"),
                    )
                    hy += 34

        self._draw_footer(draw, slide, total_slides)
        return img

    def render_deck(self, deck: CarouselDeck, output_dir: Path) -> List[Path]:
        """Renders all slides in a CarouselDeck and writes them to output_dir."""
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        total = len(deck.slides)

        for slide in deck.slides:
            img = self.render_slide(slide, total_slides=total)
            slide_path = output_dir / f"slide_{slide.slide_number:02d}.png"
            img.save(slide_path, "PNG", optimize=True)
            paths.append(slide_path)

        meta_path = output_dir / "deck_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(deck.model_dump_json(indent=2))

        return paths


def render_carousel_deck(deck: CarouselDeck, output_dir: Path, brand: Optional[BrandSettings] = None) -> List[Path]:
    """Helper function to render a deck directly."""
    renderer = CarouselRenderer(brand=brand)
    return renderer.render_deck(deck, output_dir)
