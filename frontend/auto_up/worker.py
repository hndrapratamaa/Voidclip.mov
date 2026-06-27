from __future__ import annotations
import time
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition
from tiktokautouploader.function import upload_tiktok, TikTokUploadError

class AutoUpWorker(QThread):
    sig_log = Signal(str)
    sig_progress = Signal(int, int)
    sig_done = Signal()
    sig_error = Signal(str)

    def __init__(self, episode_folder: Path, parent=None) -> None:
        super().__init__(parent)
        self.episode_folder = episode_folder
        self._is_running = True
        self._is_paused = False
        self._mutex = QMutex()
        self._pause_cond = QWaitCondition()

    def run(self) -> None:
        try:
            video_files = sorted([p for p in self.episode_folder.glob("*.mp4") if p.is_file()])
            total_files = len(video_files)
            if total_files == 0:
                self.sig_error.emit("Tidak ditemukan berkas video .mp4 di folder target.")
                return
            for idx, video_path in enumerate(video_files):
                self._mutex.lock()
                while self._is_paused:
                    self._pause_cond.wait(self._mutex)
                if not self._is_running:
                    self._mutex.unlock()
                    break
                self._mutex.unlock()
                caption = video_path.stem
                self.sig_log.emit(f"🔄 Memproses unggahan otomatis: {video_path.name}")
                try:
                    res = upload_tiktok(
                        video=str(video_path),
                        description=caption,
                        accountname="akun_utama_voidclip",
                        headless=True
                    )
                    if res == "Error":
                        raise TikTokUploadError("Driver internal mengembalikan status Error")
                    self.sig_log.emit(f"✅ Berhasil diunggah sempurna: {video_path.name}")
                except TikTokUploadError as e:
                    self.sig_log.emit(f"❌ Kesalahan Unggahan ({video_path.name}): {str(e)}")
                except Exception as e:
                    self.sig_log.emit(f"❌ Hambatan Tak Terduga ({video_path.name}): {str(e)}")
                self.sig_progress.emit(idx + 1, total_files)
                time.sleep(2)
            if self._is_running:
                self.sig_done.emit()
        except Exception as e:
            self.sig_error.emit(f"Kritis Engine Error: {str(e)}")

    def pause(self) -> None:
        self._mutex.lock()
        self._is_paused = True
        self._mutex.unlock()

    def resume(self) -> None:
        self._mutex.lock()
        self._is_paused = False
        self._pause_cond.wakeAll()
        self._mutex.unlock()

    def stop(self) -> None:
        self._mutex.lock()
        self._is_running = False
        self._is_paused = False
        self._pause_cond.wakeAll()
        self._mutex.unlock()