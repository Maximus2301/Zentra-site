"""
Unified Multi-Format Content Generation Pipeline for Personal Brand Engine.
Orchestrates ideation -> SEO/AEO/Meta-aligned synthesis -> $0 visual/video rendering
-> 5-Axis Critic -> AEO Web-Snippet Export -> HITL Queue across all 4 Instagram formats.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from ..config.settings import BrandSettings, PROJECT_ROOT, get_brand_settings
from ..generators.carousel_generator import generate_carousel
from ..generators.carousel_renderer import render_carousel_deck
from ..generators.reel_generator import ReelRenderer, generate_reel_script
from ..generators.static_post_generator import StaticPostRenderer, generate_static_post
from ..generators.status_generator import StatusRenderer, generate_status_card
from ..hitl.queue_manager import PostStatus, QueueManager, QueuedItem
from .critic import evaluate_post_package
from .search_intel import export_aeo_snippet

logger = logging.getLogger("personal_brand.pipeline")

SUPPORTED_FORMATS = ("status", "static", "carousel", "reel")


def build_and_render_post(
    topic: str,
    format_type: str = "carousel",
    pillar_id: Optional[str] = None,
    brand: Optional[BrandSettings] = None,
    brand_id: Optional[str] = None,
    hook_override: Optional[str] = None,
    angle_summary: Optional[str] = None,
    primary_search_keyword: Optional[str] = None,
    aeo_question: Optional[str] = None,
    photo_path: Optional[Path] = None,
    user_audio_path: Optional[Path] = None,
    alternate_hook: bool = False,
    queue_manager: Optional[QueueManager] = None,
    output_root: Optional[Path] = None,
    tenant_id: str = "",
    brand_slug: str = "default",
) -> QueuedItem:
    """
    Generates, renders, critiques, exports AEO article snippet, and enqueues an Instagram post.
    """
    b = brand or get_brand_settings(brand_id)
    fmt = (format_type or "carousel").strip().lower()
    if fmt not in SUPPORTED_FORMATS:
        fmt = "carousel"

    if not pillar_id:
        pillar_id = b.pillars[0]["id"] if b.pillars else "general"

    timestamp = int(time.time())
    safe_topic = "".join(c if c.isalnum() else "_" for c in topic.lower())[:28].strip("_") or "post"
    item_id = f"{fmt}_{timestamp}_{safe_topic}"
    base_out = output_root or (PROJECT_ROOT / "output")
    output_dir = base_out / item_id
    output_dir.mkdir(parents=True, exist_ok=True)

    slide_paths: list[str] = []
    video_path: Optional[str] = None
    caption = ""
    hashtags: list[str] = []
    alt_text = ""
    kw = primary_search_keyword or ""
    q_aeo = aeo_question or ""
    ans_aeo = ""
    hook_used = hook_override or topic
    content_summary = ""
    extra_meta: dict = {
        "hook_override": hook_override,
        "angle_summary": angle_summary,
        "primary_search_keyword": primary_search_keyword,
        "aeo_question": aeo_question,
        "photo_path": str(photo_path) if photo_path else None,
        "user_audio_path": str(user_audio_path) if user_audio_path else None,
    }

    if fmt == "status":
        card = generate_status_card(
            topic=topic,
            pillar_id=pillar_id,
            brand=b,
            hook_override=hook_override,
            angle_summary=angle_summary,
            primary_search_keyword=primary_search_keyword,
            aeo_question=aeo_question,
            alternate_hook=alternate_hook,
        )
        out_img = StatusRenderer(brand=b).render(card, output_dir)
        slide_paths = [str(out_img)]
        caption = card.caption
        hashtags = card.hashtags
        alt_text = card.alt_text
        kw = card.primary_search_keyword or kw
        q_aeo = card.aeo_question or q_aeo
        ans_aeo = card.aeo_direct_answer
        hook_used = card.headline_statement
        content_summary = f"[{card.style_variant}] {card.headline_statement} | {card.supporting_punchline or ''}"
        extra_meta["style_variant"] = card.style_variant

    elif fmt == "static":
        has_photo = bool(photo_path and photo_path.exists())
        post = generate_static_post(
            topic=topic,
            pillar_id=pillar_id,
            brand=b,
            hook_override=hook_override,
            angle_summary=angle_summary,
            primary_search_keyword=primary_search_keyword,
            aeo_question=aeo_question,
            has_photo=has_photo,
            alternate_hook=alternate_hook,
        )
        out_img = StaticPostRenderer(brand=b).render(post, output_dir, photo_path=photo_path)
        slide_paths = [str(out_img)]
        caption = post.caption
        hashtags = post.hashtags
        alt_text = post.alt_text
        kw = post.primary_search_keyword or kw
        q_aeo = post.aeo_question or q_aeo
        ans_aeo = post.aeo_direct_answer
        hook_used = post.headline
        content_summary = f"[{post.layout_type}] {post.headline} — {post.subheadline} | Points: {'; '.join(post.key_points)}"
        extra_meta["layout_type"] = post.layout_type

    elif fmt == "reel":
        script = generate_reel_script(
            topic=topic,
            pillar_id=pillar_id,
            brand=b,
            hook_override=hook_override,
            angle_summary=angle_summary,
            primary_search_keyword=primary_search_keyword,
            aeo_question=aeo_question,
            alternate_hook=alternate_hook,
        )
        out_mp4 = ReelRenderer(brand=b).render(
            script,
            output_dir,
            bg_photo_path=photo_path,
            user_audio_path=user_audio_path,
        )
        video_path = str(out_mp4)
        cover_path = output_dir / "reel_cover.png"
        if cover_path.exists():
            slide_paths = [str(cover_path)]
        caption = script.caption
        hashtags = script.hashtags
        alt_text = script.alt_text
        kw = script.primary_search_keyword or kw
        q_aeo = script.aeo_question or q_aeo
        ans_aeo = script.aeo_direct_answer
        hook_used = script.hook_0_to_3s
        content_summary = f"Hook: {script.hook_0_to_3s}\nTeleprompter: {script.teleprompter_script}"
        extra_meta["deck_title"] = script.title
        extra_meta["audio_vibe"] = script.audio_vibe
        extra_meta["teleprompter_script"] = script.teleprompter_script

    else:  # carousel
        deck = generate_carousel(
            topic=topic,
            pillar_id=pillar_id,
            brand=b,
            hook_override=hook_override,
            angle_summary=angle_summary,
            primary_search_keyword=primary_search_keyword,
            aeo_question=aeo_question,
            alternate_hook=alternate_hook,
        )
        rendered = render_carousel_deck(deck=deck, output_dir=output_dir, brand=b)
        slide_paths = [str(p) for p in rendered]
        caption = deck.caption
        hashtags = deck.hashtags
        alt_text = deck.alt_text
        kw = deck.primary_search_keyword or kw
        q_aeo = deck.aeo_question or q_aeo
        ans_aeo = deck.aeo_direct_answer
        hook_used = deck.slides[0].headline if deck.slides else deck.title
        content_summary = "\n".join(
            f"Slide {s.slide_number}: {s.headline} — {', '.join(s.body_points[:2])}"
            for s in deck.slides
        )
        extra_meta["deck_title"] = deck.title
        extra_meta["read_time"] = deck.estimated_read_time

    # Enforce modern 3-5 hyper-relevant semantic hashtags
    normalized_tags = [
        (t if t.startswith("#") else f"#{t}").strip()
        for t in (hashtags or [])
        if t and t.strip()
    ][:5]
    if normalized_tags:
        tag_str = " ".join(normalized_tags)
        if tag_str not in caption and "#" not in caption.splitlines()[-1]:
            caption = f"{caption.rstrip()}\n\n{tag_str}"

    # Export AEO Markdown + FAQPage JSON-LD snippet
    aeo_path = export_aeo_snippet(
        topic=topic,
        aeo_question=q_aeo,
        aeo_direct_answer=ans_aeo,
        primary_keyword=kw,
        caption=caption,
        hashtags=normalized_tags,
        output_dir=output_dir,
        brand=b,
    )
    extra_meta["aeo_article_path"] = str(aeo_path)

    # Run 5-Axis Brand, Virality, SEO & AEO Critic
    critic = evaluate_post_package(
        format_type=fmt,
        topic=topic,
        hook=hook_used,
        content_summary=content_summary,
        caption=caption,
        primary_keyword=kw,
        aeo_question=q_aeo,
        alt_text=alt_text,
        hashtags=normalized_tags,
        brand=b,
    )

    item = QueuedItem(
        id=item_id,
        tenant_id=tenant_id,
        brand_slug=brand_slug,
        topic=topic,
        pillar=pillar_id,
        format_type=fmt,
        status=PostStatus.PENDING_REVIEW,
        slide_paths=slide_paths,
        video_path=video_path,
        caption=caption,
        hashtags=normalized_tags,
        alt_text=alt_text,
        primary_search_keyword=kw,
        aeo_question=q_aeo,
        aeo_direct_answer=ans_aeo,
        pinned_comment=critic.suggested_pinned_comment,
        critic=critic.model_dump(),
        meta=extra_meta,
    )

    qm = queue_manager or QueueManager(base_output_dir=base_out)
    qm.enqueue(item)
    try:
        from . import cloud_memory
        cloud_memory.sync_directory(output_dir)
    except Exception:
        pass
    return item
