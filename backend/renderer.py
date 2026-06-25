"""
backend/renderer.py
===================
Jembatan kontroler (Facade) antara backend processing dan GUI PySide6.

Membungkus run_job ke dalam threading.Thread standar (kompatibel dengan
PySide6 QThread maupun threading biasa) agar GUI tidak macet saat render.

Pola komunikasi:
  GUI membuat RenderController, mendaftar callback, lalu memanggil .start().
  Semua callback dipanggil dari thread worker — GUI harus menggunakan
  Qt signal/slot atau QMetaObject.invokeMethod untuk update widget yang aman.

Kelas utama:
  - RenderController  : Thread wrapper utama dengan sinyal-sinyal progres.
  - RenderControllerQt: Subklass QThread untuk PySide6 (import bersyarat).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from backend.config import (
    DEFAULT_PRESET_NAME,
    DEFAULT_WATERMARK_CONFIG,
    DEFAULT_ZOOM_CONFIG,
    OUTPUT_DIR,
    RENDER_PRESETS,
    WatermarkConfig,
    ZoomConfig,
)
from backend.video_processor import (
    JobSpec,
    ProgressCallback,
    SegmentProgress,
    prepare_job,
    run_job,
)


# ---------------------------------------------------------------------------
# Tipe callback yang diekspos ke GUI
# ---------------------------------------------------------------------------

LogCallback      = Callable[[str], None]
FinishCallback   = Callable[[bool, Optional[str]], None]
# bool = sukses, str = pesan error atau None


# ---------------------------------------------------------------------------
# Dataclass konfigurasi render yang dikirim dari GUI
# ---------------------------------------------------------------------------

@dataclass
class RenderRequest:
    """
    Parameter render yang diisi oleh GUI dan dikirimkan ke RenderController.
    Semua nilai memiliki default yang masuk akal agar GUI tidak wajib mengisi semua.
    """
    input_path:    Path
    preset_name:   str            = DEFAULT_PRESET_NAME
    watermark_cfg: WatermarkConfig = None   # type: ignore[assignment]
    zoom_config:   ZoomConfig      = None   # type: ignore[assignment]
    output_dir:    Optional[Path]  = None
    seed:          Optional[int]   = None   # None = benar-benar acak

    def __post_init__(self) -> None:
        if self.watermark_cfg is None:
            self.watermark_cfg = DEFAULT_WATERMARK_CONFIG
        if self.zoom_config is None:
            self.zoom_config = DEFAULT_ZOOM_CONFIG
        if self.output_dir is None:
            self.output_dir = OUTPUT_DIR


# ---------------------------------------------------------------------------
# RenderController: threading.Thread biasa (backend-agnostic)
# ---------------------------------------------------------------------------

class RenderController(threading.Thread):
    """
    Thread controller untuk satu pekerjaan render.

    Cara pakai (threading murni, tanpa PySide6):
    -----------------------------------------------
        req = RenderRequest(input_path=Path("video.mp4"))
        ctrl = RenderController(request=req)
        ctrl.on_log      = lambda msg: print(msg)
        ctrl.on_progress = lambda p: print(f"Overall: {p.overall_pct:.1f}%")
        ctrl.on_finish   = lambda ok, err: print("OK" if ok else f"Error: {err}")
        ctrl.start()
        ctrl.join()   # blokir sampai selesai (opsional)

    Cara cancel:
        ctrl.cancel()

    Cara pakai di PySide6 (non-QThread):
    -------------------------------------
        Gunakan QMetaObject.invokeMethod atau emit signal dari dalam callback
        untuk memastikan pembaruan UI terjadi di main thread.
        Atau gunakan subklass RenderControllerQt di bawah.
    """

    def __init__(
        self,
        request: RenderRequest,
        on_log:      Optional[LogCallback]      = None,
        on_progress: Optional[ProgressCallback] = None,
        on_finish:   Optional[FinishCallback]   = None,
    ) -> None:
        super().__init__(daemon=True, name=f"RenderThread-{request.input_path.stem[:20]}")
        self.request    = request
        self.on_log     = on_log
        self.on_progress = on_progress
        self.on_finish   = on_finish

        self._cancel_event = threading.Event()
        self._job: Optional[JobSpec] = None
        self._success: Optional[bool] = None
        self._error_msg: Optional[str] = None

    # ------------------------------------------------------------------
    # Properti publik (aman dibaca dari thread manapun)
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """True jika thread sedang berjalan."""
        return self.is_alive()

    @property
    def job(self) -> Optional[JobSpec]:
        """JobSpec yang sedang/sudah dikerjakan (None sebelum run)."""
        return self._job

    @property
    def succeeded(self) -> Optional[bool]:
        """True/False setelah selesai, None saat masih berjalan."""
        return self._success

    @property
    def error_message(self) -> Optional[str]:
        """Pesan error terakhir, atau None jika sukses."""
        return self._error_msg

    # ------------------------------------------------------------------
    # Kontrol
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """
        Kirim sinyal cancel ke proses FFmpeg yang sedang berjalan.
        Thread akan berhenti setelah segmen aktif selesai dibatalkan.
        """
        self._cancel_event.set()
        if self.on_log:
            self.on_log("[controller] Permintaan cancel dikirim...")

    def wait_done(self, timeout: Optional[float] = None) -> bool:
        """
        Blokir sampai thread selesai.
        Kembalikan True jika thread selesai dalam waktu timeout.
        """
        self.join(timeout=timeout)
        return not self.is_alive()

    # ------------------------------------------------------------------
    # Entri titik thread
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Entri titik eksekusi thread.
        Dipanggil otomatis oleh .start().
        """
        req = self.request

        def _log(msg: str) -> None:
            if self.on_log:
                self.on_log(msg)

        _log(f"[controller] Memulai: '{req.input_path.name}' | "
             f"preset='{req.preset_name}'")

        # --- Fase 1: Siapkan job (probe + hitung segmen) ---
        try:
            self._job = prepare_job(
                input_path=req.input_path,
                preset_name=req.preset_name,
                watermark_cfg=req.watermark_cfg,
                zoom_config=req.zoom_config,
                output_dir=req.output_dir,
                seed=req.seed,
            )
        except Exception as exc:
            self._success = False
            self._error_msg = f"Gagal menyiapkan job: {exc}"
            _log(f"[controller] ERROR prepare_job: {exc}")
            if self.on_finish:
                self.on_finish(False, self._error_msg)
            return

        job = self._job
        _log(
            f"[controller] Job '{job.job_id}' disiapkan: "
            f"{job.total_segments} segmen, "
            f"~{job.total_input_duration:.0f}s dari "
            f"{job.video_info.duration:.0f}s video."
        )

        # --- Fase 2: Jalankan render ---
        try:
            run_job(
                job=job,
                log_callback=self.on_log,
                progress_callback=self.on_progress,
                cancel_event=self._cancel_event,
            )
            self._success = True
            _log(f"[controller] Job selesai dalam {job.elapsed_sec:.1f}s.")
            if self.on_finish:
                self.on_finish(True, None)

        except RuntimeError as exc:
            self._success = False
            self._error_msg = str(exc)
            _log(f"[controller] ERROR run_job: {exc}")
            if self.on_finish:
                self.on_finish(False, self._error_msg)

        except Exception as exc:
            self._success = False
            self._error_msg = f"Error tidak terduga: {exc}"
            _log(f"[controller] UNEXPECTED ERROR: {exc}")
            if self.on_finish:
                self.on_finish(False, self._error_msg)


