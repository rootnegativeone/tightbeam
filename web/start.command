#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
PORT=5173

if [ ! -d "$DIST_DIR" ]; then
  echo "dist/ directory not found next to start.command. Please run npm run build first." >&2
  exit 1
fi

echo "Launching Tightbeam demo server on http://localhost:$PORT"
cd "$DIST_DIR"

python3 -m http.server "$PORT" >/tmp/tightbeam-demo.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null' EXIT INT TERM

sleep 1
open "http://localhost:$PORT" >/dev/null 2>&1 || true

echo "Press Ctrl+C or close this window when you are finished."
wait "$SERVER_PID"
