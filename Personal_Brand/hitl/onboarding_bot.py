"""
Multi-Tenant, Multi-Account Telegram Personal Brand Studio.
Security & SaaS Pilot Features:
- Strict tenant isolation keyed by immutable Telegram User ID (`update.effective_user.id`)
- Subscription gating (`/register <user_id>`, `/activate <key>`, admin `/gen_key`, 1-tap approval)
- Multi-Instagram-Account switcher (`/brands` -> create & switch between multiple brand personas)
- Per-tenant daily generation rate limiting
- All 4 Instagram formats (Status, Static Graphic/Photo Overlay, Carousel, 9:16 Kinetic Reel)
- SEO + AEO + Meta Reach optimization (`/bio_seo`, 5-axis Critic, AEO export)
- Grounded zero-cost Q&A advisor (`/ask` & `[Answer as Question]`)
"""
from __future__ import annotations

import html
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..config.settings import (
    BrandSettings,
    OUTPUT_DIR,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from ..core.assistant import answer_user_query
from ..core.ideator import generate_content_overview, load_angle_from_cache
from ..core.llm_client import LLMNotConfiguredError
from ..core.pipeline import build_and_render_post
from ..core.search_intel import optimize_instagram_bio
from ..core.tenant_store import tenant_store
from ..core.voice_processor import extract_voice_dna, transcribe_voice_note
from .queue_manager import PostStatus, QueueManager, QueuedItem
from .telegram_gate import format_review_card_text

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("personal_brand.bot")

# Onboarding Conversation States
(
    STATE_NAME_HANDLE,
    STATE_AVATAR,
    STATE_GENRE_AUDIENCE,
    STATE_TAGLINE_BIO,
    STATE_VOICE_STYLE,
    STATE_PILLARS_GOAL,
    STATE_SOCIALS,
) = range(7)

# Granular Edit & Brand Creation States
(
    EDIT_NAME,
    EDIT_AVATAR,
    EDIT_AUDIENCE,
    EDIT_BIO,
    EDIT_VOICE,
    EDIT_PILLARS,
    EDIT_VIRALITY,
    EDIT_SOCIALS,
    EDIT_ACCENT,
    EDIT_CAPTION,
    ADD_BRAND,
) = range(10, 21)

ASK_MODE = 30

THOUGHTS_CACHE_DIR = OUTPUT_DIR / "thoughts_cache"
THOUGHTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ── Tenant Context & Subscription Gate Helpers ────────────────────────────────

def _get_uid(update: Update) -> str:
    """Returns Telegram's guaranteed immutable numeric user ID (or chat ID fallback)."""
    if update.effective_user:
        return str(update.effective_user.id)
    if update.effective_chat:
        return str(update.effective_chat.id)
    return "anonymous"


def _tenant_ctx(update: Update) -> Tuple[str, str, BrandSettings, Path, QueueManager]:
    """Resolves isolated (tenant_id, brand_slug, BrandSettings, brand_dir, QueueManager)."""
    uid = _get_uid(update)
    slug = tenant_store.get_active_brand_slug(uid)
    brand_dir = tenant_store.get_brand_dir(uid, slug)
    brand_settings = tenant_store.get_brand_settings(uid, slug)
    qm = QueueManager(base_output_dir=brand_dir / "output")
    return uid, slug, brand_settings, brand_dir, qm


async def _require_active_subscriber(update: Update) -> bool:
    """Blocks unsubscribed users and explains how to register a User ID or redeem a key."""
    uid = _get_uid(update)
    active, status = tenant_store.is_active_subscriber(uid)
    if active:
        return True

    target = update.callback_query.message if update.callback_query else update.message
    if not target:
        return False

    if status == "pending_approval":
        msg = (
            f"⏳ <b>Pilot Registration Pending Approval</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Your Telegram User ID: <code>{html.escape(uid)}</code>\n\n"
            f"Your request has been sent to the admin. If you have an activation key, enter:\n"
            f"<code>/activate PILOT-XXXX-XXXX</code>"
        )
    elif status in ("suspended", "expired"):
        msg = (
            f"🔒 <b>Subscription {html.escape(status.upper())}</b>\n"
            f"Your Telegram ID: <code>{html.escape(uid)}</code>\n\n"
            f"Renew or redeem a new activation key via:\n"
            f"<code>/activate PILOT-XXXX-XXXX</code>"
        )
    else:
        msg = (
            f"🔐 <b>Pilot Access Required</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Your Telegram User ID: <code>{html.escape(uid)}</code>\n\n"
            f"To unlock this Personal Brand Studio:\n"
            f"1️⃣ <b>Have a license key?</b> Send:\n"
            f"   <code>/activate PILOT-XXXX-XXXX</code>\n\n"
            f"2️⃣ <b>New to the Pilot?</b> Create your User ID to request access:\n"
            f"   <code>/register your_user_id</code>"
        )
    await target.reply_html(msg)
    return False


async def _consume_quota_or_notify(update: Update, message) -> bool:
    """Enforces daily per-tenant rate limit to protect shared API quotas."""
    uid = _get_uid(update)
    ok, used, limit = tenant_store.check_and_consume_quota(uid)
    if not ok:
        await message.reply_html(
            f"⏱️ <b>Daily Quota Reached ({used}/{limit} posts today)</b>\n"
            f"Your quota resets automatically at 00:00 UTC."
        )
        return False
    return True


def _save_thought_cache(
    tenant_id: str,
    thought: str,
    photo_path: Optional[str] = None,
    audio_path: Optional[str] = None,
) -> str:
    uid = uuid.uuid4().hex[:8]
    payload = {
        "uid": uid,
        "tenant_id": str(tenant_id),
        "thought": thought,
        "photo_path": photo_path,
        "audio_path": audio_path,
    }
    (THOUGHTS_CACHE_DIR / f"{uid}.json").write_text(json.dumps(payload), encoding="utf-8")
    return uid


def _load_thought_cache(uid: str, expected_tenant_id: str) -> Optional[dict]:
    safe_uid = "".join(c for c in uid if c.isalnum())
    path = THOUGHTS_CACHE_DIR / f"{safe_uid}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("tenant_id") != str(expected_tenant_id):
        return None
    return data


def _process_avatar_image(source_path: Path, dest_path: Path) -> bool:
    """Crops and saves image into a circular 400x400 brand avatar PNG."""
    try:
        img = Image.open(source_path).convert("RGBA")
        w, h = img.size
        min_dim = min(w, h)
        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
        img = img.resize((400, 400), Image.Resampling.LANCZOS)

        mask = Image.new("L", (400, 400), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 400, 400), fill=255)

        circle_img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        circle_img.paste(img, (0, 0), mask=mask)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        circle_img.save(dest_path, "PNG")
        return True
    except Exception as e:
        logger.error(f"Error processing avatar image: {e}")
        return False


