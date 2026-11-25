"""
Settings and configuration loader for Personal Brand Engine.
Loads environment variables and parses config/brand_profile.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Root project paths
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent

# Load environment variables from workspace root .env if present
load_dotenv(WORKSPACE_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env")

BRAND_PROFILE_PATH = CURRENT_DIR / "brand_profile.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# API Keys & Credentials (Zero-cost / free-tier text LLM providers)
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

# Optional Instagram Direct Publishing Credentials
INSTAGRAM_ACCESS_TOKEN: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ACCOUNT_ID: str = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")


def load_brand_profile(path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads and returns the brand profile JSON configuration."""
    target_path = path or BRAND_PROFILE_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Brand profile not found at {target_path}")
    with open(target_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_brand_profile(data: Dict[str, Any], path: Optional[Path] = None) -> None:
    """Saves updated brand profile dictionary to JSON and syncs to cloud memory if enabled."""
    target_path = path or BRAND_PROFILE_PATH
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        from ..core import cloud_memory
        cloud_memory.sync_file(target_path)
    except Exception:
        pass


class BrandSettings:
    """Convenience wrapper for accessing personal brand configuration."""

    def __init__(self, profile_path: Optional[Path] = None):
        self._profile_path = profile_path or BRAND_PROFILE_PATH
        self.reload()

    def reload(self) -> None:
        """Reloads profile configuration from disk."""
        self._raw_profile = load_brand_profile(self._profile_path)
        self.creator = self._raw_profile.get("creator", {})
        self.target_audience = self._raw_profile.get("target_audience", {})
        self.voice = self._raw_profile.get("voice_and_tone", {})
        self.virality_strategy = self._raw_profile.get("virality_strategy", {})
        self.pillars = self._raw_profile.get("content_pillars", [])
        self.theme = self._raw_profile.get("visual_theme", {})
        self.carousel_specs = self._raw_profile.get("carousel_specs", {})
        self.hitl = self._raw_profile.get("hitl_preferences", {})

    def update_creator(self, **kwargs) -> None:
        """Updates creator identity fields and persists."""
        self.creator.update(kwargs)
        if self.creator.get("name") and self.creator.get("handle"):
            self.creator["is_configured"] = True
        self._raw_profile["creator"] = self.creator
        save_brand_profile(self._raw_profile, self._profile_path)

    def update_audience(self, **kwargs) -> None:
        """Updates target audience fields and persists."""
        self.target_audience.update(kwargs)
        self._raw_profile["target_audience"] = self.target_audience
        save_brand_profile(self._raw_profile, self._profile_path)

    def update_voice(self, **kwargs) -> None:
        """Updates voice and tone fields and persists."""
        self.voice.update(kwargs)
        self._raw_profile["voice_and_tone"] = self.voice
        save_brand_profile(self._raw_profile, self._profile_path)

    def update_virality(self, **kwargs) -> None:
        """Updates virality & engagement strategy fields and persists."""
        self.virality_strategy.update(kwargs)
        self._raw_profile["virality_strategy"] = self.virality_strategy
        save_brand_profile(self._raw_profile, self._profile_path)

    def update_theme(self, active_preset: str, custom_accent: Optional[str] = None) -> None:
        """Sets active visual preset (and optional custom accent hex) and persists."""
        self.theme["active_preset"] = active_preset
        if custom_accent is not None:
            self.theme["custom_accent"] = custom_accent
        self._raw_profile["visual_theme"] = self.theme
        save_brand_profile(self._raw_profile, self._profile_path)

    def update_socials(self, **kwargs) -> None:
        """Updates connected social handles."""
        socials = self.creator.setdefault("socials", {})
        socials.update(kwargs)
        self.update_creator(socials=socials)

    def update_pillars(self, pillars: list) -> None:
        """Updates authority pillars."""
        self.pillars = pillars
        self._raw_profile["content_pillars"] = pillars
        save_brand_profile(self._raw_profile, self._profile_path)

    @property
    def is_configured(self) -> bool:
        """Returns True if the creator has completed onboarding."""
        return bool(self.creator.get("is_configured") and self.creator.get("name") and self.creator.get("handle"))

    @property
    def handle(self) -> str:
        return self.creator.get("handle", "")

    @property
    def name(self) -> str:
        return self.creator.get("name", "")

    @property
    def active_palette(self) -> Dict[str, str]:
        active_name = self.theme.get("active_preset", "clean_minimal")
        presets = self.theme.get("presets", {})
        palette = dict(presets.get(active_name) or next(iter(presets.values()), {}))
        custom_accent = (self.theme.get("custom_accent") or "").strip()
        if custom_accent.startswith("#") and len(custom_accent) in (4, 7):
            palette["accent"] = custom_accent
        return palette

    @property
    def font_paths(self) -> Dict[str, str]:
        return self.theme.get("fonts", {})


def get_brand_settings(brand_identifier: Optional[str | Path] = None) -> BrandSettings:
    """Resolves and returns a BrandSettings instance for a named brand or profile path."""
    if not brand_identifier:
        return BrandSettings()

    target_path = Path(brand_identifier)
    if target_path.is_file():
        return BrandSettings(target_path)
    if target_path.is_dir() and (target_path / "brand_profile.json").is_file():
        return BrandSettings(target_path / "brand_profile.json")

    # Check relative to PROJECT_ROOT (e.g. "drhimanibharti")
    sub_path = PROJECT_ROOT / brand_identifier / "brand_profile.json"
    if sub_path.is_file():
        return BrandSettings(sub_path)

    # Check relative to CURRENT_DIR
    cfg_path = CURRENT_DIR / f"{brand_identifier}.json"
    if cfg_path.is_file():
        return BrandSettings(cfg_path)

    return BrandSettings(Path(brand_identifier))


# Default instance
settings = BrandSettings()
