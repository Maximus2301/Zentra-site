"""FastAPI Cloud Run & Web Server for the Autonomous Instagram Agent System."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Literal
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from datetime import datetime, timezone
import uuid

from .config.settings import load_all_accounts, get_account_by_id, OUTPUT_DIR
from .workflow import execute_campaign
from .auth import (
    authenticate_user,
    change_user_password,
    create_session_token,
    verify_session_token,
    verify_google_id_token,
    init_user_store,
    create_new_user,
)
from .storage.session_store import (
    save_session,
    list_sessions,
    get_session,
    get_session_media_path,
    delete_session,
    list_all_active_users,
)

# Initialize user accounts store on startup
init_user_store()
security = HTTPBearer(auto_error=False)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("instagram_adk.server")

app = FastAPI(
    title="Zentra Autonomous Instagram Campaign API",
    description="Google ADK 2.0 Multi-Account Publishing and Media Synthesis Engine",
    version="1.1.0",
)

# Enable CORS for zentraai.in and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://zentraai.in",
        "https://www.zentraai.in",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
    ],
    allow_origin_regex=r"https://.*\.zentraai\.in",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated media assets
if OUTPUT_DIR.exists():
    app.mount("/media", StaticFiles(directory=str(OUTPUT_DIR)), name="media")

# Creator Studio UI directory resolution (works locally, in package, and in container)
PACKAGE_WEB_DIR = Path(__file__).resolve().parent / "web"
ROOT_CREATOR_DIR = Path(__file__).resolve().parent.parent / "creator"
LOCAL_CREATOR_DIR = Path(__file__).resolve().parent.parent / "zentra-site" / "creator"
CONTAINER_CREATOR_DIR = Path("/app/creator")

def get_creator_index_file() -> Path | None:
    for candidate in [ROOT_CREATOR_DIR / "index.html", PACKAGE_WEB_DIR / "index.html", LOCAL_CREATOR_DIR / "index.html", CONTAINER_CREATOR_DIR / "index.html"]:
        if candidate.exists():
            return candidate
    return None


@app.get("/", response_class=HTMLResponse)
async def serve_root_studio() -> HTMLResponse:
    """Serves the standalone Creator Studio UI at root."""
    creator_index = get_creator_index_file()
    if creator_index and creator_index.exists():
        return HTMLResponse(content=creator_index.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(
        content="""
        <html>
            <body style='background:#0d0d0f;color:#fff;font-family:sans-serif;padding:40px;text-align:center;'>
                <h1>Zentra Autonomous Instagram Campaign API</h1>
                <p>Google ADK 2.0 Multi-Account Publishing Engine</p>
                <p><a style='color:#c9a22a;' href='/docs'>Swagger API Docs</a> · <a style='color:#6ecfdb;' href='/healthz'>Health Check</a></p>
            </body>
        </html>
        """,
        status_code=200,
    )


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email (e.g. admin or vyantec@gmail.com)")
    password: str = Field(..., description="User password")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New desired password (minimum 6 characters)")


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., description="Google OAuth ID Token from Google Identity Services")


class CampaignRequest(BaseModel):
    account_id: str = Field(..., description="Target account ID (workplace_rights_watch, fintech_save_smart, alex_tech_ceo)")
    raw_user_script: str | None = Field(None, description="Optional raw grievance email, rough draft notes, or bullet points")
    requested_topic: str | None = Field(None, description="Optional high-level topic")
    requested_emotion: str | None = Field(None, description="Optional target emotion (e.g., 'Righteous Indignation', 'Financial Relief')")
    active_formats: list[str] = Field(
        default=["static_post", "story", "reel", "status"],
        description="Deliverable formats to generate"
    )
    requested_duration_seconds: int = Field(
        default=30,
        description="Video duration in seconds (<=30s: in-dashboard MP4; >30s: Google Vids workspace)"
    )


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict[str, Any]:
    """Dependency validating Bearer JWT/HMAC token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to access the Zentra Campaign Studio.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_session_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or token is invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


@app.post("/api/auth/login")
async def login(req: LoginRequest) -> dict[str, Any]:
    """Authenticates username/email & password and issues a signed session token."""
    valid, user, msg = authenticate_user(req.username, req.password)
    if not valid or not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)

    role = user.get("role", "admin" if user["username"] == "admin" else "creator")
    token = create_session_token(
        username=user["username"],
        email=user.get("email", ""),
        must_change_password=user.get("must_change_password", False),
        role=role,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "email": user.get("email", ""),
            "role": role,
            "must_change_password": user.get("must_change_password", False),
        },
    }


