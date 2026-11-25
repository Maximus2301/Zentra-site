"""
Google Cloud Storage (GCS) Persistent Cloud Memory Layer for Personal Brand Engine.
Preserves SQLite state (`data/brand_os.db`), isolated tenant brand profiles & avatars
(`tenants/`), queues, and caches across Google Cloud Run scale-to-zero restarts at near-$0 cost.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
import threading
from pathlib import Path
from typing import Optional

from ..config.settings import PROJECT_ROOT

logger = logging.getLogger("personal_brand.cloud_memory")

_LOCK = threading.Lock()
_RESTORED = False
_GCS_BUCKET = None
STATE_PREFIX = "state/"


def get_bucket_name() -> str:
    return (os.getenv("GCS_MEMORY_BUCKET") or "").strip()


def is_enabled() -> bool:
    return bool(get_bucket_name())


def _get_bucket():
    global _GCS_BUCKET
    bucket_name = get_bucket_name()
    if not bucket_name:
        return None
    if _GCS_BUCKET is None:
        from google.cloud import storage
        client = storage.Client()
        _GCS_BUCKET = client.bucket(bucket_name)
    return _GCS_BUCKET


def _rel_key(local_path: Path) -> Optional[str]:
    try:
        rel = local_path.resolve().relative_to(PROJECT_ROOT.resolve())
        return f"{STATE_PREFIX}{rel.as_posix()}"
    except Exception:
        return None


def restore_all(force: bool = False) -> int:
    """
    Restores persisted state (SQLite DB, tenant profiles, avatars, queues, caches)
    from GCS into PROJECT_ROOT on Cloud Run cold start.
    """
    global _RESTORED
    if not is_enabled():
        return 0

    with _LOCK:
        if _RESTORED and not force:
            return 0
        count = 0
        try:
            bucket = _get_bucket()
            if bucket is None:
                return 0
            blobs = list(bucket.list_blobs(prefix=STATE_PREFIX))
            for blob in blobs:
                rel_path = blob.name[len(STATE_PREFIX) :]
                if not rel_path or rel_path.endswith("/"):
                    continue
                dest = (PROJECT_ROOT / rel_path).resolve()
                # Path traversal guard
                if not str(dest).startswith(str(PROJECT_ROOT.resolve())):
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                blob.download_to_filename(str(dest))
                count += 1
            _RESTORED = True
            logger.info(f"☁️ Restored {count} persistent memory file(s) from gs://{get_bucket_name()}/{STATE_PREFIX}")
        except Exception as e:
            logger.warning(f"Cloud memory restore failed ({e}); continuing with local state.")
        return count


def sync_file(local_path: Path) -> bool:
    """Uploads a single mutated file inside PROJECT_ROOT to GCS."""
    if not is_enabled() or not local_path.exists() or not local_path.is_file():
        return False
    key = _rel_key(local_path)
    if not key:
        return False
    try:
        bucket = _get_bucket()
        if bucket is None:
            return False
        blob = bucket.blob(key)
        blob.upload_from_filename(str(local_path))
        return True
    except Exception as e:
        logger.warning(f"Cloud memory sync_file failed for {key}: {e}")
        return False


def sync_sqlite_db(db_path: Path) -> bool:
    """
    Takes a transactionally consistent online backup snapshot of SQLite (WAL-safe)
    and uploads it to GCS.
    """
    if not is_enabled() or not db_path.exists():
        return False
    key = _rel_key(db_path)
    if not key:
        return False
    try:
        bucket = _get_bucket()
        if bucket is None:
            return False
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            snap_path = Path(tmp.name)
        try:
            with _LOCK:
                src = sqlite3.connect(str(db_path), timeout=15)
                dst = sqlite3.connect(str(snap_path))
                try:
                    src.backup(dst)
                finally:
                    dst.close()
                    src.close()
                bucket.blob(key).upload_from_filename(str(snap_path))
            return True
        finally:
            snap_path.unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Cloud memory sync_sqlite_db failed: {e}")
        return False


def sync_directory(dir_path: Path, max_file_mb: int = 25) -> int:
    """Syncs all files inside dir_path (e.g. rendered output assets) to GCS."""
    if not is_enabled() or not dir_path.exists():
        return 0
    uploaded = 0
    max_bytes = max_file_mb * 1024 * 1024
    for file_path in dir_path.rglob("*"):
        if file_path.is_file() and file_path.stat().st_size <= max_bytes:
            if sync_file(file_path):
                uploaded += 1
    return uploaded