def _get_edit_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✏️ Name & Handle", callback_data="edit_start:name"),
            InlineKeyboardButton("📸 Update Photo", callback_data="edit_start:avatar"),
        ],
        [
            InlineKeyboardButton("🎯 Genre & Audience", callback_data="edit_start:audience"),
            InlineKeyboardButton("📝 Tagline & Bio", callback_data="edit_start:bio"),
        ],
        [
            InlineKeyboardButton("🎙️ Voice DNA", callback_data="edit_start:voice"),
            InlineKeyboardButton("🏛️ Edit Pillars", callback_data="edit_start:pillars"),
        ],
        [
            InlineKeyboardButton("🔥 Virality Goal", callback_data="edit_start:virality"),
            InlineKeyboardButton("🌐 Edit Socials", callback_data="edit_start:socials"),
        ],
        [
            InlineKeyboardButton("🎨 Change Theme", callback_data="action:theme"),
            InlineKeyboardButton("🔍 Optimize Bio SEO", callback_data="action:bio_seo"),
        ],
        [
            InlineKeyboardButton("🏷️ Switch Brand", callback_data="action:brands"),
            InlineKeyboardButton("🚀 Content Roadmap", callback_data="action:overview"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _dispatch_item_to_chat(message, item: QueuedItem) -> None:
    """Sends rendered video/image/album + interactive review card."""
    if item.format_type == "reel" and item.video_path and Path(item.video_path).exists():
        with open(item.video_path, "rb") as vf:
            await message.reply_video(
                video=vf,
                caption=f"🎬 <b>{html.escape(item.topic)}</b>\n\n<i>Audio vibe: {html.escape(item.meta.get('audio_vibe', 'Minimal beat'))}</i>",
                parse_mode="HTML",
                supports_streaming=True,
            )
    else:
        rendered_paths = [Path(p) for p in item.slide_paths if Path(p).exists()]
        if len(rendered_paths) == 1:
            with open(rendered_paths[0], "rb") as ph:
                await message.reply_photo(photo=ph)
        elif len(rendered_paths) > 1:
            media_group = []
            handles = []
            for p in rendered_paths[:10]:
                fh = open(p, "rb")
                handles.append(fh)
                media_group.append(InputMediaPhoto(media=fh))
            try:
                await message.reply_media_group(media=media_group)
            finally:
                for fh in handles:
                    fh.close()

    review_text = format_review_card_text(item)
    card_keyboard = [
        [InlineKeyboardButton("🚀 Approve & Queue", callback_data=f"approve:{item.id}")],
        [
            InlineKeyboardButton("🔄 Alternate Hook", callback_data=f"regen:{item.id}"),
            InlineKeyboardButton("✏️ Edit Caption", callback_data=f"edit_cap:{item.id}"),
        ],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject:{item.id}")],
    ]
    await message.reply_html(review_text, reply_markup=InlineKeyboardMarkup(card_keyboard))


def _format_llm_error_message(err: Exception) -> str:
    return (
        "⚠️ <b>AI Provider Temporarily Unavailable</b>\n\n"
        f"<code>{html.escape(str(err)[:300])}</code>"
    )


# ── Subscription, Licensing & Multi-Brand Commands ────────────────────────────

async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows a new user to create a User ID linked to their Telegram ID for pilot approval."""
    uid = _get_uid(update)
    tg_user = update.effective_user.username if update.effective_user else ""
    desired_id = " ".join(context.args).strip() if getattr(context, "args", None) else ""

    if not desired_id:
        await update.message.reply_html(
            f"🆔 <b>Create Your Pilot User ID</b>\n"
            f"Your Telegram ID: <code>{html.escape(uid)}</code>\n\n"
            f"Send: <code>/register your_chosen_id</code>\n"
            f"<i>Example: /register priya_fitness</i>"
        )
        return

    ok, result = tenant_store.register_pending_user(uid, desired_id, telegram_username=tg_user or "")
    if not ok:
        await update.message.reply_html(f"⚠️ {html.escape(result)}")
        return

    active, _ = tenant_store.is_active_subscriber(uid)
    if active:
        await update.message.reply_html(f"✅ {html.escape(result)}")
        return

    await update.message.reply_html(
        f"✅ <b>Registration Submitted!</b>\n"
        f"• User ID: <code>{html.escape(result)}</code>\n"
        f"• Telegram ID: <code>{html.escape(uid)}</code>\n\n"
        f"⏳ Waiting for admin approval (or enter <code>/activate KEY</code> if you have a license key)."
    )

    if TELEGRAM_CHAT_ID:
        try:
            admin_msg = (
                f"🆕 <b>NEW PILOT SUBSCRIPTION REQUEST</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• Custom User ID: <code>{html.escape(result)}</code>\n"
                f"• Telegram ID: <code>{html.escape(uid)}</code>\n"
                f"• Username: @{html.escape(tg_user or 'none')}"
            )
            kb = [[
                InlineKeyboardButton("✅ Approve 30d Pilot", callback_data=f"admin_approve:{uid}"),
                InlineKeyboardButton("❌ Deny", callback_data=f"admin_deny:{uid}"),
            ]]
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=admin_msg,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(kb),
            )
        except Exception as e:
            logger.warning(f"Could not notify admin of registration: {e}")


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activates a subscriber account with a single-use license key."""
    uid = _get_uid(update)
    tg_user = update.effective_user.username if update.effective_user else ""
    code = " ".join(context.args).strip() if getattr(context, "args", None) else ""
    if not code:
        await update.message.reply_html("🔑 Usage: <code>/activate PILOT-XXXX-XXXX</code>")
        return

    ok, msg = tenant_store.redeem_license_key(code, uid, telegram_username=tg_user or "")
    if ok:
        await update.message.reply_html(
            f"🎉 <b>{html.escape(msg)}</b>\n\nTap /setup to configure your first Instagram Brand Persona!"
        )
    else:
        await update.message.reply_html(f"❌ {html.escape(msg)}")


async def cmd_gen_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to mint single-use pilot activation keys."""
    uid = _get_uid(update)
    if not tenant_store.is_admin(uid):
        await update.message.reply_html("🔒 Admin access only.")
        return

    days = 30
    if getattr(context, "args", None):
        try:
            days = max(1, min(365, int(context.args[0])))
        except ValueError:
            pass

    code = tenant_store.generate_license_key(created_by=uid, duration_days=days)
    await update.message.reply_html(
        f"🎟️ <b>New Pilot Activation Key ({days} days)</b>\n"
        f"<code>{code}</code>\n\n"
        f"Share with your subscriber to run:\n<code>/activate {code}</code>"
    )


async def cmd_brands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all Instagram brands owned by this subscriber and lets them switch or add one."""
    if not await _require_active_subscriber(update):
        return

    uid, active_slug, _, _, _ = _tenant_ctx(update)
    brands = tenant_store.list_brands(uid)
    user = tenant_store.get_user(uid) or {}
    max_b = user.get("max_brands", 3)

    lines = [
        f"🏷️ <b>YOUR INSTAGRAM BRANDS ({len(brands)}/{max_b})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    ]
    keyboard = []
    for b in brands:
        slug = b["brand_slug"]
        is_active = slug == active_slug
        marker = "🟢 " if is_active else "⚪ "
        handle_str = f" ({html.escape(b['ig_handle'])})" if b.get("ig_handle") else ""
        lines.append(f"{marker}<b>{html.escape(b['display_name'])}</b>{handle_str}")
        if not is_active:
            keyboard.append([
                InlineKeyboardButton(
                    f"Switch → {b['display_name']}",
                    callback_data=f"switch_brand:{slug}",
                )
            ])

    keyboard.append([InlineKeyboardButton("➕ Add New Instagram Brand", callback_data="edit_start:add_brand")])
    keyboard.append([InlineKeyboardButton("👤 View Active Persona", callback_data="action:profile")])

    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_html("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))


# ── Core Commands ─────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return

    uid, slug, brand_settings, _, _ = _tenant_ctx(update)
    user = tenant_store.get_user(uid) or {}

    if not brand_settings.is_configured:
        text = (
            f"👑 <b>Personal Brand Engine</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ <b>Workspace:</b> <code>{html.escape(slug)}</code> • Plan: <code>{html.escape(str(user.get('plan', 'pilot')))}</code>\n"
            f"⚠️ <b>Status: Brand Persona Not Configured Yet</b>\n\n"
            f"Create customized Instagram <b>Status Cards, Static Posts, Carousels &amp; Reels</b> "
            f"optimized for SEO, AEO &amp; Meta reach.\n\n"
            f"👉 <b>Tap below or type /setup to configure this brand!</b>"
        )
        keyboard = [
            [InlineKeyboardButton("🚀 Start Onboarding Wizard", callback_data="action:start_setup")],
            [
                InlineKeyboardButton("🏷️ Switch / Add Brand", callback_data="action:brands"),
                InlineKeyboardButton("💬 Ask AI Advisor", callback_data="action:ask"),
            ],
            [InlineKeyboardButton("📖 View Command Help", callback_data="action:help")],
        ]
    else:
        genre = brand_settings.creator.get("genre") or "General"
        audience = brand_settings.target_audience.get("primary_audience") or "Not specified"
        text = (
            f"👑 <b>Personal Brand Engine</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <b>Active Brand:</b> {html.escape(brand_settings.name)} (<code>{html.escape(brand_settings.handle)}</code>)\n"
            f"🎭 <b>Genre:</b> {html.escape(genre)}\n"
            f"👥 <b>Audience:</b> {html.escape(audience[:80])}\n"
            f"🎨 <b>Theme:</b> <code>{html.escape(str(brand_settings.theme.get('active_preset')))}</code>\n\n"
            f"<b>Create anytime:</b> Send a <b>text idea</b>, <b>voice note</b>, or <b>photo</b> right here!"
        )
        keyboard = [
            [
                InlineKeyboardButton("🎯 Viral Roadmap", callback_data="action:overview"),
                InlineKeyboardButton("👤 Brand Persona", callback_data="action:profile"),
            ],
            [
                InlineKeyboardButton("🏷️ Switch / Add Brand", callback_data="action:brands"),
                InlineKeyboardButton("💬 Ask AI Advisor", callback_data="action:ask"),
            ],
            [
                InlineKeyboardButton("🎨 Switch Theme", callback_data="action:theme"),
                InlineKeyboardButton("📖 Help & Guide", callback_data="action:help"),
            ],
        ]

    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return

    text = (
        f"📖 <b>PERSONAL BRAND ENGINE — COMMAND GUIDE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Core Commands:</b>\n"
        f"• <b>/start</b> — Home dashboard &amp; active brand status.\n"
        f"• <b>/brands</b> — Create &amp; switch between multiple Instagram brands.\n"
        f"• <b>/setup</b> — Full Brand Persona, Genre, Audience &amp; Voice wizard.\n"
        f"• <b>/overview</b> (or <b>/ideas</b>) — Generate 4 customized angles (Status, Static, Carousel, Reel).\n"
        f"• <b>/profile</b> — View &amp; edit Persona DNA, Audience, Pillars &amp; Virality Goal.\n"
        f"• <b>/bio_seo</b> — Optimize Instagram Display Name &amp; Bio for search.\n"
        f"• <b>/theme</b> — Choose from 6 visual presets or custom accent hex.\n"
        f"• <b>/ask [question]</b> — Ask anything about this tool or Instagram growth.\n\n"
        f"<b>Create On-Demand:</b>\n"
        f"Send any <b>text idea</b>, <b>voice note</b>, or <b>photo</b> anytime!"
    )
    keyboard = [
        [
            InlineKeyboardButton("🎯 Viral Roadmap", callback_data="action:overview"),
            InlineKeyboardButton("🏷️ Switch Brand", callback_data="action:brands"),
        ],
        [
            InlineKeyboardButton("💬 Ask AI Advisor", callback_data="action:ask"),
            InlineKeyboardButton("⚙️ Run Setup", callback_data="action:start_setup"),
        ],
    ]
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return

    uid, slug, brand_settings, brand_dir, _ = _tenant_ctx(update)
    target = update.callback_query.message if update.callback_query else update.message

    if not brand_settings.is_configured:
        keyboard = [[InlineKeyboardButton("🚀 Start Onboarding Wizard", callback_data="action:start_setup")]]
        await target.reply_html(
            f"⚠️ <i>Brand workspace '<code>{html.escape(slug)}</code>' is not configured yet. Tap below to run /setup!</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    creator = brand_settings.creator
    audience = brand_settings.target_audience
    voice = brand_settings.voice
    virality = brand_settings.virality_strategy
    socials = creator.get("socials", {})
    social_text = "\n".join(
        f"  • {html.escape(k.capitalize())}: <code>{html.escape(str(v))}</code>" for k, v in socials.items()
    ) or "  • <i>None</i>"
    pillars_text = "\n".join(
        f"  • {html.escape(str(p.get('name')))}" for p in (brand_settings.pillars or [])
    ) or "  • <i>None</i>"

    card = (
        f"👤 <b>BRAND PERSONA DNA</b> (<code>{html.escape(slug)}</code>)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ <b>Identity:</b> {html.escape(str(creator.get('name')))} (<code>{html.escape(str(creator.get('handle')))}</code>)\n"
        f"🎭 <b>Genre / Niche:</b> {html.escape(str(creator.get('genre') or 'Not set'))}\n"
        f"👥 <b>Target Audience:</b> {html.escape(str(audience.get('primary_audience') or 'Not set'))}\n"
        f"📌 <b>Tagline:</b> {html.escape(str(creator.get('tagline') or 'Not set'))}\n"
        f"📝 <b>Bio:</b> {html.escape(str(creator.get('bio') or 'Not set'))}\n\n"
        f"🎙️ <b>Voice DNA:</b>\n"
        f"• Archetype: {html.escape(str(voice.get('archetype') or 'Dynamic'))}\n"
        f"• Cadence: <i>{html.escape(str(voice.get('cadence') or voice.get('writing_style') or 'Direct'))}</i>\n"
        f"• Perspective: {html.escape(str(voice.get('perspective') or 'First-person'))}\n\n"
        f"🔥 <b>Virality Goal:</b> <code>{html.escape(str(virality.get('primary_goal', 'saves_and_shares')))}</code>\n"
        f"🏛️ <b>Pillars:</b>\n{pillars_text}\n\n"
        f"🌐 <b>Socials:</b>\n{social_text}\n"
        f"🎨 <b>Theme:</b> <code>{html.escape(str(brand_settings.theme.get('active_preset')))}</code>\n\n"
        f"<i>Tap below to edit any field:</i>"
    )

    rel_av = creator.get("avatar_path") or "assets/avatar.png"
    avatar_path = Path(rel_av) if Path(rel_av).is_absolute() else (brand_dir / rel_av)
    if avatar_path.exists():
        with open(avatar_path, "rb") as photo:
            await target.reply_photo(photo=photo, caption=card[:1024], parse_mode="HTML", reply_markup=_get_edit_keyboard())
    else:
        await target.reply_html(card, reply_markup=_get_edit_keyboard())


async def cmd_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return

    uid, slug, brand_settings, _, _ = _tenant_ctx(update)
    target = update.callback_query.message if update.callback_query else update.message
    if not brand_settings.is_configured:
        await target.reply_html(
            "⚠️ Please configure this brand first via /setup so ideas match your niche and audience.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Start Setup", callback_data="action:start_setup")]]),
        )
        return

    if not await _consume_quota_or_notify(update, target):
        return

    msg = await target.reply_html("🧠 <i>Brainstorming SEO/AEO viral angles across Status, Static, Carousel &amp; Reels...</i>")
    try:
        roadmap = generate_content_overview(brand_settings, tenant_id=uid, brand_slug=slug)
    except LLMNotConfiguredError as e:
        await msg.edit_text(_format_llm_error_message(e), parse_mode="HTML")
        return
    except Exception as e:
        logger.exception("Overview ideation failed")
        await msg.edit_text(f"⚠️ Ideation failed: <code>{html.escape(str(e)[:200])}</code>", parse_mode="HTML")
        return

    text_parts = [
        f"📋 <b>CUSTOM VIRAL ROADMAP</b>\n"
        f"<i>{html.escape(roadmap.creator_handle)} • {html.escape(str(brand_settings.creator.get('genre') or 'Personal Brand'))}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    ]
    format_emojis = {"status": "💬", "static": "🖼️", "carousel": "📑", "reel": "🎬"}
    keyboard = []
    for angle in roadmap.angles:
        emo = format_emojis.get(angle.format, "⚡")
        kw_html = f" • 🔍 <code>{html.escape(angle.primary_search_keyword)}</code>" if angle.primary_search_keyword else ""
        text_parts.append(
            f"<b>#{angle.id}. {emo} {html.escape(angle.format_label)}</b>\n"
            f"🏷️ <i>{html.escape(angle.pillar)}</i>{kw_html}\n"
            f"⚡ <b>Hook:</b> \"{html.escape(angle.hook)}\"\n"
            f"📖 <b>Angle:</b> {html.escape(angle.angle_summary)}\n"
            f"🔥 <b>Why it works:</b> {html.escape(angle.why_it_works)}\n"
        )
        keyboard.append([
            InlineKeyboardButton(
                f"{emo} Generate {angle.format.upper()} #{angle.id}",
                callback_data=f"gen_angle:{angle.uid}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔄 Fresh Angles", callback_data="action:overview"),
        InlineKeyboardButton("👤 Edit Persona", callback_data="action:profile"),
    ])
    await msg.edit_text("\n".join(text_parts), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def cmd_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return

    _, _, brand_settings, _, _ = _tenant_ctx(update)
    curr = brand_settings.theme.get("active_preset", "clean_minimal")
    custom_acc = brand_settings.theme.get("custom_accent", "")
    text = (
        f"🎨 <b>SELECT YOUR VISUAL BRAND THEME</b>\n"
        f"Current: <code>{html.escape(str(curr))}</code>"
        + (f" (Accent: <code>{html.escape(str(custom_acc))}</code>)" if custom_acc else "")
        + "\n\n"
        "• <b>Clean Minimal:</b> Crisp white &amp; royal blue\n"
        "• <b>Warm Creator:</b> Cream &amp; terracotta\n"
        "• <b>Bold Viral:</b> High-contrast black &amp; yellow\n"
        "• <b>Dark Terminal:</b> Charcoal &amp; emerald/sky\n"
        "• <b>Editorial Luxury:</b> Obsidian &amp; amber gold\n"
        "• <b>Clinical Serene:</b> Trustworthy teal &amp; navy"
    )
    keyboard = [
        [
            InlineKeyboardButton("🤍 Clean Minimal", callback_data="set_theme:clean_minimal"),
            InlineKeyboardButton("🧡 Warm Creator", callback_data="set_theme:warm_creator"),
        ],
        [
            InlineKeyboardButton("⚡ Bold Viral", callback_data="set_theme:bold_viral"),
            InlineKeyboardButton("🌙 Dark Terminal", callback_data="set_theme:dark_terminal"),
        ],
        [
            InlineKeyboardButton("✨ Editorial Luxury", callback_data="set_theme:editorial_luxury"),
            InlineKeyboardButton("🩺 Clinical Serene", callback_data="set_theme:clinical_serene"),
        ],
        [
            InlineKeyboardButton("🎯 Custom Accent Hex", callback_data="edit_start:accent"),
            InlineKeyboardButton("👤 Profile", callback_data="action:profile"),
        ],
    ]
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def cmd_bio_seo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return

    _, _, brand_settings, _, _ = _tenant_ctx(update)
    target = update.callback_query.message if update.callback_query else update.message
    if not brand_settings.is_configured:
        await target.reply_html("⚠️ Please run /setup first so I know your niche and audience.")
        return

    msg = await target.reply_html("🔍 <i>Optimizing your Instagram Display Name &amp; Bio for Search...</i>")
    try:
        opt = optimize_instagram_bio(brand_settings)
        kws = ", ".join(f"<code>{html.escape(k)}</code>" for k in opt.primary_search_keywords)
        text = (
            f"🔍 <b>INSTAGRAM BIO &amp; SEARCH SEO</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ <b>Searchable Display Name</b> <i>(highest search weight!)</i>:\n"
            f"<code>{html.escape(opt.optimized_display_name)}</code>\n\n"
            f"📝 <b>Search-Rich Bio (&lt;=150 chars):</b>\n"
            f"<blockquote>{html.escape(opt.optimized_bio)}</blockquote>\n\n"
            f"🎯 <b>Target Rank Keywords:</b>\n{kws}\n\n"
            f"💡 <i>{html.escape(opt.why_this_ranks)}</i>"
        )
        await msg.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 Back to Profile", callback_data="action:profile")]]),
        )
    except LLMNotConfiguredError as e:
        await msg.edit_text(_format_llm_error_message(e), parse_mode="HTML")
    except Exception as e:
        await msg.edit_text(f"⚠️ Bio SEO failed: <code>{html.escape(str(e)[:200])}</code>", parse_mode="HTML")


# ── Interactive Onboarding Wizard (Per-Tenant & Per-Brand) ────────────────────

async def onboarding_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return ConversationHandler.END

    _, slug, _, _, _ = _tenant_ctx(update)
    text = (
        f"🚀 <b>BRAND ONBOARDING (Step 1/7)</b> — <code>{html.escape(slug)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>What is this Brand's Public Name and Instagram Handle?</b>\n"
        f"<i>Format: Name | @handle</i>\n"
        f"<i>Example: Priya Sharma | @priya.fitness</i>"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_html(text)
    else:
        await update.message.reply_html(text)
    return STATE_NAME_HANDLE


async def onboarding_name_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    if "|" in raw:
        name, handle = [p.strip() for p in raw.split("|", 1)]
    else:
        parts = raw.split(" ")
        name = parts[0]
        handle = parts[1] if len(parts) > 1 else f"@{name.lower()}"
    if not handle.startswith("@"):
        handle = f"@{handle}"

    context.user_data["onboarding_name"] = name
    context.user_data["onboarding_handle"] = handle

    await update.message.reply_html(
        f"✔ Saved: <b>{html.escape(name)}</b> (<code>{html.escape(handle)}</code>)\n\n"
        f"📸 <b>Step 2/7: Upload Brand Profile Photo / Headshot</b>\n"
        f"<i>(Or type 'skip')</i>"
    )
    return STATE_AVATAR


async def onboarding_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, _, brand_dir, _ = _tenant_ctx(update)
    if update.message.text and update.message.text.lower().strip() == "skip":
        context.user_data["onboarding_avatar"] = ""
    else:
        if not update.message.photo:
            await update.message.reply_html("⚠️ Please upload a photo or type 'skip'.")
            return STATE_AVATAR
        photo = update.message.photo[-1]
        file = await photo.get_file()
        temp_path = brand_dir / "assets" / "temp_avatar.jpg"
        await file.download_to_drive(temp_path)
        avatar_dest = brand_dir / "assets" / "avatar.png"
        success = _process_avatar_image(temp_path, avatar_dest)
        temp_path.unlink(missing_ok=True)
        if not success:
            await update.message.reply_html("⚠️ Could not process image. Try another photo or 'skip'.")
            return STATE_AVATAR
        context.user_data["onboarding_avatar"] = str(avatar_dest)

    await update.message.reply_html(
        f"✔ <b>Avatar saved!</b>\n\n"
        f"🎭 <b>Step 3/7: Niche/Genre &amp; Target Audience</b>\n"
        f"<i>Format: Genre | Target Audience &amp; Pain Points</i>\n"
        f"<i>Example: Personal Finance | Salaried 20-somethings struggling to save</i>"
    )
    return STATE_GENRE_AUDIENCE


async def onboarding_genre_audience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    if "|" in raw:
        genre, audience = [p.strip() for p in raw.split("|", 1)]
    else:
        genre, audience = raw, f"People interested in {raw}"

    context.user_data["onboarding_genre"] = genre
    context.user_data["onboarding_audience"] = audience

    await update.message.reply_html(
        f"✔ Genre: <b>{html.escape(genre)}</b>\n\n"
        f"📝 <b>Step 4/7: Tagline &amp; Bio</b>\n"
        f"<i>Format: Tagline | Short Bio</i>"
    )
    return STATE_TAGLINE_BIO


async def onboarding_tagline_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    if "|" in raw:
        tagline, bio = [p.strip() for p in raw.split("|", 1)]
    else:
        tagline, bio = raw, raw

    context.user_data["onboarding_tagline"] = tagline
    context.user_data["onboarding_bio"] = bio

    await update.message.reply_html(
        f"🎙️ <b>Step 5/7: Voice &amp; Vibe Calibration</b>\n"
        f"Send a <b>15–30s voice note</b> (or a paragraph) in your natural style."
    )
    return STATE_VOICE_STYLE


async def onboarding_voice_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, _, brand_dir, _ = _tenant_ctx(update)
    if update.message.voice or update.message.audio:
        voice_obj = update.message.voice or update.message.audio
        file = await voice_obj.get_file()
        temp_audio = brand_dir / "assets" / "temp_voice.oga"
        await file.download_to_drive(temp_audio)
        status_msg = await update.message.reply_html("🎧 <i>Transcribing &amp; extracting Voice DNA...</i>")
        try:
            transcript = transcribe_voice_note(temp_audio)
            dna = extract_voice_dna(transcript)
            context.user_data["onboarding_voice_dna"] = dna
            context.user_data["onboarding_voice_style"] = dna["cadence"]
            await status_msg.edit_text(
                f"✔ <b>Voice Transcribed!</b>\n🎭 Archetype: {html.escape(str(dna.get('archetype', 'Creator')))}",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Voice transcription error: {e}")
            context.user_data["onboarding_voice_dna"] = {"archetype": "Authentic Creator", "cadence": "Conversational"}
            context.user_data["onboarding_voice_style"] = "Natural, authentic, engaging"
            await status_msg.edit_text("✔ Voice note recorded.")
        finally:
            temp_audio.unlink(missing_ok=True)
    else:
        voice_desc = update.message.text.strip()
        dna = extract_voice_dna(voice_desc)
        context.user_data["onboarding_voice_dna"] = dna
        context.user_data["onboarding_voice_style"] = voice_desc
        await update.message.reply_html(f"✔ Voice calibrated ({html.escape(str(dna.get('archetype', 'Custom')))}).")

    await update.message.reply_html(
        f"🏛️ <b>Step 6/7: Content Pillars &amp; Virality Goal</b>\n"
        f"Comma-separated topics + optional <code>| goal</code> (<code>saves</code>, <code>reach</code>, <code>comments</code>, <code>leads</code>)."
    )
    return STATE_PILLARS_GOAL


async def onboarding_pillars_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    goal = "saves_and_shares"
    if "|" in raw:
        pillars_part, goal_raw = [p.strip() for p in raw.split("|", 1)]
        g = goal_raw.lower()
        if "reach" in g or "viral" in g:
            goal = "viral_reach"
        elif "comment" in g or "debate" in g:
            goal = "comments_and_debate"
        elif "lead" in g or "dm" in g:
            goal = "dm_leads"
    else:
        pillars_part = raw

    pillar_names = [p.strip() for p in pillars_part.split(",") if p.strip()] or ["Core Insights", "Myths vs Reality", "Actionable Tips"]
    pillars_data = [
        {"id": f"pillar_{i+1}", "name": name, "weight": round(1.0 / len(pillar_names), 2)}
        for i, name in enumerate(pillar_names)
    ]
    context.user_data["onboarding_pillars"] = pillars_data
    context.user_data["onboarding_goal"] = goal

    await update.message.reply_html(
        f"🌐 <b>Step 7/7: Optional Linked Socials</b>\n"
        f"<i>Example: Instagram: @handle, YouTube: @chan (or 'skip')</i>"
    )
    return STATE_SOCIALS


async def onboarding_socials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, slug, brand_settings, _, _ = _tenant_ctx(update)
    raw = update.message.text.strip()
    socials = {}
    if raw.lower() != "skip":
        for part in raw.split(","):
            if ":" in part:
                k, v = part.split(":", 1)
                socials[k.strip().lower()] = v.strip()

    name = context.user_data.get("onboarding_name", "Creator")
    handle = context.user_data.get("onboarding_handle", "@creator")
    brand_settings.update_creator(
        name=name,
        handle=handle,
        avatar_path=context.user_data.get("onboarding_avatar", ""),
        genre=context.user_data.get("onboarding_genre", ""),
        tagline=context.user_data.get("onboarding_tagline", ""),
        bio=context.user_data.get("onboarding_bio", ""),
        socials=socials,
    )
    brand_settings.update_audience(primary_audience=context.user_data.get("onboarding_audience", ""))
    voice_dna = context.user_data.get("onboarding_voice_dna", {})
    brand_settings.update_voice(
        archetype=voice_dna.get("archetype", "Authentic Domain Creator"),
        tone_attributes=voice_dna.get("extracted_attributes", []),
        writing_style=context.user_data.get("onboarding_voice_style", "Authentic and clear"),
        cadence=voice_dna.get("cadence", "Conversational and engaging"),
        perspective=voice_dna.get("perspective", "First-person authentic voice"),
        sample_transcript=voice_dna.get("voice_sample_transcript", ""),
        vocabulary={
            "encouraged": voice_dna.get("encouraged_words", []),
            "forbidden": voice_dna.get("forbidden_words", []),
        },
    )
    brand_settings.update_pillars(context.user_data.get("onboarding_pillars", []))
    brand_settings.update_virality(primary_goal=context.user_data.get("onboarding_goal", "saves_and_shares"))
    tenant_store.sync_brand_metadata(uid, slug, name, handle)

    card = (
        f"🎉 <b>BRAND PERSONA READY!</b> (<code>{html.escape(slug)}</code>)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Identity:</b> {html.escape(name)} ({html.escape(handle)})\n"
        f"• <b>Genre:</b> {html.escape(str(brand_settings.creator.get('genre')))}\n"
        f"• <b>Audience:</b> {html.escape(str(brand_settings.target_audience.get('primary_audience')))}\n\n"
        f"💡 <b>Send any thought, voice note, or photo now</b> to generate Status, Static, Carousel, or Reels!"
    )
    await update.message.reply_html(card, reply_markup=_get_edit_keyboard())
    return ConversationHandler.END


async def onboarding_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("❌ Cancelled.")
    return ConversationHandler.END


# ── Granular Edit & Brand Creation Conversations ──────────────────────────────

async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return ConversationHandler.END

    query = update.callback_query
    await query.answer()
    action, param = query.data.split(":", 1)

    if action == "edit_cap":
        context.user_data["editing_caption_item_id"] = param
        await query.message.reply_html("✏️ <b>Send the new Instagram caption text:</b>")
        return EDIT_CAPTION

    prompts = {
        "name": ("✏️ <b>Send new Name and Handle:</b>\n<i>Format: Name | @handle</i>", EDIT_NAME),
        "avatar": ("📸 <b>Send a new Headshot / Photo:</b>", EDIT_AVATAR),
        "audience": ("🎯 <b>Send Genre &amp; Target Audience:</b>\n<i>Format: Genre | Target Audience</i>", EDIT_AUDIENCE),
        "bio": ("📝 <b>Send new Tagline and Bio:</b>\n<i>Format: Tagline | Bio</i>", EDIT_BIO),
        "voice": ("🎙️ <b>Send a voice note or paragraph to re-calibrate Voice DNA:</b>", EDIT_VOICE),
        "pillars": ("🏛️ <b>Send new Content Pillars (comma-separated):</b>", EDIT_PILLARS),
        "virality": ("🔥 <b>Send Virality Goal &amp; CTA Style:</b>\n<i>Format: goal | CTA or DM keyword</i>", EDIT_VIRALITY),
        "socials": ("🌐 <b>Send updated Social Handles:</b>", EDIT_SOCIALS),
        "accent": ("🎨 <b>Send a custom hex accent color:</b>\n<i>Example: #EC4899 (or 'clear')</i>", EDIT_ACCENT),
        "add_brand": ("🏷️ <b>Add New Instagram Brand</b>\n<i>Format: Brand Name | @ig_handle</i>\n<i>Example: FitWithPriya | @fitwithpriya</i>", ADD_BRAND),
    }
    if param in prompts:
        msg, state = prompts[param]
        await query.message.reply_html(msg)
        return state
    return ConversationHandler.END


async def edit_handle_add_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = _get_uid(update)
    raw = update.message.text.strip()
    if "|" in raw:
        bname, handle = [p.strip() for p in raw.split("|", 1)]
    else:
        bname, handle = raw, ""
    if handle and not handle.startswith("@"):
        handle = f"@{handle}"

    ok, slug, msg = tenant_store.create_brand(uid, bname, handle)
    if not ok:
        await update.message.reply_html(f"⚠️ {html.escape(msg)}")
        return ConversationHandler.END

    await update.message.reply_html(
        f"✅ <b>{html.escape(msg)}</b>\n\nTap /setup to configure this brand's Genre, Audience &amp; Voice DNA!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Run Setup for New Brand", callback_data="action:start_setup")]]),
    )
    return ConversationHandler.END


