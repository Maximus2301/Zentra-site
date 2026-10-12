"""Comprehensive automated verification tests for the Instagram ADK 2.0 system."""
from __future__ import annotations

import logging
from pathlib import Path
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
        active_formats=["static_post", "story"],
    )

    assert result["account"]["account_id"] == "fintech_save_smart"
    assert result["status"] == "published"
    assert "static_post" in result
    assert "story_sequence" in result
    assert Path(result["preview_html_path"]).exists()

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

    print("✓ Test 3 Passed! Reel duration:", result["reel"]["duration_seconds"], "seconds")


if __name__ == "__main__":
    test_workplace_rights_campaign()
    test_fintech_campaign()
    test_executive_branding_campaign()
    print("\n🎉 ALL 3 MULTI-ACCOUNT ADK 2.0 WORKFLOW TESTS PASSED PERFECTLY!")
