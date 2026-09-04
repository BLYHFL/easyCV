#!/usr/bin/env bash
# start.sh — one-click launcher for easyCV (macOS / Linux)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

HOST="127.0.0.1"
PORT=8010

# ── 1. Ensure Python 3.9+ ────────────────────────────────────────────────────
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" -c "import sys; print(sys.version_info >= (3,9))" 2>/dev/null || echo False)
        if [[ "$ver" == "True" ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo "❌  Python 3.9+ not found."
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "   Install via Homebrew:  brew install python"
    fi
    exit 1
fi

echo "✅  Using $($PYTHON --version)"

# ── 2. Create / activate virtual environment ─────────────────────────────────
if [[ ! -d ".venv" ]]; then
    echo "⚙️   Creating virtual environment..."
    "$PYTHON" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# ── 3. Install / sync dependencies ───────────────────────────────────────────
if [[ -f requirements.txt ]]; then
    echo "📦  Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
fi

# ── 4. Open browser on macOS ─────────────────────────────────────────────────
if [[ "$(uname)" == "Darwin" ]]; then
    (sleep 1.5 && open "http://${HOST}:${PORT}") &
    echo "🌐  Browser will open at http://${HOST}:${PORT}"
fi

# ── 5. Launch server ─────────────────────────────────────────────────────────
echo "🚀  Starting easyCV at http://${HOST}:${PORT} ..."
exec uvicorn app:app --reload --host "$HOST" --port "$PORT"
