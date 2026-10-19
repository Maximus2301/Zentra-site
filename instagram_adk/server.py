"""FastAPI Cloud Run & Web Server for the Autonomous Instagram Agent System."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Literal
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config.settings import load_all_accounts, get_account_by_id, OUTPUT_DIR
from .workflow import execute_campaign

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


class CampaignRequest(BaseModel):
    account_id: str = Field(..., description="Target account ID (workplace_rights_watch, fintech_save_smart, alex_tech_ceo)")
    raw_user_script: str | None = Field(None, description="Optional raw grievance email, rough draft notes, or bullet points")
    requested_topic: str | None = Field(None, description="Optional high-level topic")
    requested_emotion: str | None = Field(None, description="Optional target emotion (e.g., 'Righteous Indignation', 'Financial Relief')")
    active_formats: list[str] = Field(
        default=["static_post", "story", "reel", "status"],
        description="Deliverable formats to generate"
    )


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
async def generate_campaign(req: CampaignRequest) -> dict[str, Any]:
    """Executes the full 7-stage ADK 2.0 workflow pipeline and returns structured deliverables."""
    account = get_account_by_id(req.account_id)
    if not account:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown account_id: '{req.account_id}'. Use /api/accounts to see configured profiles."
        )

    logger.info(f"Received campaign generation request for channel: {req.account_id}")
    try:
        result = await execute_campaign(
            account_id=req.account_id,
            raw_user_script=req.raw_user_script,
            requested_topic=req.requested_topic,
            requested_emotion=req.requested_emotion,
            active_formats=req.active_formats,
            user_id="cloud_api_user",
        )
    except Exception as e:
        logger.error(f"Campaign execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent workflow error: {str(e)}")

    preview_file = OUTPUT_DIR / f"preview_{req.account_id}.html"
    preview_url = f"/api/campaign/preview/{req.account_id}" if preview_file.exists() else None

    return {
        "status": result.get("status", "completed"),
        "account_id": req.account_id,
        "channel_name": result.get("account", {}).get("name"),
        "handle": result.get("account", {}).get("handle"),
        "cohort_matched": result.get("narrative", {}).get("cohort_name"),
        "target_emotion": result.get("narrative", {}).get("target_emotion"),
        "core_hook": result.get("narrative", {}).get("hook"),
        "critic_review": result.get("critic"),
        "formats_generated": list((result.get("campaign_bundle") or {}).get("formats", {}).keys()),
        "media_assets": {k: f"/media/{Path(v).name}" for k, v in result.get("media_assets", {}).items()},
        "preview_url": preview_url,
        "bundle": result.get("campaign_bundle"),
    }


@app.get("/api/campaign/preview/{account_id}", response_class=HTMLResponse)
async def get_preview_html(account_id: str) -> HTMLResponse:
    """Returns the standalone interactive iPhone 16 Pro visualizer HTML."""
    preview_file = OUTPUT_DIR / f"preview_{account_id}.html"
    if not preview_file.exists():
        raise HTTPException(status_code=404, detail=f"No preview generated for '{account_id}' yet.")
    return HTMLResponse(content=preview_file.read_text(encoding="utf-8"), status_code=200)
