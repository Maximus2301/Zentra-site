"""
Queue and State Manager for Personal Brand Human-on-the-Loop workflows.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..config.settings import PROJECT_ROOT


class PostStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REGENERATING = "REGENERATING"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"


class QueuedItem(BaseModel):
    id: str
    tenant_id: str = ""
    brand_slug: str = "default"
    topic: str
    pillar: str
    format_type: str = "carousel"
    status: PostStatus = PostStatus.PENDING_REVIEW
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    slide_paths: List[str] = Field(default_factory=list)
    video_path: Optional[str] = None
    caption: str
    hashtags: List[str] = Field(default_factory=list)
    alt_text: Optional[str] = None
    primary_search_keyword: Optional[str] = None
    aeo_question: Optional[str] = None
    aeo_direct_answer: Optional[str] = None
    pinned_comment: Optional[str] = None
    critic: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)


class QueueManager:
    """Manages file-backed queue storage for HITL reviews."""

    def __init__(self, queue_dir: Optional[Path] = None, base_output_dir: Optional[Path] = None):
        root_out = base_output_dir or (PROJECT_ROOT / "output")
        self.queue_dir = queue_dir or (root_out / "queue")
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.approved_dir = root_out / "approved"
        self.approved_dir.mkdir(parents=True, exist_ok=True)

    def _get_item_path(self, item_id: str) -> Path:
        safe_id = Path(item_id).name
        return self.queue_dir / f"{safe_id}.json"

    def _sync(self, path: Path) -> None:
        try:
            from ..core import cloud_memory
            cloud_memory.sync_file(path)
        except Exception:
            pass

    def enqueue(self, item: QueuedItem) -> QueuedItem:
        """Saves a newly generated item to the review queue."""
        path = self._get_item_path(item.id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(item.model_dump_json(indent=2))
        self._sync(path)
        return item

    def get(self, item_id: str) -> Optional[QueuedItem]:
        """Retrieves a queued item by ID."""
        path = self._get_item_path(item_id)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return QueuedItem.model_validate_json(f.read())

    def update_status(self, item_id: str, new_status: PostStatus, note: Optional[str] = None) -> Optional[QueuedItem]:
        """Transitions an item's status and updates queue files."""
        item = self.get(item_id)
        if not item:
            return None

        item.status = new_status
        item.updated_at = datetime.now(timezone.utc).isoformat()
        if note:
            item.meta["status_note"] = note

        # Save back to queue
        path = self._get_item_path(item_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(item.model_dump_json(indent=2))
        self._sync(path)

        # If approved, also copy/link into output/approved
        if new_status == PostStatus.APPROVED:
            approved_path = self.approved_dir / f"{Path(item_id).name}.json"
            with open(approved_path, "w", encoding="utf-8") as f:
                f.write(item.model_dump_json(indent=2))
            self._sync(approved_path)

        return item

    def update_caption(self, item_id: str, new_caption: str) -> Optional[QueuedItem]:
        """Updates a queued item's caption and persists."""
        item = self.get(item_id)
        if not item:
            return None
        item.caption = new_caption.strip()
        item.updated_at = datetime.now(timezone.utc).isoformat()
        path = self._get_item_path(item_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(item.model_dump_json(indent=2))
        self._sync(path)
        return item

    def list_items(self, status: Optional[PostStatus] = None) -> List[QueuedItem]:
        """Lists items in queue, optionally filtered by status."""
        items = []
        for file in sorted(self.queue_dir.glob("*.json"), reverse=True):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    item = QueuedItem.model_validate_json(f.read())
                    if status is None or item.status == status:
                        items.append(item)
            except Exception:
                continue
        return items
