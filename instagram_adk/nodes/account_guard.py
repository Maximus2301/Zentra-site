"""Stage 0: Account Selector & Context Guard."""
from __future__ import annotations

import logging
from typing import Any
from ..config.settings import get_account_by_id, load_all_accounts
from ..models.state import AccountContext

logger = logging.getLogger("instagram_adk.account_guard")


def account_guard_node(ctx: Any) -> str:
    """Stage 0 FunctionNode: Validates and binds the selected Instagram account.

    Locks the account persona, mission, guardrails, and audience cohorts
    into the session state before any content planning or generation occurs.
    """
    state = ctx.state

    # Read user input if invoked from Web UI chat
    user_text = ""
    inv_ctx = getattr(ctx, "_invocation_context", None)
    if inv_ctx and hasattr(inv_ctx, "user_content") and inv_ctx.user_content:
        uc = inv_ctx.user_content
        if getattr(uc, "parts", None) and len(uc.parts) > 0:
            user_text = getattr(uc.parts[0], "text", "") or ""

    account_id = state.get("account_id")

    # If account_id not set, check if user mentioned a channel in Web UI text
    if not account_id and user_text:
        ut_lower = user_text.lower()
        if "fintech" in ut_lower or "save" in ut_lower or "invest" in ut_lower:
            account_id = "fintech_save_smart"
        elif "alex" in ut_lower or "ceo" in ut_lower or "startup" in ut_lower or "founder" in ut_lower:
            account_id = "alex_tech_ceo"
        elif "right" in ut_lower or "salary" in ut_lower or "fraud" in ut_lower or "labor" in ut_lower or "wage" in ut_lower:
            account_id = "workplace_rights_watch"

    if user_text and not state.get("raw_user_script") and not state.get("requested_topic"):
        state["raw_user_script"] = user_text

    # Auto-detect or default active_formats
    active_formats = state.get("active_formats")
    if not active_formats:
        detected_formats = []
        if user_text:
            ut_lower = user_text.lower()
            if "reel" in ut_lower:
                detected_formats.append("reel")
            if "story" in ut_lower or "stories" in ut_lower:
                detected_formats.append("story")
            if "status" in ut_lower:
                detected_formats.append("status")
            if "post" in ut_lower or "feed" in ut_lower or "static" in ut_lower:
                detected_formats.append("static_post")

        state["active_formats"] = detected_formats if detected_formats else ["static_post", "story", "reel", "status"]

    state["revision_count"] = state.get("revision_count", 0)
    state["max_revisions"] = state.get("max_revisions", 2)

    if not account_id:
        # Default to first configured account if none explicitly provided
        all_accs = load_all_accounts()
        if not all_accs:
            raise ValueError("No Instagram accounts configured in accounts.json!")
        account_id = all_accs[0]["account_id"]
        logger.info(f"No account_id provided. Defaulting to: {account_id}")

    raw_account = get_account_by_id(account_id)
    if not raw_account:
        available = [a["account_id"] for a in load_all_accounts()]
        raise ValueError(f"Account '{account_id}' not found! Available accounts: {available}")

    account_context = AccountContext(**raw_account)

    state["account_id"] = account_id
    state["account"] = account_context.model_dump()
    state["status"] = "account_locked"

    logger.info(
        f"✓ Channel Context Locked: {account_context.name} ({account_context.handle}) | "
        f"Active Formats: {state['active_formats']} | Cohorts: {len(account_context.audience_cohorts)}"
    )
    return f"locked:{account_id}"
