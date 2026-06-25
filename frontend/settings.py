from __future__ import annotations
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QGroupBox, QVBoxLayout,
)
from backend import database as db
from backend.config import RENDER_PRESETS, SubtitleMode
from backend.renderer import Renderer


class SettingsDialog(QDialog):
    def __init__(self, renderer: Renderer, parent=None) -> None:
        super().__init__(parent)
        self.renderer = renderer
        self.setWindowTitle("Settings")
        self.setMinimumWidth(440)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        grp = QGroupBox("Render Preset")
        pf = QFormLayout(grp)

        self.cb_preset = QComboBox()
        self.cb_preset.addItems(list(RENDER_PRESETS.keys()))
        pf.addRow("Preset:", self.cb_preset)

        self.cb_subtitle = QComboBox()
        self.cb_subtitle.addItems(["keep", "burn", "disable"])
        pf.addRow("Subtitle Mode:", self.cb_subtitle)

        layout.addWidget(grp)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._apply)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _apply(self) -> None:
        self.renderer.set_preset(self.cb_preset.currentText())
        self.renderer.set_subtitle_mode(self.cb_subtitle.currentText())
        self.accept()
