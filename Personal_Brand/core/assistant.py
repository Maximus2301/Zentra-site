"""
Zero-Cost Conversational Q&A Assistant for Personal Brand Engine.
Answers user queries strictly scoped to the caller's active Brand Persona and Queue.
"""
from __future__ import annotations

from typing import Optional

from ..config.settings import BrandSettings, settings
from ..hitl.queue_manager import QueueManager
from .llm_client import build_brand_context_block, call_text_llm

TOOL_MANUAL_DIGEST = """=== PERSONAL BRAND CONTENT CREATOR — TOOL GUIDE ===
Supported Instagram Formats ($0 media generation):
1. Status / Quote Card (4:5 PNG): Tweet-style takes, bold quotes, contrarian thoughts.
2. Static Single-Image Post (4:5 PNG): Infographic checklists, Myth vs Fact comparisons, Stat spotlights, OR Photo Overlay (send any photo in Telegram and tap [Create Static Photo Post]).
3. Authority Carousel (5-7 slides, 4:5 PNG): High-save educational decks with hook, framework, tactics, checklist & CTA.
4. Kinetic Reel (1080x1920 MP4 + teleprompter.txt): FFmpeg zoompan motion + free neural voiceover (edge-tts) or user's Telegram voice note.

Available Telegram Commands:
- /start: Home dashboard & status.
- /brands: Create or switch between multiple Instagram brand accounts/personas.
- /setup: 7-step Brand Persona wizard (Name/Handle, Photo, Genre & Audience, Tagline/Bio, Voice DNA via Whisper, Pillars & Virality Goal, Socials).
- /overview (or /ideas): Generates 4 search-grounded angles across all 4 formats using live autocomplete signals.
- /profile: View Brand DNA & edit Name, Photo, Genre/Audience, Bio, Voice DNA, Pillars, Virality Goal, Socials, Theme.
- /bio_seo: Generates an Instagram Search-weighted Display Name (Name | Niche) and <=150-char Bio.
- /theme: Switch between 6 visual themes (Clean Minimal, Warm Creator, Bold Viral, Dark Terminal, Editorial Luxury, Clinical Serene) or set custom accent hex.
- /ask [question]: Ask anything about using this tool or your personal brand strategy (type /done to exit Q&A mode).
- Freeform Input: Send any text idea, voice note, or photo directly in chat to pick a format button, brainstorm 4 angles, or tap [Answer as Question].

Quality & Reach Engine:
- 5-Axis Critic scores every post out of 100 across: Hook Power (1-10), Persona Fit (1-10), Meta Viral Signals (1-10), SEO (1-10), and AEO (1-10).
- Each generated post exports `aeo_article.md` (with FAQPage JSON-LD) and suggests a Pinned Comment & Instagram ALT text.
- Note on Publishing: Approving a post stages files inside the brand's `output/approved/` folder (automated Meta Graph API posting is not yet enabled; post manually using the rendered media, caption, ALT text, and pinned comment).
"""


def _recent_queue_digest(queue_manager: Optional[QueueManager] = None, limit: int = 5) -> str:
    """Builds a compact tenant-scoped summary of recent posts for context-aware Q&A."""
    if queue_manager is None:
        return "Recent Posts: None generated in this workspace yet."
    try:
        items = queue_manager.list_items()[:limit]
        if not items:
            return "Recent Posts: None generated in this workspace yet."
        lines = []
        for it in items:
            c = it.critic or {}
            score = c.get("overall_score", "-")
            axes = (
                f"Hook={c.get('hook_score', '-')}/10, Fit={c.get('persona_alignment_score', '-')}/10, "
                f"Meta={c.get('virality_engagement_score', '-')}/10, SEO={c.get('seo_discoverability_score', '-')}/10, "
                f"AEO={c.get('aeo_citation_score', '-')}/10"
                if c
                else "No critic scores"
            )
            impr = "; ".join(c.get("improvements", [])[:2])
            lines.append(
                f"  - [{it.format_type.upper()}] '{it.topic}' | Status={it.status.value} | "
                f"Overall={score}/100 ({axes}) | Keyword='{it.primary_search_keyword or ''}'"
                + (f" | Notes: {impr}" if impr else "")
            )
        return "Recent Generated Posts (Active Brand Workspace Only):\n" + "\n".join(lines)
    except Exception:
        return "Recent Posts: Unavailable."


def answer_user_query(
    question: str,
    brand: Optional[BrandSettings] = None,
    history: Optional[list[dict[str, str]]] = None,
    queue_manager: Optional[QueueManager] = None,
) -> str:
    """Answers a user query grounded in the tool manual, caller's active persona, and scoped queue."""
    b = brand or settings
    brand_context = build_brand_context_block(b)
    queue_context = _recent_queue_digest(queue_manager)

    system_instruction = f"""You are the Helpful AI Advisor & Brand Strategist built into the Personal Brand Content Creator Telegram bot.

{TOOL_MANUAL_DIGEST}

{brand_context}

{queue_context}

Response Guidelines:
1. Be concise, practical, and directly answer the user's question (ideal for reading on Telegram mobile).
2. Quote ONLY exact commands and button labels from the Tool Guide above.
3. Tailor strategy, hooks, SEO, AEO, or Instagram reach advice specifically to their active Genre, Target Audience, and Pillars.
4. Never fabricate features that don't exist.
5. Use clean plain text with simple bullet points (avoid heavy markdown tables or raw HTML tags).
"""

    return call_text_llm(
        prompt=question.strip(),
        system_instruction=system_instruction,
        history=history,
        temperature=0.55,
    )
