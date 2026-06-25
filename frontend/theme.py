from __future__ import annotations
from PySide6.QtWidgets import QWidget

_DARK = {
    "bg":          "#10131a",
    "surface":     "#161b25",
    "surface2":    "#1c2333",
    "border":      "#252d40",
    "accent":      "#0a84ff",
    "accent_h":    "#1a8fff",
    "accent_p":    "#0060d0",
    "accent2":     "#30d158",
    "warn":        "#ffd60a",
    "danger":      "#ff453a",
    "text":        "#f0f4ff",
    "text2":       "#8e99b0",
    "text3":       "#3d4a60",
    "shadow_d":    "#07090e",
    "terminal_bg": "#0c0e14",
    "terminal_fg": "#b8c8d8",
    "sel_bg":      "#0a84ff",
    "sel_fg":      "#ffffff",
}

_LIGHT = {
    "bg":          "#f0f2f5",
    "surface":     "#ffffff",
    "surface2":    "#e8eaee",
    "border":      "#d0d4dc",
    "accent":      "#0071e3",
    "accent_h":    "#0077ed",
    "accent_p":    "#005bbf",
    "accent2":     "#28cd41",
    "warn":        "#ff9f0a",
    "danger":      "#ff3b30",
    "text":        "#1a1d23",
    "text2":       "#4a5568",
    "text3":       "#9aa0ab",
    "shadow_d":    "#c8ccd4",
    "terminal_bg": "#1a1d23",
    "terminal_fg": "#c5d0e0",
    "sel_bg":      "#0071e3",
    "sel_fg":      "#ffffff",
}


