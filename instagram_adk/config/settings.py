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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""


def load_all_accounts() -> list[dict[str, Any]]:
    """Loads all configured account dossiers from accounts.json."""
    if not ACCOUNTS_FILE.exists():
        raise FileNotFoundError(f"Accounts configuration file not found at {ACCOUNTS_FILE}")
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("accounts", [])


def get_account_by_id(account_id: str) -> dict[str, Any] | None:
    """Finds an account dossier by its ID."""
    accounts = load_all_accounts()
    for acc in accounts:
        if acc.get("account_id") == account_id:
            return acc
    return None
