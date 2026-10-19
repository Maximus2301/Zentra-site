"""Configuration and account profile loaders."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Load root .env
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

CONFIG_DIR = Path(__file__).resolve().parent
ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR = OUTPUT_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_BUCKET_NAME = os.getenv("SESSIONS_BUCKET_NAME", "zentra-creator-sessions-546102264289")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

THEME_PRESETS: dict[str, dict[str, Any]] = {
    "investigative_legal": {
        "theme": "investigative_legal",
        "theme_label": "Investigative Legal High-Contrast",
        "channel_icon": "⚖️",
        "iconography_style": "line",
        "primary_color": "#E63946",
        "accent_color": "#38BDF8",
        "bg_color": "#0B0F19",
        "text_color": "#F8FAFC",
        "color_palette": ["#0B0F19", "#E63946", "#38BDF8", "#F1FAEE", "#334155"],
        "headline_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "font_weight": "bold",
        "letter_spacing": "tracked",
        "description": "High-contrast authoritative palette with stark crimson alert borders and sky blue statutory highlights."
    },
    "fintech_mint_gold": {
        "theme": "fintech_mint_gold",
        "theme_label": "FinTech Mint & Wealth Gold",
        "channel_icon": "💰",
        "iconography_style": "glassmorphism",
        "primary_color": "#00B4D8",
        "accent_color": "#C9A22A",
        "bg_color": "#0B132B",
        "text_color": "#FFFFFF",
        "color_palette": ["#0B132B", "#00B4D8", "#C9A22A", "#90E0EF", "#1C2541"],
        "headline_font": "Space Grotesk",
        "body_font": "Inter",
        "font_weight": "bold",
        "letter_spacing": "normal",
        "description": "Sleek wealth aesthetic blending modern deep navy, champagne gold metrics, and mint automation accents."
    },
    "cyberpunk_tech_glow": {
        "theme": "cyberpunk_tech_glow",
        "theme_label": "Cyberpunk / AI Tech Glow",
        "channel_icon": "🚀",
        "iconography_style": "tech_terminal",
        "primary_color": "#8B5CF6",
        "accent_color": "#06B6D4",
        "bg_color": "#08080C",
        "text_color": "#F1F5F9",
        "color_palette": ["#08080C", "#8B5CF6", "#06B6D4", "#EC4899", "#1E1E2F"],
        "headline_font": "Syne",
        "body_font": "JetBrains Mono",
        "font_weight": "bold",
        "letter_spacing": "tracked",
        "description": "Ultra-modern avant-garde tech aesthetic featuring neon violet-cyan glows, monospace details, and deep obsidian surfaces."
    },
    "editorial_luxury": {
        "theme": "editorial_luxury",
        "theme_label": "Editorial Serif & Executive Luxury",
        "channel_icon": "🏛️",
        "iconography_style": "editorial_serif",
        "primary_color": "#D4AF37",
        "accent_color": "#E2E8F0",
        "bg_color": "#121212",
        "text_color": "#FFFFFF",
        "color_palette": ["#121212", "#D4AF37", "#E2E8F0", "#3E2723", "#F5F5F0"],
        "headline_font": "Playfair Display",
        "body_font": "Lora",
        "font_weight": "bold",
        "letter_spacing": "tracked",
        "description": "Refined magazine typography with warm gold flourishes, platinum subheadings, and deep matte luxury dark tones."
    },
    "vibrant_pop": {
        "theme": "vibrant_pop",
        "theme_label": "Vibrant Pop & Viral Punch",
        "channel_icon": "🔥",
        "iconography_style": "vibrant_emoji",
        "primary_color": "#FF007F",
        "accent_color": "#FFB703",
        "bg_color": "#0D0D15",
        "text_color": "#FFFFFF",
        "color_palette": ["#0D0D15", "#FF007F", "#FFB703", "#7928CA", "#00DFD8"],
        "headline_font": "Bebas Neue",
        "body_font": "Roboto",
        "font_weight": "bold",
        "letter_spacing": "tracked",
        "description": "High-energy punch with vivid electric magenta, sunburst amber, and condensed bold headline typography."
    },
    "nordic_minimal": {
        "theme": "nordic_minimal",
        "theme_label": "Nordic Minimalist & Calm",
        "channel_icon": "💡",
        "iconography_style": "line",
        "primary_color": "#10B981",
        "accent_color": "#64748B",
        "bg_color": "#0F172A",
        "text_color": "#F8FAFC",
        "color_palette": ["#0F172A", "#10B981", "#64748B", "#E2E8F0", "#1E293B"],
        "headline_font": "Outfit",
        "body_font": "Inter",
        "font_weight": "semibold",
        "letter_spacing": "normal",
        "description": "Clean, spacious Scandinavian balance featuring tranquil emerald sage, cool slate grey, and friendly modern geometry."
    }
}


def load_all_accounts() -> list[dict[str, Any]]:
    """Loads all configured account dossiers from accounts.json."""
    if not ACCOUNTS_FILE.exists():
        raise FileNotFoundError(f"Accounts configuration file not found at {ACCOUNTS_FILE}")
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("accounts", [])


def save_all_accounts(accounts: list[dict[str, Any]]) -> None:
    """Saves updated accounts list back to accounts.json."""
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"accounts": accounts}, f, indent=2, ensure_ascii=False)


def get_account_by_id(account_id: str) -> dict[str, Any] | None:
    """Finds an account dossier by its ID."""
    accounts = load_all_accounts()
    for acc in accounts:
        if acc.get("account_id") == account_id:
            return acc
    return None


def update_account_connections(account_id: str, connections_data: dict[str, Any]) -> dict[str, Any] | None:
    """Updates and persists linked accounts (Instagram & YouTube) for an account."""
    accounts = load_all_accounts()
    target = None
    for acc in accounts:
        if acc.get("account_id") == account_id:
            curr_links = acc.setdefault("linked_accounts", {})
            if "instagram" in connections_data:
                curr_links.setdefault("instagram", {}).update(connections_data["instagram"])
            if "youtube" in connections_data:
                curr_links.setdefault("youtube", {}).update(connections_data["youtube"])
            target = acc
            break
    if target:
        save_all_accounts(accounts)
    return target


def update_account_branding(account_id: str, branding_data: dict[str, Any]) -> dict[str, Any] | None:
    """Updates and persists visual identity and color palette for an account."""
    accounts = load_all_accounts()
    target = None
    for acc in accounts:
        if acc.get("account_id") == account_id:
            curr_vi = acc.setdefault("visual_identity", {})
            curr_vi.update(branding_data)
            # Sync root color_palette if provided
            if "color_palette" in branding_data:
                acc["color_palette"] = branding_data["color_palette"]
            target = acc
            break
    if target:
        save_all_accounts(accounts)
    return target
