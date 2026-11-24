"""
Telegram Mobile HITL (Human-on-the-Loop) Review Gate.
Dispatches slide decks and caption previews to Telegram with interactive action buttons:
[🚀 Approve & Queue] | [🔄 Alternate Hook] | [✏️ Edit Caption]
"""
from __future__ import annotations

import html
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from .queue_manager import QueueManager, PostStatus, QueuedItem
from ..config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("personal_brand.telegram_gate")


def format_review_card_text(item: QueuedItem) -> str:
    """Formats the Telegram review card with 5-axis SEO/AEO/Meta scores, ALT text, and pinned comment."""
    format_labels = {
        "status": "Status / Quote Card (4:5)",
        "static": "Static Single-Image Post (4:5)",
        "carousel": f"{len(item.slide_paths)}-Slide Authority Carousel (4:5)",
        "reel": "Kinetic 9:16 Vertical Reel (MP4)",
    }
    fmt_label = format_labels.get(item.format_type, item.format_type.upper())
    critic = item.critic or {}
    score_line = ""
    if critic:
        score_line = (
            f"📊 <b>Reach & Search Score:</b> {critic.get('overall_score', 80)}/100\n"
            f"   Hook {critic.get('hook_score', 8)} • Fit {critic.get('persona_alignment_score', 8)} • "
            f"Meta {critic.get('virality_engagement_score', 8)} • SEO {critic.get('seo_discoverability_score', 8)} • "
            f"AEO {critic.get('aeo_citation_score', 8)}\n"
        )
    kw_line = (
        f"🔍 <b>SEO Keyword:</b> <code>{html.escape(item.primary_search_keyword)}</code>\n"
        if item.primary_search_keyword
        else ""
    )
    alt_line = (
        f"\n🏷️ <b>Instagram ALT Text:</b>\n<code>{html.escape(item.alt_text[:220])}</code>\n"
        if item.alt_text
        else ""
    )
    pinned_line = (
        f"\n💬 <b>Suggested Pinned Comment:</b>\n<i>{html.escape(item.pinned_comment)}</i>\n"
        if item.pinned_comment
        else ""
    )

    return (
        f"🎯 <b>PERSONAL BRAND POST REVIEW</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Topic:</b> {html.escape(item.topic)}\n"
        f"🖼️ <b>Format:</b> {html.escape(fmt_label)}\n"
        f"{kw_line}"
        f"{score_line}"
        f"⚡ <b>Status:</b> <code>{html.escape(item.status.value)}</code>\n\n"
        f"📝 <b>Proposed Caption:</b>\n"
        f"<blockquote>{html.escape(item.caption[:500])}</blockquote>"
        f"{alt_line}"
        f"{pinned_line}\n"
        f"<i>Tap below to approve, test an alternate hook, or edit caption:</i>"
    )


