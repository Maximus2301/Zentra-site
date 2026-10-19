"""Google AI Media Generation Tools (Imagen 3 & Veo 2.0 Video)."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from ..agents.llm_client import get_genai_client

logger = logging.getLogger("instagram_adk.google_media")


def _generate_with_gemini_image_model(client: Any, prompt: str, aspect_ratio: str, output_path: Path) -> bool:
    """Generates high-definition photorealistic AI images via Google Gemini Flash Image models."""
    import base64
    from google.genai import types

    target_ratio = "3:4" if aspect_ratio == "4:5" else ("9:16" if aspect_ratio == "9:16" else "1:1")
    ratio_desc = (
        "4:5 vertical portrait for Instagram feed"
        if aspect_ratio == "4:5"
        else ("9:16 vertical full-screen mobile story" if aspect_ratio == "9:16" else "1:1 square")
    )
    full_prompt = (
        f"Generate a photorealistic, award-winning commercial editorial photograph: {prompt}. "
        f"Aspect ratio: {ratio_desc}. High production value, 8k resolution, cinematic lighting, sharp focus, clean composition."
    )
    models_to_try = [
        "gemini-2.5-flash-image",
        "gemini-3.1-flash-image",
        "gemini-2.0-flash-exp-image-generation",
        "gemini-3-pro-image",
    ]

    for model_name in models_to_try:
        # Attempt 1: With response_modalities and image_config
        configs_to_try = []
        try:
            configs_to_try.append(
                types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=target_ratio,
                        output_mime_type="image/png",
                    ),
                )
            )
        except Exception:
            pass

        try:
            configs_to_try.append(
                types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
            )
        except Exception:
            pass

        configs_to_try.append(None)

        for cfg in configs_to_try:
            try:
                logger.info(f"🎨 Invoking Google GenAI Image Model ({model_name}, aspect: {target_ratio})...")
                kwargs = {"model": model_name, "contents": [full_prompt]}
                if cfg is not None:
                    kwargs["config"] = cfg

                response = client.models.generate_content(**kwargs)

                # Inspect parts for inline image bytes
                parts = getattr(response, "parts", None)
                if not parts and getattr(response, "candidates", None) and response.candidates and response.candidates[0].content:
                    parts = response.candidates[0].content.parts

                if parts:
                    for part in parts:
                        inline_data = getattr(part, "inline_data", None)
                        if inline_data and getattr(inline_data, "data", None):
                            raw_bytes = inline_data.data
                            if isinstance(raw_bytes, str):
                                raw_bytes = base64.b64decode(raw_bytes)
                            output_path.write_bytes(raw_bytes)
                            logger.info(
                                f"✓ AI image successfully generated via {model_name} and saved to {output_path.name} ({len(raw_bytes)} bytes)"
                            )
                            return True
            except Exception as e:
                logger.warning(f"Image model {model_name} (cfg={type(cfg)}) returned: {e}")
                continue

    return False


def generate_imagen_image(
    prompt: str,
    output_path: Path,
    aspect_ratio: str = "4:5",
    color_palette: list[str] | None = None,
    account_name: str = "Brand",
    handle: str = "@handle",
    overlay_hook: str = "",
    visual_identity: dict[str, Any] | None = None,
) -> Path:
    """Generates high-definition visual assets using Google GenAI Image models (with aesthetic composite fallback)."""
    client = get_genai_client()

    if client:
        # 1. Primary: Native Google GenAI Image Model (gemini-2.5-flash-image / gemini-3.1-flash-image)
        if _generate_with_gemini_image_model(client, prompt, aspect_ratio, output_path):
            return output_path

        # 2. Secondary: Google Imagen 3 generate_images API
        try:
            imagen_ratio = "3:4" if aspect_ratio == "4:5" else ("9:16" if aspect_ratio == "9:16" else "1:1")
            logger.info(f"🎨 Invoking Google Imagen 3 (model: imagen-3.0-generate-002, aspect: {imagen_ratio})...")
            from google.genai import types

            response = client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=f"{prompt}, commercial editorial photography, award winning lighting, 8k resolution",
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

    # 3. High-Aesthetic Offline Composite Renderer fallback
    return render_high_aesthetic_card(
        output_path=output_path,
        aspect_ratio=aspect_ratio,
        account_name=account_name,
        handle=handle,
        hook=overlay_hook or prompt[:80],
        prompt_hint=prompt,
        color_palette=color_palette or ["#0F172A", "#E63946", "#38BDF8"],
        visual_identity=visual_identity,
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
    visual_identity: dict[str, Any] | None = None,
) -> Path:
    """Renders a magazine-grade, glassmorphic visual composite with lighting gradients."""
    width = 1080
    height = 1350 if aspect_ratio == "4:5" else (1920 if aspect_ratio == "9:16" else 1080)

    vi = visual_identity or {}
    bg_hex = vi.get("bg_color") or (color_palette[0] if color_palette else "#0B0F19")
    accent_hex = vi.get("primary_color") or (color_palette[1] if len(color_palette) > 1 else "#E63946")
    highlight_hex = vi.get("accent_color") or (color_palette[2] if len(color_palette) > 2 else "#38BDF8")
    channel_icon = vi.get("channel_icon") or "●"
    theme_label = vi.get("theme_label") or "AI Studio Verified"

    bg_rgb = hex_to_rgb(bg_hex)
    accent_rgb = hex_to_rgb(accent_hex)
    highlight_rgb = hex_to_rgb(highlight_hex)

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
    draw.text((110, 115), f"{channel_icon}  {account_name.upper()}  |  {handle}", fill=(255, 255, 255))
    draw.text((width - 360, 115), f"THEME: {theme_label[:18].upper()}", fill=highlight_rgb)

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

    h_lower = handle.lower()
    if "fintech" in h_lower or "save" in h_lower:
        badge_header = "SMART WEALTH TAKEAWAY:"
        sub_desc = "Automate your safety net and compound growth. Swipe for action steps."
        cta_footer = "SAVE THIS POST  •  SHARE WITH SOMEONE BUILDING WEALTH"
    elif "alex" in h_lower or "ceo" in h_lower:
        badge_header = "FOUNDER STRATEGY INSIGHT:"
        sub_desc = "Optimize for velocity and high-agency execution. Swipe for framework."
        cta_footer = "SAVE THIS POST  •  SHARE WITH FELLOW BUILDERS & LEADERS"
    else:
        badge_header = "KEY RIGHTS TAKEAWAY & ACTION:"
        sub_desc = "Statutory compliance guidelines and remedies. Swipe for action checklist."
        cta_footer = "SAVE THIS POST  •  SHARE WITH SOMEONE WHO NEEDS THIS SUPPORT"

    draw.text((card_margin_x + 50, y), badge_header, fill=highlight_rgb)
    y += 50
    draw.text((card_margin_x + 50, y), sub_desc[:65], fill=(200, 210, 230))

    # Bottom Studio Footer
    draw.rounded_rectangle([(70, height - 170), (width - 70, height - 70)], radius=18, fill=accent_rgb)
    draw.text((110, height - 130), cta_footer, fill=(255, 255, 255))

    base_img.save(output_path, "PNG")
    return output_path
