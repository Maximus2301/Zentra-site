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
    """Test campaign generation with active authenticated session (<=30s: In-Dashboard MP4)."""
    payload = {
        "account_id": "alex_tech_ceo",
        "raw_user_script": "Founders must focus on velocity and shipping modular agents instead of 6-month monolithic rewrites.",
        "requested_topic": "Velocity as Moat: Fast ADK Deployments",
        "requested_emotion": "Clarity & Founder Conviction",
        "requested_duration_seconds": 15,
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
    assert data["video_routing"] == "in_dashboard_mp4"
    assert data["video_url"] is not None
    assert data["video_url"].endswith(".mp4")
    assert data["critic_review"]["score"] >= 8.0
    print(f"✓ <=30s In-Dashboard Video Generation verified: {data['video_url']}")


def test_google_vids_workspace_generation(valid_token: str):
    """Test campaign generation with >30s duration routing to Google Vids Workspace."""
    payload = {
        "account_id": "fintech_save_smart",
        "raw_user_script": "Emergency fund setup in 3 automated steps.",
        "requested_topic": "Wealth Automation Mastery",
        "requested_emotion": "Financial Freedom",
        "requested_duration_seconds": 45,
        "active_formats": ["reel"]
    }
    response = client.post(
        "/api/campaign/generate",
        json=payload,
        headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200, f"Error: {response.text}"
    data = response.json()
    assert data["video_routing"] == "google_vids_workspace"
    assert data["google_vids_blueprint"] is not None
    blueprint = data["google_vids_blueprint"]
    assert blueprint["vids_launcher_url"] == "https://vids.new"
    assert "google_vids_prompt" in blueprint
    assert len(blueprint["scenes"]) >= 4
    print("✓ >30s Google Vids Workspace Route verified: Prompt & Blueprint ready for vids.new")


def test_session_history_and_superuser_access(admin_token: str):
    """Test user-specific session history and superuser (admin) global auditing."""
    # 1. Login as standard user vyantec@gmail.com
    vyan_login = client.post("/api/auth/login", json={"username": "vyantec@gmail.com", "password": "ZentraVyan2026!"})
    assert vyan_login.status_code == 200
    vyan_token = vyan_login.json()["access_token"]
    assert vyan_login.json()["user"]["role"] == "creator"

    # 2. Standard user generates a campaign
    vyan_gen = client.post(
        "/api/campaign/generate",
        json={"account_id": "alex_tech_ceo", "raw_user_script": "Vyan content draft test", "requested_duration_seconds": 15},
        headers={"Authorization": f"Bearer {vyan_token}"}
    )
    assert vyan_gen.status_code == 200
    vyan_data = vyan_gen.json()
    vyan_session_id = vyan_data.get("session_id")
    assert vyan_session_id is not None
    print(f"✓ Standard user generated session: {vyan_session_id}")

    # 3. Standard user queries /api/history
    vyan_history = client.get("/api/history", headers={"Authorization": f"Bearer {vyan_token}"})
    assert vyan_history.status_code == 200
    vh_data = vyan_history.json()
    assert vh_data["is_admin"] is False
    assert any(s["session_id"] == vyan_session_id for s in vh_data["sessions"])
    print("✓ Standard user history returned successfully")

    # 4. Standard user tries to query /api/history/users (must get 403 Forbidden)
    forbidden_users = client.get("/api/history/users", headers={"Authorization": f"Bearer {vyan_token}"})
    assert forbidden_users.status_code == 403
    print("✓ Standard user forbidden from accessing /api/history/users (403 verified)")

    # 5. Superuser (admin) queries /api/history without all_users
    admin_history = client.get("/api/history", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_history.status_code == 200
    assert admin_history.json()["is_admin"] is True

    # 6. Superuser (admin) queries /api/history with all_users=true
    admin_all_history = client.get("/api/history?all_users=true", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_all_history.status_code == 200
    all_sess = admin_all_history.json()["sessions"]
    # Admin must see Vyan's session
    assert any(s["session_id"] == vyan_session_id for s in all_sess)
    print("✓ Superuser (admin) can see sessions created by standard users (all_users=true)")

    # 7. Superuser (admin) queries /api/history/users
    admin_users = client.get("/api/history/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_users.status_code == 200
    assert "users" in admin_users.json()
    print("✓ Admin successfully accessed user list from /api/history/users")

    # 8. Retrieve session detail via /api/history/{session_id}
    detail_res = client.get(f"/api/history/{vyan_session_id}", headers={"Authorization": f"Bearer {vyan_token}"})
    assert detail_res.status_code == 200
    assert detail_res.json()["session_id"] == vyan_session_id

    # 9. Admin can also retrieve Vyan's session detail
    admin_detail = client.get(f"/api/history/{vyan_session_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_detail.status_code == 200
    assert admin_detail.json()["session_id"] == vyan_session_id
    print("✓ Admin superuser access to individual user session verified")


if __name__ == "__main__":
    test_health_check()
    test_root_creator_studio_served()
    test_list_accounts()
    test_unauthenticated_generate_rejected()
    active_token = test_authentication_and_password_change_flow()
    test_authenticated_campaign_generation(active_token)
    test_google_vids_workspace_generation(active_token)
    test_session_history_and_superuser_access(active_token)
    print("\n🎉 ALL TESTS (AUTH, IN-DASHBOARD VIDEO, GOOGLE VIDS & MULTI-USER HISTORY) PASSED PERFECTLY!")