class TelegramHITLGate:
    """Manages mobile push notifications and interactive approval gates via Telegram."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        queue_manager: Optional[QueueManager] = None,
    ):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.queue = queue_manager or QueueManager()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram Bot Token or Chat ID is missing in configuration.")

    def verify_bot(self) -> Dict[str, Any]:
        """Checks bot connectivity and identity."""
        r = requests.get(f"{self.base_url}/getMe", timeout=10)
        r.raise_for_status()
        return r.json().get("result", {})

    def send_video(self, video_path: Path, caption: Optional[str] = None) -> bool:
        """Sends a rendered 9:16 MP4 Reel video to Telegram."""
        if not video_path.exists():
            return False
        try:
            with open(video_path, "rb") as vf:
                data = {"chat_id": self.chat_id, "supports_streaming": True}
                if caption:
                    data["caption"] = caption[:1024]
                res = requests.post(
                    f"{self.base_url}/sendVideo",
                    data=data,
                    files={"video": vf},
                    timeout=60,
                )
                res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send video to Telegram: {e}")
            return False

    def send_media_group(self, image_paths: List[Path]) -> bool:
        """Sends 1 photo (sendPhoto) or 2-10 slides as a grouped multi-image album (sendMediaGroup)."""
        if not image_paths:
            return False

        if len(image_paths) == 1:
            try:
                with open(image_paths[0], "rb") as fh:
                    res = requests.post(
                        f"{self.base_url}/sendPhoto",
                        data={"chat_id": self.chat_id},
                        files={"photo": fh},
                        timeout=30,
                    )
                    res.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Failed to send photo to Telegram: {e}")
                return False

        media_payload = []
        files = {}
        file_handles = []

        try:
            for idx, p in enumerate(image_paths[:10]):
                field_name = f"photo_{idx}"
                media_payload.append({
                    "type": "photo",
                    "media": f"attach://{field_name}",
                })
                fh = open(p, "rb")
                file_handles.append(fh)
                files[field_name] = fh

            data = {
                "chat_id": self.chat_id,
                "media": json.dumps(media_payload),
            }

            res = requests.post(f"{self.base_url}/sendMediaGroup", data=data, files=files, timeout=30)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send media group to Telegram: {e}")
            return False
        finally:
            for fh in file_handles:
                try:
                    fh.close()
                except Exception:
                    pass

    def send_review_card(self, item: QueuedItem) -> Optional[int]:
        """
        Sends formatted post review card with SEO/AEO/Meta scores & interactive approval buttons.
        Returns the Telegram message_id.
        """
        card_text = format_review_card_text(item)

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "🚀 Approve & Queue",
                        "callback_data": f"approve:{item.id}",
                    }
                ],
                [
                    {
                        "text": "🔄 Alternate Hook",
                        "callback_data": f"regen:{item.id}",
                    },
                    {
                        "text": "✏️ Edit Caption",
                        "callback_data": f"edit_cap:{item.id}",
                    },
                    {
                        "text": "❌ Reject",
                        "callback_data": f"reject:{item.id}",
                    },
                ],
            ]
        }

        payload = {
            "chat_id": self.chat_id,
            "text": card_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard),
        }

        try:
            res = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=15)
            res.raise_for_status()
            msg_data = res.json().get("result", {})
            msg_id = msg_data.get("message_id")
            if msg_id:
                item.meta["telegram_message_id"] = msg_id
                self.queue.enqueue(item)
            return msg_id
        except Exception as e:
            logger.error(f"Failed to send review card to Telegram: {e}")
            return None

    def dispatch_for_review(self, item: QueuedItem) -> bool:
        """
        High-level dispatcher: sends rendered video/image/album + interactive review card.
        """
        self.queue.enqueue(item)

        if item.format_type == "reel" and item.video_path and Path(item.video_path).exists():
            self.send_video(Path(item.video_path), caption=f"🎬 {item.topic}")
        else:
            image_paths = [Path(p) for p in item.slide_paths if Path(p).exists()]
            if image_paths:
                self.send_media_group(image_paths)

        msg_id = self.send_review_card(item)
        return msg_id is not None

    def poll_for_decision(self, item_id: str, max_wait_seconds: int = 60, poll_interval: int = 2) -> Optional[PostStatus]:
        """
        Listens for the founder's interactive button tap on Telegram.
        Updates queue item state when tapped.
        """
        start_time = time.time()
        last_update_id = 0

        # Get initial update offset
        try:
            updates = requests.get(f"{self.base_url}/getUpdates?offset=-1", timeout=10).json().get("result", [])
            if updates:
                last_update_id = updates[-1]["update_id"] + 1
        except Exception:
            pass

        logger.info(f"Listening for Telegram interaction on item {item_id} (timeout: {max_wait_seconds}s)...")

        while time.time() - start_time < max_wait_seconds:
            try:
                res = requests.get(f"{self.base_url}/getUpdates?offset={last_update_id}&timeout=3", timeout=10)
                updates = res.json().get("result", [])

                for update in updates:
                    last_update_id = update["update_id"] + 1

                    # Check for callback query from inline button
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        cb_data = cb.get("data", "")
                        cb_id = cb.get("id")

                        if ":" in cb_data:
                            action, target_id = cb_data.split(":", 1)
                            if target_id == item_id:
                                # Acknowledge tap
                                status_map = {
                                    "approve": (PostStatus.APPROVED, "✅ Post Approved & Queued!"),
                                    "regen": (PostStatus.REGENERATING, "🔄 Regenerating alternate hook..."),
                                    "reject": (PostStatus.REJECTED, "❌ Post Rejected."),
                                }
                                new_status, ack_text = status_map.get(
                                    action, (PostStatus.PENDING_REVIEW, "Action received")
                                )

                                # Answer callback
                                requests.post(
                                    f"{self.base_url}/answerCallbackQuery",
                                    json={"callback_query_id": cb_id, "text": ack_text},
                                    timeout=5,
                                )

                                # Update queue
                                updated_item = self.queue.update_status(item_id, new_status)

                                # Update Telegram card to reflect decision
                                if "message" in cb:
                                    orig_msg = cb["message"]
                                    orig_text = orig_msg.get("text", "")
                                    edited_text = (
                                        f"{orig_text}\n\n"
                                        f"<b>DECISION RECORDED:</b> {new_status.value} 🟢\n"
                                        f"<i>Processed by Personal Brand HITL Gate</i>"
                                    )
                                    requests.post(
                                        f"{self.base_url}/editMessageText",
                                        json={
                                            "chat_id": self.chat_id,
                                            "message_id": orig_msg["message_id"],
                                            "text": edited_text,
                                            "parse_mode": "HTML",
                                        },
                                        timeout=5,
                                    )

                                logger.info(f"Recorded decision {new_status.value} for {item_id}")
                                return new_status
            except Exception as e:
                logger.warning(f"Polling loop encountered error: {e}")

            time.sleep(poll_interval)

        logger.info(f"Decision polling timed out after {max_wait_seconds}s. Item remains PENDING_REVIEW.")
        return None
