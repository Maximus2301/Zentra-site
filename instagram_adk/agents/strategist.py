"""Stage 1: Strategist, Audience Matcher & Script Evolver Agent."""
from __future__ import annotations

import logging
from typing import Any
from ..models.state import AccountContext, CoreNarrative
from .llm_client import call_structured_gemini

logger = logging.getLogger("instagram_adk.strategist")


def run_strategist_agent(ctx: Any) -> str:
    """Stage 1 Node: Identifies Audience Cohort, calibrates EQ, and evolves script into CoreNarrative."""
    state = ctx.state
    raw_account = state.get("account")
    account = AccountContext.model_validate(raw_account)

    raw_user_script = state.get("raw_user_script")
    requested_topic = state.get("requested_topic")
    requested_emotion = state.get("requested_emotion")
    critic_feedback = (state.get("critic") or {}).get("feedback", "")

    cohorts_summary = "\n".join([
        f"- ID: {c.segment_id} | Name: {c.name} | Fears: {', '.join(c.core_fears)} | Resonance: {c.tone_resonance}"
        for c in account.audience_cohorts
    ])

    system_instruction = f"""You are the Lead Social Media Strategist and Editorial Director for {account.name} ({account.handle}).
MISSION: {account.mission}
TONE RULES: {'; '.join(account.tone_rules)}
FORBIDDEN: {'; '.join(account.forbidden_terms)}

AVAILABLE AUDIENCE COHORTS FOR THIS ACCOUNT:
{cohorts_summary}

YOUR TASK:
1. Cohort Matching: Analyze the input topic/script and select the single best-fit audience cohort ID from the available list that will have maximum emotional resonance.
2. EQ Calibration: Formulate the target emotional arc (use '{requested_emotion}' if specified, otherwise infer the highest-converting emotion for this account's mission).
3. Script Evolution: Evolve the input idea/raw notes into a high-retention Core Narrative with:
   - Compelling curiosity/agitation hook (0-3s attention grabber)
   - Core insight (unveiling the underlying truth or solution)
   - 3 actionable bullet takeaways
   - Clear conversion CTA
"""

    prompt = f"""Target Account: {account.name} ({account.handle})
User Raw Script/Notes: {raw_user_script or 'None provided'}
User Requested Topic: {requested_topic or 'Auto-select high-performing topic for channel mission'}
Requested Emotion: {requested_emotion or 'Auto-infer based on mission'}
Previous Revision Critique (if any): {critic_feedback or 'None (initial run)'}

Generate a structured CoreNarrative output."""

    def fallback_generator() -> CoreNarrative:
        # High quality offline fallback calibrated to account
        matched_cohort = account.audience_cohorts[0]
        if "fraud" in account.account_id or "rights" in account.account_id:
            if raw_user_script and ("fresher" in raw_user_script.lower() or "bond" in raw_user_script.lower()):
                matched_cohort = account.audience_cohorts[0]
            elif len(account.audience_cohorts) > 1:
                matched_cohort = account.audience_cohorts[1]  # mid-senior corporate

            target_eq = requested_emotion or "Righteous Indignation & Legal Empowerment"

            # Dynamically adapt to specific script details if provided
            script_lower = (raw_user_script or "").lower()
            if "linkedin" in script_lower or "retaliat" in script_lower:
                hook = "Withholding an ex-employee's earned salary because they voiced grievances on LinkedIn isn't HR policy—it's illegal retaliation."
                core_insight = "Under the Payment of Wages Act and statutory labour norms, earned wages and Full & Final settlements cannot be held hostage over personal vendettas or public grievances. Earned salary is a statutory obligation, not a discretionary bonus."
                takeaways = [
                    "Document every broken settlement commitment with date-stamped email chains.",
                    "Withholding FnF past statutory limits is non-negotiable wage theft, regardless of social media posts.",
                    "File an immediate grievance with the Labour Commissioner and issue a formal 15-day statutory notice."
                ]
                cta = "Facing FnF withholding or retaliation? Know your statutory exit rights. Save this checklist and comment 'RIGHTS' for the legal notice draft."
            elif "month" in script_lower or "delay" in script_lower or "notice" in script_lower:
                hook = "Months of silence and broken HR promises on your Full & Final settlement isn't 'processing time'—it's an interest-free loan on your hard-earned wages."
                core_insight = "Under statutory labor law, an employer is legally mandated to disburse all earned dues upon completion of notice period. Withholding FnF to coerce silence is legally untenable."
                takeaways = [
                    "Document every follow-up via registered email, not unrecorded phone calls.",
                    "Send a formal 15-day statutory demand notice citing Section 15 of the Payment of Wages Act.",
                    "Escalate to the Labour Commissioner before signing any conditional liability waivers."
                ]
                cta = "Know your exit rights. Save this checklist and comment 'RIGHTS' for the statutory notice template."
            else:
                hook = "75 days of silence on your Full & Final settlement isn't 'HR processing time'—it's an interest-free loan on your hard-earned salary."
                core_insight = "Under statutory labor law, an employer is obligated to clear all dues within the statutory window after your last working day. Withholding FnF to coerce release signatures is legally untenable."
                takeaways = [
                    "Document every follow-up via registered email, not unrecorded phone calls.",
                    "Send a formal 15-day statutory legal notice citing Section 15 of the Payment of Wages Act.",
                    "File an online grievance via the Samadhan Labor Portal before signing any conditional waivers."
                ]
                cta = "Know your exit rights. Save this checklist and comment 'RIGHTS' for the statutory notice template."

        elif "fintech" in account.account_id:
            matched_cohort = account.audience_cohorts[0]
            target_eq = requested_emotion or "Financial Reassurance & Stress Relief"
            hook = "The $1,000 emergency fund rule works, but 90% of young earners make this one fatal mistake with it."
            core_insight = "Keeping your emergency cushion in your primary checking account guarantees lifestyle creep. It needs to be automated and frictionless, yet out of immediate swipe reach."
            takeaways = [
                "Automate $5/day savings transfers immediately on payday morning.",
                "Park emergency reserves in a dedicated high-yield liquid instrument, not checking.",
                "Build the first 30 days of safety before touching volatile equity investments."
            ]
            cta = "Take control of your money today. Comment 'SAVE' to get our automated 30-day budget template."

        else:
            matched_cohort = account.audience_cohorts[0]
            target_eq = requested_emotion or "Introspective Clarity & Founder Ambition"
            hook = "Most first-time founders hire for resumes when they desperately need momentum and high agency."
            core_insight = "Early-stage velocity is crushed when you hire corporate specialists before finding product-market fit. Your first 10 team members must be problem-solvers who thrive in ambiguity."
            takeaways = [
                "Test candidates for agency: give them an open-ended real problem with no instructions.",
                "Hire generalists who write code, talk to users, and fix broken processes.",
                "Fire fast when cultural misalignment or political posturing appears."
            ]
            cta = "Building your core team? Save this framework and share your biggest hiring lesson below."

        return CoreNarrative(
            selected_cohort_id=matched_cohort.segment_id,
            cohort_name=matched_cohort.name,
            target_emotion=target_eq,
            hook=hook,
            core_insight=core_insight,
            actionable_takeaways=takeaways,
            call_to_action=cta,
            emotional_arc=f"Agitation ({target_eq.split('&')[0].strip()}) -> Clarity -> Empowerment",
        )

    narrative = call_structured_gemini(
        prompt=prompt,
        system_instruction=system_instruction,
        response_schema=CoreNarrative,
        fallback_factory=fallback_generator,
    )

    state["narrative"] = narrative.model_dump()
    state["status"] = "narrative_evolved"

    logger.info(
        f"✓ Stage 1 Narrative Evolved: Cohort '{narrative.cohort_name}' | "
        f"EQ: '{narrative.target_emotion}' | Hook: '{narrative.hook[:60]}...'"
    )
    return "narrative_ready"