async def edit_handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, slug, brand_settings, _, _ = _tenant_ctx(update)
    raw = update.message.text.strip()
    if "|" in raw:
        name, handle = [p.strip() for p in raw.split("|", 1)]
    else:
        parts = raw.split()
        name = parts[0]
        handle = parts[1] if len(parts) > 1 else f"@{name.lower()}"
    if not handle.startswith("@"):
        handle = f"@{handle}"
    brand_settings.update_creator(name=name, handle=handle)
    tenant_store.sync_brand_metadata(uid, slug, name, handle)
    await update.message.reply_html(
        f"✔ Identity updated: <b>{html.escape(name)}</b> (<code>{html.escape(handle)}</code>)",
        reply_markup=_get_edit_keyboard(),
    )
    return ConversationHandler.END


async def edit_handle_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, brand_settings, brand_dir, _ = _tenant_ctx(update)
    if not update.message.photo:
        await update.message.reply_html("⚠️ Please upload a photo.")
        return EDIT_AVATAR
    photo = update.message.photo[-1]
    file = await photo.get_file()
    temp_path = brand_dir / "assets" / "temp_avatar.jpg"
    await file.download_to_drive(temp_path)
    avatar_dest = brand_dir / "assets" / "avatar.png"
    success = _process_avatar_image(temp_path, avatar_dest)
    temp_path.unlink(missing_ok=True)
    if success:
        brand_settings.update_creator(avatar_path=str(avatar_dest))
        await update.message.reply_html("✔ <b>Headshot updated!</b>", reply_markup=_get_edit_keyboard())
        return ConversationHandler.END
    await update.message.reply_html("⚠️ Could not process image.")
    return EDIT_AVATAR


