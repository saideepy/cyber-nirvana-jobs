#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       C2C AI Job Board  v2.0             ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Python backend ───────────────────────────────────────────────────────────
echo "▶ Setting up Python backend…"
mkdir -p data

cd backend

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  Created Python venv."
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -q --disable-pip-version-check
echo "  Python dependencies ready."

# Start backend
echo "  Starting FastAPI on http://localhost:8000 …"
python main.py &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

# Give backend a moment to bind
sleep 2

# ── Node frontend ─────────────────────────────────────────────────────────────
echo ""
echo "▶ Setting up React frontend…"
cd frontend

if [ ! -d "node_modules" ]; then
    echo "  Installing npm packages (first run may take a minute)…"
    npm install --silent
fi

echo "  Starting Vite dev server on http://localhost:5173 …"
npm run dev &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "  Backend  ▸  http://localhost:8000"
echo "  Frontend ▸  http://localhost:5173"
echo "  API docs ▸  http://localhost:8000/docs"
echo ""
echo "  Scraping starts automatically and repeats every 1 hour."
echo "  Press Ctrl+C to stop everything."
echo ""

cleanup() {
    echo ""
    echo "Stopping servers…"
    kill "$BACKEND_PID"  2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait
    echo "Done."
}
trap cleanup INT TERM

wait
