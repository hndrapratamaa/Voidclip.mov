from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional
from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QMainWindow
from frontend.auto_up.worker import AutoUpWorker

class AutoUpController(QObject):
    def __init__(
        self,
        main_window: QMainWindow,
        log_cb: Optional[Callable[[str], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self._log_cb = log_cb
        self._worker: Optional[AutoUpWorker] = None
        self._paused = False
        self._episode_folder: Optional[Path] = None

    def set_episode_folder(self, folder: Path) -> None:
        self._episode_folder = folder

    def _emit_log(self, msg: str) -> None:
        if self._log_cb:
            self._log_cb(msg)

    def launch(self) -> None:
        if not self._episode_folder or not self._episode_folder.exists():
            self._emit_log("⚠️ Folder target belum ditentukan atau tidak ditemukan.")
            return
        if self._worker is not None:
            self._emit_log("⚠️ Proses background antrean sedang berjalan.")
            return
        self._worker = AutoUpWorker(episode_folder=self._episode_folder)
        self._connect_worker_signals(self._worker)
        self._paused = False
        self._emit_log("🚀 Memulai proses pengerjaan pipeline otomatisasi...")
        self._worker.start()

    def _connect_worker_signals(self, worker: AutoUpWorker) -> None:
        worker.sig_log.connect(self._on_worker_log)
        worker.sig_progress.connect(self._on_worker_progress)
        worker.sig_done.connect(self._on_worker_done)
        worker.sig_error.connect(self._on_worker_error)

    def _teardown_worker(self, wait_msecs: int = 2000) -> None:
        if self._worker is None:
            return
        self._worker.stop()
        if not self._worker.wait(wait_msecs):
            self._worker.terminate()
            self._worker.wait()
        self._worker = None

    def _on_toggle_pause(self) -> None:
        if self._worker is None:
            return
        if self._paused:
            self._paused = False
            self._emit_log("▶️ Melanjutkan kembali antrean.")
            self._worker.resume()
        else:
            self._paused = True
            self._emit_log("⏸️ Menjeda antrean setelah tugas aktif selesai.")
            self._worker.pause()

    def _on_stop(self) -> None:
        self._teardown_worker(wait_msecs=3000)
        self._emit_log("⏹️ Seluruh antrean proses berhasil dibatalkan.")

    def on_main_window_close(self) -> None:
        self._teardown_worker(wait_msecs=1500)

    @Slot(str)
    def _on_worker_log(self, msg: str) -> None:
        self._emit_log(msg)

    @Slot(int, int)
    def _on_worker_progress(self, done: int, total: int) -> None:
        self._emit_log(f"📊 Kemajuan: {done}/{total} video selesai diproses.")

    @Slot()
    def _on_worker_done(self) -> None:
        self._emit_log("🎉 Selesai! Semua item dalam folder berhasil diproses.")
        self._teardown_worker(wait_msecs=100)

    @Slot(str)
    def _on_worker_error(self, err_msg: str) -> None:
        self._emit_log(f"❌ Hambatan Sistem: {err_msg}")
        self._teardown_worker(wait_msecs=100)