@app.post("/api/auth/change-password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Changes password for the currently logged in user and clears must_change_password."""
    username = current_user.get("sub", "")
    success, msg = change_user_password(username, req.old_password, req.new_password)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    role = current_user.get("role", "admin" if username == "admin" else "creator")
    new_token = create_session_token(
        username=username,
        email=current_user.get("email", ""),
        must_change_password=False,
        role=role,
    )
    return {
        "success": True,
        "message": "Password changed successfully.",
        "access_token": new_token,
    }


@app.post("/api/auth/google")
async def google_login(req: GoogleAuthRequest) -> dict[str, Any]:
    """Authenticates Google OAuth2 ID Token and issues a Zentra session token."""
    valid, user_info, msg = await verify_google_id_token(req.id_token)
    if not valid or not user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)

    role = "creator"
    token = create_session_token(
        username=user_info["username"],
        email=user_info["email"],
        must_change_password=False,
        role=role,
    )
    user_info["role"] = role
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_info,
    }


@app.get("/api/auth/me")
async def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Returns profile and password status of current session."""
    return {
        "username": current_user.get("sub"),
        "email": current_user.get("email"),
        "role": current_user.get("role", "admin" if current_user.get("sub") == "admin" else "creator"),
        "must_change_password": current_user.get("mcp", False),
    }


@app.get("/healthz")
@app.get("/health")
@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    """Cloud Run health check probe endpoint."""
    return {
        "status": "healthy",
        "service": "zentra-instagram-agent",
        "version": "1.1.0",
        "engine": "google-adk-2.11.0",
    }


@app.get("/api/accounts")
async def list_accounts() -> dict[str, Any]:
    """Returns all configured brand accounts, missions, and audience cohorts."""
    accounts = load_all_accounts()
    return {
        "count": len(accounts),
        "accounts": [
            {
                "account_id": a["account_id"],
                "handle": a["handle"],
                "name": a["name"],
                "category": a.get("category", ""),
                "mission": a.get("mission", ""),
                "color_palette": a.get("color_palette", []),
                "cohorts": [c["name"] for c in a.get("audience_cohorts", [])],
            }
            for a in accounts
        ],
    }


@app.post("/api/campaign/generate")
async def generate_campaign(
    req: CampaignRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Executes the full 7-stage ADK 2.0 workflow pipeline and returns structured deliverables."""
    if current_user.get("mcp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Requirement: First-time login detected for this account. Please update your password before generating campaigns.",
        )
    account = get_account_by_id(req.account_id)
    if not account:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown account_id: '{req.account_id}'. Use /api/accounts to see configured profiles."
        )

    username = current_user.get("sub", "admin")
    logger.info(f"Received campaign generation request for channel: {req.account_id} by user: {username}")
    try:
        result = await execute_campaign(
            account_id=req.account_id,
            raw_user_script=req.raw_user_script,
            requested_topic=req.requested_topic,
            requested_emotion=req.requested_emotion,
            active_formats=req.active_formats,
            requested_duration_seconds=req.requested_duration_seconds,
            user_id=username,
        )
    except Exception as e:
        logger.error(f"Campaign execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(e)}")

    preview_file = OUTPUT_DIR / f"preview_{req.account_id}.html"
    preview_url = f"/api/campaign/preview/{req.account_id}" if preview_file.exists() else None

    bundle = result.get("campaign_bundle") or {}
    reel_info = (bundle.get("formats") or {}).get("reel") or {}
    video_routing = reel_info.get("video_routing", "in_dashboard_mp4" if req.requested_duration_seconds <= 30 else "google_vids_workspace")
    reel_video_path = result.get("media_assets", {}).get("reel_video")
    reel_video_url = f"/media/{Path(reel_video_path).name}" if reel_video_path and Path(reel_video_path).exists() else None

    session_id = result.get("session_id") or str(uuid.uuid4())
    session_response = {
        "status": result.get("status", "completed"),
        "session_id": session_id,
        "user_id": username,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "account_id": req.account_id,
        "channel_name": result.get("account", {}).get("name"),
        "handle": result.get("account", {}).get("handle"),
        "cohort_matched": result.get("narrative", {}).get("cohort_name"),
        "target_emotion": result.get("narrative", {}).get("target_emotion"),
        "core_hook": result.get("narrative", {}).get("hook"),
        "critic_review": result.get("critic"),
        "formats_generated": list(bundle.get("formats", {}).keys()),
        "media_assets": {k: f"/media/{Path(v).name}" for k, v in result.get("media_assets", {}).items()},
        "video_routing": video_routing,
        "video_duration_seconds": req.requested_duration_seconds,
        "video_url": reel_video_url,
        "google_vids_blueprint": reel_info.get("google_vids_blueprint"),
        "google_vids_prompt": reel_info.get("google_vids_prompt"),
        "preview_url": preview_url,
        "bundle": bundle,
    }

    # Persist session to multi-user durable storage (GCS + local cache)
    try:
        media_files_map = dict(result.get("media_assets", {}))
        if preview_file.exists():
            media_files_map["preview_html"] = str(preview_file)
        save_session(
            user_id=username,
            session_data=session_response,
            media_files=media_files_map,
        )
    except Exception as e:
        logger.error(f"Failed to persist session to session store: {e}")

    return session_response


