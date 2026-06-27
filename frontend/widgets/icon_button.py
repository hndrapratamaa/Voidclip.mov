from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QWidget


class IconButton(QPushButton):
    def __init__(
        self,
        glyph:    str,
        tooltip:  str  = "",
        size:     int  = 32,
        icon_sz:  int  = 16,
        role:     str  = "iconBtn",
        on_click: Optional[Callable] = None,
        parent:   Optional[QWidget]  = None,
    ) -> None:
        super().__init__(parent)
        self.setText(glyph)
        self.setFixedSize(size, size)
        self.setProperty("role", role)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        calculated_radius = size // 2
        self.setStyleSheet(f"border-radius: {calculated_radius}px;")

        if tooltip:
            self.setToolTip(tooltip)

        if on_click:
            self.clicked.connect(on_click)

    @classmethod
    def from_icon(
        cls,
        icon:     QIcon,
        tooltip:  str = "",
        size:     int = 32,
        icon_sz:  int = 16,
        role:     str = "iconBtn",
        on_click: Optional[Callable] = None,
        parent:   Optional[QWidget]  = None,
    ) -> "IconButton":
        btn = cls("", tooltip, size, icon_sz, role, on_click, parent)
        btn.setIcon(icon)
        btn.setIconSize(QSize(icon_sz, icon_sz))
        return btn


class IconButtonGroup:
    def __init__(self, exclusive: bool = False) -> None:
        self._btns: list[IconButton] = []
        self._exclusive              = exclusive

    def add(self, btn: IconButton) -> IconButton:
        if self._exclusive:
            btn.setCheckable(True)
            btn.clicked.connect(lambda: self._activate(btn))
        self._btns.append(btn)
        return btn

    def _activate(self, active: IconButton) -> None:
        for b in self._btns:
            b.setChecked(b is active)

    def widgets(self) -> list[IconButton]:
        return list(self._btns)