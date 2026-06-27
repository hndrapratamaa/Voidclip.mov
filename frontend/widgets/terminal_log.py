from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QColor, QFont, QTextCharFormat, QTextCursor,
)
from PySide6.QtWidgets import QPlainTextEdit, QWidget

_TERMINAL_BG    = "#080b10"
_TERMINAL_FG    = "#a8ffa8"
_TERMINAL_DIM   = "#5a9a5a"
_TERMINAL_WARN  = "#ffd60a"
_TERMINAL_ERR   = "#ff6860"
_TERMINAL_ACCENT = "#5ac8fa"
_CURSOR_COLOR   = "#a8ffa8"

_FONT_STACK = "'SF Mono', 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace"
_FONT_SIZE  = 11

_KEYWORD_COLORS = {
    "error":   _TERMINAL_ERR,
    "gagal":   _TERMINAL_ERR,
    "eror":    _TERMINAL_ERR,
    "failed":  _TERMINAL_ERR,
    "warn":    _TERMINAL_WARN,
    "blay":    _TERMINAL_WARN,
    "ok":      _TERMINAL_FG,
    "kelar":   _TERMINAL_FG,
    "beres":   _TERMINAL_FG,
    "gas":     _TERMINAL_ACCENT,
    "start":   _TERMINAL_ACCENT,
    "mulai":   _TERMINAL_ACCENT,
}

_DEPOK_PHRASE_MAP = [
    ("already queued",        "udah masuk antrian blay"),
    ("no files queued",       "belom ada file di antrian blay"),
    ("import some videos first", "masukin video dulu bos"),
    ("pause requested",       "santai dulu bentaran"),
    ("finishing current segment", "abisin segmen ini dulu ye"),
    ("resuming",               "gas lanjut lagi"),
    ("stop requested",         "oke distop ye bos"),
    ("skipping missing file",  "kelewat tuh, filenya kagak ketemu"),
    ("queued",                  "masuk antrian"),
    ("job cancelled",           "job dibatalin blay"),
    ("finished",                 "kelar gas"),
    ("segments",                  "segmen"),
    ("total",                     "totalan"),
    ("encode aborted by stop",  "encode keberhentian gara-gara distop"),
    ("done",                       "kelar"),
    ("scanning",                   "lagi nyariin"),
    ("processing",                  "lagi diproses"),
    ("rendering",                    "lagi ngerender"),
    ("loading",                       "lagi muat"),
    ("saving",                         "lagi nyimpen"),
    ("uploading",                      "lagi ngeupload"),
    ("downloading",                    "lagi ngedownload"),
    ("connecting",                      "lagi nyambungin"),
    ("connected",                        "udah konek"),
    ("disconnected",                     "putus konek"),
    ("retrying",                          "coba lagi ye"),
    ("waiting",                            "nungguin nih"),
    ("cancelled",                            "dibatalin"),
    ("success",                                "sukses gas"),
    ("warning",                                 "awas nih"),
    ("not found",                                "kagak ketemu"),
    ("invalid",                                   "kagak valid"),
    ("missing",                                    "kagak ada"),
    ("checking",                                    "lagi dicek"),
    ("completed",                                     "udah kelar"),
    ("starting",                                       "mulai gas"),
    ("stopped",                                         "distop"),
    ("paused",                                            "dijeda"),
]

_DEPOK_SUFFIX_MAP = [
    ("kah?",  "kah blay?"),
    ("nya.",  "nya bos."),
    (" ini",  " ini nih"),
]


def _depokin(line: str) -> str:
    hasil = line
    low   = hasil.lower()
    for eng, depok in _DEPOK_PHRASE_MAP:
        if eng in low:
            idx = low.find(eng)
            hasil = hasil[:idx] + depok + hasil[idx + len(eng):]
            low   = hasil.lower()
    if hasil == line and hasil and not hasil.rstrip().endswith(("blay", "bos", "cuy", "bro", "gas", "ye", "nih")):
        hasil = hasil.rstrip() + " blay"
    return hasil


