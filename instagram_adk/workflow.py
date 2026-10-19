"""Google ADK 2.0 Workflow Definition and Orchestrator."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from google.adk.workflow import Workflow, START
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from .models.state import InstagramCampaignState
from .nodes.account_guard import account_guard_node
from .agents.strategist import run_strategist_agent
from .agents.format_specialists import (
    run_static_post_agent,
    run_story_agent,
    run_reel_agent,
    run_status_agent,
)
from .nodes.media_generator import run_media_generator_node
from .nodes.assembler import run_campaign_assembler_node
from .agents.critic import run_critic_agent
from .nodes.publisher import run_account_bound_publisher_node

logger = logging.getLogger("instagram_adk.workflow")


def discard_campaign_node(ctx: Any) -> str:
    """Terminal node when a campaign is rejected by the Critic and max retries exceeded."""
    state = ctx.state
    state["status"] = "discarded"
    logger.error("🛑 Campaign terminated and logged to discarded audit registry.")
    return "discarded"


def build_instagram_workflow() -> Workflow:
    """Builds the complete ADK 2.0 Workflow Graph.

    Graph Pipeline:
    START -> account_guard_node (Stage 0)
          -> strategist_agent (Stage 1)
          -> static_post_agent (Stage 2A)
          -> story_agent (Stage 2B)
          -> reel_agent (Stage 2C)
          -> status_agent (Stage 2D)
          -> media_generator_node (Stage 3)
          -> campaign_assembler_node (Stage 4)
          -> critic_agent (Stage 5)
          -> [conditional routing]:
               'approved' -> publisher_node (Stage 6)
               'revision_needed' -> strategist_agent (Feedback loop)
               'rejected' -> discard_node
    """
    edges = [
        # Stage 0 -> Stage 1
        (START, account_guard_node, run_strategist_agent),
        # Stage 1 -> Stage 2 (Format Specialists)
        (
            run_strategist_agent,
            run_static_post_agent,
            run_story_agent,
            run_reel_agent,
            run_status_agent,
            run_media_generator_node,
            run_campaign_assembler_node,
            run_critic_agent,
        ),
        # Stage 5: Conditional Branching based on Critic evaluation
        (
            run_critic_agent,
            {
                "approved": run_account_bound_publisher_node,
                "revision_needed": run_strategist_agent,
                "rejected": discard_campaign_node,
            },
        ),
    ]

    return Workflow(
        name="autonomous_instagram_campaign_engine",
        state_schema=InstagramCampaignState,
        edges=edges,
    )


async def execute_campaign(
    account_id: str = "workplace_rights_watch",
    raw_user_script: str | None = None,
    requested_topic: str | None = None,
    requested_emotion: str | None = None,
    active_formats: list[str] | None = None,
    requested_duration_seconds: int = 30,
    user_id: str = "admin",
    visual_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Asynchronously runs the full ADK 2.0 workflow pipeline."""
    if active_formats is None:
        active_formats = ["static_post", "story", "reel", "status"]

    initial_state = {
        "account_id": account_id,
        "raw_user_script": raw_user_script,
        "requested_topic": requested_topic,
        "requested_emotion": requested_emotion,
        "requested_duration_seconds": requested_duration_seconds,
        "active_formats": active_formats,
        "visual_identity": visual_identity,
        "status": "initialized",
        "revision_count": 0,
        "max_revisions": 2,
        "media_assets": {},
        "published_media_ids": {},
    }

    workflow = build_instagram_workflow()
    session_service = InMemorySessionService()
    runner = Runner(
        agent=workflow,
        session_service=session_service,
        app_name="instagram_adk_engine",
    )

    session = await session_service.create_session(
        app_name="instagram_adk_engine",
        user_id=user_id,
        state=initial_state,
    )

    logger.info(f"🚀 Launching ADK 2.0 Workflow for account '{account_id}' (Session: {session.id})...")

    # Run the graph orchestration loop
    async for event in runner.run_async(session_id=session.id, user_id=user_id):
        pass

    final_session = await session_service.get_session(
        app_name="instagram_adk_engine",
        user_id=user_id,
        session_id=session.id,
    )

    logger.info(f"🏁 ADK 2.0 Workflow completed with final status: {final_session.state.get('status')}")
    return final_session.state


def run_campaign_sync(
    account_id: str = "workplace_rights_watch",
    raw_user_script: str | None = None,
    requested_topic: str | None = None,
    requested_emotion: str | None = None,
    active_formats: list[str] | None = None,
    requested_duration_seconds: int = 30,
    visual_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synchronous entrypoint for CLI and script execution."""
    return asyncio.run(
        execute_campaign(
            account_id=account_id,
            raw_user_script=raw_user_script,
            requested_topic=requested_topic,
            requested_emotion=requested_emotion,
            active_formats=active_formats,
            requested_duration_seconds=requested_duration_seconds,
            visual_identity=visual_identity,
        )
    )
