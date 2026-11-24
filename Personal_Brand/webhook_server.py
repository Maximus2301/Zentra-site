"""
FastAPI Serverless Webhook Server for Personal Brand Agent on Google Cloud Run.
Hardened with fail-closed Telegram secret token verification, constant-time admin
endpoint protection, and sanitized health checks.
"""
from __future__ import annotations

import hmac
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query, Request
import requests
from telegram import Update

# Ensure workspace root is in path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Personal_Brand.config.settings import TELEGRAM_BOT_TOKEN
from Personal_Brand.hitl.onboarding_bot import create_bot_app

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("personal_brand.webhook_server")

TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
IS_CLOUD_RUN = bool(os.getenv("K_SERVICE"))
REQUIRE_WEBHOOK_SECRET = (
    os.getenv("WEBHOOK_REQUIRE_SECRET", "true" if IS_CLOUD_RUN else "false").lower() == "true"
)

ptb_app = create_bot_app()


def _verify_admin_key(x_admin_key: Optional[str]) -> None:
    """Rejects unauthenticated calls to webhook management endpoints."""
    if not ADMIN_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Admin endpoints disabled (ADMIN_API_KEY not configured).",
        )
    if not x_admin_key or not hmac.compare_digest(x_admin_key, ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid admin key.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes and manages python-telegram-bot application lifecycle."""
    logger.info("⚡ Waking up Personal Brand Webhook container...")
    await ptb_app.initialize()
    await ptb_app.start()
    yield
    logger.info("💤 Shutting down PTB application...")
    await ptb_app.stop()
    await ptb_app.shutdown()


app = FastAPI(
    title="Personal Brand Agent — Cloud Run Serverless Webhook",
    description="Multi-tenant hardened Telegram webhook service.",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/")
@app.get("/health")
async def health_check():
    """Sanitized health check endpoint (exposes zero tenant/creator PII)."""
    return {
        "status": "healthy",
        "service": "personal-brand-agent",
        "version": "2.0.0",
    }


@app.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
):
    """
    Main webhook receiver: validates Telegram secret token in constant time,
    deserializes Update, and dispatches to tenant-isolated bot handlers.
    """
    if REQUIRE_WEBHOOK_SECRET and not TELEGRAM_WEBHOOK_SECRET:
        logger.error("TELEGRAM_WEBHOOK_SECRET is required in production but missing.")
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")

    if TELEGRAM_WEBHOOK_SECRET:
        if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
            x_telegram_bot_api_secret_token, TELEGRAM_WEBHOOK_SECRET
        ):
            logger.warning("Rejected webhook call with invalid secret token.")
            raise HTTPException(status_code=403, detail="Invalid Telegram secret token.")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    update = Update.de_json(data, ptb_app.bot)
    if not update:
        raise HTTPException(status_code=400, detail="Could not parse Telegram Update.")

    await ptb_app.process_update(update)
    return {"status": "ok"}


@app.post("/api/set-webhook")
async def set_telegram_webhook(
    webhook_url: str = Query(..., description="Full Cloud Run public HTTPS URL including /webhook/telegram"),
    secret_token: Optional[str] = Query(None, description="Optional secret token for verification"),
    x_admin_key: Optional[str] = Header(None),
):
    """Admin-only endpoint to configure Telegram webhook destination."""
    _verify_admin_key(x_admin_key)

    token = TELEGRAM_BOT_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN not configured.")

    secret = secret_token or TELEGRAM_WEBHOOK_SECRET
    params = {"url": webhook_url, "drop_pending_updates": False}
    if secret:
        params["secret_token"] = secret

    res = requests.post(f"https://api.telegram.org/bot{token}/setWebhook", json=params, timeout=10)
    return {"telegram_response": res.json(), "configured_url": webhook_url}


@app.post("/api/delete-webhook")
async def delete_telegram_webhook(x_admin_key: Optional[str] = Header(None)):
    """Admin-only endpoint to remove webhook."""
    _verify_admin_key(x_admin_key)
    token = TELEGRAM_BOT_TOKEN
    res = requests.post(f"https://api.telegram.org/bot{token}/deleteWebhook", timeout=10)
    return res.json()
