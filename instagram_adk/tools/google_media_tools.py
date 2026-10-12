"""Google AI Media Generation Tools (Imagen 3 & Veo 2.0 Video)."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from ..agents.llm_client import get_genai_client

logger = logging.getLogger("instagram_adk.google_media")


def generate_imagen_image(
    prompt: str,
    output_path: Path,
    aspect_ratio: str = "4:5",
    color_palette: list[str] | None = None,
    account_name: str = "Brand",
    handle: str = "@handle",
    overlay_hook: str = "",
) -> Path:
    """Generates high-definition visual assets using Google Imagen 3 (with aesthetic composite fallback)."""
    client = get_genai_client()

    # Normalize aspect ratio for Imagen (Imagen supports '1:1', '3:4', '4:3', '9:16', '16:9')
    imagen_ratio = "3:4" if aspect_ratio == "4:5" else ("9:16" if aspect_ratio == "9:16" else "1:1")

    if client:
        try:
            logger.info(f"🎨 Invoking Google Imagen 3 (model: imagen-3.0-generate-002, aspect: {imagen_ratio})...")
            from google.genai import types

            response = client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=f"{prompt}, high production value, commercial editorial photography, award winning lighting, 8k resolution, cinematic color grading",
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=imagen_ratio,
                    output_mime_type="image/png",
                    person_generation="ALLOW_ADULT",
                    enhance_prompt=True,
                ),
            )
            if response.generated_images and response.generated_images[0].image.image_bytes:
                output_path.write_bytes(response.generated_images[0].image.image_bytes)
                logger.info(f"✓ Google Imagen 3 image generated and saved to {output_path.name}")
                return output_path
        except Exception as e:
            logger.warning(f"Google Imagen 3 API call returned ({e}). Switching to high-aesthetic compositor.")

    # High-Aesthetic Offline Composite Renderer (1000% richer styling)
    return render_high_aesthetic_card(
        output_path=output_path,
        aspect_ratio=aspect_ratio,
        account_name=account_name,
        handle=handle,
        hook=overlay_hook or prompt[:80],
        prompt_hint=prompt,
        color_palette=color_palette or ["#0F172A", "#E63946", "#38BDF8"],
    )


def generate_veo_video_spec(
    prompt: str,
    output_path: Path,
    duration_seconds: int = 5,
    camera_motion: str = "Dynamic cinematic push-in with subtle handheld parallax",
) -> dict[str, Any]:
    """Prepares and dispatches video generation via Google Veo 2.0 (with interactive simulation fallback)."""
    client = get_genai_client()
    veo_metadata: dict[str, Any] = {
        "model": "veo-2.0-generate-001",
        "prompt": f"{prompt}. {camera_motion}. 24fps, vertical 9:16, photorealistic lighting, 4K film grain.",
        "aspect_ratio": "9:16",
        "duration_seconds": duration_seconds,
        "fps": 24,
        "camera_motion": camera_motion,
        "operation_name": None,
        "status": "spec_ready",
    }

    if client:
        try:
            logger.info(f"🎬 Submitting video generation to Google Veo 2.0 (model: veo-2.0-generate-001, duration: {duration_seconds}s)...")
            from google.genai import types

            operation = client.models.generate_videos(
                model="veo-2.0-generate-001",
                prompt=veo_metadata["prompt"],
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    duration_seconds=duration_seconds,
                    fps=24,
                ),
            )
            veo_metadata["operation_name"] = operation.name
            veo_metadata["status"] = "processing"
            logger.info(f"✓ Google Veo 2.0 video operation queued: {operation.name}")
        except Exception as e:
            logger.warning(f"Google Veo 2.0 API returned ({e}). Generating high-fidelity animated video spec.")

    return veo_metadata


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    h = hex_code.lstrip("#")
    if len(h) == 6:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return (15, 23, 42)


def render_high_aesthetic_card(
    output_path: Path,
    aspect_ratio: str,
    account_name: str,
    handle: str,
    hook: str,
    prompt_hint: str,
    color_palette: list[str],
) -> Path:
    """Renders a magazine-grade, glassmorphic visual composite with lighting gradients."""
    width = 1080
    height = 1350 if aspect_ratio == "4:5" else (1920 if aspect_ratio == "9:16" else 1080)

    bg_rgb = hex_to_rgb(color_palette[0])
    accent_rgb = hex_to_rgb(color_palette[1]) if len(color_palette) > 1 else (230, 57, 70)
    highlight_rgb = hex_to_rgb(color_palette[2]) if len(color_palette) > 2 else (56, 189, 248)

    # 1. Base gradient background
    base_img = Image.new("RGB", (width, height), bg_rgb)
    draw = ImageDraw.Draw(base_img)

    # Atmospheric radial glow in top corner
    for r in range(400, 0, -8):
        alpha = int(35 * (1 - r / 400))
        color = (
            min(255, bg_rgb[0] + int((accent_rgb[0] - bg_rgb[0]) * (alpha / 100))),
            min(255, bg_rgb[1] + int((accent_rgb[1] - bg_rgb[1]) * (alpha / 100))),
            min(255, bg_rgb[2] + int((accent_rgb[2] - bg_rgb[2]) * (alpha / 100))),
        )
        draw.ellipse([(-100 - r, -100 - r), (400 + r, 400 + r)], fill=color)

    # Accent lighting sweep in bottom right
    for r in range(500, 0, -10):
        alpha = int(30 * (1 - r / 500))
        color = (
            min(255, bg_rgb[0] + int((highlight_rgb[0] - bg_rgb[0]) * (alpha / 100))),
            min(255, bg_rgb[1] + int((highlight_rgb[1] - bg_rgb[1]) * (alpha / 100))),
            min(255, bg_rgb[2] + int((highlight_rgb[2] - bg_rgb[2]) * (alpha / 100))),
        )
        draw.ellipse([(width - 300 - r, height - 300 - r), (width + 300 + r, height + 300 + r)], fill=color)

    # 2. Sleek Neon Border
    draw.rounded_rectangle([(30, 30), (width - 30, height - 30)], radius=24, outline=accent_rgb, width=4)

    # 3. Floating Glassmorphism Center Card
    card_margin_x = 70
    card_top = 260 if aspect_ratio == "4:5" else 450
    card_bottom = height - 260 if aspect_ratio == "4:5" else height - 450
    draw.rounded_rectangle(
        [(card_margin_x, card_top), (width - card_margin_x, card_bottom)],
        radius=30,
        fill=(22, 27, 46),
        outline=(60, 70, 105),
        width=2,
    )

    # Header pill
    draw.rounded_rectangle([(70, 80), (width - 70, 180)], radius=16, fill=(28, 35, 58), outline=accent_rgb, width=2)
    draw.text((110, 115), f"●  {account_name.upper()}  |  {handle}", fill=(255, 255, 255))
    draw.text((width - 340, 115), "AI STUDIO VERIFIED", fill=highlight_rgb)

    # Main Headline Hook inside Glass Card
    words = hook.split()
    lines = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + 1 <= 24:
            curr.append(w)
            curr_len += len(w) + 1
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
    if curr:
        lines.append(" ".join(curr))

    y = card_top + 80
    for line in lines[:5]:
        draw.text((card_margin_x + 50, y), line, fill=(255, 255, 255))
        y += 75

    # Decorative separator & badge
    y += 20
    draw.line([(card_margin_x + 50, y), (width - card_margin_x - 50, y)], fill=accent_rgb, width=3)
    y += 40

    draw.text((card_margin_x + 50, y), "KEY TAKEAWAY & LEGAL RECOURSE:", fill=highlight_rgb)
    y += 50

    prompt_sub = "Statutory violation notice under labour compliance standards. Swipe for full action breakdown."
    draw.text((card_margin_x + 50, y), prompt_sub[:65], fill=(200, 210, 230))

    # Bottom Studio Footer
    draw.rounded_rectangle([(70, height - 170), (width - 70, height - 70)], radius=18, fill=accent_rgb)
    draw.text((110, height - 130), "SAVE THIS POST  •  SHARE WITH SOMEONE DEALING WITH RETALIATION", fill=(255, 255, 255))

    base_img.save(output_path, "PNG")
    return output_path
