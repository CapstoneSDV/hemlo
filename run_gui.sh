#!/usr/bin/env bash
# ==============================================================================
# ARXML SecDiff - Launch Web GUI
# Usage:
#   ./run_gui.sh          (Starts Next.js Web GUI on http://localhost:3000)
#   ./run_gui.sh next     (Starts Next.js Web GUI on http://localhost:3000)
#   ./run_gui.sh python   (Starts Python GUI on http://localhost:8080)
#   ./run_gui.sh both     (Starts both Python backend on 8080 & Next.js on 3000)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-next}"

echo "=========================================================="
echo "           ARXML SecDiff - GUI Launcher                  "
echo "=========================================================="

case "$MODE" in
  python|py|8080)
    echo "Starting Python Lightweight GUI on http://localhost:8080..."
    python pipeline_gui/server.py
    ;;

  both|all)
    echo "Starting Python server on http://localhost:8080 in background..."
    python pipeline_gui/server.py &
    PY_PID=$!
    
    cleanup() {
      echo -e "\nStopping Python server (PID: $PY_PID)..."
      kill $PY_PID 2>/dev/null || true
    }
    trap cleanup EXIT INT TERM

    echo "Starting Next.js Web GUI on http://localhost:3000..."
    cd web_gui/next-app
    pnpm dev --port 3000
    ;;

  next|3000|*)
    echo "Starting Interactive Next.js Web GUI on http://localhost:3000..."
    cd web_gui/next-app
    pnpm dev --port 3000
    ;;
esac
