"""Comprehensive automated verification tests for the Instagram ADK 2.0 system."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from instagram_adk.workflow import run_campaign_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def test_workplace_rights_campaign():
    print("\n" + "=" * 60)
    print("TEST 1: Corporate Rights & Unpaid Salary Awareness")
    print("=" * 60)

    raw_script = "My previous company refused to pay my 2 months notice period salary and delayed my Full and Final settlement for 80 days. What can I do?"
    result = run_campaign_sync(
        account_id="workplace_rights_watch",
        raw_user_script=raw_script,
        requested_emotion="Righteous Indignation & Legal Empowerment",
        active_formats=["static_post", "story", "reel", "status"],
    )

    assert result["account"]["account_id"] == "workplace_rights_watch"
    assert result["status"] == "published"
    assert "narrative" in result
    assert result["narrative"]["selected_cohort_id"] in ("mid_to_senior_corporate", "freshers_and_entry_level")
    assert result["critic"]["score"] >= 8.5
    assert Path(result["preview_html_path"]).exists()
    assert len(result["media_assets"]) == 4

    # Semantic checks: ensure labor rights and disclaimer are present
    caption = result.get("static_post", {}).get("caption", "").lower()
    assert "disclaimer" in caption, "Mandatory legal disclaimer must be present in static post"
    story_slides = result.get("story_sequence", [])
    assert len(story_slides) == 4, "Story sequence must have 4 slides"
    assert "resigned" in story_slides[0]["headline"].lower() or "exit" in story_slides[0]["headline"].lower()

    print("✓ Test 1 Passed! Generated assets:", list(result["media_assets"].keys()))
    print("Preview HTML:", result["preview_html_path"])


def test_fintech_campaign():
    print("\n" + "=" * 60)
    print("TEST 2: FinTech Outreach & Savings Automation")
    print("=" * 60)

    result = run_campaign_sync(
        account_id="fintech_save_smart",
        requested_topic="Automating your first $1,000 emergency fund without lifestyle pain",
        requested_emotion="Financial Reassurance & Stress Relief",
        active_formats=["static_post", "story", "reel"],
    )

    assert result["account"]["account_id"] == "fintech_save_smart"
    assert result["status"] == "published"
    assert "static_post" in result
    assert "story_sequence" in result
    assert Path(result["preview_html_path"]).exists()

    # Semantic domain isolation checks: NO labor dispute or FnF contamination!
    story_0 = result["story_sequence"][0]["headline"].lower()
    assert "checking" in story_0 or "savings" in story_0 or "money" in story_0, \
        f"Fintech story must be finance-focused, got: {story_0}"
    assert "fnf" not in story_0 and "resigned" not in story_0, \
        "Cross-domain contamination detected: Labor dispute copy found in FinTech story!"

    # Verify investment disclaimer present
    caption = result["static_post"]["caption"].lower()
    assert "market risks" in caption or "invest" in caption, "Mandatory financial disclaimer missing"

    # Verify hashtags domain-appropriate
    tags = result["static_post"]["hashtags"]
    assert any("finance" in t or "invest" in t or "smart" in t for t in tags)
    assert not any("laborlaw" in t or "fairpay" in t for t in tags), "Labor hashtags leaked to FinTech!"

    print("✓ Test 2 Passed! FinTech Cohort matched:", result["narrative"]["cohort_name"])


def test_executive_branding_campaign():
    print("\n" + "=" * 60)
    print("TEST 3: Executive Thought Leadership")
    print("=" * 60)

    raw_notes = "Early-stage founders waste months hiring specialists when they desperately need high-agency generalists."
    result = run_campaign_sync(
        account_id="alex_tech_ceo",
        raw_user_script=raw_notes,
        requested_emotion="Introspective Clarity & Founder Ambition",
        active_formats=["reel", "status"],
    )

    assert result["account"]["account_id"] == "alex_tech_ceo"
    assert result["status"] == "published"
    assert "reel" in result
    assert "status_card" in result
    assert Path(result["preview_html_path"]).exists()

    # Semantic domain checks: NO labor or corporate grievance terms
    reel_caption = result["reel"]["caption"].lower()
    assert "hiring" in reel_caption or "founders" in reel_caption or "agency" in reel_caption or "specialists" in reel_caption
    assert "labour commissioner" not in reel_caption and "fnf" not in reel_caption

    # Check Reel on-screen text
    reel_scenes = result["reel"]["scenes"]
    assert len(reel_scenes) >= 3
    assert not any("what the law actually says" in s["on_screen_text"].lower() for s in reel_scenes), \
        "Labor law reel scene leaked to Tech CEO reel screenplay!"

    print("✓ Test 3 Passed! Reel duration:", result["reel"]["duration_seconds"], "seconds")


def test_matter_motors_grievance_campaign():
    print("\n" + "=" * 60)
    print("TEST 4: Real Grievance Email (Matter Motors Case)")
    print("=" * 60)

    grievance_script = (
        "Back in August, you were fully aware of the formal labour complaint I filed and legal notice sent. "
        "At that time, on our call, you committed that my FnF and pending salary would be settled by end of month. "
        "Telling an ex-employee not to call and explicitly stating that FnF is being withheld because I voiced my "
        "grievance on LinkedIn is blatant retaliation. Withholding an employee's rightfully earned wages for over "
        "five months is unconscionable wage theft."
    )
    result = run_campaign_sync(
        account_id="workplace_rights_watch",
        raw_user_script=grievance_script,
        requested_emotion="Righteous Indignation & Legal Empowerment",
        active_formats=["static_post", "reel"],
    )

    assert result["account"]["account_id"] == "workplace_rights_watch"
    assert result["status"] == "published"
    assert "retaliation" in result["narrative"]["hook"].lower() or "linkedin" in result["narrative"]["hook"].lower() or "withholding" in result["narrative"]["hook"].lower()
    assert result["critic"]["score"] >= 8.5
    print("✓ Test 4 Passed! Evolved Hook:", result["narrative"]["hook"])


if __name__ == "__main__":
    test_workplace_rights_campaign()
    test_fintech_campaign()
    test_executive_branding_campaign()
    test_matter_motors_grievance_campaign()
    print("\n🎉 ALL 4 MULTI-ACCOUNT ADK 2.0 WORKFLOW TESTS PASSED PERFECTLY WITH ZERO CONTAMINATION!")
