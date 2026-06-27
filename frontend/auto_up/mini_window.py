from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QSizePolicy,
    QFrame,
)

from backend.lang_id import (
    JUDUL_WINDOW_MINI,
    LBL_START_SCRIPT, LBL_PAUSE_SCRIPT, LBL_STOP_SCRIPT,
    LBL_NOTEPAD_MINI, TOOLTIP_START, TOOLTIP_PAUSE, TOOLTIP_STOP,
    TOOLTIP_NOTEPAD,
)


class MiniWindow(QWidget):
    sig_start  = Signal()
    sig_pause  = Signal()
    sig_stop   = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(JUDUL_WINDOW_MINI)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFixedSize(320, 420)
        self.setObjectName("MiniWindow")
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel(JUDUL_WINDOW_MINI)
        title.setObjectName("MiniTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("MiniSep")
        root.addWidget(sep)

        lbl_notepad = QLabel(LBL_NOTEPAD_MINI)
        lbl_notepad.setObjectName("MiniLabel")
        lbl_notepad.setToolTip(TOOLTIP_NOTEPAD)
        root.addWidget(lbl_notepad)

        self.notepad = QTextEdit()
        self.notepad.setObjectName("MiniNotepad")
        self.notepad.setPlaceholderText("Tulis deskripsi, hashtag, dll...")
        self.notepad.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        root.addWidget(self.notepad, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_start = QPushButton(LBL_START_SCRIPT)
        self.btn_start.setObjectName("BtnStart")
        self.btn_start.setToolTip(TOOLTIP_START)
        self.btn_start.clicked.connect(self.sig_start)

        self.btn_pause = QPushButton(LBL_PAUSE_SCRIPT)
        self.btn_pause.setObjectName("BtnPause")
        self.btn_pause.setToolTip(TOOLTIP_PAUSE)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.sig_pause)

        self.btn_stop = QPushButton(LBL_STOP_SCRIPT)
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.setToolTip(TOOLTIP_STOP)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.sig_stop)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_stop)
        root.addLayout(btn_row)

    def _apply_style(self) -> None:
        # Liquid glass look: translucent fill + bright top/left "specular"
        # edge (simulates light hitting the glass), faint dark bottom/right
        # edge. No real backdrop blur (Qt/QSS can't do that) — see theme.py
        # for the same approach applied globally.
        self.setStyleSheet("""
            #MiniWindow {
                background-color: #1B1D24;
                border-top: 1.5px solid rgba(255, 255, 255, 60);
                border-left: 1.5px solid rgba(255, 255, 255, 40);
                border-bottom: 1.5px solid rgba(0, 0, 0, 90);
                border-right: 1.5px solid rgba(0, 0, 0, 90);
                border-radius: 22px;
            }
            #MiniTitle {
                color: #F2F5F9;
                font-size: 13px;
                font-weight: bold;
                padding: 4px;
                background: transparent;
            }
            #MiniSep {
                border: none;
                border-top: 1px solid rgba(255, 255, 255, 18);
                max-height: 1px;
                background: transparent;
            }
            #MiniLabel {
                color: #aab3c2;
                font-size: 11px;
                background: transparent;
            }
            #MiniNotepad {
                background-color: rgba(0, 0, 0, 60);
                color: #F2F5F9;
                border-top: 1.5px solid rgba(0, 0, 0, 90);
                border-left: 1.5px solid rgba(0, 0, 0, 90);
                border-bottom: 1.5px solid rgba(255, 255, 255, 40);
                border-right: 1.5px solid rgba(255, 255, 255, 40);
                border-radius: 18px;
                font-size: 11px;
                padding: 8px;
            }
            #BtnStart {
                background-color: #0a84ff;
                color: #ffffff;
                border-top: 1.5px solid rgba(255, 255, 255, 110);
                border-left: 1.5px solid rgba(255, 255, 255, 60);
                border-bottom: 1.5px solid #0060cc;
                border-right: 1.5px solid #0060cc;
                border-radius: 18px;
                padding: 6px 12px;
                font-weight: bold;
            }
            #BtnStart:hover { background-color: #3d9eff; }
            #BtnStart:pressed { background-color: #0060d0; }
            #BtnStart:disabled {
                background-color: rgba(255, 255, 255, 14);
                color: #717a89;
                border-top: 1.5px solid rgba(255, 255, 255, 18);
                border-left: 1.5px solid rgba(255, 255, 255, 18);
                border-bottom: 1.5px solid rgba(255, 255, 255, 18);
                border-right: 1.5px solid rgba(255, 255, 255, 18);
            }
            #BtnPause {
                background-color: rgba(255, 214, 10, 50);
                color: #F2F5F9;
                border-top: 1.5px solid rgba(255, 255, 255, 90);
                border-left: 1.5px solid rgba(255, 255, 255, 50);
                border-bottom: 1.5px solid rgba(0, 0, 0, 90);
                border-right: 1.5px solid rgba(0, 0, 0, 90);
                border-radius: 18px;
                padding: 6px 12px;
                font-weight: bold;
            }
            #BtnPause:hover { background-color: rgba(255, 214, 10, 80); }
            #BtnPause:disabled {
                background-color: rgba(255, 255, 255, 14);
                color: #717a89;
                border-top: 1.5px solid rgba(255, 255, 255, 18);
                border-left: 1.5px solid rgba(255, 255, 255, 18);
                border-bottom: 1.5px solid rgba(255, 255, 255, 18);
                border-right: 1.5px solid rgba(255, 255, 255, 18);
            }
            #BtnStop {
                background-color: rgba(255, 69, 58, 50);
                color: #F2F5F9;
                border-top: 1.5px solid rgba(255, 255, 255, 90);
                border-left: 1.5px solid rgba(255, 255, 255, 50);
                border-bottom: 1.5px solid rgba(0, 0, 0, 90);
                border-right: 1.5px solid rgba(0, 0, 0, 90);
                border-radius: 18px;
                padding: 6px 12px;
                font-weight: bold;
            }
            #BtnStop:hover { background-color: rgba(255, 69, 58, 85); }
            #BtnStop:disabled {
                background-color: rgba(255, 255, 255, 14);
                color: #717a89;
                border-top: 1.5px solid rgba(255, 255, 255, 18);
                border-left: 1.5px solid rgba(255, 255, 255, 18);
                border-bottom: 1.5px solid rgba(255, 255, 255, 18);
                border-right: 1.5px solid rgba(255, 255, 255, 18);
            }
        """)

    def get_deskripsi(self) -> str:
        return self.notepad.toPlainText().strip()

    def set_running(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_pause.setEnabled(running)
        self.btn_stop.setEnabled(running)

    def set_paused_label(self, paused: bool) -> None:
        from backend.lang_id import LBL_PAUSE_SCRIPT, BTN_LANJUT
        self.btn_pause.setText(BTN_LANJUT if paused else LBL_PAUSE_SCRIPT)