async def edit_handle_audience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, brand_settings, _, _ = _tenant_ctx(update)
    raw = update.message.text.strip()
    if "|" in raw:
        genre, audience = [p.strip() for p in raw.split("|", 1)]
    else:
        genre, audience = raw, brand_settings.target_audience.get("primary_audience", "")
    brand_settings.update_creator(genre=genre)
    if audience:
        brand_settings.update_audience(primary_audience=audience)
    await update.message.reply_html(
        f"✔ Updated Genre: <b>{html.escape(genre)}</b>",
        reply_markup=_get_edit_keyboard(),
    )
    return ConversationHandler.END


async def edit_handle_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, brand_settings, _, _ = _tenant_ctx(update)
    raw = update.message.text.strip()
    if "|" in raw:
        tagline, bio = [p.strip() for p in raw.split("|", 1)]
    else:
        tagline, bio = raw, raw
    brand_settings.update_creator(tagline=tagline, bio=bio)
    await update.message.reply_html("✔ Tagline &amp; Bio updated.", reply_markup=_get_edit_keyboard())
    return ConversationHandler.END


async def edit_handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, brand_settings, brand_dir, _ = _tenant_ctx(update)
    if update.message.voice or update.message.audio:
        voice_obj = update.message.voice or update.message.audio
        file = await voice_obj.get_file()
        temp_audio = brand_dir / "assets" / "temp_voice.oga"
        await file.download_to_drive(temp_audio)
        status_msg = await update.message.reply_html("🎧 <i>Transcribing &amp; extracting Voice DNA...</i>")
        try:
            transcript = transcribe_voice_note(temp_audio)
            dna = extract_voice_dna(transcript)
            brand_settings.update_voice(
                archetype=dna.get("archetype", brand_settings.voice.get("archetype", "Creator")),
                tone_attributes=dna.get("extracted_attributes", []),
                writing_style=dna["cadence"],
                cadence=dna["cadence"],
                perspective=dna["perspective"],
                sample_transcript=transcript,
            )
            await status_msg.edit_text(f"✔ <b>Voice DNA Updated!</b>", parse_mode="HTML")
        finally:
            temp_audio.unlink(missing_ok=True)
    else:
        text = update.message.text.strip()
        dna = extract_voice_dna(text)
        brand_settings.update_voice(
            archetype=dna.get("archetype", brand_settings.voice.get("archetype", "Creator")),
            tone_attributes=dna.get("extracted_attributes", []),
            writing_style=text,
            cadence=dna["cadence"],
            perspective=dna["perspective"],
            sample_transcript=text,
        )
        await update.message.reply_html("✔ Voice DNA updated.")
    await update.message.reply_html("Profile saved.", reply_markup=_get_edit_keyboard())
    return ConversationHandler.END


