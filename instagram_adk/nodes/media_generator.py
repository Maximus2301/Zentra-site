"""Stage 3: Visual & Media Asset Generator with Google Imagen 3 and Veo 2.0 Video."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from ..config.settings import OUTPUT_DIR
from ..models.state import AccountContext, CoreNarrative
from ..tools.google_media_tools import generate_imagen_image, generate_veo_video_spec

logger = logging.getLogger("instagram_adk.media_generator")


def run_media_generator_node(ctx: Any) -> str:
    """Stage 3 Node: Generates visual & video assets using Google Imagen 3 and Google Veo 2.0."""
    state = ctx.state
    account = AccountContext.model_validate(state.get("account"))
    narrative = CoreNarrative.model_validate(state.get("narrative"))
    active_formats = state.get("active_formats") or ["static_post", "story", "reel", "status"]
    static_post = state.get("static_post") or {}

    assets: dict[str, str] = {}
    video_specs: dict[str, Any] = {}

    # 1. Static Feed Post: Google Imagen 3 (4:5 Aspect Ratio)
    if "static_post" in active_formats or "all" in active_formats:
        feed_file = OUTPUT_DIR / f"{account.account_id}_feed_4x5.png"
        prompt_text = (
            static_post.get("visual_prompt")
            or f"Cinematic editorial photography representing '{narrative.hook}', dramatic cinematic lighting, color palette {account.color_palette[:3]}, award winning commercial portrait"
        )
        generate_imagen_image(
            prompt=prompt_text,
            output_path=feed_file,
            aspect_ratio="4:5",
            color_palette=account.color_palette,
            account_name=account.name,
            handle=account.handle,
            overlay_hook=narrative.hook,
        )
        assets["static_post"] = str(feed_file)
        logger.info(f"✓ Google Imagen 3 Feed Visual generated: {feed_file.name}")

    # 2. Instagram Story: Google Imagen 3 (9:16 Vertical)
    if "story" in active_formats or "all" in active_formats:
        story_file = OUTPUT_DIR / f"{account.account_id}_story_9x16.png"
        story_prompt = f"Vertical 9:16 mobile story layout, high tech editorial lighting, dramatic neon accents {account.color_palette[1]}, clean typography space, minimalist luxury aesthetic"
        generate_imagen_image(
            prompt=story_prompt,
            output_path=story_file,
            aspect_ratio="9:16",
            color_palette=account.color_palette,
            account_name=account.name,
            handle=account.handle,
            overlay_hook="STORY ALERT: " + narrative.hook,
        )
        assets["story"] = str(story_file)
        logger.info(f"✓ Google Imagen 3 Story Visual generated: {story_file.name}")

    # 3. Instagram Reel: Google Veo 2.0 Video Engine (9:16 Vertical)
    if "reel" in active_formats or "all" in active_formats:
        reel_cover_file = OUTPUT_DIR / f"{account.account_id}_reel_cover_9x16.png"
        if "fintech" in account.account_id or "save" in account.account_id:
            reel_prompt = f"Cinematic 9:16 vertical video representing modern automated personal finance and wealth freedom, elegant minimalist interface, clean bright cinematic lighting, 4K film look"
        elif "alex" in account.account_id or "ceo" in account.account_id:
            reel_prompt = f"Cinematic 9:16 vertical video representing startup engineering velocity and leadership decision making, sleek modern tech office, warm natural cinematic lighting, 4K film look"
        else:
            reel_prompt = f"Cinematic 9:16 vertical motion scene representing corporate accountability and legal empowerment, brooding volumetric lighting, slow motion push-in, 4K film look"
        
        # Call Google Veo 2.0 Video Generator
        veo_spec = generate_veo_video_spec(
            prompt=reel_prompt,
            output_path=reel_cover_file,
            duration_seconds=5,
            camera_motion="Cinematic slow-motion push-in tracking subject with dramatic shadows",
        )
        video_specs["veo"] = veo_spec

        # Generate accompanying 9:16 keyframe cover
        generate_imagen_image(
            prompt=reel_prompt,
            output_path=reel_cover_file,
            aspect_ratio="9:16",
            color_palette=account.color_palette,
            account_name=account.name,
            handle=account.handle,
            overlay_hook="30S REEL SCREENPLAY: " + narrative.hook,
        )
        assets["reel"] = str(reel_cover_file)
        logger.info(f"✓ Google Veo 2.0 Video Engine asset generated: {reel_cover_file.name}")

    # 4. Status Snippet: Google Imagen 3 (1:1 Square)
    if "status" in active_formats or "all" in active_formats:
        status_file = OUTPUT_DIR / f"{account.account_id}_status_card.png"
        status_prompt = f"Square 1:1 minimalist typography quote poster, glowing neon borders {account.color_palette[1]}, clean luxury tech editorial"
        generate_imagen_image(
            prompt=status_prompt,
            output_path=status_file,
            aspect_ratio="1:1",
            color_palette=account.color_palette,
            account_name=account.name,
            handle=account.handle,
            overlay_hook=narrative.hook,
        )
        assets["status"] = str(status_file)
        logger.info(f"✓ Status Graphic generated: {status_file.name}")

    state["media_assets"] = assets
    state["video_specs"] = video_specs
    return "media_ready"
