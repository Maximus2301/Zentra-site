"""Stage 4: Campaign Assembler Node."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from ..models.state import AccountContext, CoreNarrative

logger = logging.getLogger("instagram_adk.assembler")


def run_campaign_assembler_node(ctx: Any) -> str:
    """Stage 4 Node: Combines format deliverables, media paths, and narrative into a single campaign bundle."""
    state = ctx.state
    account = AccountContext.model_validate(state.get("account"))
    narrative = CoreNarrative.model_validate(state.get("narrative"))
    media_assets = state.get("media_assets") or {}

    bundle: dict[str, Any] = {
        "account_id": account.account_id,
        "account_handle": account.handle,
        "assembled_at": datetime.now(timezone.utc).isoformat(),
        "cohort": {
            "id": narrative.selected_cohort_id,
            "name": narrative.cohort_name,
        },
        "target_emotion": narrative.target_emotion,
        "core_hook": narrative.hook,
        "media_assets": media_assets,
        "formats": {},
    }

    if state.get("static_post"):
        bundle["formats"]["static_post"] = state.get("static_post")

    if state.get("story_sequence"):
        bundle["formats"]["story"] = state.get("story_sequence")

    if state.get("reel"):
        bundle["formats"]["reel"] = state.get("reel")

    if state.get("status_card"):
        bundle["formats"]["status"] = state.get("status_card")

    state["campaign_bundle"] = bundle
    state["status"] = "critique_pending"

    logger.info(f"✓ Campaign Assembled: {list(bundle['formats'].keys())} tagged with {account.handle}")
    return "bundle_ready"