def _resolve_line_color(line: str) -> str:
    low = line.lower()
    for kw, col in _KEYWORD_COLORS.items():
        if kw in low:
            return col
    return _TERMINAL_FG


class TerminalLog(QPlainTextEdit):
    MAX_LINES = 2000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("TerminalLog")
        self._cursor_visible = True
        self._cursor_block   = "\u2588"
        self._setup_font()
        self._setup_style()
        self._setup_cursor_blink()

    def _setup_font(self) -> None:
        font = QFont()
        font.setFamilies(["SF Mono", "JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas"])
        font.setFixedPitch(True)
        font.setPointSize(_FONT_SIZE)
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        self.setFont(font)

    def _setup_style(self) -> None:
        # Terminal keeps its near-opaque dark fill (readability of green-on-
        # black text matters more than transparency here), but gets the same
        # specular top/left + dark bottom/right edge as the rest of the glass UI.
        self.setStyleSheet(f"""
            QPlainTextEdit#TerminalLog {{
                background-color: rgba(8, 11, 16, 210);
                color: {_TERMINAL_FG};
                border-top: 1.5px solid rgba(255, 255, 255, 50);
                border-left: 1.5px solid rgba(255, 255, 255, 28);
                border-bottom: 1.5px solid rgba(0, 0, 0, 110);
                border-right: 1.5px solid rgba(0, 0, 0, 110);
                border-radius: 18px;
                padding: 12px 14px;
                selection-background-color: #0a84ff;
                selection-color: #ffffff;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 5px;
                margin: 4px 2px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 30);
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 55);
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        palette = self.palette()
        palette.setColor(palette.ColorRole.Base, QColor(_TERMINAL_BG))
        palette.setColor(palette.ColorRole.Text, QColor(_TERMINAL_FG))
        self.setPalette(palette)

    def _setup_cursor_blink(self) -> None:
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(530)
        self._blink_timer.timeout.connect(self._blink_tick)
        self._blink_timer.start()
        self._cursor_line_id: int = -1

    def _blink_tick(self) -> None:
        self._cursor_visible = not self._cursor_visible
        self._refresh_cursor()

    def _refresh_cursor(self) -> None:
        doc   = self.document()
        if doc.blockCount() == 0:
            return

        last_block = doc.lastBlock()
        if not last_block.isValid():
            return

        cursor = QTextCursor(last_block)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)

        char_fmt = QTextCharFormat()
        if self._cursor_visible:
            char_fmt.setForeground(QColor(_CURSOR_COLOR))
        else:
            char_fmt.setForeground(QColor(_TERMINAL_BG))

        cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
        last_char = cursor.selectedText()
        if last_char == self._cursor_block:
            cursor.mergeCharFormat(char_fmt)

    def append_line(self, msg: str) -> None:
        msg = _depokin(msg)
        self._strip_last_cursor()

        doc       = self.document()
        line_col  = _resolve_line_color(msg)

        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if doc.blockCount() > 1 or doc.toPlainText():
            cursor.insertBlock()

        body_fmt = QTextCharFormat()
        body_fmt.setForeground(QColor(line_col))
        cursor.setCharFormat(body_fmt)
        cursor.insertText(msg)

        caret_fmt = QTextCharFormat()
        caret_fmt.setForeground(QColor(_CURSOR_COLOR))
        cursor.setCharFormat(caret_fmt)
        cursor.insertText(self._cursor_block)

        self._prune_old_lines()
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.ensureCursorVisible()

    def _strip_last_cursor(self) -> None:
        doc = self.document()
        if doc.blockCount() == 0:
            return

        last_block = doc.lastBlock()
        text       = last_block.text()
        if text.endswith(self._cursor_block):
            cursor = QTextCursor(last_block)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

    def _prune_old_lines(self) -> None:
        doc = self.document()
        while doc.blockCount() > self.MAX_LINES:
            cursor = QTextCursor(doc.firstBlock())
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

    def clear_terminal(self) -> None:
        self.clear()

    def write_log(self, msg: str) -> None:
        self.append_line(msg)
