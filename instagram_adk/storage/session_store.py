"""Durable, frugal multi-user session history storage (GCS + Local Cache).

Provides persistent session storage for agentic campaigns with strict per-user
isolation and Superuser (admin) global auditing capabilities.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config.settings import SESSIONS_BUCKET_NAME, SESSIONS_DIR

logger = logging.getLogger("instagram_adk.session_store")

_GCS_CLIENT = None
_GCS_BUCKET = None
_GCS_INITIALIZED = False


def get_gcs_bucket() -> Any | None:
    """Returns the Google Cloud Storage bucket if running in GCP with ADC, else None."""
    global _GCS_CLIENT, _GCS_BUCKET, _GCS_INITIALIZED
    if _GCS_INITIALIZED:
        return _GCS_BUCKET

    _GCS_INITIALIZED = True
    # In Cloud Run, K_SERVICE is automatically provided; or if GOOGLE_APPLICATION_CREDENTIALS is set
    if not (os.getenv("K_SERVICE") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")):
        logger.info("Local environment detected; using fast local session store.")
        return None

    try:
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket(SESSIONS_BUCKET_NAME)
        # Verify access by checking existence
        if bucket.exists():
            _GCS_CLIENT = client
            _GCS_BUCKET = bucket
            logger.info(f"✓ Connected to Google Cloud Storage bucket: gs://{SESSIONS_BUCKET_NAME}")
            return _GCS_BUCKET
        else:
            logger.warning(f"GCS bucket gs://{SESSIONS_BUCKET_NAME} does not exist.")
    except Exception as e:
        logger.info(f"GCS bucket not available in this environment ({e}). Using local session store.")

    return None


def _get_user_local_dir(user_id: str) -> Path:
    """Returns the local directory path for a user's session data."""
    clean_user = "".join(c if c.isalnum() or c in ("-", "_", "@", ".") else "_" for c in user_id)
    user_dir = SESSIONS_DIR / clean_user
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _read_local_index(user_id: str) -> list[dict[str, Any]]:
    """Reads the user's session index from local disk."""
    index_file = _get_user_local_dir(user_id) / "index.json"
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read local index for {user_id}: {e}")
    return []


def _write_local_index(user_id: str, index_data: list[dict[str, Any]]) -> None:
    """Writes the user's session index to local disk."""
    index_file = _get_user_local_dir(user_id) / "index.json"
    try:
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write local index for {user_id}: {e}")


def save_session(
    user_id: str,
    session_data: dict[str, Any],
    media_files: dict[str, str | Path] | None = None,
) -> dict[str, Any]:
    """Persists a new content creation session to GCS and local cache.
    
    Args:
        user_id: Authenticated username / email.
        session_data: Complete campaign result dictionary.
        media_files: Mapping of asset key to file path on disk.
        
    Returns:
        The stored session dictionary with normalized IDs and timestamps.
    """
    clean_user = "".join(c if c.isalnum() or c in ("-", "_", "@", ".") else "_" for c in user_id)
    session_id = session_data.get("session_id") or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{clean_user[:8]}"
    created_at = session_data.get("created_at") or datetime.now(timezone.utc).isoformat()

    # 1. Prepare session metadata record
    record = dict(session_data)
    record["session_id"] = session_id
    record["user_id"] = user_id
    record["created_at"] = created_at

    # 2. Local session directory
    session_dir = _get_user_local_dir(user_id) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = session_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 3. Copy / upload media assets
    persisted_media_urls: dict[str, str] = {}
    bucket = get_gcs_bucket()

    if media_files:
        for asset_key, file_path_raw in media_files.items():
            if not file_path_raw:
                continue
            src_file = Path(file_path_raw)
            if src_file.exists():
                dest_file = assets_dir / src_file.name
                shutil.copy2(src_file, dest_file)
                # Serve via media route or history media route
                persisted_media_urls[asset_key] = f"/api/history/{session_id}/media/{src_file.name}"

                # GCS upload if bucket active
                if bucket:
                    try:
                        gcs_path = f"users/{clean_user}/sessions/{session_id}/assets/{src_file.name}"
                        blob = bucket.blob(gcs_path)
                        content_type = "video/mp4" if src_file.suffix == ".mp4" else ("image/png" if src_file.suffix == ".png" else "application/octet-stream")
                        blob.upload_from_filename(str(src_file), content_type=content_type)
                        logger.info(f"✓ Uploaded {asset_key} to gs://{SESSIONS_BUCKET_NAME}/{gcs_path}")
                    except Exception as e:
                        logger.warning(f"Failed to upload {asset_key} to GCS: {e}")

    if persisted_media_urls:
        record["media_assets"] = persisted_media_urls

    # 4. Save session.json locally
    session_json_path = session_dir / "session.json"
    session_json_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    # 5. GCS upload of session.json
    if bucket:
        try:
            gcs_json_path = f"users/{clean_user}/sessions/{session_id}/session.json"
            blob = bucket.blob(gcs_json_path)
            blob.upload_from_string(json.dumps(record, indent=2), content_type="application/json")
            logger.info(f"✓ Uploaded session metadata to gs://{SESSIONS_BUCKET_NAME}/{gcs_json_path}")
        except Exception as e:
            logger.warning(f"Failed to upload session.json to GCS: {e}")

    # 6. Update user index (lightweight summary)
    summary = {
        "session_id": session_id,
        "user_id": user_id,
        "account_id": record.get("account_id"),
        "channel_name": record.get("channel_name"),
        "created_at": created_at,
        "core_hook": record.get("core_hook"),
        "cohort_matched": record.get("cohort_matched"),
        "target_emotion": record.get("target_emotion"),
        "critic_score": (record.get("critic_review") or {}).get("score", 9.0),
        "critic_verdict": (record.get("critic_review") or {}).get("verdict", "APPROVED"),
        "video_routing": record.get("video_routing"),
        "video_duration_seconds": record.get("video_duration_seconds", 30),
        "formats_generated": record.get("formats_generated", []),
        "media_assets": record.get("media_assets", {}),
    }

    current_index = _read_local_index(user_id)
    # Prepend new session, filter duplicate
    updated_index = [summary] + [s for s in current_index if s.get("session_id") != session_id]
    _write_local_index(user_id, updated_index)

    if bucket:
        try:
            gcs_index_path = f"users/{clean_user}/index.json"
            blob = bucket.blob(gcs_index_path)
            blob.upload_from_string(json.dumps(updated_index, indent=2), content_type="application/json")
        except Exception as e:
            logger.warning(f"Failed to update index in GCS: {e}")

    logger.info(f"✓ Session {session_id} successfully persisted for user '{user_id}'")
    return record


