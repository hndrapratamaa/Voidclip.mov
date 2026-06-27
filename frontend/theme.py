from __future__ import annotations
from PySide6.QtWidgets import QWidget

# ── Liquid glass palette ────────────────────────────────────────────────
# Background colors stay mostly the same (canvas behind the glass panes),
# but every "panel" surface now uses low-alpha rgba so the canvas bleeds
# through, plus a brighter "specular" tone used only for the highlight
# edge that simulates light catching the top of a glass surface.

_DARK = {
    "canvas":       "#1B1D24",
    "bg":           "#1B1D24",
    "bg2":          "#1B1D24",
    "surface":      "rgba(255, 255, 255, 10)",
    "surface2":     "rgba(255, 255, 255, 16)",
    "surface3":     "rgba(255, 255, 255, 22)",
    "border":       "rgba(255, 255, 255, 18)",
    "border_glow":  "rgba(255, 255, 255, 60)",
    "accent":       "#0a84ff",
    "accent_h":     "#3d9eff",
    "accent_p":     "#0060cc",
    "accent2":      "#30d158",
    "accent2_h":    "#40e668",
    "warn":         "#ffd60a",
    "danger":       "#ff453a",
    "danger_h":     "#ff6860",
    "text":         "#F2F5F9",
    "text2":        "#aab3c2",
    "text3":        "#717a89",
    "glass_fill":     "rgba(255, 255, 255, 14)",
    "glass_fill_hov": "rgba(255, 255, 255, 24)",
    "glass_fill_prs": "rgba(255, 255, 255, 8)",
    "glass_fill_inset": "rgba(0, 0, 0, 70)",
    "specular":     "rgba(255, 255, 255, 110)",
    "specular_dim": "rgba(255, 255, 255, 40)",
    "shadow_edge":  "rgba(0, 0, 0, 90)",
    "terminal_bg":  "rgba(10, 12, 16, 130)",
    "terminal_fg":  "#a8ffa8",
    "sel_bg":       "#0a84ff",
    "sel_fg":       "#ffffff",
    "inset_bg":     "rgba(0, 0, 0, 60)",
    "inset_border": "rgba(255, 255, 255, 14)",
}

_LIGHT = {
    "canvas":       "#E7ECF4",
    "bg":           "#E7ECF4",
    "bg2":          "#E7ECF4",
    "surface":      "rgba(255, 255, 255, 110)",
    "surface2":     "rgba(255, 255, 255, 140)",
    "surface3":     "rgba(255, 255, 255, 170)",
    "border":       "rgba(255, 255, 255, 160)",
    "border_glow":  "rgba(255, 255, 255, 230)",
    "accent":       "#0071e3",
    "accent_h":     "#1a82f0",
    "accent_p":     "#005bbf",
    "accent2":      "#28cd41",
    "accent2_h":    "#35d94e",
    "warn":         "#ff9f0a",
    "danger":       "#ff3b30",
    "danger_h":     "#ff5a50",
    "text":         "#28303D",
    "text2":        "#5c6b80",
    "text3":        "#8d99ad",
    "glass_fill":     "rgba(255, 255, 255, 120)",
    "glass_fill_hov": "rgba(255, 255, 255, 165)",
    "glass_fill_prs": "rgba(255, 255, 255, 90)",
    "glass_fill_inset": "rgba(170, 182, 200, 90)",
    "specular":     "rgba(255, 255, 255, 235)",
    "specular_dim": "rgba(255, 255, 255, 140)",
    "shadow_edge":  "rgba(120, 132, 150, 90)",
    "terminal_bg":  "rgba(195, 204, 217, 160)",
    "terminal_fg":  "#2a5c2a",
    "sel_bg":       "#0071e3",
    "sel_fg":       "#ffffff",
    "inset_bg":     "rgba(160, 172, 190, 70)",
    "inset_border": "rgba(255, 255, 255, 150)",
}

_RADIUS    = 22
_RADIUS_SM = 16
_RADIUS_PILL = 26