def _sheet(c: dict) -> str:
    return f"""

QMainWindow, QDialog {{
    background-color: {c['bg']};
}}

QWidget {{
    color: {c['text']};
    font-family: 'SF Pro Text', 'Inter', 'Segoe UI', sans-serif;
    font-size: 12px;
    background-color: transparent;
}}

QFrame[role="card"] {{
    background-color: {c['surface']};
    border-radius: 12px;
    border: 1px solid {c['border']};
}}

QSplitter::handle {{
    background-color: {c['border']};
    border-radius: 2px;
}}

QSplitter::handle:horizontal {{ width: 5px; }}
QSplitter::handle:vertical   {{ height: 5px; }}

QLabel[role="appTitle"] {{
    font-size: 16px;
    font-weight: 700;
    color: {c['text']};
    letter-spacing: -0.3px;
    background: transparent;
}}

QLabel[role="sectionTitle"] {{
    font-size: 9px;
    font-weight: 700;
    color: {c['text3']};
    letter-spacing: 1.4px;
    background: transparent;
}}

QLabel[role="statusReady"]   {{ font-size: 12px; font-weight: 600; color: {c['accent2']}; background: transparent; }}
QLabel[role="statusRunning"] {{ font-size: 12px; font-weight: 600; color: {c['warn']};    background: transparent; }}
QLabel[role="statusPaused"]  {{ font-size: 12px; font-weight: 600; color: #ffd60a;        background: transparent; }}

QLabel {{
    background: transparent;
}}

QFrame[role="divider"] {{
    border: none;
    border-top: 1px solid {c['border']};
    max-height: 1px;
}}

QListWidget {{
    background-color: {c['surface2']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}

QListWidget::item {{
    padding: 5px 8px;
    border-radius: 5px;
    color: {c['text']};
}}

QListWidget::item:hover {{
    background-color: {c['border']};
}}

QListWidget::item:selected {{
    background-color: {c['sel_bg']};
    color: {c['sel_fg']};
}}

QTreeView {{
    background-color: {c['surface2']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 4px;
    outline: none;
    show-decoration-selected: 1;
}}

QTreeView::item {{
    padding: 4px 4px;
    color: {c['text']};
}}

QTreeView::item:hover {{
    background-color: {c['border']};
}}

QTreeView::item:selected {{
    background-color: {c['sel_bg']};
    color: {c['sel_fg']};
}}

QTreeView::branch {{
    background: transparent;
}}

QHeaderView {{
    background-color: {c['surface2']};
}}

QHeaderView::section {{
    background-color: {c['surface2']};
    color: {c['text2']};
    border: none;
    padding: 4px;
    font-weight: 600;
    font-size: 10px;
}}

QPlainTextEdit {{
    background-color: {c['terminal_bg']};
    color: {c['terminal_fg']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 8px;
    font-family: 'SF Mono', 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 11px;
    selection-background-color: {c['sel_bg']};
}}

QPushButton {{
    background-color: {c['surface']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 9px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}}

QPushButton:hover {{
    background-color: {c['surface2']};
    border-color: {c['accent']};
    color: {c['accent']};
}}

QPushButton:pressed, QPushButton[depressed="true"] {{
    background-color: {c['shadow_d']};
    border-color: {c['accent']};
    color: {c['accent']};
    padding-top: 9px;
    padding-bottom: 5px;
}}

QPushButton:disabled {{
    color: {c['text3']};
    border-color: {c['border']};
    background-color: {c['surface']};
}}

QPushButton:checked {{
    background-color: {c['surface2']};
    border-color: {c['accent']};
    color: {c['accent']};
}}

QPushButton[role="accentBtn"] {{
    background-color: {c['accent']};
    color: #ffffff;
    border: 1px solid {c['accent']};
}}

QPushButton[role="accentBtn"]:hover {{
    background-color: {c['accent_h']};
    border-color: {c['accent_h']};
    color: #ffffff;
}}

QPushButton[role="accentBtn"]:pressed, QPushButton[role="accentBtn"][depressed="true"] {{
    background-color: {c['accent_p']};
    border-color: {c['accent_p']};
    color: #ffffff;
    padding-top: 9px;
    padding-bottom: 5px;
}}

QPushButton[role="accentBtn"]:disabled {{
    background-color: {c['border']};
    border-color: {c['border']};
    color: {c['text3']};
}}

QPushButton[role="dangerBtn"] {{
    background-color: {c['surface']};
    color: {c['danger']};
    border: 1px solid {c['border']};
}}

QPushButton[role="dangerBtn"]:hover {{
    border-color: {c['danger']};
    background-color: {c['surface2']};
}}

QPushButton[role="dangerBtn"]:pressed, QPushButton[role="dangerBtn"][depressed="true"] {{
    background-color: {c['shadow_d']};
    padding-top: 9px;
    padding-bottom: 5px;
}}

QPushButton[role="dangerBtn"]:disabled {{
    color: {c['text3']};
    border-color: {c['border']};
}}

QProgressBar {{
    background-color: {c['surface2']};
    border: 1px solid {c['border']};
    border-radius: 5px;
    height: 10px;
    text-align: center;
    color: {c['text']};
    font-size: 10px;
    font-weight: 600;
}}

QProgressBar::chunk {{
    background-color: {c['accent']};
    border-radius: 4px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 7px;
    border-radius: 3px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {c['border']};
    border-radius: 3px;
    min-height: 20px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 7px;
    border-radius: 3px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: {c['border']};
    border-radius: 3px;
    min-width: 20px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QComboBox {{
    background-color: {c['surface2']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 4px 10px;
    font-weight: 500;
}}

QComboBox:hover {{ border-color: {c['accent']}; }}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {c['surface']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    selection-background-color: {c['sel_bg']};
    selection-color: {c['sel_fg']};
}}

QGroupBox {{
    border: 1px solid {c['border']};
    border-radius: 10px;
    margin-top: 10px;
    padding: 10px;
    color: {c['text2']};
    font-weight: 600;
    font-size: 11px;
    background-color: {c['surface']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {c['accent']};
}}

QVideoWidget {{
    background-color: #000000;
    border-radius: 10px;
    border: 1px solid {c['border']};
}}

QDialogButtonBox QPushButton {{
    min-width: 80px;
}}
"""


def apply_theme(widget: QWidget, dark: bool = True) -> None:
    c = _DARK if dark else _LIGHT
    widget.setStyleSheet(_sheet(c))


NEU_STYLE = _sheet(_DARK)