def list_sessions(
    user_id: str,
    is_admin: bool = False,
    all_users: bool = False,
    user_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Lists past sessions.
    
    If is_admin and all_users is True, returns sessions across all users.
    Standard users are strictly restricted to their own sessions.
    """
    bucket = get_gcs_bucket()

    # Admin global view
    if is_admin and (all_users or user_filter):
        target_users: list[str] = []
        if user_filter:
            target_users = [user_filter]
        else:
            # Discover all users from local disk + GCS
            target_users = list_all_active_users()

        combined: list[dict[str, Any]] = []
        for u in target_users:
            combined.extend(_get_user_sessions(u, bucket))

        # Sort combined sessions descending by date
        combined.sort(key=lambda s: s.get("created_at", ""), reverse=True)
        return combined

    # Standard user view: strictly their own sessions
    sessions = _get_user_sessions(user_id, bucket)
    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return sessions


def _get_user_sessions(user_id: str, bucket: Any | None) -> list[dict[str, Any]]:
    """Retrieves session list for a single user, syncing from GCS if needed."""
    clean_user = "".join(c if c.isalnum() or c in ("-", "_", "@", ".") else "_" for c in user_id)
    
    # 1. Try syncing index from GCS if bucket available
    if bucket:
        try:
            gcs_index_path = f"users/{clean_user}/index.json"
            blob = bucket.blob(gcs_index_path)
            if blob.exists():
                data = json.loads(blob.download_as_text(encoding="utf-8"))
                _write_local_index(user_id, data)
                return data
        except Exception as e:
            logger.debug(f"Could not fetch GCS index for {user_id}: {e}")

    # 2. Fallback to local index
    local_index = _read_local_index(user_id)
    if local_index:
        return local_index

    # 3. Fallback to scanning local user directory
    user_dir = _get_user_local_dir(user_id)
    scanned: list[dict[str, Any]] = []
    if user_dir.exists():
        for sess_dir in user_dir.iterdir():
            if sess_dir.is_dir() and (sess_dir / "session.json").exists():
                try:
                    s_data = json.loads((sess_dir / "session.json").read_text(encoding="utf-8"))
                    scanned.append({
                        "session_id": s_data.get("session_id", sess_dir.name),
                        "user_id": user_id,
                        "account_id": s_data.get("account_id"),
                        "channel_name": s_data.get("channel_name"),
                        "created_at": s_data.get("created_at", ""),
                        "core_hook": s_data.get("core_hook"),
                        "critic_score": (s_data.get("critic_review") or {}).get("score", 9.0),
                        "critic_verdict": (s_data.get("critic_review") or {}).get("verdict", "APPROVED"),
                        "video_routing": s_data.get("video_routing"),
                        "video_duration_seconds": s_data.get("video_duration_seconds", 30),
                        "formats_generated": s_data.get("formats_generated", []),
                        "media_assets": s_data.get("media_assets", {}),
                    })
                except Exception:
                    pass

    return scanned


def get_session(session_id: str, user_id: str, is_admin: bool = False) -> dict[str, Any] | None:
    """Retrieves full details of a specific session with access control enforcement."""
    clean_user = "".join(c if c.isalnum() or c in ("-", "_", "@", ".") else "_" for c in user_id)
    bucket = get_gcs_bucket()

    # 1. Search in user's own directory
    user_sess_file = _get_user_local_dir(user_id) / session_id / "session.json"
    if user_sess_file.exists():
        try:
            return json.loads(user_sess_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 2. If GCS is available, check GCS for this user
    if bucket:
        try:
            gcs_path = f"users/{clean_user}/sessions/{session_id}/session.json"
            blob = bucket.blob(gcs_path)
            if blob.exists():
                data = json.loads(blob.download_as_text(encoding="utf-8"))
                # Cache locally
                user_sess_file.parent.mkdir(parents=True, exist_ok=True)
                user_sess_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                return data
        except Exception as e:
            logger.debug(f"Could not load session from GCS: {e}")

    # 3. If admin, search all user directories
    if is_admin:
        all_users = list_all_active_users()
        for other_user in all_users:
            if other_user == user_id:
                continue
            sess = get_session(session_id, other_user, is_admin=False)
            if sess:
                return sess

    return None


def get_session_media_path(session_id: str, filename: str, user_id: str, is_admin: bool = False) -> Path | None:
    """Locates a media file for a session, downloading from GCS to local cache if needed."""
    session = get_session(session_id, user_id, is_admin=is_admin)
    if not session:
        return None

    owner_user = session.get("user_id", user_id)
    clean_owner = "".join(c if c.isalnum() or c in ("-", "_", "@", ".") else "_" for c in owner_user)

    local_asset = _get_user_local_dir(owner_user) / session_id / "assets" / filename
    if local_asset.exists():
        return local_asset

    # Download from GCS if bucket available
    bucket = get_gcs_bucket()
    if bucket:
        try:
            gcs_asset_path = f"users/{clean_owner}/sessions/{session_id}/assets/{filename}"
            blob = bucket.blob(gcs_asset_path)
            if blob.exists():
                local_asset.parent.mkdir(parents=True, exist_ok=True)
                blob.download_to_filename(str(local_asset))
                return local_asset
        except Exception as e:
            logger.warning(f"Failed to fetch asset from GCS: {e}")

    return None


def delete_session(session_id: str, user_id: str, is_admin: bool = False) -> bool:
    """Deletes a session and its associated media files."""
    session = get_session(session_id, user_id, is_admin=is_admin)
    if not session:
        return False

    owner_user = session.get("user_id", user_id)
    if not is_admin and owner_user != user_id:
        return False

    clean_owner = "".join(c if c.isalnum() or c in ("-", "_", "@", ".") else "_" for c in owner_user)
    session_dir = _get_user_local_dir(owner_user) / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)

    # Update local index
    current_index = _read_local_index(owner_user)
    updated_index = [s for s in current_index if s.get("session_id") != session_id]
    _write_local_index(owner_user, updated_index)

    # GCS deletion if active
    bucket = get_gcs_bucket()
    if bucket:
        try:
            prefix = f"users/{clean_owner}/sessions/{session_id}/"
            blobs = list(bucket.list_blobs(prefix=prefix))
            for b in blobs:
                b.delete()
            # Update GCS index
            gcs_index_path = f"users/{clean_owner}/index.json"
            blob = bucket.blob(gcs_index_path)
            blob.upload_from_string(json.dumps(updated_index, indent=2), content_type="application/json")
            logger.info(f"✓ Deleted session {session_id} from GCS")
        except Exception as e:
            logger.warning(f"Error deleting session from GCS: {e}")

    return True


def list_all_active_users() -> list[str]:
    """Finds all distinct users with session history (for Admin filtering)."""
    users_set: set[str] = set()

    # 1. Local directories
    if SESSIONS_DIR.exists():
        for d in SESSIONS_DIR.iterdir():
            if d.is_dir() and (d / "index.json").exists():
                users_set.add(d.name)

    # 2. GCS prefixes
    bucket = get_gcs_bucket()
    if bucket:
        try:
            blobs = bucket.list_blobs(prefix="users/", delimiter="/")
            # Prefixes give subfolders under users/
            for page in blobs.pages:
                for prefix in page.prefixes:
                    parts = prefix.strip("/").split("/")
                    if len(parts) >= 2:
                        users_set.add(parts[1])
        except Exception as e:
            logger.debug(f"Could not list GCS user prefixes: {e}")

    # Fallback to known accounts
    users_set.add("admin")
    users_set.add("vyantec@gmail.com")

    return sorted(list(users_set))
