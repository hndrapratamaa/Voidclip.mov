"""
app.py
─────────────────────────────────────────────────────────────────────────────
Voidclip.mov — Application Entry Point

Run:
    python app.py
─────────────────────────────────────────────────────────────────────────────
"""

import sys
import os

# Ensure project root is on sys.path when running from any CWD
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.logger import setup_logging
setup_logging()

from backend.logger import get_logger
log = get_logger("app")


def _check_dependencies() -> None:
    """Fail fast with a clear, actionable message instead of a raw traceback."""
    missing = []
    for module in ("PySide6", "xxhash", "send2trash"):
        try:
            __import__(module)
        except ModuleNotFoundError:
            missing.append(module)
    if missing:
        msg = (
            "\n"
            "═══════════════════════════════════════════════════\n"
            "  Missing dependencies: " + ", ".join(missing) + "\n"
            "\n"
            "  Fix:\n"
            "    source .venv/bin/activate\n"
            "    pip install -r requirements.txt\n"
            "═══════════════════════════════════════════════════\n"
        )
        print(msg, file=sys.stderr)
        log.error("Missing dependencies: %s", ", ".join(missing))
        sys.exit(1)


def main() -> None:
    log.info("═══════════════════════════════════")
    log.info("  Voidclip.mov  starting…")
    log.info("═══════════════════════════════════")

    _check_dependencies()

    # ── PySide6 application ───────────────────────────────────────────────
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("Voidclip.mov")
    app.setOrganizationName("Voidclip")
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # ── Renderer (backend facade) ─────────────────────────────────────────
    from backend.renderer import Renderer
    renderer = Renderer()

    # ── Main window ───────────────────────────────────────────────────────
    from frontend.main_window import MainWindow
    window = MainWindow(renderer)
    window.show()

    log.info("GUI launched")
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Fatal error during startup")
        raise

