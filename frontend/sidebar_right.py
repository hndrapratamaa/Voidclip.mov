from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QDir, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileSystemModel, QHBoxLayout, QPushButton,
    QTreeView, QVBoxLayout, QWidget
)
from backend.config import OUTPUT_DIR


class SidebarRight(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.btn_back = QPushButton("⏴ Back")
        self.btn_back.setFixedSize(70, 26)
        self.btn_back.clicked.connect(self._go_back)

        self.btn_explore = QPushButton("📁 Folder")
        self.btn_explore.setFixedSize(80, 26)
        self.btn_explore.clicked.connect(self._open_in_explorer)

        self.model = QFileSystemModel()
        self.model.setRootPath(str(OUTPUT_DIR))
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.setRootIndex(self.model.index(str(OUTPUT_DIR)))
        self.tree_view.setHeaderHidden(True)
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        self.tree_view.doubleClicked.connect(self._on_double_click)

        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)

        self.btn_play = QPushButton("▶ Play / Pause")
        self.btn_play.setFixedWidth(130)
        self.btn_play.clicked.connect(self._toggle_play)

    def _on_double_click(self, index) -> None:
        path = Path(self.model.filePath(index))
        if path.is_dir():
            self.tree_view.setRootIndex(index)
        elif path.suffix == ".mp4":
            self.player.setSource(QUrl.fromLocalFile(str(path)))
            self.player.play()

    def _go_back(self) -> None:
        cur = self.tree_view.rootIndex()
        if self.model.filePath(cur) != str(OUTPUT_DIR):
            self.tree_view.setRootIndex(cur.parent())

    def _toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _open_in_explorer(self) -> None:
        idxs = self.tree_view.selectedIndexes()
        if not idxs:
            return
        path_str = self.model.filePath(idxs[0])
        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", os.path.normpath(path_str)])
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", path_str])
        else:
            subprocess.run(["xdg-open", str(Path(path_str).parent)])
