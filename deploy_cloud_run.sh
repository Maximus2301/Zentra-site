#!/usr/bin/env bash
# ==============================================================================
# Autonomous Instagram Agent System - Google Cloud Run Deployment Script
# Zentra AI / HYT Systems
# ==============================================================================

set -euo pipefail

# Default configuration
SERVICE_NAME="zentra-instagram-agent"
DEFAULT_REGION="asia-south1"
DEFAULT_MEMORY="1Gi"
DEFAULT_CPU="1"
MIN_INSTANCES="0"
MAX_INSTANCES="5"

# Terminal colors
BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}====================================================================${NC}"
echo -e "${BOLD}${CYAN}  Zentra AI - Autonomous Instagram Agent Cloud Run Deployment       ${NC}"
echo -e "${BOLD}${CYAN}====================================================================${NC}"

# Ensure Google Cloud SDK in PATH
if [ -d "$HOME/google-cloud-sdk/bin" ]; then
    export PATH="$HOME/google-cloud-sdk/bin:$PATH"
fi

# 1. Check gcloud CLI
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}[ERROR] 'gcloud' CLI is not installed or not in PATH.${NC}"
    echo -e "Please install the Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    echo -e "Or deploy via GitHub Actions using the provided workflow: .github/workflows/deploy-agent-cloudrun.yml"
    exit 1
fi

# 1b. Check GCP Authentication
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || echo "")
if [ -z "${ACTIVE_ACCOUNT}" ]; then
    echo -e "${YELLOW}[ACTION NEEDED] No active Google Cloud account found in gcloud.${NC}"
    echo -e "Please authenticate using one of the following:"
    echo -e "  • Standard login:  ${BOLD}gcloud auth login${NC}"
    echo -e "  • Remote login:    ${BOLD}gcloud auth login --no-browser${NC}"
    echo -e "  • Service Account: ${BOLD}gcloud auth activate-service-account --key-file=/path/to/key.json${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Authenticated as: ${BOLD}${ACTIVE_ACCOUNT}${NC}"

# 2. GCP Project ID detection
GCP_PROJECT="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo "")}"
if [ -z "${GCP_PROJECT}" ] || [ "${GCP_PROJECT}" = "(unset)" ]; then
    echo -e "${YELLOW}Enter your GCP Project ID (e.g., zentra-ai-prod):${NC} "
    read -r GCP_PROJECT
    if [ -z "${GCP_PROJECT}" ]; then
        echo -e "${RED}[ERROR] GCP Project ID cannot be empty.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Using GCP Project: ${BOLD}${GCP_PROJECT}${NC}"

# 3. Region selection
REGION="${GCP_REGION:-${DEFAULT_REGION}}"
echo -e "${GREEN}✓ Using Region: ${BOLD}${REGION}${NC}"

# 4. Gemini API Key check
GEMINI_KEY="${GEMINI_API_KEY:-}"
if [ -z "${GEMINI_KEY}" ]; then
    # Try reading from .env or PMS/.env
    if [ -f "PMS/.env" ]; then
        GEMINI_KEY=$(grep -E "^GEMINI_API_KEY=" PMS/.env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || echo "")
    elif [ -f ".env" ]; then
        GEMINI_KEY=$(grep -E "^GEMINI_API_KEY=" .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || echo "")
    fi
fi

if [ -z "${GEMINI_KEY}" ]; then
    echo -e "${YELLOW}Enter your GEMINI_API_KEY for the agent workflow:${NC} "
    read -r -s GEMINI_KEY
    echo ""
    if [ -z "${GEMINI_KEY}" ]; then
        echo -e "${RED}[ERROR] GEMINI_API_KEY is required to generate campaign content.${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ GEMINI_API_KEY detected.${NC}"

# 5. Enable necessary GCP APIs
echo -e "\n${BOLD}${CYAN}[Step 1/3] Enabling Google Cloud Services...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project="${GCP_PROJECT}"

# 6. Deploy to Google Cloud Run via Source (Automatic Cloud Build)
echo -e "\n${BOLD}${CYAN}[Step 2/3] Building and Deploying to Cloud Run...${NC}"
echo -e "Executing: ${CYAN}gcloud run deploy ${SERVICE_NAME} --source . ...${NC}"

gcloud run deploy "${SERVICE_NAME}" \
    --project="${GCP_PROJECT}" \
    --region="${REGION}" \
    --source="." \
    --platform="managed" \
    --allow-unauthenticated \
    --port="8080" \
    --memory="${DEFAULT_MEMORY}" \
    --cpu="${DEFAULT_CPU}" \
    --min-instances="${MIN_INSTANCES}" \
    --max-instances="${MAX_INSTANCES}" \
    --set-env-vars="GEMINI_API_KEY=${GEMINI_KEY},PYTHONUNBUFFERED=1"

# 7. Retrieve Service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --project="${GCP_PROJECT}" \
    --region="${REGION}" \
    --format="value(status.url)")

echo -e "\n${BOLD}${GREEN}====================================================================${NC}"
echo -e "${BOLD}${GREEN}  Deployment Successful! 🎉                                        ${NC}"
echo -e "${BOLD}${GREEN}====================================================================${NC}"
echo -e "Service URL: ${BOLD}${CYAN}${SERVICE_URL}${NC}"
echo -e "Health Check: ${BOLD}${CYAN}${SERVICE_URL}/healthz${NC}"
echo -e "Accounts Endpoint: ${BOLD}${CYAN}${SERVICE_URL}/api/accounts${NC}"
echo -e "Generate Endpoint: ${BOLD}${CYAN}${SERVICE_URL}/api/campaign/generate${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Test health check: curl -s ${SERVICE_URL}/healthz"
echo -e "2. Use this Service URL in https://zentraai.in/creator/ to trigger autonomous campaigns!"
