from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from backend.lang_id import (
    LOG_SCAN_FOLDER, LOG_TOTAL_PART, LOG_MULAI_PART,
    LOG_KLIK_UP, LOG_PILIH_VID, LOG_CONFIRM_VID,
    LOG_ISI_DESK, LOG_SCROLL, LOG_PILIH_PLAYLIST,
    LOG_KLIK_POST, LOG_POST_NOW, LOG_UPLOAD_TUNGGU,
    LOG_PART_BERES, LOG_SEMUA_BERES,
    LOG_BERSIHIN, LOG_FILE_DIHAPUS, LOG_BERSIHIN_KELAR,
    LOG_DIJEDA, LOG_DILANJUT, LOG_DISTOP, LOG_ERROR,
    ERR_FOLDER_KOSONG, ERR_PART_GAK_KETEMU, ERR_PYAUTOGUI,
)
from backend.autoup_config import (
    JEDA_AWAL_S, JEDA_STANDAR_S, JEDA_PLAYLIST_S,
    JEDA_POST_S, JEDA_POST_NOW_S, JEDA_AKHIR_A_S,
    JEDA_AKHIR_B_S, JEDA_UPLOAD_S,
    COORD_UP_BUTTON, COORD_PICK_VID,
    COORD_DESKRIPSI, COORD_ARROW_PLAYLIST,
    COORD_SELECT_PLAYLIST, COORD_POST_BUTTON, COORD_POST_NOW,
    SCROLL_INTENSITY, MOUSE_DURATION, TYPING_INTERVAL,
)


def _scan_parts(folder: Path) -> list[Path]:
    pattern = re.compile(r"[Pp]art\s*\d+", re.IGNORECASE)
    candidates = sorted(
        [f for f in folder.iterdir() if f.is_file() and pattern.search(f.stem)],
        key=lambda p: int(re.search(r"\d+", re.search(r"[Pp]art\s*(\d+)", p.stem).group()).group())
    )
    return candidates


class AutoUpWorker(QThread):
    sig_log      = Signal(str)
    sig_progress = Signal(int, int)
    sig_done     = Signal()
    sig_error    = Signal(str)

    def __init__(
        self,
        episode_folder: Path,
        deskripsi: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.episode_folder  = episode_folder
        self.deskripsi       = deskripsi
        self._paused         = False
        self._stopped        = False
        self._uploaded_files: list[Path] = []

    def pause(self) -> None:
        self._paused = True
        self.sig_log.emit(LOG_DIJEDA)

    def resume(self) -> None:
        self._paused = False
        self.sig_log.emit(LOG_DILANJUT)

    def stop(self) -> None:
        self._stopped = True
        self._paused  = False
        self.sig_log.emit(LOG_DISTOP)

    def _cek_pause_stop(self) -> bool:
        while self._paused and not self._stopped:
            time.sleep(0.5)
        return self._stopped

    def _jeda(self, detik: float) -> bool:
        slices = int(detik * 2)
        for _ in range(slices):
            if self._stopped:
                return True
            while self._paused and not self._stopped:
                time.sleep(0.5)
            time.sleep(0.5)
        return self._stopped

    def _import_pyautogui(self):
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE    = 0.1
            return pyautogui
        except ImportError:
            self.sig_error.emit(ERR_PYAUTOGUI)
            return None

    def _upload_satu_part(self, pg, video_path: Path, index: int, total: int) -> bool:
        self.sig_log.emit(LOG_MULAI_PART.format(index, total))

        if self._jeda(JEDA_AWAL_S):
            return False

        self.sig_log.emit(LOG_KLIK_UP)
        pg.click(*COORD_UP_BUTTON, duration=MOUSE_DURATION)
        if self._jeda(JEDA_STANDAR_S):
            return False

        self.sig_log.emit(LOG_PILIH_VID.format(video_path.name))
        pg.click(*COORD_PICK_VID, duration=MOUSE_DURATION)
        pg.typewrite(str(video_path), interval=TYPING_INTERVAL)
        pg.press("enter")
        if self._jeda(JEDA_STANDAR_S):
            return False

        self.sig_log.emit(LOG_CONFIRM_VID)
        pg.press("return")
        if self._jeda(JEDA_STANDAR_S):
            return False

        self.sig_log.emit(LOG_ISI_DESK)
        pg.doubleClick(*COORD_DESKRIPSI, duration=MOUSE_DURATION)
        import pyperclip
        pyperclip.copy(self.deskripsi)
        pg.hotkey("ctrl", "v")
        if self._jeda(JEDA_STANDAR_S):
            return False

        self.sig_log.emit(LOG_SCROLL)
        pg.scroll(SCROLL_INTENSITY)
        if self._jeda(JEDA_STANDAR_S):
            return False

        self.sig_log.emit(LOG_PILIH_PLAYLIST)
        pg.click(*COORD_ARROW_PLAYLIST, duration=MOUSE_DURATION)
        if self._jeda(JEDA_PLAYLIST_S):
            return False

        pg.click(*COORD_SELECT_PLAYLIST, duration=MOUSE_DURATION)
        if self._jeda(JEDA_PLAYLIST_S):
            return False

        self.sig_log.emit(LOG_KLIK_POST)
        pg.click(*COORD_POST_BUTTON, duration=MOUSE_DURATION)
        if self._jeda(JEDA_POST_S):
            return False

        self.sig_log.emit(LOG_POST_NOW)
        pg.click(*COORD_POST_NOW, duration=MOUSE_DURATION)
        if self._jeda(JEDA_POST_NOW_S):
            return False

        if self._jeda(JEDA_AKHIR_A_S):
            return False
        if self._jeda(JEDA_AKHIR_B_S):
            return False

        self.sig_log.emit(LOG_UPLOAD_TUNGGU)
        if self._jeda(JEDA_UPLOAD_S):
            return False

        self._uploaded_files.append(video_path)
        self.sig_log.emit(LOG_PART_BERES.format(index))
        return True

    def _housekeeping(self) -> None:
        self.sig_log.emit(LOG_BERSIHIN)
        for f in self._uploaded_files:
            try:
                f.unlink(missing_ok=True)
                self.sig_log.emit(LOG_FILE_DIHAPUS.format(f.name))
            except Exception as exc:
                self.sig_log.emit(LOG_ERROR.format(str(exc)))
        self.sig_log.emit(LOG_BERSIHIN_KELAR)

    def run(self) -> None:
        folder = self.episode_folder

        if not folder.exists() or not folder.is_dir():
            self.sig_error.emit(ERR_FOLDER_KOSONG)
            return

        self.sig_log.emit(LOG_SCAN_FOLDER.format(folder))
        parts = _scan_parts(folder)

        if not parts:
            self.sig_error.emit(ERR_PART_GAK_KETEMU)
            return

        total = len(parts)
        self.sig_log.emit(LOG_TOTAL_PART.format(total))

        pg = self._import_pyautogui()
        if pg is None:
            return

        for idx, video_path in enumerate(parts, start=1):
            if self._stopped:
                break

            self.sig_progress.emit(idx - 1, total)
            sukses = self._upload_satu_part(pg, video_path, idx, total)
            if not sukses:
                break
            self.sig_progress.emit(idx, total)

        if not self._stopped:
            self.sig_log.emit(LOG_SEMUA_BERES)
            self._housekeeping()

        self.sig_done.emit()