async def edit_handle_pillars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, brand_settings, _, _ = _tenant_ctx(update)
    raw = update.message.text.strip()
    pillar_names = [p.strip() for p in raw.split(",") if p.strip()]
    pillars_data = [
        {"id": f"pillar_{i+1}", "name": name, "weight": round(1.0 / len(pillar_names), 2)}
        for i, name in enumerate(pillar_names)
    ]
    brand_settings.update_pillars(pillars_data)
    await update.message.reply_html("✔ Pillars updated.", reply_markup=_get_edit_keyboard())
    return ConversationHandler.END


async def edit_handle_virality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, brand_settings, _, _ = _tenant_ctx(update)
    raw = update.message.text.strip()
    if "|" in raw:
        goal, cta = [p.strip() for p in raw.split("|", 1)]
        brand_settings.update_virality(primary_goal=goal, cta_style=cta)
    else:
        brand_settings.update_virality(primary_goal=raw)
    await update.message.reply_html("✔ Virality &amp; Engagement goal updated.", reply_markup=_get_edit_keyboard())
    return ConversationHandler.END


async def edit_handle_socials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, brand_settings, _, _ = _tenant_ctx(update)
    raw = update.message.text.strip()
    socials = {}
    for part in raw.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            socials[k.strip().lower()] = v.strip()
    brand_settings.update_socials(**socials)
    await update.message.reply_html("✔ Socials updated.", reply_markup=_get_edit_keyboard())
    return ConversationHandler.END


