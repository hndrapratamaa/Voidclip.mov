from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QFileSystemWatcher
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget
)
from backend.config import INPUT_DIR, SUPPORTED_VIDEO_EXTENSIONS


class SidebarLeft(QWidget):
    def __init__(self, renderer, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.renderer = renderer
        self._build_ui()
        self._watch()
        self.refresh()

    def _build_ui(self) -> None:
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(6)
        self.btn_import = QPushButton("📥  Import")
        self.btn_delete = QPushButton("🗑  Delete")
        self.btn_import.clicked.connect(self._import)
        self.btn_delete.clicked.connect(self._delete)
        self.actions_layout.addWidget(self.btn_import)
        self.actions_layout.addWidget(self.btn_delete)

    def _watch(self) -> None:
        self.watcher = QFileSystemWatcher([str(INPUT_DIR)], self)
        self.watcher.directoryChanged.connect(self.refresh)

    def refresh(self) -> None:
        self.list_widget.clear()
        if INPUT_DIR.exists():
            for f in sorted(INPUT_DIR.iterdir()):
                if f.is_file() and f.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                    item = QListWidgetItem(f.name)
                    item.setData(Qt.ItemDataRole.UserRole, str(f))
                    self.list_widget.addItem(item)

    def get_selected_paths(self) -> list[Path]:
        return [Path(i.data(Qt.ItemDataRole.UserRole)) for i in self.list_widget.selectedItems()]

    def _import(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import Videos", str(Path.home()), "Videos (*.mp4 *.mkv *.mov)"
        )
        import shutil
        for p in paths:
            shutil.copy2(Path(p), INPUT_DIR / Path(p).name)
        self.refresh()

    def _delete(self) -> None:
        from send2trash import send2trash
        for i in self.list_widget.selectedItems():
            p = Path(i.data(Qt.ItemDataRole.UserRole))
            if p.exists():
                send2trash(str(p))
        self.refresh()
