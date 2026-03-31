#!/usr/bin/env bash
# AI Test Suite Orchestrator — startup script
# Usage: ./run.sh

set -e
cd "$(dirname "$0")"

# ── Check API key ──────────────────────────────────────────────────────────
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo ""
  echo "  ERROR: ANTHROPIC_API_KEY is not set."
  echo ""
  echo "  Export it before running:"
  echo "    export ANTHROPIC_API_KEY=sk-ant-..."
  echo ""
  exit 1
fi

# ── Setup virtualenv if needed ─────────────────────────────────────────────
VENV="backend/venv"
if [ ! -d "$VENV" ]; then
  echo "→ Creating Python virtual environment…"
  python3 -m venv "$VENV"
  echo "→ Installing dependencies…"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r backend/requirements.txt
  echo "→ Attempting Playwright chromium install (optional)…"
  "$VENV/bin/playwright" install chromium --with-deps 2>/dev/null \
    || echo "  (Playwright not installed — take_screenshot tool will be unavailable)"
else
  # Ensure deps are up to date
  "$VENV/bin/pip" install --quiet -r backend/requirements.txt 2>/dev/null
fi

# ── Start backend ──────────────────────────────────────────────────────────
echo ""
echo "→ Starting backend API on http://localhost:8000 …"
"$VENV/bin/uvicorn" main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --app-dir backend \
  --log-level warning &
BACKEND_PID=$!

# Give the server a moment to bind
sleep 1

# ── Start frontend ─────────────────────────────────────────────────────────
echo "→ Serving frontend on http://localhost:8080 …"
"$VENV/bin/python" -m http.server 8080 \
  --directory frontend \
  --bind 0.0.0.0 \
  2>/dev/null &
FRONTEND_PID=$!

# ── Ready ──────────────────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║  AI Test Suite is running                ║"
echo "  ║                                          ║"
echo "  ║  Frontend  →  http://localhost:8080      ║"
echo "  ║  API       →  http://localhost:8000      ║"
echo "  ║                                          ║"
echo "  ║  Press Ctrl+C to stop.                   ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# ── Shutdown handler ───────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "→ Shutting down…"
  kill "$BACKEND_PID"  2>/dev/null || true
  kill "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

wait
