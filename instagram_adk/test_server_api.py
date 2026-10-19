"""FastAPI test suite for Zentra Autonomous Instagram Campaign Server with Authentication."""
from __future__ import annotations

import sys
from pathlib import Path
from starlette.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from instagram_adk.server import app
from instagram_adk.auth import init_user_store

client = TestClient(app)


def test_health_check():
    """Verify Cloud Run liveness/readiness probe endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "zentra-instagram-agent"
    print("✓ Health check endpoint verified")


def test_root_creator_studio_served():
    """Verify Creator Studio HTML is served directly at the root URL."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Creator Studio" in response.text
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


def test_unauthenticated_generate_rejected():
    """Verify 401 Unauthorized when generating campaign without token."""
    payload = {
        "account_id": "alex_tech_ceo",
        "raw_user_script": "Test unauthorized script"
    }
    response = client.post("/api/campaign/generate", json=payload)
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]
    print("✓ Unauthenticated generate rejected with 401")


def test_authentication_and_password_change_flow():
    """Test full login, must_change_password enforcement, and password change."""
    # Reset store for clean test
    init_user_store(force=True)

    # 1. Login with invalid password fails
    bad_login = client.post("/api/auth/login", json={"username": "admin", "password": "WrongPassword"})
    assert bad_login.status_code == 401

    # 2. Login with initial default password succeeds
    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "ZentraCreator2026!"})
    assert admin_login.status_code == 200
    login_data = admin_login.json()
    assert "access_token" in login_data
    assert login_data["user"]["must_change_password"] is True
    initial_token = login_data["access_token"]
    print("✓ Admin login with initial default password succeeded (must_change_password=True)")

    # 3. Attempting to generate campaign with must_change_password=True triggers 403
    forbidden_res = client.post(
        "/api/campaign/generate",
        json={"account_id": "alex_tech_ceo", "raw_user_script": "Prompt test"},
        headers={"Authorization": f"Bearer {initial_token}"}
    )
    assert forbidden_res.status_code == 403
    assert "First-time login detected" in forbidden_res.json()["detail"]
    print("✓ Mandatory first-time password change enforced with 403 on campaign generation")

    # 4. Change password to new secure password
    new_password = "ZentraNewAdminPass2026!#"
    change_res = client.post(
        "/api/auth/change-password",
        json={"old_password": "ZentraCreator2026!", "new_password": new_password},
        headers={"Authorization": f"Bearer {initial_token}"}
    )
    assert change_res.status_code == 200
    new_token = change_res.json()["access_token"]
    print("✓ Password successfully changed and new token issued")

    # 5. Check /api/auth/me with new token shows must_change_password=False
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["must_change_password"] is False
    print("✓ Session verified: must_change_password is now False")

    # 6. Test second user: vyantec@gmail.com
    vyan_login = client.post("/api/auth/login", json={"username": "vyantec@gmail.com", "password": "ZentraVyan2026!"})
    assert vyan_login.status_code == 200
    assert vyan_login.json()["user"]["email"] == "vyantec@gmail.com"
    assert vyan_login.json()["user"]["must_change_password"] is False
    print("✓ vyantec@gmail.com authenticated successfully")

    return new_token


def test_authenticated_campaign_generation(valid_token: str):
    """Test campaign generation with active authenticated session."""
    payload = {
        "account_id": "alex_tech_ceo",
        "raw_user_script": "Founders must focus on velocity and shipping modular agents instead of 6-month monolithic rewrites.",
        "requested_topic": "Velocity as Moat: Fast ADK Deployments",
        "requested_emotion": "Clarity & Founder Conviction",
        "active_formats": ["static_post", "story", "reel", "status"]
    }
    response = client.post(
        "/api/campaign/generate",
        json=payload,
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert data["status"] in ("published", "completed")
    assert data["account_id"] == "alex_tech_ceo"
    assert data["channel_name"] == "Alex Vance | Tech CEO"
    assert data["critic_review"]["score"] >= 8.0
    print("✓ Authenticated campaign generation succeeded with HTTP 200!")


if __name__ == "__main__":
    test_health_check()
    test_root_creator_studio_served()
    test_list_accounts()
    test_unauthenticated_generate_rejected()
    active_token = test_authentication_and_password_change_flow()
    test_authenticated_campaign_generation(active_token)
    print("\n🎉 ALL AUTHENTICATION & CAMPAIGN TESTS PASSED PERFECTLY!")
