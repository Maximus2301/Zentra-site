"""
Multi-Tenant, Multi-Account & Subscription Security Store for Personal Brand Engine.
Provides:
1. Strict tenant isolation keyed by immutable Telegram User ID (and optional custom User ID).
2. Multiple Instagram brand personas/accounts per tenant (`/brands` switcher).
3. Pilot subscription gating, admin license key generation (`/gen_key`), and `/activate`.
4. Per-tenant daily generation rate limiting (quota protection).
"""
from __future__ import annotations

import logging
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..config.settings import (
    BRAND_PROFILE_PATH,
    BrandSettings,
    PROJECT_ROOT,
    TELEGRAM_CHAT_ID,
    load_brand_profile,
    save_brand_profile,
)

logger = logging.getLogger("personal_brand.tenant_store")

DATA_DIR = PROJECT_ROOT / "data"
TENANTS_DIR = PROJECT_ROOT / "tenants"
DB_PATH = DATA_DIR / "brand_os.db"


def _slugify(value: str, fallback: str = "default") -> str:
    clean = re.sub(r"[^a-z0-9_-]+", "_", (value or "").strip().lower()).strip("_")
    return clean[:32] or fallback


class TenantStore:
    """SQLite + isolated filesystem store for multi-tenant SaaS pilot operations."""

    def __init__(self, db_path: Optional[Path] = None, tenants_root: Optional[Path] = None):
        self._use_cloud = db_path is None
        self.db_path = db_path or DB_PATH
        self.tenants_root = tenants_root or TENANTS_DIR
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.tenants_root.mkdir(parents=True, exist_ok=True)
        if self._use_cloud:
            from . import cloud_memory
            cloud_memory.restore_all()
        is_new_db = not self.db_path.exists()
        self._init_db()
        if is_new_db:
            self._sync_db()

    def _sync_db(self) -> None:
        if self._use_cloud:
            from . import cloud_memory
            cloud_memory.sync_sqlite_db(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_user_id TEXT PRIMARY KEY,
                    custom_user_id TEXT UNIQUE,
                    telegram_username TEXT DEFAULT '',
                    plan TEXT NOT NULL DEFAULT 'pending',
                    status TEXT NOT NULL DEFAULT 'pending_approval',
                    max_brands INTEGER NOT NULL DEFAULT 3,
                    daily_limit INTEGER NOT NULL DEFAULT 15,
                    daily_used INTEGER NOT NULL DEFAULT 0,
                    usage_date TEXT DEFAULT '',
                    active_brand_slug TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    expires_at TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS brands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id TEXT NOT NULL,
                    brand_slug TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    ig_handle TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(telegram_user_id, brand_slug),
                    FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS licenses (
                    code TEXT PRIMARY KEY,
                    plan TEXT NOT NULL DEFAULT 'pilot',
                    max_brands INTEGER NOT NULL DEFAULT 3,
                    daily_limit INTEGER NOT NULL DEFAULT 15,
                    duration_days INTEGER NOT NULL DEFAULT 30,
                    created_by TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    redeemed_by TEXT DEFAULT '',
                    redeemed_at TEXT DEFAULT ''
                );
                """
            )
            # Auto-seed owner from TELEGRAM_CHAT_ID as active admin
            if TELEGRAM_CHAT_ID:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users (
                        telegram_user_id, custom_user_id, plan, status,
                        max_brands, daily_limit, active_brand_slug, created_at
                    ) VALUES (?, ?, 'admin', 'active', 20, 999, 'default', ?)
                    """,
                    (str(TELEGRAM_CHAT_ID), "owner_admin", now),
                )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO brands (
                        telegram_user_id, brand_slug, display_name, created_at
                    ) VALUES (?, 'default', 'Primary Brand', ?)
                    """,
                    (str(TELEGRAM_CHAT_ID), now),
                )

    # ── User & Subscription Lifecycle ─────────────────────────────────────────

    def is_admin(self, telegram_user_id: str) -> bool:
        if TELEGRAM_CHAT_ID and str(telegram_user_id) == str(TELEGRAM_CHAT_ID):
            return True
        user = self.get_user(telegram_user_id)
        return bool(user and user["plan"] == "admin" and user["status"] == "active")

    def get_user(self, telegram_user_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE telegram_user_id = ?",
                (str(telegram_user_id),),
            ).fetchone()
            return dict(row) if row else None

    def is_active_subscriber(self, telegram_user_id: str) -> Tuple[bool, str]:
        """Checks whether user exists, is active, and has not expired."""
        if self.is_admin(telegram_user_id):
            return True, "admin"
        user = self.get_user(telegram_user_id)
        if not user:
            return False, "unregistered"
        if user["status"] != "active":
            return False, user["status"]
        if user.get("expires_at"):
            try:
                exp = datetime.fromisoformat(user["expires_at"])
                if datetime.now(timezone.utc) > exp:
                    with self._connect() as conn:
                        conn.execute(
                            "UPDATE users SET status = 'expired' WHERE telegram_user_id = ?",
                            (str(telegram_user_id),),
                        )
                    return False, "expired"
            except ValueError:
                pass
        return True, "active"

    def register_pending_user(
        self,
        telegram_user_id: str,
        custom_user_id: str,
        telegram_username: str = "",
    ) -> Tuple[bool, str]:
        """Registers a user-chosen User ID linked to their immutable Telegram ID for pilot approval."""
        clean_id = _slugify(custom_user_id, fallback="")
        if len(clean_id) < 3:
            return False, "User ID must be at least 3 alphanumeric characters (letters, digits, _ or -)."

        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conflict = conn.execute(
                "SELECT telegram_user_id FROM users WHERE custom_user_id = ? AND telegram_user_id != ?",
                (clean_id, str(telegram_user_id)),
            ).fetchone()
            if conflict:
                return False, f"User ID '{clean_id}' is already taken. Please choose another."

            existing = conn.execute(
                "SELECT status, plan FROM users WHERE telegram_user_id = ?",
                (str(telegram_user_id),),
            ).fetchone()
            if existing and existing["status"] == "active":
                conn.execute(
                    "UPDATE users SET custom_user_id = ?, telegram_username = ? WHERE telegram_user_id = ?",
                    (clean_id, telegram_username, str(telegram_user_id)),
                )
                self._sync_db()
                return True, f"Updated your User ID to '{clean_id}' (account already active)."

            conn.execute(
                """
                INSERT INTO users (
                    telegram_user_id, custom_user_id, telegram_username,
                    plan, status, max_brands, daily_limit, active_brand_slug, created_at
                ) VALUES (?, ?, ?, 'pilot', 'pending_approval', 3, 15, 'default', ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    custom_user_id = excluded.custom_user_id,
                    telegram_username = excluded.telegram_username,
                    status = 'pending_approval'
                """,
                (str(telegram_user_id), clean_id, telegram_username, now),
            )
        self._sync_db()
        return True, clean_id

    def approve_user(
        self,
        telegram_user_id: str,
        plan: str = "pilot",
        max_brands: int = 3,
        daily_limit: int = 15,
        duration_days: int = 30,
    ) -> None:
        now = datetime.now(timezone.utc)
        exp = (now + timedelta(days=duration_days)).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    telegram_user_id, plan, status, max_brands, daily_limit,
                    active_brand_slug, created_at, expires_at
                ) VALUES (?, ?, 'active', ?, ?, 'default', ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    plan = excluded.plan,
                    status = 'active',
                    max_brands = excluded.max_brands,
                    daily_limit = excluded.daily_limit,
                    expires_at = excluded.expires_at
                """,
                (str(telegram_user_id), plan, max_brands, daily_limit, now.isoformat(), exp),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO brands (telegram_user_id, brand_slug, display_name, created_at)
                VALUES (?, 'default', 'Primary Instagram Brand', ?)
                """,
                (str(telegram_user_id), now.isoformat()),
            )
        self._sync_db()

    def suspend_user(self, telegram_user_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET status = 'suspended' WHERE telegram_user_id = ?",
                (str(telegram_user_id),),
            )
        self._sync_db()

    def generate_license_key(
        self,
        created_by: str,
        plan: str = "pilot",
        max_brands: int = 3,
        daily_limit: int = 15,
        duration_days: int = 30,
    ) -> str:
        """Creates a single-use pilot activation key."""
        token = secrets.token_hex(4).upper()
        code = f"PILOT-{token[:4]}-{token[4:]}"
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO licenses (code, plan, max_brands, daily_limit, duration_days, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (code, plan, max_brands, daily_limit, duration_days, str(created_by), now),
            )
        self._sync_db()
        return code

    def redeem_license_key(
        self,
        code: str,
        telegram_user_id: str,
        telegram_username: str = "",
    ) -> Tuple[bool, str]:
        """Activates a subscriber account using a single-use license key."""
        clean_code = (code or "").strip().upper()
        with self._connect() as conn:
            lic = conn.execute("SELECT * FROM licenses WHERE code = ?", (clean_code,)).fetchone()
            if not lic:
                return False, "Invalid activation key."
            if lic["redeemed_by"]:
                return False, "This activation key has already been redeemed."

            now = datetime.now(timezone.utc)
            exp = (now + timedelta(days=int(lic["duration_days"]))).isoformat()
            conn.execute(
                "UPDATE licenses SET redeemed_by = ?, redeemed_at = ? WHERE code = ?",
                (str(telegram_user_id), now.isoformat(), clean_code),
            )
            conn.execute(
                """
                INSERT INTO users (
                    telegram_user_id, telegram_username, plan, status,
                    max_brands, daily_limit, active_brand_slug, created_at, expires_at
                ) VALUES (?, ?, ?, 'active', ?, ?, 'default', ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    telegram_username = excluded.telegram_username,
                    plan = excluded.plan,
                    status = 'active',
                    max_brands = excluded.max_brands,
                    daily_limit = excluded.daily_limit,
                    expires_at = excluded.expires_at
                """,
                (
                    str(telegram_user_id),
                    telegram_username,
                    lic["plan"],
                    lic["max_brands"],
                    lic["daily_limit"],
                    now.isoformat(),
                    exp,
                ),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO brands (telegram_user_id, brand_slug, display_name, created_at)
                VALUES (?, 'default', 'Primary Instagram Brand', ?)
                """,
                (str(telegram_user_id), now.isoformat()),
            )
        self._sync_db()
        return True, f"Activated '{lic['plan']}' plan ({lic['max_brands']} IG brands, {lic['daily_limit']} posts/day for {lic['duration_days']} days)."

    # ── Quota / Rate Limiting ─────────────────────────────────────────────────

    def check_and_consume_quota(self, telegram_user_id: str) -> Tuple[bool, int, int]:
        """Checks daily generation quota and increments counter if allowed."""
        if self.is_admin(telegram_user_id):
            return True, 0, 999

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._connect() as conn:
            user = conn.execute(
                "SELECT daily_limit, daily_used, usage_date FROM users WHERE telegram_user_id = ?",
                (str(telegram_user_id),),
            ).fetchone()
            if not user:
                return False, 0, 0
            limit = int(user["daily_limit"])
            used = int(user["daily_used"]) if user["usage_date"] == today else 0
            if used >= limit:
                return False, used, limit
            conn.execute(
                "UPDATE users SET daily_used = ?, usage_date = ? WHERE telegram_user_id = ?",
                (used + 1, today, str(telegram_user_id)),
            )
        self._sync_db()
        return True, used + 1, limit

    # ── Multi-Account / Brand Isolation ───────────────────────────────────────

    def get_tenant_dir(self, telegram_user_id: str) -> Path:
        tdir = self.tenants_root / _slugify(str(telegram_user_id))
        tdir.mkdir(parents=True, exist_ok=True)
        return tdir

    def get_brand_dir(self, telegram_user_id: str, brand_slug: str) -> Path:
        bdir = self.get_tenant_dir(telegram_user_id) / "brands" / _slugify(brand_slug)
        (bdir / "assets").mkdir(parents=True, exist_ok=True)
        (bdir / "output" / "queue").mkdir(parents=True, exist_ok=True)
        (bdir / "output" / "approved").mkdir(parents=True, exist_ok=True)
        return bdir

    def get_active_brand_slug(self, telegram_user_id: str) -> str:
        user = self.get_user(telegram_user_id)
        return _slugify(user["active_brand_slug"]) if user else "default"

    def list_brands(self, telegram_user_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM brands WHERE telegram_user_id = ? ORDER BY id ASC",
                (str(telegram_user_id),),
            ).fetchall()
            return [dict(r) for r in rows]

    def create_brand(
        self,
        telegram_user_id: str,
        brand_name: str,
        ig_handle: str = "",
    ) -> Tuple[bool, str, str]:
        """Creates a new isolated Instagram brand workspace for the tenant."""
        user = self.get_user(telegram_user_id)
        max_brands = int(user["max_brands"]) if user else 3
        existing = self.list_brands(telegram_user_id)
        if len(existing) >= max_brands and not self.is_admin(telegram_user_id):
            return False, "", f"Brand limit reached ({max_brands} accounts on your plan)."

        slug = _slugify(brand_name, fallback=f"brand_{len(existing) + 1}")
        existing_slugs = {b["brand_slug"] for b in existing}
        if slug in existing_slugs:
            slug = f"{slug}_{len(existing) + 1}"

        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO brands (telegram_user_id, brand_slug, display_name, ig_handle, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(telegram_user_id), slug, brand_name.strip(), ig_handle.strip(), now),
            )
            conn.execute(
                "UPDATE users SET active_brand_slug = ? WHERE telegram_user_id = ?",
                (slug, str(telegram_user_id)),
            )

        # Initialize clean isolated brand_profile.json
        self._sync_db()
        self.get_brand_settings(telegram_user_id, slug)
        return True, slug, f"Created & switched to brand '{brand_name}' ({slug})."

    def switch_brand(self, telegram_user_id: str, brand_slug: str) -> Tuple[bool, str]:
        clean_slug = _slugify(brand_slug)
        brands = {b["brand_slug"]: b for b in self.list_brands(telegram_user_id)}
        if clean_slug not in brands:
            return False, f"Brand '{clean_slug}' not found in your account."
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET active_brand_slug = ? WHERE telegram_user_id = ?",
                (clean_slug, str(telegram_user_id)),
            )
        self._sync_db()
        return True, f"Switched active workspace to {brands[clean_slug]['display_name']}."

    def sync_brand_metadata(self, telegram_user_id: str, brand_slug: str, name: str, handle: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO brands (telegram_user_id, brand_slug, display_name, ig_handle, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(telegram_user_id, brand_slug) DO UPDATE SET
                    display_name = excluded.display_name,
                    ig_handle = excluded.ig_handle
                """,
                (
                    str(telegram_user_id),
                    _slugify(brand_slug),
                    name,
                    handle,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        self._sync_db()

    def get_brand_settings(self, telegram_user_id: str, brand_slug: Optional[str] = None) -> BrandSettings:
        """Loads or initializes an isolated BrandSettings instance for (tenant, brand)."""
        slug = _slugify(brand_slug or self.get_active_brand_slug(telegram_user_id))
        bdir = self.get_brand_dir(telegram_user_id, slug)
        profile_path = bdir / "brand_profile.json"
        if not profile_path.exists():
            template = load_brand_profile(BRAND_PROFILE_PATH)
            template["creator"]["is_configured"] = False
            template["creator"]["name"] = ""
            template["creator"]["handle"] = ""
            template["creator"]["avatar_path"] = ""
            save_brand_profile(template, profile_path)
        return BrandSettings(profile_path)


tenant_store = TenantStore()
