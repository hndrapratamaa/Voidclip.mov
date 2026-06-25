#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Voidclip.mov — Launcher script
# Activates the virtual environment and starts the app.
# Used by the .desktop shortcut (see Voidclip.desktop) so the user never
# needs to open a terminal manually.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Resolve the directory this script lives in, regardless of where it's
# invoked from (important for .desktop launchers).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"

show_error() {
    local msg="$1"
    echo "═══════════════════════════════════════════════════" >&2
    echo "  Voidclip.mov failed to start" >&2
    echo "  $msg" >&2
    echo "═══════════════════════════════════════════════════" >&2
    # Also show a GUI dialog if zenity/xmessage is available, since this
    # is launched from a dock/launcher with no visible terminal.
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Voidclip.mov" --text="$msg" 2>/dev/null || true
    elif command -v xmessage >/dev/null 2>&1; then
        xmessage "Voidclip.mov: $msg" 2>/dev/null || true
    fi
    exit 1
}

if [ ! -d "$VENV_DIR" ]; then
    show_error "Virtual environment not found at $VENV_DIR

Run this once in a terminal inside the project folder:
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if ! command -v ffmpeg >/dev/null 2>&1; then
    show_error "ffmpeg not found in PATH.
Install it with: sudo apt install ffmpeg"
fi

exec python app.py