# ---------------------------------------------------------------------------
# RenderControllerQt: Subklass QThread untuk integrasi PySide6 langsung
# ---------------------------------------------------------------------------

def _try_make_qt_controller() -> Optional[type]:
    """
    Buat kelas RenderControllerQt secara dinamis hanya jika PySide6 tersedia.
    Kembalikan kelas atau None jika PySide6 tidak terinstall.
    """
    try:
        from PySide6.QtCore import QThread, Signal, QObject   # type: ignore[import]
    except ImportError:
        return None

    class RenderControllerQt(QThread):
        """
        QThread wrapper untuk RenderController.

        Sinyal PySide6:
          log_received(str)                  : Setiap baris log
          progress_updated(SegmentProgress)  : Setiap tick progres
          render_finished(bool, str)         : Selesai (sukses, pesan_error)

        Cara pakai di GUI PySide6:
        --------------------------
            req  = RenderRequest(input_path=Path("video.mp4"))
            ctrl = RenderControllerQt(request=req, parent=self)
            ctrl.log_received.connect(self.append_log)
            ctrl.progress_updated.connect(self.update_progress_bar)
            ctrl.render_finished.connect(self.on_render_done)
            ctrl.start()

        Cara cancel:
            ctrl.cancel()   # panggil dari thread GUI kapan saja
        """

        log_received     = Signal(str)
        progress_updated = Signal(object)   # SegmentProgress (tidak bisa hint langsung)
        render_finished  = Signal(bool, str)

        def __init__(
            self,
            request: RenderRequest,
            parent: Optional[QObject] = None,
        ) -> None:
            super().__init__(parent)
            self.request        = request
            self._cancel_event  = threading.Event()
            self._job: Optional[JobSpec] = None
            self._success: Optional[bool] = None
            self._error_msg: Optional[str] = None

        # ------------------------------------------------------------------
        # Properti
        # ------------------------------------------------------------------

        @property
        def job(self) -> Optional[JobSpec]:
            return self._job

        @property
        def succeeded(self) -> Optional[bool]:
            return self._success

        @property
        def error_message(self) -> Optional[str]:
            return self._error_msg

        # ------------------------------------------------------------------
        # Kontrol
        # ------------------------------------------------------------------

        def cancel(self) -> None:
            """Batalkan render yang sedang berjalan."""
            self._cancel_event.set()
            self.log_received.emit("[controller] Permintaan cancel dikirim...")

        # ------------------------------------------------------------------
        # QThread.run() — entri titik thread Qt
        # ------------------------------------------------------------------

        def run(self) -> None:
            req = self.request

            def _log(msg: str) -> None:
                self.log_received.emit(msg)

            def _on_progress(prog: SegmentProgress) -> None:
                self.progress_updated.emit(prog)

            _log(f"[controller-qt] Memulai: '{req.input_path.name}' | "
                 f"preset='{req.preset_name}'")

            # Fase 1: prepare_job
            try:
                self._job = prepare_job(
                    input_path=req.input_path,
                    preset_name=req.preset_name,
                    watermark_cfg=req.watermark_cfg,
                    zoom_config=req.zoom_config,
                    output_dir=req.output_dir,
                    seed=req.seed,
                )
            except Exception as exc:
                self._success = False
                self._error_msg = f"Gagal menyiapkan job: {exc}"
                _log(f"[controller-qt] ERROR prepare_job: {exc}")
                self.render_finished.emit(False, self._error_msg)
                return

            job = self._job
            _log(
                f"[controller-qt] Job '{job.job_id}' disiapkan: "
                f"{job.total_segments} segmen, "
                f"~{job.total_input_duration:.0f}s."
            )

            # Fase 2: run_job
            try:
                run_job(
                    job=job,
                    log_callback=_log,
                    progress_callback=_on_progress,
                    cancel_event=self._cancel_event,
                )
                self._success = True
                _log(f"[controller-qt] Job selesai dalam {job.elapsed_sec:.1f}s.")
                self.render_finished.emit(True, "")

            except RuntimeError as exc:
                self._success = False
                self._error_msg = str(exc)
                _log(f"[controller-qt] ERROR run_job: {exc}")
                self.render_finished.emit(False, self._error_msg)

            except Exception as exc:
                self._success = False
                self._error_msg = f"Error tidak terduga: {exc}"
                _log(f"[controller-qt] UNEXPECTED ERROR: {exc}")
                self.render_finished.emit(False, self._error_msg)

    return RenderControllerQt


