#!/usr/bin/env bash
set -euo pipefail

# Start backend and frontend locally inside Codespaces (no Docker needed)
# Uses ports 5555 (Flask) and 3001 (Next.js)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Python deps
cd "$ROOT_DIR/backend"
pip install -r requirements.txt

# Node deps
cd "$ROOT_DIR/frontend"
npm ci --no-audit --no-fund

# Start backend (background)
cd "$ROOT_DIR/backend"
export PORT=5555
export DB_PATH="${ROOT_DIR}/data/chipax_data.db"
nohup python server.py >/tmp/backend.log 2>&1 &
echo "Backend started on :5555 (log: /tmp/backend.log)"

# Start frontend (foreground)
cd "$ROOT_DIR/frontend"
export NEXT_PUBLIC_API_BASE="http://localhost:5555/api"
npm run dev
