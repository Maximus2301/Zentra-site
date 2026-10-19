"""Authentication and User Management Module for Zentra Creator Studio.

Provides salted PBKDF2-HMAC-SHA256 password hashing, cryptographically signed
session tokens, persistent user storage, and Google ID token verification.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any, Tuple, Optional
import httpx

from .config.settings import OUTPUT_DIR

logger = logging.getLogger("instagram_adk.auth")

USERS_FILE = OUTPUT_DIR / "users.json"

# Secret key used for signing session tokens (reads from env or generates persistent secret)
JWT_SECRET_KEY = os.environ.get("PCE_JWT_SECRET") or os.environ.get("CREATOR_JWT_SECRET") or "zentra-campaign-secret-key-2026"
TOKEN_EXPIRY_SECONDS = 30 * 24 * 3600  # 30 days

# Whitelist for Google Sign-In authentication
ALLOWED_GOOGLE_EMAILS = [
    "vyantec@gmail.com",
    os.environ.get("CREATOR_ADMIN_EMAIL", "vyantec@gmail.com").lower()
]


def _hash_password(plain_password: str, salt: str | None = None) -> Tuple[str, str]:
    """Generates a salted PBKDF2-HMAC-SHA256 password hash."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return hashed.hex(), salt


def _verify_password_hash(plain_password: str, salt: str, expected_hash: str) -> bool:
    """Verifies a plain password against a stored salt and hash."""
    computed_hash, _ = _hash_password(plain_password, salt)
    return hmac.compare_digest(computed_hash, expected_hash)


def init_user_store(force: bool = False) -> dict[str, Any]:
    """Initializes user storage with default admin and vyantec@gmail.com accounts if missing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if USERS_FILE.exists() and not force:
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read existing users.json ({e}), re-initializing...")

    # Default initial accounts
    admin_hash, admin_salt = _hash_password("ZentraCreator2026!")
    vyan_hash, vyan_salt = _hash_password("ZentraVyan2026!")

    default_users = {
        "admin": {
            "username": "admin",
            "email": "admin@zentraai.in",
            "password_hash": admin_hash,
            "salt": admin_salt,
            "role": "admin",
            "must_change_password": True,
            "created_at": time.time(),
        },
        "vyantec@gmail.com": {
            "username": "vyantec@gmail.com",
            "email": "vyantec@gmail.com",
            "password_hash": vyan_hash,
            "salt": vyan_salt,
            "role": "admin",
            "must_change_password": False,
            "created_at": time.time(),
        },
    }

    USERS_FILE.write_text(json.dumps(default_users, indent=2), encoding="utf-8")
    return default_users


def get_users() -> dict[str, Any]:
    """Loads users from the persistent store."""
    if not USERS_FILE.exists():
        return init_user_store()
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return init_user_store()


def save_users(users: dict[str, Any]) -> None:
    """Saves updated user dictionary to persistent JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def authenticate_user(username_or_email: str, plain_password: str) -> Tuple[bool, Optional[dict[str, Any]], str]:
    """Authenticates credentials against registered users. Returns (is_valid, user_dict, message)."""
    users = get_users()
    key = username_or_email.strip().lower()

    target_user = None
    for u_key, u_data in users.items():
        if u_key.lower() == key or u_data.get("email", "").lower() == key:
            target_user = u_data
            break

    if not target_user:
        return False, None, "Invalid username or password"

    salt = target_user.get("salt", "")
    expected_hash = target_user.get("password_hash", "")

    if not _verify_password_hash(plain_password, salt, expected_hash):
        return False, None, "Invalid username or password"

    return True, target_user, "Authentication successful"


def change_user_password(username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
    """Validates old password and updates user's password, resetting must_change_password to False."""
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."

    users = get_users()
    key = username.strip().lower()

    target_key = None
    for u_key, u_data in users.items():
        if u_key.lower() == key or u_data.get("email", "").lower() == key:
            target_key = u_key
            break

    if not target_key:
        return False, f"User '{username}' not found."

    target_user = users[target_key]
    salt = target_user.get("salt", "")
    expected_hash = target_user.get("password_hash", "")

    if not _verify_password_hash(old_password, salt, expected_hash):
        return False, "Current password does not match."

    # Compute new hash
    new_hash, new_salt = _hash_password(new_password)
    target_user["password_hash"] = new_hash
    target_user["salt"] = new_salt
    target_user["must_change_password"] = False
    target_user["updated_at"] = time.time()

    users[target_key] = target_user
    save_users(users)
    return True, "Password successfully updated."


def create_session_token(username: str, email: str, must_change_password: bool = False) -> str:
    """Creates a URL-safe cryptographically signed session token."""
    payload = {
        "sub": username,
        "email": email,
        "mcp": must_change_password,
        "exp": int(time.time()) + TOKEN_EXPIRY_SECONDS,
        "nonce": secrets.token_hex(8),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_session_token(token: str) -> Optional[dict[str, Any]]:
    """Verifies HMAC signature and expiration of a session token."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, signature = token.split(".", 1)
        expected_sig = hmac.new(JWT_SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Add padding back if necessary
        rem = len(payload_b64) % 4
        padded = payload_b64 + ("=" * (4 - rem) if rem else "")
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception as e:
        logger.debug(f"Token verification error: {e}")
        return None


async def verify_google_id_token(id_token: str) -> Tuple[bool, Optional[dict[str, Any]], str]:
    """Verifies a Google OAuth2 ID token using Google's public tokeninfo endpoint.
    
    Validates token integrity and checks whether the authenticated email is in ALLOWED_GOOGLE_EMAILS.
    """
    if not id_token:
        return False, None, "Google ID token cannot be empty."

    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return False, None, f"Google token verification failed (HTTP {res.status_code})"

            info = res.json()
            email = info.get("email", "").lower()
            email_verified = info.get("email_verified") in (True, "true")

            if not email_verified:
                return False, None, "Google account email is not verified."

            # Check if email is in allowed list
            if email not in [e.lower() for e in ALLOWED_GOOGLE_EMAILS]:
                return False, None, f"Access denied for '{email}'. Only authorized Zentra administrators can access this studio."

            return True, {
                "username": email,
                "email": email,
                "name": info.get("name", email),
                "picture": info.get("picture", ""),
                "must_change_password": False,
            }, "Google authentication successful"

    except Exception as e:
        logger.error(f"Error validating Google token: {e}")
        return False, None, f"Google authentication service error: {str(e)}"