@app.get("/api/campaign/preview/{account_id}", response_class=HTMLResponse)
async def get_preview_html(account_id: str) -> HTMLResponse:
    """Returns the standalone interactive iPhone 16 Pro visualizer HTML."""
    preview_file = OUTPUT_DIR / f"preview_{account_id}.html"
    if not preview_file.exists():
        raise HTTPException(status_code=404, detail=f"No preview generated for '{account_id}' yet.")
    return HTMLResponse(content=preview_file.read_text(encoding="utf-8"), status_code=200)


@app.get("/api/history")
async def get_session_history(
    all_users: bool = False,
    user_filter: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieves past content creation sessions. Superuser (admin) can view all users' sessions."""
    username = current_user.get("sub", "admin")
    is_admin = current_user.get("role") == "admin" or username == "admin"
    if not is_admin:
        all_users = False
        user_filter = None

    sessions = list_sessions(
        user_id=username,
        is_admin=is_admin,
        all_users=all_users,
        user_filter=user_filter,
    )
    return {
        "status": "success",
        "count": len(sessions),
        "is_admin": is_admin,
        "current_user": username,
        "sessions": sessions,
    }


@app.get("/api/history/users")
async def get_history_users(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Admin-only: Lists all active users who have created sessions."""
    username = current_user.get("sub", "admin")
    is_admin = current_user.get("role") == "admin" or username == "admin"
    if not is_admin:
        raise HTTPException(status_code=403, detail="Superuser (admin) access required.")
    users = list_all_active_users()
    return {"status": "success", "users": users}


@app.get("/api/history/{session_id}")
async def get_session_detail(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieves complete details of a specific past session."""
    username = current_user.get("sub", "admin")
    is_admin = current_user.get("role") == "admin" or username == "admin"
    sess = get_session(
        session_id=session_id,
        user_id=username,
        is_admin=is_admin,
    )
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found or access denied.")
    return sess


@app.get("/api/history/{session_id}/media/{filename}")
async def get_history_media(
    session_id: str,
    filename: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Streams a historical media asset with authorization check."""
    username = current_user.get("sub", "admin")
    is_admin = current_user.get("role") == "admin" or username == "admin"
    media_path = get_session_media_path(
        session_id=session_id,
        filename=filename,
        user_id=username,
        is_admin=is_admin,
    )
    if not media_path or not media_path.exists():
        alt_path = OUTPUT_DIR / filename
        if alt_path.exists():
            media_path = alt_path
        else:
            raise HTTPException(status_code=404, detail="Media asset not found.")

    media_type = "video/mp4" if media_path.suffix == ".mp4" else ("image/png" if media_path.suffix == ".png" else "application/octet-stream")
    return FileResponse(media_path, media_type=media_type)


@app.delete("/api/history/{session_id}")
async def delete_history_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Deletes a past session record and associated media."""
    username = current_user.get("sub", "admin")
    is_admin = current_user.get("role") == "admin" or username == "admin"
    success = delete_session(
        session_id=session_id,
        user_id=username,
        is_admin=is_admin,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or permission denied.")
    return {"status": "deleted", "session_id": session_id}
