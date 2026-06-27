from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QMainWindow, QMessageBox

from backend.lang_id import (
    MSG_ANTRIAN_KOSONG, MSG_SELESAI, MSG_GAGAL,
    LOG_ERROR, ERR_FOLDER_KOSONG,
    JUDUL_AUTO_UP,
)
from frontend.auto_up.mini_window import MiniWindow
from frontend.auto_up.worker import AutoUpWorker


class AutoUpController(QObject):
    def __init__(
        self,
        main_window: QMainWindow,
        log_cb: Optional[Callable[[str], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.main_window     = main_window
        self._log_cb         = log_cb
        self._worker: Optional[AutoUpWorker] = None
        self._paused         = False
        self._mini: Optional[MiniWindow] = None
        self._episode_folder: Optional[Path] = None

    def set_episode_folder(self, folder: Path) -> None:
        self._episode_folder = folder

    def _emit_log(self, msg: str) -> None:
        if self._log_cb:
            self._log_cb(msg)

    def launch(self) -> None:
        if self._mini is None:
            self._mini = MiniWindow()
            self._mini.sig_start.connect(self._on_start)
            self._mini.sig_pause.connect(self._on_pause)
            self._mini.sig_stop.connect(self._on_stop)

        self.main_window.showMinimized()
        self._mini.show()
        self._mini.raise_()
        self._mini.activateWindow()

    def _on_start(self) -> None:
        if self._episode_folder is None or not self._episode_folder.is_dir():
            QMessageBox.warning(self._mini, JUDUL_AUTO_UP, ERR_FOLDER_KOSONG)
            return

        deskripsi = self._mini.get_deskripsi() if self._mini else ""

        self._worker = AutoUpWorker(
            episode_folder=self._episode_folder,
            deskripsi=deskripsi,
        )
        self._worker.sig_log.connect(self._on_worker_log)
        self._worker.sig_progress.connect(self._on_worker_progress)
        self._worker.sig_done.connect(self._on_worker_done)
        self._worker.sig_error.connect(self._on_worker_error)

        self._paused = False
        if self._mini:
            self._mini.set_running(True)
            self._mini.set_paused_label(False)

        self._worker.start()

    def _on_pause(self) -> None:
        if self._worker is None:
            return

        if self._paused:
            self._paused = False
            self._worker.resume()
            if self._mini:
                self._mini.set_paused_label(False)
        else:
            self._paused = True
            self._worker.pause()
            if self._mini:
                self._mini.set_paused_label(True)

    def _on_stop(self) -> None:
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(msecs=3000)
        self._reset_ui()

    @Slot(str)
    def _on_worker_log(self, msg: str) -> None:
        self._emit_log(msg)

    @Slot(int, int)
    def _on_worker_progress(self, done: int, total: int) -> None:
        self._emit_log(f"Progress: {done}/{total} part kelar bos.")

    @Slot()
    def _on_worker_done(self) -> None:
        self._emit_log(MSG_SELESAI)
        self._reset_ui()
        self._restore_main()

    @Slot(str)
    def _on_worker_error(self, msg: str) -> None:
        self._emit_log(LOG_ERROR.format(msg))
        if self._mini:
            QMessageBox.critical(self._mini, JUDUL_AUTO_UP, msg)
        self._reset_ui()

    def _reset_ui(self) -> None:
        self._paused = False
        self._worker = None
        if self._mini:
            self._mini.set_running(False)
            self._mini.set_paused_label(False)

    def _restore_main(self) -> None:
        if self._mini:
            self._mini.hide()
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def close(self) -> None:
        self._on_stop()
        if self._mini:
            self._mini.close()
            self._mini = None
