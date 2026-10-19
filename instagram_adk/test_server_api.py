"""FastAPI test suite for Zentra Autonomous Instagram Campaign Server."""
from __future__ import annotations

import sys
from pathlib import Path
from starlette.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from instagram_adk.server import app

client = TestClient(app)


def test_health_check():
    """Verify Cloud Run liveness/readiness probe endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "zentra-instagram-agent"
    assert data["version"] == "1.1.0"
    assert data["engine"] == "google-adk-2.11.0"
    print("✓ Health check endpoint verified")


def test_root_creator_studio_served():
    """Verify Creator Studio HTML is served directly at the root URL."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Creator Studio" in response.text
    assert "Zentra AI" in response.text
    assert "Autonomous Multi-Agent Publisher" in response.text
    print("✓ Root Creator Studio UI verified")


def test_list_accounts():
    """Verify configured brand channels and audience cohorts."""
    response = client.get("/api/accounts")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    account_ids = [a["account_id"] for a in data["accounts"]]
    assert "workplace_rights_watch" in account_ids
    assert "fintech_save_smart" in account_ids
    assert "alex_tech_ceo" in account_ids
    print(f"✓ List accounts verified: {account_ids}")


def test_cors_headers():
    """Verify CORS allow headers for zentraai.in production domain."""
    headers = {
        "Origin": "https://zentraai.in",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/campaign/generate", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://zentraai.in"
    print("✓ CORS preflight for https://zentraai.in verified")


def test_generate_invalid_account():
    """Verify 400 error handling for non-existent accounts."""
    payload = {
        "account_id": "non_existent_channel_xyz",
        "raw_user_script": "Test script"
    }
    response = client.post("/api/campaign/generate", json=payload)
    assert response.status_code == 400
    assert "Unknown account_id" in response.json()["detail"]
    print("✓ Invalid account 400 check verified")


def test_generate_valid_campaign_workflow():
    """Execute end-to-end campaign generation through the FastAPI API endpoint."""
    payload = {
        "account_id": "alex_tech_ceo",
        "raw_user_script": "Founders must focus on velocity and shipping modular agents instead of 6-month monolithic rewrites.",
        "requested_topic": "Velocity as Moat: Fast ADK Deployments",
        "requested_emotion": "Clarity & Founder Conviction",
        "active_formats": ["static_post", "story", "reel", "status"]
    }
    response = client.post("/api/campaign/generate", json=payload)
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()

    assert data["status"] in ("published", "completed")
    assert data["account_id"] == "alex_tech_ceo"
    assert data["channel_name"] == "Alex Vance | Tech CEO"
    assert data["critic_review"]["score"] >= 8.0
    assert len(data["formats_generated"]) >= 3
    assert data["preview_url"] is not None

    # Verify preview endpoint returns HTML
    preview_res = client.get(data["preview_url"])
    assert preview_res.status_code == 200
    assert "text/html" in preview_res.headers.get("content-type", "")
    assert "Alex Vance" in preview_res.text or "alex_tech_ceo" in preview_res.text

    print(f"✓ Campaign generation API endpoint verified! Critic score: {data['critic_review']['score']}")
    print(f"✓ Formats: {data['formats_generated']}")
    print(f"✓ Preview URL: {data['preview_url']}")


if __name__ == "__main__":
    test_health_check()
    test_root_creator_studio_served()
    test_list_accounts()
    test_cors_headers()
    test_generate_invalid_account()
    test_generate_valid_campaign_workflow()
    print("\n🎉 ALL FASTAPI SERVER TESTS PASSED!")
