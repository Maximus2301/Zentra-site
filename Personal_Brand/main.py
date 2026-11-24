"""
Personal Brand Engine — Unified Multi-Format CLI Orchestrator.
Generates, renders, critiques, and dispatches Instagram Status Cards, Static Posts,
Carousels, and Kinetic Reels to the Telegram HITL review gate.

Usage:
  python -m Personal_Brand.main --format carousel --topic "3 Habits That Doubled My Focus"
  python -m Personal_Brand.main --format status --topic "Most Morning Routines Are Procrastination"
  python -m Personal_Brand.main --format static --topic "My 5-Minute Meal Prep" --photo path/to/img.jpg
  python -m Personal_Brand.main --format reel --topic "How I Budget My Salary" --no-telegram
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from Personal_Brand.config.settings import get_brand_settings
from Personal_Brand.core.pipeline import build_and_render_post
from Personal_Brand.hitl.queue_manager import QueueManager, QueuedItem
from Personal_Brand.hitl.telegram_gate import TelegramHITLGate


def run_pipeline(
    topic: str,
    format_type: str = "carousel",
    pillar_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    photo_path: Optional[str] = None,
    send_telegram: bool = True,
    wait_for_decision: bool = False,
    wait_timeout: int = 120,
) -> QueuedItem:
    """Executes the full persona-driven generation -> rendering -> critic -> HITL pipeline."""
    brand = get_brand_settings(brand_id)
    queue = QueueManager()

    print(f"\n🚀 [Personal Brand Engine] Starting '{format_type.upper()}' Pipeline:")
    print(f"   ▶ Topic: '{topic}'")
    print(f"   ▶ Creator: {brand.name or 'Creator'} ({brand.handle or '@creator'})")
    print(f"   ▶ Genre: {brand.creator.get('genre') or 'Unconfigured'}\n")

    item = build_and_render_post(
        topic=topic,
        format_type=format_type,
        pillar_id=pillar_id,
        brand=brand,
        photo_path=Path(photo_path) if photo_path else None,
        queue_manager=queue,
    )

    print(f"   ✔ Generated & Rendered ID: {item.id}")
    if item.video_path:
        print(f"   ✔ Video MP4: {item.video_path}")
    else:
        print(f"   ✔ Images: {len(item.slide_paths)} rendered file(s)")
    if item.critic:
        print(
            f"   ✔ Reach & Search Critic: {item.critic.get('overall_score')}/100 "
            f"(Hook {item.critic.get('hook_score')}/10 | Fit {item.critic.get('persona_alignment_score')}/10 | "
            f"Meta {item.critic.get('virality_engagement_score')}/10 | SEO {item.critic.get('seo_discoverability_score')}/10 | "
            f"AEO {item.critic.get('aeo_citation_score')}/10)"
        )

    if send_telegram:
        gate = TelegramHITLGate(queue_manager=queue)
        print("\n📲 Dispatching asset and interactive review card to Telegram...")
        success = gate.dispatch_for_review(item)
        if success:
            print("   ✔ Successfully pushed to Telegram!")
            if wait_for_decision:
                print(f"\n⏳ Waiting up to {wait_timeout}s for your interactive tap on Telegram...")
                decision = gate.poll_for_decision(item_id=item.id, max_wait_seconds=wait_timeout)
                print(f"   🎉 Decision: {decision.value if decision else 'Timed out (PENDING_REVIEW)'}")
        else:
            print("   ⚠️ Could not push to Telegram. Check bot credentials or network connectivity.")
    else:
        print("\n⏩ Telegram dispatch skipped (--no-telegram flag set).")

    print("\n✅ Pipeline complete!")
    return item


def main():
    parser = argparse.ArgumentParser(description="Personal Brand Instagram Pipeline")
    parser.add_argument("--brand", type=str, default=None, help="Brand profile directory or ID (e.g. 'drhimanibharti')")
    parser.add_argument("--format", type=str, default="carousel", choices=["status", "static", "carousel", "reel"], help="Instagram format")
    parser.add_argument("--topic", type=str, required=True, help="Topic, thought, or prompt")
    parser.add_argument("--pillar", type=str, default=None, help="Content pillar ID")
    parser.add_argument("--photo", type=str, default=None, help="Optional photo path for static overlay or reel background")
    parser.add_argument("--no-telegram", action="store_true", help="Skip sending to Telegram")
    parser.add_argument("--wait", action="store_true", help="Wait for mobile approval decision via Telegram")
    parser.add_argument("--timeout", type=int, default=120, help="Wait timeout in seconds")

    args = parser.parse_args()

    run_pipeline(
        topic=args.topic,
        format_type=args.format,
        pillar_id=args.pillar,
        brand_id=args.brand,
        photo_path=args.photo,
        send_telegram=not args.no_telegram,
        wait_for_decision=args.wait,
        wait_timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
