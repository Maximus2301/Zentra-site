"""
Shared Pillow Rendering Utilities for Personal Brand Visual Generators.
Provides font fallback resolution, circular avatar cropping, pixel-accurate text wrapping,
and color/gradient helpers across Carousels, Status Cards, Static Posts, and Reels.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from ..config.settings import BrandSettings, PROJECT_ROOT


DEFAULT_BOLD_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
DEFAULT_REG_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
DEFAULT_MONO_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


def sanitize_pil_text(text: str) -> str:
    """Strips unsupported color emojis from PIL text so tofu boxes never appear."""
    if not text:
        return ""
    cleaned = text.replace("➔", "→").replace("➤", "→")
    # Remove high Unicode emoji / pictograph codepoints unsupported by standard TTFs
    cleaned = re.sub(r"[\U00010000-\U0010FFFF]", "", cleaned)
    cleaned = re.sub(r"[\u2600-\u26FF\u2700-\u2704\u2705-\u2712\u2715-\u27BF]", "", cleaned)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


def hex_to_rgb(hex_code: str, default: Tuple[int, int, int] = (15, 23, 42)) -> Tuple[int, int, int]:
    """Converts #RRGGBB or #RGB hex string to an RGB tuple."""
    h = (hex_code or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 6:
        try:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        except ValueError:
            return default
    return default


def resolve_font(preferred_path: Optional[str], size: int, role: str = "regular") -> ImageFont.ImageFont:
    """Loads TrueType font at requested size with resilient cross-distro fallbacks."""
    candidates: List[str] = []
    if preferred_path:
        candidates.append(preferred_path)
    if role == "bold":
        candidates.extend(DEFAULT_BOLD_FONTS)
    elif role == "mono":
        candidates.extend(DEFAULT_MONO_FONTS)
    else:
        candidates.extend(DEFAULT_REG_FONTS)

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue
    return ImageFont.load_default()


def load_circular_avatar(brand: BrandSettings, size: int = 68) -> Optional[Image.Image]:
    """Loads and circularly masks the creator's avatar image."""
    rel_path = brand.creator.get("avatar_path") or "assets/avatar.png"
    p = Path(rel_path)
    if p.is_absolute():
        avatar_path = p
    else:
        profile_dir_candidate = Path(brand._profile_path).resolve().parent / rel_path
        avatar_path = profile_dir_candidate if profile_dir_candidate.exists() else (PROJECT_ROOT / rel_path)
    if not avatar_path.exists():
        return None
    try:
        avatar = Image.open(avatar_path).convert("RGBA")
        avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, size, size), fill=255)
        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(avatar, (0, 0), mask=mask)
        return output
    except Exception:
        return None


def wrap_text(
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    draw: ImageDraw.ImageDraw,
) -> List[str]:
    """Wraps text across lines to fit strictly within max_width pixels, honoring newlines."""
    text = sanitize_pil_text(text)
    if not text:
        return []

    final_lines: List[str] = []
    for paragraph in text.splitlines():
        words = paragraph.split(" ")
        curr_line = ""
        for word in words:
            if not word and curr_line:
                continue
            test_line = f"{curr_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if (bbox[2] - bbox[0]) <= max_width:
                curr_line = test_line
            else:
                if curr_line:
                    final_lines.append(curr_line)
                # Guard against single ultra-long word exceeding max_width
                wb = draw.textbbox((0, 0), word, font=font)
                if (wb[2] - wb[0]) > max_width and len(word) > 4:
                    chunk = ""
                    for ch in word:
                        cb = draw.textbbox((0, 0), chunk + ch, font=font)
                        if (cb[2] - cb[0]) <= max_width:
                            chunk += ch
                        else:
                            if chunk:
                                final_lines.append(chunk)
                            chunk = ch
                    curr_line = chunk
                else:
                    curr_line = word
        if curr_line:
            final_lines.append(curr_line)
    return final_lines


def draw_author_header(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    brand: BrandSettings,
    palette: dict,
    x: int,
    y: int,
    avatar_size: int = 68,
    avatar_img: Optional[Image.Image] = None,
    name_font: Optional[ImageFont.ImageFont] = None,
    handle_font: Optional[ImageFont.ImageFont] = None,
) -> None:
    """Draws the creator's circular avatar, display name, accent verified dot, and handle."""
    name = brand.name or "Creator"
    handle = brand.handle or "@creator"
    font_paths = brand.font_paths
    f_name = name_font or resolve_font(font_paths.get("headline_bold"), 24, "bold")
    f_handle = handle_font or resolve_font(font_paths.get("body_regular"), 20, "regular")

    if avatar_img:
        if avatar_img.size != (avatar_size, avatar_size):
            resized = avatar_img.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
            img.paste(resized, (x, y), mask=resized)
        else:
            img.paste(avatar_img, (x, y), mask=avatar_img)
    else:
        draw.ellipse(
            (x, y, x + avatar_size, y + avatar_size),
            fill=palette.get("card_bg", "#121824"),
            outline=palette.get("accent", "#10B981"),
            width=2,
        )
        initial = name[:1].upper() or "C"
        draw.text(
            (x + avatar_size // 3, y + avatar_size // 4),
            initial,
            font=f_name,
            fill=palette.get("accent", "#10B981"),
        )

    text_x = x + avatar_size + 16
    draw.text((text_x, y + 6), name, font=f_name, fill=palette.get("text_primary", "#F8FAFC"))

    # Small verified accent badge next to name
    nb = draw.textbbox((text_x, y + 6), name, font=f_name)
    dot_x = nb[2] + 10
    dot_y = y + 12
    draw.ellipse((dot_x, dot_y, dot_x + 14, dot_y + 14), fill=palette.get("accent", "#10B981"))

    draw.text((text_x, y + 38), handle, font=f_handle, fill=palette.get("text_muted", "#64748B"))


def apply_subtle_radial_glow(
    img: Image.Image,
    accent_hex: str,
    bg_hex: str,
    center: Tuple[int, int] = (900, 220),
    radius: int = 520,
    intensity: float = 0.14,
) -> None:
    """Applies a smooth atmospheric glow onto an RGB image without external assets."""
    base_rgb = hex_to_rgb(bg_hex)
    acc_rgb = hex_to_rgb(accent_hex)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    steps = 28
    for i in range(steps, 0, -1):
        r = int(radius * (i / steps))
        alpha = int(255 * intensity * ((1 - i / steps) ** 1.6))
        if alpha <= 0:
            continue
        color = (acc_rgb[0], acc_rgb[1], acc_rgb[2], alpha)
        odraw.ellipse(
            (center[0] - r, center[1] - r, center[0] + r, center[1] + r),
            fill=color,
        )
    combined = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img.paste(combined)
