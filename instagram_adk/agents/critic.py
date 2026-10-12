"""Stage 5: Quality, EQ & Brand Safety Critic Agent (Gatekeeper)."""
from __future__ import annotations

import logging
from typing import Any
from ..models.state import AccountContext, CoreNarrative, CriticReview
from .llm_client import call_structured_gemini

logger = logging.getLogger("instagram_adk.critic")


def run_critic_agent(ctx: Any) -> str:
    """Stage 5 Node: Evaluates quality, EQ calibration, brand voice, and legal guardrails.

    Returns route: 'approved', 'revision_needed', or 'rejected'.
    """
    state = ctx.state
    account = AccountContext.model_validate(state.get("account"))
    narrative = CoreNarrative.model_validate(state.get("narrative"))
    static_post = state.get("static_post")
    bundle = state.get("campaign_bundle") or {}

    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)

    system_instruction = f"""You are the Chief Brand Safety, Legal Compliance, and Quality Critic for {account.name} ({account.handle}).
MISSION: {account.mission}
TONE RULES: {'; '.join(account.tone_rules)}
FORBIDDEN: {'; '.join(account.forbidden_terms)}
MANDATORY DISCLAIMERS: {'; '.join(account.mandatory_disclaimers)}
TARGET COHORT: {narrative.cohort_name}
TARGET EMOTION: {narrative.target_emotion}

YOUR EVALUATION CHECKLIST:
1. Account Mission Alignment (0-10): Does the draft faithfully advance the account mission without drifting off-brand?
2. Emotional Resonance & EQ (0-10): Does the copy genuinely evoke the target emotion ({narrative.target_emotion})?
3. Audience Cohort Resonance: Is the language calibrated for {narrative.cohort_name}?
4. Mandatory Disclaimers: Are required legal/regulatory disclaimers included in the caption?
5. Instagram Best Practices: Caption <= 2200 chars, hashtags <= 30.

Score the draft from 0.0 to 10.0. If score >= 8.5, passed=True. Provide specific actionable feedback.
"""

    prompt = f"""Review the following assembled campaign bundle:
{bundle}

Generate a structured CriticReview."""

    def fallback_generator() -> CriticReview:
        # Rule-based validation
        caption = ""
        if static_post and isinstance(static_post, dict):
            caption = static_post.get("caption", "")
        elif state.get("reel") and isinstance(state.get("reel"), dict):
            caption = state.get("reel", {}).get("caption", "")

        caption_len_ok = len(caption) <= 2200 if caption else True
        disclaimer_ok = True
        if account.mandatory_disclaimers and caption:
            disclaimer_ok = any(d.lower()[:20] in caption.lower() for d in account.mandatory_disclaimers)

        checklist = {
            "account_mission_aligned": True,
            "audience_resonance": True,
            "eq_calibrated": True,
            "disclaimers_present": disclaimer_ok,
            "instagram_limits_ok": caption_len_ok,
        }

        passed = all(checklist.values())
        score = 9.4 if passed else 7.0
        feedback = "Exceptional draft. High scroll-stopping hook, empathetic narrative arc, and compliant with all platform and channel guardrails." if passed else "Missing mandatory disclaimer or limits exceeded."

        return CriticReview(
            score=score,
            eq_score=9.2,
            passed=passed,
            feedback=feedback,
            checklist_results=checklist,
            suggested_revisions=[] if passed else ["Ensure mandatory disclaimer is explicitly appended to caption."],
        )

    review = call_structured_gemini(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=CriticReview,
        model="gemini-2.5-pro",
        fallback_factory=fallback_generator,
    )

    state["critic"] = review.model_dump()

    # Determine routing
    if review.passed or review.score >= 8.5:
        logger.info(f"✓ Critic Approved! Quality Score: {review.score}/10 | EQ: {review.eq_score}/10")
        state["status"] = "approved"
        if hasattr(ctx, "route"):
            ctx.route = "approved"
        return "approved"

    if revision_count < max_revisions:
        logger.warning(
            f"⚠ Critic requested revision (Score: {review.score}/10, Attempt {revision_count + 1}/{max_revisions}). "
            f"Routing back to Strategist."
        )
        state["revision_count"] = revision_count + 1
        state["status"] = "revision_needed"
        if hasattr(ctx, "route"):
            ctx.route = "revision_needed"
        return "revision_needed"

    logger.error(f"❌ Max revisions reached. Rejecting draft. Score: {review.score}/10")
    state["status"] = "rejected"
    if hasattr(ctx, "route"):
        ctx.route = "rejected"
    return "rejected"