# Ekspor kelas Qt jika tersedia, None jika tidak
RenderControllerQt: Optional[type] = _try_make_qt_controller()


# ---------------------------------------------------------------------------
# Factory function — pilih implementasi terbaik secara otomatis
# ---------------------------------------------------------------------------

def create_controller(
    request:     RenderRequest,
    prefer_qt:   bool = True,
    parent:      object = None,
) -> "RenderController | RenderControllerQt":
    """
    Buat controller yang sesuai:
      - Jika prefer_qt=True dan PySide6 tersedia, kembalikan RenderControllerQt.
      - Jika tidak, kembalikan RenderController (threading.Thread biasa).

    Parameter
    ---------
    request    : RenderRequest dari GUI.
    prefer_qt  : Gunakan QThread jika PySide6 tersedia (default True).
    parent     : QObject parent untuk RenderControllerQt (diabaikan jika non-Qt).

    Contoh penggunaan universal:
    ----------------------------
        ctrl = create_controller(RenderRequest(input_path=Path("video.mp4")))
        if hasattr(ctrl, "log_received"):
            # PySide6 QThread
            ctrl.log_received.connect(my_log_slot)
            ctrl.progress_updated.connect(my_progress_slot)
            ctrl.render_finished.connect(my_finish_slot)
        else:
            # threading.Thread biasa
            ctrl.on_log      = my_log_callback
            ctrl.on_progress = my_progress_callback
            ctrl.on_finish   = my_finish_callback
        ctrl.start()
    """
    if prefer_qt and RenderControllerQt is not None:
        return RenderControllerQt(request=request, parent=parent)   # type: ignore[call-arg]
    return RenderController(request=request)


# ---------------------------------------------------------------------------
# Utilitas: jalankan job secara blocking (untuk scripting / test)
# ---------------------------------------------------------------------------

def run_blocking(
    request:     RenderRequest,
    log_callback:      Optional[LogCallback]      = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> JobSpec:
    """
    Jalankan job di thread saat ini (blocking).
    Berguna untuk testing dan scripting CLI tanpa GUI.

    Kembalikan JobSpec yang telah selesai.
    Raise RuntimeError jika render gagal.
    """
    job = prepare_job(
        input_path=request.input_path,
        preset_name=request.preset_name,
        watermark_cfg=request.watermark_cfg,
        zoom_config=request.zoom_config,
        output_dir=request.output_dir,
        seed=request.seed,
    )
    run_job(
        job=job,
        log_callback=log_callback,
        progress_callback=progress_callback,
        cancel_event=None,
    )
    return job
