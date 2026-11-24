#!/usr/bin/env bash
# ==============================================================================
# Personal Brand Agent — Google Cloud Run Zero-Cost Serverless Deployment
# Deploys with min-instances=0 so it sleeps at $0 cost and wakes on Telegram triggers
# ==============================================================================

set -euo pipefail

SERVICE_NAME="personal-brand-agent"
DEFAULT_REGION="asia-south1"
DEFAULT_MEMORY="1Gi"
DEFAULT_CPU="1"
MIN_INSTANCES="0"    # Crucial: 0 instances when idle = $0.00 compute cost!
MAX_INSTANCES="2"

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}====================================================================${NC}"
echo -e "${BOLD}${CYAN}  Personal Brand Agent — Cloud Run Serverless Deployment             ${NC}"
echo -e "${BOLD}${CYAN}====================================================================${NC}"

# 1. Check gcloud CLI
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}[ERROR] 'gcloud' CLI is not installed or not in PATH.${NC}"
    exit 1
fi

# 2. Check GCP Project
GCP_PROJECT="${GCP_PROJECT:-branding-marketing-zentra}"
echo -e "${GREEN}✓ Using GCP Project: ${BOLD}${GCP_PROJECT}${NC}"

REGION="${GCP_REGION:-${DEFAULT_REGION}}"
echo -e "${GREEN}✓ Using Region: ${BOLD}${REGION}${NC}"

# 3. Read Telegram Credentials from .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(dirname "${SCRIPT_DIR}")"

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"
GEMINI_KEY="${GEMINI_API_KEY:-}"
GROQ_KEY="${GROQ_API_KEY:-}"
OPENROUTER_KEY="${OPENROUTER_API_KEY:-}"

if [ -f "${WORKSPACE_ROOT}/.env" ]; then
    BOT_TOKEN="${BOT_TOKEN:-$(grep -E "^TELEGRAM_BOT_TOKEN=" "${WORKSPACE_ROOT}/.env" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)}"
    CHAT_ID="${CHAT_ID:-$(grep -E "^TELEGRAM_CHAT_ID=" "${WORKSPACE_ROOT}/.env" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)}"
    GEMINI_KEY="${GEMINI_KEY:-$(grep -E "^GEMINI_API_KEY=" "${WORKSPACE_ROOT}/.env" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)}"
    GROQ_KEY="${GROQ_KEY:-$(grep -E "^GROQ_API_KEY=" "${WORKSPACE_ROOT}/.env" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)}"
    OPENROUTER_KEY="${OPENROUTER_KEY:-$(grep -E "^OPENROUTER_API_KEY=" "${WORKSPACE_ROOT}/.env" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)}"
fi

if [ -z "${BOT_TOKEN}" ]; then
    echo -e "${RED}[ERROR] TELEGRAM_BOT_TOKEN not found in environment or .env file.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Telegram Bot Token detected.${NC}"

# Generate random webhook & admin secrets if not already set
WEBHOOK_SECRET="${TELEGRAM_WEBHOOK_SECRET:-$(openssl rand -hex 16)}"
ADMIN_KEY="${ADMIN_API_KEY:-$(openssl rand -hex 20)}"

# 4. Enable Google Cloud APIs
echo -e "\n${BOLD}${CYAN}[Step 1/3] Enabling Google Cloud Services...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    containerregistry.googleapis.com \
    --project="${GCP_PROJECT}"

# 5. Build Container with Cloud Build
echo -e "\n${BOLD}${CYAN}[Step 2/3] Building Container with Google Cloud Build...${NC}"
cd "${WORKSPACE_ROOT}"

IMAGE_TAG="gcr.io/${GCP_PROJECT}/${SERVICE_NAME}"

gcloud builds submit \
    --project="${GCP_PROJECT}" \
    --config="Personal_Brand/cloudbuild.yaml" \
    .

# 6. Deploy to Cloud Run
echo -e "\n${BOLD}${CYAN}[Step 3/3] Deploying to Cloud Run (min-instances=0)...${NC}"
ENV_VARS="TELEGRAM_BOT_TOKEN=${BOT_TOKEN},TELEGRAM_CHAT_ID=${CHAT_ID},TELEGRAM_WEBHOOK_SECRET=${WEBHOOK_SECRET},ADMIN_API_KEY=${ADMIN_KEY},WEBHOOK_REQUIRE_SECRET=true,PYTHONUNBUFFERED=1"
[ -n "${GEMINI_KEY}" ] && ENV_VARS="${ENV_VARS},GEMINI_API_KEY=${GEMINI_KEY}"
[ -n "${GROQ_KEY}" ] && ENV_VARS="${ENV_VARS},GROQ_API_KEY=${GROQ_KEY}"
[ -n "${OPENROUTER_KEY}" ] && ENV_VARS="${ENV_VARS},OPENROUTER_API_KEY=${OPENROUTER_KEY}"

gcloud run deploy "${SERVICE_NAME}" \
    --project="${GCP_PROJECT}" \
    --region="${REGION}" \
    --image="${IMAGE_TAG}" \
    --platform="managed" \
    --allow-unauthenticated \
    --port="8080" \
    --memory="${DEFAULT_MEMORY}" \
    --cpu="${DEFAULT_CPU}" \
    --min-instances="${MIN_INSTANCES}" \
    --max-instances="${MAX_INSTANCES}" \
    --set-env-vars="${ENV_VARS}"

# 7. Retrieve Service URL and register Telegram Webhook
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --project="${GCP_PROJECT}" \
    --region="${REGION}" \
    --format="value(status.url)")

WEBHOOK_URL="${SERVICE_URL}/webhook/telegram"

echo -e "\n${BOLD}${CYAN}[Configuring Webhook] Pointing Telegram to Cloud Run...${NC}"
echo -e "Webhook Endpoint: ${BOLD}${CYAN}${WEBHOOK_URL}${NC}"

RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${WEBHOOK_URL}\", \"secret_token\": \"${WEBHOOK_SECRET}\", \"drop_pending_updates\": false}")

echo -e "Telegram API Response: ${RESPONSE}"

echo -e "\n${BOLD}${GREEN}====================================================================${NC}"
echo -e "${BOLD}${GREEN}  Deployment Successful! 🎉                                        ${NC}"
echo -e "${BOLD}${GREEN}====================================================================${NC}"
echo -e "Cloud Run URL:     ${BOLD}${CYAN}${SERVICE_URL}${NC}"
echo -e "Webhook Endpoint:  ${BOLD}${CYAN}${WEBHOOK_URL}${NC}"
echo -e "Idle Cost:         ${BOLD}${GREEN}\$0.00 / month (Scales to 0 instances when not in use)${NC}"
echo -e "Wakeup Behavior:   ${BOLD}Instantly awakens when you send a message/voice note on Telegram${NC}"
echo ""
echo -e "${BOLD}You can now close your laptop! The Telegram bot will run 24/7 on Google Cloud Run.${NC}"