async def edit_handle_accent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, brand_settings, _, _ = _tenant_ctx(update)
    raw = update.message.text.strip()
    curr = brand_settings.theme.get("active_preset", "clean_minimal")
    if raw.lower() == "clear":
        brand_settings.update_theme(curr, custom_accent="")
        await update.message.reply_html("✔ Custom accent cleared.", reply_markup=_get_edit_keyboard())
    else:
        if not raw.startswith("#"):
            raw = f"#{raw}"
        brand_settings.update_theme(curr, custom_accent=raw)
        await update.message.reply_html(f"✔ Custom accent set to <code>{html.escape(raw)}</code>.", reply_markup=_get_edit_keyboard())
    return ConversationHandler.END


async def edit_handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, _, _, qm = _tenant_ctx(update)
    item_id = context.user_data.pop("editing_caption_item_id", None)
    new_caption = update.message.text.strip()
    if not item_id:
        await update.message.reply_html("⚠️ No active post found.")
        return ConversationHandler.END

    updated = qm.update_caption(item_id, new_caption)
    if not updated:
        await update.message.reply_html("⚠️ Post not found in your active brand workspace.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("🚀 Approve & Queue", callback_data=f"approve:{updated.id}")],
        [
            InlineKeyboardButton("🔄 Alternate Hook", callback_data=f"regen:{updated.id}"),
            InlineKeyboardButton("✏️ Edit Caption", callback_data=f"edit_cap:{updated.id}"),
        ],
    ]
    await update.message.reply_html(
        f"✅ <b>Caption Updated!</b>\n<blockquote>{html.escape(updated.caption[:600])}</blockquote>",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END


# ── Free-form Thought, Voice Note & Photo Content Creator ─────────────────────

async def handle_freeform_thought(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return

    uid, slug, brand_settings, brand_dir, _ = _tenant_ctx(update)
    uploads_dir = brand_dir / "output" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    photo_path_str: Optional[str] = None
    audio_path_str: Optional[str] = None

    if update.message.photo:
        if not brand_settings.is_configured:
            await update.message.reply_html("⚠️ Please run /setup first before creating photo posts.")
            return
        photo = update.message.photo[-1]
        file = await photo.get_file()
        dest = uploads_dir / f"photo_{int(time.time())}.jpg"
        await file.download_to_drive(dest)
        photo_path_str = str(dest)
        thought = (update.message.caption or "").strip() or "Visual story & key insight from this moment"
        t_uid = _save_thought_cache(uid, thought, photo_path=photo_path_str)
        keyboard = [
            [
                InlineKeyboardButton("🖼️ Create Static Photo Post", callback_data=f"gen_fmt:static:{t_uid}"),
                InlineKeyboardButton("🎬 Create 9:16 Reel", callback_data=f"gen_fmt:reel:{t_uid}"),
            ],
            [InlineKeyboardButton("🧠 Brainstorm 4 Viral Angles", callback_data=f"brainstorm:{t_uid}")],
        ]
        await update.message.reply_html(
            f"📸 <b>Photo Received!</b>\n<i>Context: \"{html.escape(thought[:120])}\"</i>",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if update.message.voice or update.message.audio:
        status_msg = await update.message.reply_html("🎧 <i>Transcribing your voice note...</i>")
        voice_obj = update.message.voice or update.message.audio
        file = await voice_obj.get_file()
        dest_audio = uploads_dir / f"voice_{int(time.time())}.oga"
        await file.download_to_drive(dest_audio)
        try:
            thought = transcribe_voice_note(dest_audio)
            audio_path_str = str(dest_audio)
        except Exception as e:
            await status_msg.edit_text(f"⚠️ Voice transcription error: <code>{html.escape(str(e)[:200])}</code>", parse_mode="HTML")
            return
    else:
        thought = (update.message.text or "").strip()
        if not thought or thought.startswith("/"):
            return
        status_msg = await update.message.reply_html("💡 <i>Preparing your options...</i>")

    t_uid = _save_thought_cache(uid, thought, audio_path=audio_path_str)
    if not brand_settings.is_configured:
        keyboard = [
            [InlineKeyboardButton("💬 Answer as Question", callback_data=f"ask_uid:{t_uid}")],
            [InlineKeyboardButton("🚀 Run /setup to Create Posts", callback_data="action:start_setup")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("💬 Status Card", callback_data=f"gen_fmt:status:{t_uid}"),
                InlineKeyboardButton("🖼️ Static Post", callback_data=f"gen_fmt:static:{t_uid}"),
            ],
            [
                InlineKeyboardButton("📑 Carousel (5-7 Slides)", callback_data=f"gen_fmt:carousel:{t_uid}"),
                InlineKeyboardButton("🎬 Kinetic Reel (MP4)", callback_data=f"gen_fmt:reel:{t_uid}"),
            ],
            [InlineKeyboardButton("🧠 Brainstorm 4 Viral Angles First", callback_data=f"brainstorm:{t_uid}")],
            [InlineKeyboardButton("💬 Answer as Question", callback_data=f"ask_uid:{t_uid}")],
        ]

    await status_msg.edit_text(
        f"🧠 <b>INPUT CAPTURED</b> (<code>{html.escape(slug)}</code>)\n"
        f"<blockquote>\"{html.escape(thought[:240])}\"</blockquote>\n\n"
        f"<b>Choose an action:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ── Interactive Q&A Advisor (/ask) ────────────────────────────────────────────

async def _reply_with_qa_answer(
    target_message,
    question: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    in_ask_mode: bool = True,
) -> None:
    _, _, brand_settings, _, qm = _tenant_ctx(update)
    status_msg = await target_message.reply_html("💬 <i>Thinking...</i>")
    history = context.user_data.setdefault("qa_history", [])
    try:
        answer = answer_user_query(question, brand=brand_settings, history=history, queue_manager=qm)
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        context.user_data["qa_history"] = history[-8:]

        kb = (
            [[InlineKeyboardButton("✅ Exit Q&A Mode", callback_data="qa:exit")]]
            if in_ask_mode
            else [[InlineKeyboardButton("💬 Ask Follow-up", callback_data="action:ask")]]
        )
        safe_ans = html.escape(answer[:3800])
        await status_msg.edit_text(
            f"💡 <b>AI Advisor</b>\n━━━━━━━━━━━━━━━━━━━━\n{safe_ans}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb),
        )
    except LLMNotConfiguredError as e:
        await status_msg.edit_text(_format_llm_error_message(e), parse_mode="HTML")
    except Exception as e:
        logger.exception("Q&A failed")
        await status_msg.edit_text(f"⚠️ Error: <code>{html.escape(str(e)[:200])}</code>", parse_mode="HTML")


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return ConversationHandler.END

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_html(
            "💬 <b>Q&amp;A Mode Active</b>\n"
            "Ask any question about this tool, your Brand Persona, or Instagram SEO/reach.\n"
            "<i>Type or send a voice note (type /done to exit).</i>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Exit Q&A Mode", callback_data="qa:exit")]]),
        )
        return ASK_MODE

    inline_q = " ".join(context.args).strip() if getattr(context, "args", None) else ""
    if inline_q:
        await _reply_with_qa_answer(update.message, inline_q, update, context, in_ask_mode=True)
        return ASK_MODE

    await update.message.reply_html(
        "💬 <b>Q&amp;A Mode Active</b>\n"
        "Ask me anything about this Personal Brand tool, your active workspace, or Instagram growth!\n"
        "<i>Type or send a voice note (type /done to exit).</i>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Exit Q&A Mode", callback_data="qa:exit")]]),
    )
    return ASK_MODE