def _sheet(c: dict) -> str:
    return f"""
QMainWindow, QDialog {{
    background-color: {c['canvas']};
}}

QWidget {{
    color: {c['text']};
    font-family: -apple-system, 'SF Pro Text', 'Inter', 'Segoe UI', sans-serif;
    font-size: 12px;
    background-color: transparent;
}}

/* ── Glass card ──────────────────────────────────────────────────────── */
/* The "specular" border (light side) sits top+left, simulating a light
   source hitting the upper edge of a glass pane. The bottom+right edge
   stays faint, just enough to read as a separate plane from the canvas. */
QFrame[role="card"] {{
    background-color: {c['glass_fill']};
    border-radius: {_RADIUS}px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
}}

QFrame[role="card-inset"] {{
    background-color: {c['glass_fill_inset']};
    border-radius: {_RADIUS}px;
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
}}

QFrame[role="divider"] {{
    border: none;
    border-top: 1px solid {c['border']};
    max-height: 1px;
    background: transparent;
}}

QSplitter::handle {{
    background-color: {c['border']};
    border-radius: 2px;
}}

QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical   {{ height: 1px; }}

QLabel {{
    background: transparent;
}}

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
    letter-spacing: 1.8px;
    background: transparent;
    text-transform: uppercase;
}}

QLabel[role="statusReady"]   {{
    font-size: 12px;
    font-weight: 600;
    color: {c['accent2']};
    background: transparent;
}}

QLabel[role="statusRunning"] {{
    font-size: 12px;
    font-weight: 600;
    color: {c['warn']};
    background: transparent;
}}

QLabel[role="statusPaused"]  {{
    font-size: 12px;
    font-weight: 600;
    color: {c['warn']};
    background: transparent;
}}

/* ── Glass buttons ───────────────────────────────────────────────────── */
/* Flat translucent fill, no gradient — the specular line on hover/press
   does the "liquid" work instead of a fake light-sweep gradient. */
QPushButton {{
    background-color: {c['glass_fill']};
    color: {c['text']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
    padding: 6px 16px;
    font-weight: 600;
    font-size: 11px;
}}

QPushButton:hover {{
    background-color: {c['glass_fill_hov']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
    padding: 6px 16px;
    color: {c['accent_h']};
}}

QPushButton:pressed {{
    background-color: {c['glass_fill_prs']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    color: {c['text2']};
    padding: 7px 16px 5px 16px;
}}

QPushButton[depressed="true"] {{
    background-color: {c['glass_fill_prs']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    color: {c['text2']};
    padding: 7px 16px 5px 16px;
}}

QPushButton:disabled {{
    color: {c['text3']};
    background-color: {c['glass_fill_inset']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['border']};
    border-left: 1.5px solid {c['border']};
    border-bottom: 1.5px solid {c['border']};
    border-right: 1.5px solid {c['border']};
}}

QPushButton:checked {{
    background-color: {c['glass_fill_inset']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    color: {c['accent']};
}}

QPushButton[role="accentBtn"] {{
    background-color: {c['accent']};
    color: #ffffff;
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['accent_p']};
    border-right: 1.5px solid {c['accent_p']};
    font-weight: 700;
    font-size: 11px;
    padding: 6px 16px;
}}

QPushButton[role="accentBtn"]:hover {{
    background-color: {c['accent_h']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular']};
    padding: 6px 16px;
}}

QPushButton[role="accentBtn"]:pressed,
QPushButton[role="accentBtn"][depressed="true"] {{
    background-color: {c['accent_p']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['accent_p']};
    border-left: 1.5px solid {c['accent_p']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    color: #ffffffcc;
    padding: 7px 16px 5px 16px;
}}

QPushButton[role="accentBtn"]:disabled {{
    background-color: {c['glass_fill_inset']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['border']};
    border-left: 1.5px solid {c['border']};
    border-bottom: 1.5px solid {c['border']};
    border-right: 1.5px solid {c['border']};
    color: {c['text3']};
}}

QPushButton[role="dangerBtn"] {{
    background-color: {c['glass_fill']};
    color: {c['danger']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
    padding: 6px 16px;
    font-weight: 600;
    font-size: 11px;
}}

QPushButton[role="dangerBtn"]:hover {{
    background-color: {c['glass_fill_hov']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['danger']};
    border-left: 1.5px solid {c['danger']};
    border-bottom: 1.5px solid {c['danger_h']};
    border-right: 1.5px solid {c['danger_h']};
    padding: 6px 16px;
    color: {c['danger_h']};
}}

QPushButton[role="dangerBtn"]:pressed,
QPushButton[role="dangerBtn"][depressed="true"] {{
    background-color: {c['glass_fill_prs']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['danger']};
    border-left: 1.5px solid {c['danger']};
    border-bottom: 1.5px solid {c['danger_h']};
    border-right: 1.5px solid {c['danger_h']};
    color: {c['danger']};
    padding: 7px 16px 5px 16px;
}}

QPushButton[role="dangerBtn"]:disabled {{
    color: {c['text3']};
    background-color: {c['glass_fill_inset']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['border']};
    border-left: 1.5px solid {c['border']};
    border-bottom: 1.5px solid {c['border']};
    border-right: 1.5px solid {c['border']};
}}

QPushButton[role="iconBtn"] {{
    background-color: {c['glass_fill']};
    border-radius: 16px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
    padding: 5px;
    color: {c['text2']};
    font-size: 14px;
}}

QPushButton[role="iconBtn"]:hover {{
    background-color: {c['glass_fill_hov']};
    border-radius: 16px;
    border-top: 1.5px solid {c['accent']};
    border-left: 1.5px solid {c['accent']};
    padding: 5px;
    color: {c['accent']};
}}

QPushButton[role="iconBtn"]:pressed {{
    background-color: {c['glass_fill_prs']};
    border-radius: 16px;
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    padding: 5px;
}}

QProgressBar {{
    background-color: {c['inset_bg']};
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    border-radius: 12px;
    height: 14px;
    text-align: center;
    color: {c['text']};
    font-size: 10px;
    font-weight: 600;
}}

QProgressBar::chunk {{
    background-color: {c['accent']};
    border-radius: 10px;
}}

QProgressBar#overallBar::chunk {{
    background-color: {c['accent2']};
    border-radius: 10px;
}}

QListWidget {{
    background-color: {c['inset_bg']};
    color: {c['text']};
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    border-radius: {_RADIUS}px;
    padding: 8px;
    outline: none;
}}

QListWidget::item {{
    padding: 5px 8px;
    border-radius: 12px;
    color: {c['text']};
}}

QListWidget::item:hover {{
    background-color: {c['surface3']};
}}

QListWidget::item:selected {{
    background-color: {c['accent']};
    color: {c['sel_fg']};
    border-radius: 12px;
}}

QTreeView {{
    background-color: {c['inset_bg']};
    color: {c['text']};
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    border-radius: {_RADIUS}px;
    padding: 8px;
    outline: none;
    show-decoration-selected: 1;
}}

QTreeView::item {{
    padding: 4px;
    color: {c['text']};
}}

QTreeView::item:hover {{
    background-color: {c['surface3']};
}}

QTreeView::item:selected {{
    background-color: {c['accent']};
    color: {c['sel_fg']};
}}

QTreeView::branch {{
    background: transparent;
}}

QHeaderView {{
    background-color: {c['inset_bg']};
}}

QHeaderView::section {{
    background-color: {c['inset_bg']};
    color: {c['text2']};
    border: none;
    padding: 4px;
    font-weight: 600;
    font-size: 10px;
}}

QLineEdit {{
    background-color: {c['inset_bg']};
    color: {c['text']};
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    border-radius: {_RADIUS}px;
    padding: 6px 12px;
    font-family: 'SF Pro Text', 'Inter', 'Segoe UI', sans-serif;
    font-size: 12px;
    selection-background-color: {c['sel_bg']};
    selection-color: {c['sel_fg']};
}}

QLineEdit:focus {{
    border-top: 1.5px solid {c['accent']};
    border-left: 1.5px solid {c['accent']};
    border-bottom: 1.5px solid {c['accent']};
    border-right: 1.5px solid {c['accent']};
}}

QLineEdit:disabled {{
    color: {c['text3']};
}}

QPlainTextEdit {{
    background-color: {c['terminal_bg']};
    color: {c['terminal_fg']};
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    border-radius: {_RADIUS}px;
    padding: 10px;
    font-family: 'SF Mono', 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
    font-size: 11px;
    selection-background-color: {c['sel_bg']};
    selection-color: {c['sel_fg']};
}}

QTextEdit {{
    background-color: {c['inset_bg']};
    color: {c['text']};
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    border-radius: {_RADIUS}px;
    padding: 8px;
    font-family: 'SF Pro Text', 'Inter', 'Segoe UI', sans-serif;
    font-size: 12px;
    selection-background-color: {c['sel_bg']};
    selection-color: {c['sel_fg']};
}}

QTextEdit:focus {{
    border-top: 1.5px solid {c['accent']};
    border-left: 1.5px solid {c['accent']};
    border-bottom: 1.5px solid {c['accent']};
    border-right: 1.5px solid {c['accent']};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    border-radius: 3px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {c['border']};
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {c['text3']};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{ background: none; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    border-radius: 3px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: {c['border']};
    border-radius: 3px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {c['text3']};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0; }}

QComboBox {{
    background-color: {c['glass_fill']};
    color: {c['text']};
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
    border-radius: {_RADIUS}px;
    padding: 5px 10px;
    font-weight: 500;
    min-height: 14px;
}}

QComboBox:hover {{
    border-top: 1.5px solid {c['accent']};
    border-left: 1.5px solid {c['accent']};
    color: {c['accent_h']};
}}

QComboBox:on {{
    background-color: {c['inset_bg']};
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {c['surface']};
    color: {c['text']};
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
    border-radius: {_RADIUS_SM}px;
    selection-background-color: {c['accent']};
    selection-color: {c['sel_fg']};
    padding: 4px;
    outline: none;
}}

QGroupBox {{
    background-color: {c['glass_fill']};
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
    border-radius: {_RADIUS}px;
    margin-top: 12px;
    padding: 12px;
    color: {c['text2']};
    font-weight: 600;
    font-size: 11px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {c['accent']};
    font-size: 10px;
    letter-spacing: 1px;
}}

QToolTip {{
    background-color: {c['surface']};
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
    border-radius: {_RADIUS_SM}px;
    color: {c['text']};
    padding: 5px 9px;
    font-size: 11px;
}}

QVideoWidget {{
    background-color: #000000;
    border-radius: {_RADIUS}px;
    border: 1px solid {c['border']};
}}

QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* ── Named widgets (mini window, about dialog, terminal log) ─────────── */

#MiniWindow {{
    background-color: {c['canvas']};
}}

#MiniTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {c['text']};
}}

#MiniSep {{
    border: none;
    border-top: 1px solid {c['border']};
    max-height: 1px;
    background: transparent;
}}

#MiniLabel {{
    color: {c['text2']};
    font-size: 10px;
    font-weight: 600;
}}

#MiniNotepad {{
    background-color: {c['inset_bg']};
    color: {c['text']};
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    border-radius: {_RADIUS}px;
    padding: 8px;
}}

#BtnStart, #BtnPause, #BtnStop {{
    border-radius: {_RADIUS_PILL}px;
}}

#TerminalLog {{
    background-color: {c['terminal_bg']};
    color: {c['terminal_fg']};
    border-top: 1.5px solid {c['shadow_edge']};
    border-left: 1.5px solid {c['shadow_edge']};
    border-bottom: 1.5px solid {c['specular_dim']};
    border-right: 1.5px solid {c['specular_dim']};
    border-radius: {_RADIUS}px;
    padding: 10px;
    font-family: 'SF Mono', 'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
    font-size: 11px;
}}

#AboutCard {{
    background-color: {c['glass_fill']};
    border-radius: {_RADIUS}px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
}}

#BtnClose, #BtnGithub, #BtnDonate {{
    background-color: {c['glass_fill']};
    border-radius: {_RADIUS_PILL}px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
    padding: 6px 16px;
}}

#BtnClose:hover, #BtnGithub:hover, #BtnDonate:hover {{
    background-color: {c['glass_fill_hov']};
    border-top: 1.5px solid {c['accent']};
    border-left: 1.5px solid {c['accent']};
}}

#AboutBadge {{
    background-color: {c['glass_fill']};
    border-radius: 18px;
    border-top: 1.5px solid {c['specular']};
    border-left: 1.5px solid {c['specular_dim']};
    border-bottom: 1.5px solid {c['shadow_edge']};
    border-right: 1.5px solid {c['shadow_edge']};
}}

#AboutAppName {{
    font-size: 16px;
    font-weight: 700;
    color: {c['text']};
}}

#AboutVersion {{
    font-size: 11px;
    color: {c['text2']};
}}

#AboutDivider {{
    border: none;
    border-top: 1px solid {c['border']};
    max-height: 1px;
    background: transparent;
}}

#AboutBy, #AboutDev, #AboutDesc, #AboutLicense {{
    color: {c['text2']};
    font-size: 11px;
}}
"""


def apply_theme(widget: QWidget, dark: bool = True) -> None:
    c = _DARK if dark else _LIGHT
    widget.setStyleSheet(_sheet(c))


NEU_STYLE = _sheet(_DARK)