async def handle_ask_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _require_active_subscriber(update):
        return ConversationHandler.END

    _, _, _, brand_dir, _ = _tenant_ctx(update)
    if update.message.voice or update.message.audio:
        voice_obj = update.message.voice or update.message.audio
        file = await voice_obj.get_file()
        dest_audio = brand_dir / "output" / f"ask_voice_{int(time.time())}.oga"
        await file.download_to_drive(dest_audio)
        try:
            question = transcribe_voice_note(dest_audio)
        finally:
            dest_audio.unlink(missing_ok=True)
    else:
        question = (update.message.text or "").strip()

    if not question:
        return ASK_MODE

    await _reply_with_qa_answer(update.message, question, update, context, in_ask_mode=True)
    return ASK_MODE


async def ask_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "✅ <b>Exited Q&amp;A Mode.</b> Send any idea, voice note, or photo anytime to create content!"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_html(msg)
    elif update.message:
        await update.message.reply_html(msg)
    return ConversationHandler.END


# ── Interactive Callback Router ───────────────────────────────────────────────

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    caller_uid = _get_uid(update)

    # Admin-only subscriber approval callbacks
    if data.startswith("admin_approve:") or data.startswith("admin_deny:"):
        if not tenant_store.is_admin(caller_uid):
            await query.message.reply_html("🔒 Admin privileges required.")
            return
        action, target_uid = data.split(":", 1)
        if action == "admin_approve":
            tenant_store.approve_user(target_uid, plan="pilot", max_brands=3, daily_limit=15, duration_days=30)
            await query.edit_message_text(f"{query.message.text}\n\n✅ <b>APPROVED (30d Pilot)</b>", parse_mode="HTML")
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text="🎉 <b>Your Pilot Access Is Approved!</b>\n\nTap /setup to configure your first Instagram Brand Persona!",
                    parse_mode="HTML",
                )
            except Exception:
                pass
        else:
            tenant_store.suspend_user(target_uid)
            await query.edit_message_text(f"{query.message.text}\n\n❌ <b>DENIED</b>", parse_mode="HTML")
        return

    if not await _require_active_subscriber(update):
        return

    uid, slug, brand_settings, brand_dir, qm = _tenant_ctx(update)

    if data == "action:overview":
        await cmd_overview(update, context)
    elif data == "action:profile":
        await cmd_profile(update, context)
    elif data == "action:theme":
        await cmd_theme(update, context)
    elif data == "action:bio_seo":
        await cmd_bio_seo(update, context)
    elif data == "action:brands":
        await cmd_brands(update, context)
    elif data == "action:help":
        await cmd_help(update, context)

    elif data.startswith("switch_brand:"):
        target_slug = data.split(":", 1)[1]
        ok, msg = tenant_store.switch_brand(uid, target_slug)
        await query.message.reply_html(f"{'🟢' if ok else '⚠️'} {html.escape(msg)}")
        if ok:
            await cmd_profile(update, context)

    elif data.startswith("ask_uid:"):
        t_uid = data.split(":", 1)[1]
        cached = _load_thought_cache(t_uid, expected_tenant_id=uid)
        if not cached:
            await query.message.reply_html("⚠️ Input expired or unauthorized.")
            return
        await _reply_with_qa_answer(query.message, cached["thought"], update, context, in_ask_mode=False)

    elif data.startswith("set_theme:"):
        preset = data.split(":", 1)[1]
        brand_settings.update_theme(preset)
        await query.message.reply_html(
            f"🎨 Visual theme updated to: <b>{html.escape(preset)}</b> 🟢",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎯 Viral Roadmap", callback_data="action:overview")]]),
        )

    elif data.startswith("brainstorm:"):
        t_uid = data.split(":", 1)[1]
        cached = _load_thought_cache(t_uid, expected_tenant_id=uid)
        if not cached:
            await query.message.reply_html("⚠️ Input expired or unauthorized.")
            return
        if not await _consume_quota_or_notify(update, query.message):
            return
        msg = await query.message.reply_html("🧠 <i>Generating 4 tailored viral angles...</i>")
        try:
            roadmap = generate_content_overview(
                brand_settings, seed_thought=cached["thought"], tenant_id=uid, brand_slug=slug
            )
        except LLMNotConfiguredError as e:
            await msg.edit_text(_format_llm_error_message(e), parse_mode="HTML")
            return
        except Exception as e:
            await msg.edit_text(f"⚠️ Brainstorm failed: <code>{html.escape(str(e)[:200])}</code>", parse_mode="HTML")
            return

        format_emojis = {"status": "💬", "static": "🖼️", "carousel": "📑", "reel": "🎬"}
        parts = [f"🧠 <b>4 VIRAL ANGLES FOR YOUR IDEA:</b>\n<i>\"{html.escape(cached['thought'][:120])}\"</i>\n━━━━━━━━━━━━━━━━━━━━\n"]
        kb = []
        for angle in roadmap.angles:
            emo = format_emojis.get(angle.format, "⚡")
            parts.append(
                f"<b>#{angle.id}. {emo} {html.escape(angle.format_label)}</b>\n"
                f"⚡ <b>Hook:</b> \"{html.escape(angle.hook)}\"\n"
                f"📖 {html.escape(angle.angle_summary)}\n"
            )
            kb.append([
                InlineKeyboardButton(
                    f"{emo} Generate {angle.format.upper()} #{angle.id}",
                    callback_data=f"gen_angle:{angle.uid}",
                )
            ])
        await msg.edit_text("\n".join(parts), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("gen_angle:"):
        a_uid = data.split(":", 1)[1]
        angle = load_angle_from_cache(a_uid, expected_tenant_id=uid)
        if not angle:
            await query.message.reply_html("⚠️ Angle expired or unauthorized. Tap /overview to refresh.")
            return
        if not await _consume_quota_or_notify(update, query.message):
            return
        status_msg = await query.message.reply_html(
            f"🚀 <i>Creating customized <b>{html.escape(angle.format.upper())}</b> for '{html.escape(angle.topic)}'...</i>"
        )
        try:
            item = build_and_render_post(
                topic=angle.topic,
                format_type=angle.format,
                pillar_id=angle.pillar,
                brand=brand_settings,
                hook_override=angle.hook,
                angle_summary=angle.angle_summary,
                primary_search_keyword=angle.primary_search_keyword,
                aeo_question=angle.aeo_question,
                queue_manager=qm,
                output_root=brand_dir / "output",
                tenant_id=uid,
                brand_slug=slug,
            )
            await status_msg.delete()
            await _dispatch_item_to_chat(query.message, item)
        except LLMNotConfiguredError as e:
            await status_msg.edit_text(_format_llm_error_message(e), parse_mode="HTML")
        except Exception as e:
            logger.exception("Angle generation failed")
            await status_msg.edit_text(f"⚠️ Generation failed: <code>{html.escape(str(e)[:200])}</code>", parse_mode="HTML")

    elif data.startswith("gen_fmt:"):
        _, fmt, t_uid = data.split(":", 2)
        cached = _load_thought_cache(t_uid, expected_tenant_id=uid)
        if not cached:
            await query.message.reply_html("⚠️ Input expired or unauthorized.")
            return
        if not await _consume_quota_or_notify(update, query.message):
            return
        status_msg = await query.message.reply_html(
            f"🚀 <i>Crafting personalized <b>{html.escape(fmt.upper())}</b> post...</i>"
        )
        try:
            photo_p = Path(cached["photo_path"]) if cached.get("photo_path") else None
            audio_p = Path(cached["audio_path"]) if cached.get("audio_path") else None
            item = build_and_render_post(
                topic=cached["thought"],
                format_type=fmt,
                brand=brand_settings,
                photo_path=photo_p,
                user_audio_path=audio_p if fmt == "reel" else None,
                queue_manager=qm,
                output_root=brand_dir / "output",
                tenant_id=uid,
                brand_slug=slug,
            )
            await status_msg.delete()
            await _dispatch_item_to_chat(query.message, item)
        except LLMNotConfiguredError as e:
            await status_msg.edit_text(_format_llm_error_message(e), parse_mode="HTML")
        except Exception as e:
            logger.exception("Direct format generation failed")
            await status_msg.edit_text(f"⚠️ Generation failed: <code>{html.escape(str(e)[:200])}</code>", parse_mode="HTML")

    elif data.startswith("approve:"):
        item_id = data.split(":", 1)[1]
        if not qm.get(item_id):
            await query.message.reply_html("⚠️ Post not found in your active brand workspace.")
            return
        qm.update_status(item_id, PostStatus.APPROVED)
        await query.edit_message_text(
            f"{html.escape(query.message.text or '')}\n\n✅ <b>APPROVED &amp; QUEUED</b> 🟢",
            parse_mode="HTML",
        )

    elif data.startswith("reject:"):
        item_id = data.split(":", 1)[1]
        if not qm.get(item_id):
            await query.message.reply_html("⚠️ Post not found in your active brand workspace.")
            return
        qm.update_status(item_id, PostStatus.REJECTED)
        await query.edit_message_text(f"{html.escape(query.message.text or '')}\n\n❌ <b>POST REJECTED</b>", parse_mode="HTML")

    elif data.startswith("regen:"):
        item_id = data.split(":", 1)[1]
        old_item = qm.get(item_id)
        if not old_item:
            await query.message.reply_html("⚠️ Original post not found in your active brand workspace.")
            return
        if not await _consume_quota_or_notify(update, query.message):
            return
        qm.update_status(item_id, PostStatus.REGENERATING)
        status_msg = await query.message.reply_html(
            f"🔄 <i>Rewriting a sharper hook &amp; regenerating {html.escape(old_item.format_type.upper())}...</i>"
        )
        try:
            meta = old_item.meta or {}
            photo_p = Path(meta["photo_path"]) if meta.get("photo_path") else None
            audio_p = Path(meta["user_audio_path"]) if meta.get("user_audio_path") else None
            new_item = build_and_render_post(
                topic=old_item.topic,
                format_type=old_item.format_type,
                pillar_id=old_item.pillar,
                brand=brand_settings,
                hook_override=meta.get("hook_override"),
                angle_summary=meta.get("angle_summary"),
                primary_search_keyword=old_item.primary_search_keyword or meta.get("primary_search_keyword"),
                aeo_question=old_item.aeo_question or meta.get("aeo_question"),
                photo_path=photo_p,
                user_audio_path=audio_p,
                alternate_hook=True,
                queue_manager=qm,
                output_root=brand_dir / "output",
                tenant_id=uid,
                brand_slug=slug,
            )
            await status_msg.delete()
            await _dispatch_item_to_chat(query.message, new_item)
        except LLMNotConfiguredError as e:
            await status_msg.edit_text(_format_llm_error_message(e), parse_mode="HTML")
        except Exception as e:
            logger.exception("Hook regeneration failed")
            await status_msg.edit_text(f"⚠️ Regeneration failed: <code>{html.escape(str(e)[:200])}</code>", parse_mode="HTML")


async def post_init_setup(app):
    """Registers native commands in Telegram UI so the [/] button pops up the menu."""
    commands = [
        BotCommand("start", "🏠 Home dashboard & active brand"),
        BotCommand("brands", "🏷️ Create & switch Instagram brands"),
        BotCommand("setup", "🚀 Onboarding (niche, audience, voice, pillars)"),
        BotCommand("overview", "🎯 4-format viral content roadmap"),
        BotCommand("profile", "👤 View & edit active Brand Persona"),
        BotCommand("bio_seo", "🔍 Optimize Instagram Display Name & Bio SEO"),
        BotCommand("theme", "🎨 Switch visual theme (6 presets + accent)"),
        BotCommand("ask", "💬 Ask AI advisor about tool or brand strategy"),
        BotCommand("register", "🆔 Register User ID for pilot access"),
        BotCommand("activate", "🔑 Redeem pilot license key"),
        BotCommand("help", "📖 Command guide"),
    ]
    try:
        await app.bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Could not register Telegram commands: {e}")


def create_bot_app():
    """Builds and wires the multi-tenant Telegram Application."""
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init_setup).build()

    onboarding_conv = ConversationHandler(
        entry_points=[
            CommandHandler("setup", onboarding_start),
            CallbackQueryHandler(onboarding_start, pattern="^action:start_setup$"),
        ],
        states={
            STATE_NAME_HANDLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_name_handle)],
            STATE_AVATAR: [MessageHandler(filters.PHOTO | filters.TEXT, onboarding_avatar)],
            STATE_GENRE_AUDIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_genre_audience)],
            STATE_TAGLINE_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_tagline_bio)],
            STATE_VOICE_STYLE: [
                MessageHandler(filters.VOICE | filters.AUDIO, onboarding_voice_style),
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_voice_style),
            ],
            STATE_PILLARS_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_pillars_goal)],
            STATE_SOCIALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_socials)],
        },
        fallbacks=[CommandHandler("cancel", onboarding_cancel)],
        per_message=False,
    )

    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_start, pattern="^(edit_start|edit_cap):")],
        states={
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_name)],
            EDIT_AVATAR: [MessageHandler(filters.PHOTO, edit_handle_avatar)],
            EDIT_AUDIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_audience)],
            EDIT_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_bio)],
            EDIT_VOICE: [
                MessageHandler(filters.VOICE | filters.AUDIO, edit_handle_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_voice),
            ],
            EDIT_PILLARS: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_pillars)],
            EDIT_VIRALITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_virality)],
            EDIT_SOCIALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_socials)],
            EDIT_ACCENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_accent)],
            EDIT_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_caption)],
            ADD_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_handle_add_brand)],
        },
        fallbacks=[CommandHandler("cancel", onboarding_cancel)],
        per_message=False,
    )

    ask_conv = ConversationHandler(
        entry_points=[
            CommandHandler("ask", cmd_ask),
            CallbackQueryHandler(cmd_ask, pattern="^action:ask$"),
        ],
        states={
            ASK_MODE: [
                MessageHandler(filters.VOICE | filters.AUDIO, handle_ask_message),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ask_message),
                CallbackQueryHandler(ask_done, pattern="^qa:exit$"),
            ],
        },
        fallbacks=[
            CommandHandler("done", ask_done),
            CommandHandler("cancel", ask_done),
            CallbackQueryHandler(ask_done, pattern="^qa:exit$"),
        ],
        per_message=False,
    )

    app.add_handler(onboarding_conv)
    app.add_handler(edit_conv)
    app.add_handler(ask_conv)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("activate", cmd_activate))
    app.add_handler(CommandHandler("gen_key", cmd_gen_key))
    app.add_handler(CommandHandler("brands", cmd_brands))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("overview", cmd_overview))
    app.add_handler(CommandHandler("ideas", cmd_overview))
    app.add_handler(CommandHandler("bio_seo", cmd_bio_seo))
    app.add_handler(CommandHandler("theme", cmd_theme))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_freeform_thought))
    app.add_handler(MessageHandler(filters.PHOTO, handle_freeform_thought))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_freeform_thought))

    return app


if __name__ == "__main__":
    print("🤖 Starting Multi-Tenant Personal Brand Telegram Bot...")
    app = create_bot_app()
    app.run_polling()
