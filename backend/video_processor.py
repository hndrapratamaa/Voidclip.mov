"""
backend/video_processor.py
==========================
Lapisan tengah yang mengelola logika pekerjaan (job) secara stateless.

Tanggung jawab:
  - 'prepare_job': Menghitung daftar potongan segmen acak (tanpa DB).
  - 'run_job': Mengeksekusi semua segmen secara sekuensial dan menghitung
    progres live yang lengkap: seg_num, total_segs, seg_pct, overall_pct,
    fps, speed, eta_sec — kemudian dikirim ke GUI via callback.
  - Semua state disimpan sepenuhnya di memori RAM dalam dataclass Python.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from backend.config import (
    CACHE_DIR,
    DEFAULT_WATERMARK_CONFIG,
    DEFAULT_ZOOM_CONFIG,
    OUTPUT_DIR,
    RENDER_PRESETS,
    DEFAULT_PRESET_NAME,
    SEGMENT_DURATION_MAX,
    SEGMENT_DURATION_MIN,
    RenderPreset,
    WatermarkConfig,
    ZoomConfig,
)
from backend.ffmpeg_engine import (
    LogCallback,
    VideoInfo,
    probe_video,
    render_segment,
)


# ---------------------------------------------------------------------------
# Tipe data progres
# ---------------------------------------------------------------------------

@dataclass
class SegmentProgress:
    """
    Snapshot progres yang dikirim ke UI setiap tick.

    Semua field bersifat opsional (None = belum tersedia) agar
    UI tidak crash jika data belum siap di awal segmen.
    """
    seg_num:     int            # Segmen ke-N yang sedang diproses (1-based)
    total_segs:  int            # Total jumlah segmen dalam job ini
    seg_pct:     float          # Kemajuan segmen saat ini (0.0–100.0)
    overall_pct: float          # Kemajuan keseluruhan job (0.0–100.0)
    fps:         float          # Frame per detik encode saat ini
    speed:       float          # Kecepatan encode relatif (1.0 = realtime)
    eta_sec:     float          # Perkiraan sisa waktu total job (detik)
    current_output: Path        # Path file output segmen yang sedang dikerjakan


# ---------------------------------------------------------------------------
# Tipe callback ke GUI
# ---------------------------------------------------------------------------

ProgressCallback = Callable[[SegmentProgress], None]
# LogCallback sudah diimport dari ffmpeg_engine


# ---------------------------------------------------------------------------
# Dataclass: spec satu segmen
# ---------------------------------------------------------------------------

@dataclass
class SegmentSpec:
    """Spesifikasi pemotongan satu segmen, dihitung saat prepare_job."""
    index:        int     # Indeks 0-based
    start_sec:    float   # Waktu mulai dalam video sumber (detik)
    duration_sec: float   # Durasi segmen ini (detik)
    zoom_crop_pct: float  # Persentase crop anti-copyright untuk segmen ini
    output_path:  Path    # Path file output yang akan dibuat


# ---------------------------------------------------------------------------
# Dataclass: spesifikasi lengkap satu job
# ---------------------------------------------------------------------------

@dataclass
class JobSpec:
    """
    Representasi lengkap satu pekerjaan render.
    Tidak menyentuh disk — murni di RAM.
    """
    job_id:       str              # ID unik (timestamp + nama file)
    input_path:   Path             # Video sumber
    video_info:   VideoInfo        # Metadata video (dari probe)
    segments:     List[SegmentSpec] = field(default_factory=list)
    preset:       RenderPreset     = field(default_factory=lambda: RENDER_PRESETS[DEFAULT_PRESET_NAME])
    watermark_cfg: WatermarkConfig = field(default_factory=lambda: DEFAULT_WATERMARK_CONFIG)
    zoom_config:  ZoomConfig       = field(default_factory=lambda: DEFAULT_ZOOM_CONFIG)
    output_dir:   Path             = field(default_factory=lambda: OUTPUT_DIR)
    # Metadata runtime (diisi saat run_job)
    start_time:   Optional[float]  = None   # time.monotonic() saat job dimulai
    end_time:     Optional[float]  = None   # time.monotonic() saat job selesai/gagal
    error:        Optional[str]    = None   # Pesan error jika gagal

    @property
    def total_segments(self) -> int:
        return len(self.segments)

    @property
    def total_input_duration(self) -> float:
        """Total durasi semua segmen (bisa < durasi video asli)."""
        return sum(s.duration_sec for s in self.segments)

    @property
    def elapsed_sec(self) -> float:
        """Waktu berjalan job dalam detik (0 jika belum mulai)."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time is not None else time.monotonic()
        return max(0.0, end - self.start_time)


# ---------------------------------------------------------------------------
# prepare_job
# ---------------------------------------------------------------------------

def prepare_job(
    input_path:    Path,
    preset_name:   str              = DEFAULT_PRESET_NAME,
    watermark_cfg: WatermarkConfig  = DEFAULT_WATERMARK_CONFIG,
    zoom_config:   ZoomConfig       = DEFAULT_ZOOM_CONFIG,
    output_dir:    Optional[Path]   = None,
    seed:          Optional[int]    = None,
) -> JobSpec:
    """
    Hitung rencana pemotongan video menjadi segmen-segmen acak.

    Proses:
    1. Probe video untuk mendapatkan durasi dan resolusi.
    2. Bagi durasi video menjadi segmen dengan panjang acak
       antara SEGMENT_DURATION_MIN dan SEGMENT_DURATION_MAX.
    3. Tiap segmen mendapat nilai zoom_crop_pct acak dalam range
       zoom_config.zoom_min_pct hingga zoom_config.zoom_max_pct.
    4. Kembalikan JobSpec lengkap yang siap di-pass ke run_job.

    Tidak ada file yang dibuat atau database yang disentuh.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {input_path}")

    rng = random.Random(seed)   # deterministik jika seed diberikan

    # --- Probe video ---
    video_info = probe_video(input_path)

    # --- Buat job ID ---
    import time as _time
    ts = int(_time.time())
    job_id = f"{ts}_{input_path.stem[:32]}"

    # --- Tentukan direktori output ---
    out_dir = output_dir or OUTPUT_DIR
    job_out_dir = out_dir / job_id
    # Direktori belum dibuat di sini; dibuat saat render_segment dipanggil

    # --- Resolusi preset ---
    preset = RENDER_PRESETS.get(preset_name, RENDER_PRESETS[DEFAULT_PRESET_NAME])

    # --- Hitung segmen ---
    segments: list[SegmentSpec] = []
    total_duration = video_info.duration
    cursor = 0.0
    seg_index = 0

    while cursor < total_duration:
        remaining = total_duration - cursor

        # Jika sisa durasi lebih pendek dari minimum, sisipkan ke segmen terakhir
        # atau buat segmen pendek terakhir (jika minimal 10 detik)
        if remaining < SEGMENT_DURATION_MIN:
            if segments:
                # Perpanjang segmen terakhir agar menelan sisa
                last = segments[-1]
                segments[-1] = SegmentSpec(
                    index=last.index,
                    start_sec=last.start_sec,
                    duration_sec=last.duration_sec + remaining,
                    zoom_crop_pct=last.zoom_crop_pct,
                    output_path=last.output_path,
                )
            # Jika sisa < 10 detik dan belum ada segmen, skip (video terlalu pendek)
            elif remaining >= 10.0:
                zoom_pct = rng.uniform(zoom_config.zoom_min_pct, zoom_config.zoom_max_pct)
                out_file = job_out_dir / f"segment_{seg_index:04d}.mp4"
                segments.append(SegmentSpec(
                    index=seg_index,
                    start_sec=cursor,
                    duration_sec=remaining,
                    zoom_crop_pct=round(zoom_pct, 2),
                    output_path=out_file,
                ))
            break

        # Durasi segmen acak
        seg_dur = rng.uniform(
            float(SEGMENT_DURATION_MIN),
            float(SEGMENT_DURATION_MAX),
        )
        # Jangan melebihi sisa
        seg_dur = min(seg_dur, remaining)

        zoom_pct = rng.uniform(zoom_config.zoom_min_pct, zoom_config.zoom_max_pct)
        out_file = job_out_dir / f"segment_{seg_index:04d}.mp4"

        segments.append(SegmentSpec(
            index=seg_index,
            start_sec=round(cursor, 3),
            duration_sec=round(seg_dur, 3),
            zoom_crop_pct=round(zoom_pct, 2),
            output_path=out_file,
        ))

        cursor += seg_dur
        seg_index += 1

    if not segments:
        raise ValueError(
            f"Video terlalu pendek ({total_duration:.1f}s) untuk dibagi "
            f"menjadi segmen minimal {SEGMENT_DURATION_MIN}s."
        )

    return JobSpec(
        job_id=job_id,
        input_path=input_path,
        video_info=video_info,
        segments=segments,
        preset=preset,
        watermark_cfg=watermark_cfg,
        zoom_config=zoom_config,
        output_dir=job_out_dir,
    )


# ---------------------------------------------------------------------------
# run_job
# ---------------------------------------------------------------------------

def run_job(
    job:               JobSpec,
    log_callback:      Optional[LogCallback]      = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_event:      Optional[threading.Event]  = None,
) -> None:
    """
    Eksekusi semua segmen dalam JobSpec secara sekuensial.

    Menghitung progres live:
      - seg_pct      : kemajuan segmen yang sedang berjalan (0–100)
      - overall_pct  : kemajuan keseluruhan job berdasarkan durasi (0–100)
      - fps / speed  : diambil dari laporan FFmpeg terbaru
      - eta_sec      : estimasi sisa waktu berdasarkan kecepatan encode

    Semua data progres dikirim ke 'progress_callback' sebagai SegmentProgress.
    Semua log dikirim ke 'log_callback' sebagai string.

    Raise
    -----
    RuntimeError  : Jika segmen gagal dirender.
    """

    def _log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    total_segs       = job.total_segments
    total_job_dur    = job.total_input_duration  # detik total semua segmen
    completed_dur    = 0.0                        # durasi segmen yang sudah selesai

    # State live yang di-update oleh closure bawah
    _state: dict = {
        "seg_pct":    0.0,
        "fps":        0.0,
        "speed":      1.0,
        "last_tick":  time.monotonic(),
    }

    job.start_time = time.monotonic()

    _log(f"[job] Memulai job '{job.job_id}': {total_segs} segmen, "
         f"total ~{total_job_dur:.0f}s dari '{job.input_path.name}'")

    for seg in job.segments:
        seg_num = seg.index + 1  # 1-based untuk UI

        if cancel_event is not None and cancel_event.is_set():
            _log("[job] Cancel sebelum segmen dimulai.")
            raise RuntimeError("Job dibatalkan oleh pengguna.")

        _log(f"[job] Segmen {seg_num}/{total_segs} | "
             f"start={seg.start_sec:.1f}s dur={seg.duration_sec:.1f}s "
             f"zoom={seg.zoom_crop_pct:.1f}%")

        # Reset state per segmen
        _state["seg_pct"]   = 0.0
        _state["fps"]       = 0.0
        _state["speed"]     = 1.0
        _state["last_tick"] = time.monotonic()

        seg_start_monotonic = time.monotonic()

        def _on_seg_progress(seg_pct: float) -> None:
            """
            Callback internal yang dipanggil ffmpeg_engine saat ada progres
            pada segmen yang sedang berjalan.
            """
            now = time.monotonic()
            _state["seg_pct"] = seg_pct

            # Hitung elapsed sejak segmen ini mulai
            seg_elapsed = max(0.001, now - seg_start_monotonic)

            # Estimasi fps dari rasio frame/waktu
            # FFmpeg kadang memberi 0 fps di awal; jaga agar tidak NaN
            estimated_fps = (seg_pct / 100.0 * seg.duration_sec * job.video_info.fps) / seg_elapsed
            if estimated_fps > 0:
                _state["fps"] = round(estimated_fps, 1)

            # Speed: perbandingan encoded time vs wallclock time
            encoded_sec = (seg_pct / 100.0) * seg.duration_sec
            speed = encoded_sec / seg_elapsed if seg_elapsed > 0 else 1.0
            _state["speed"] = round(max(0.01, speed), 2)

            # Overall pct: durasi selesai + porsi segmen ini
            seg_done_dur = (seg_pct / 100.0) * seg.duration_sec
            overall_done = completed_dur + seg_done_dur
            overall_pct  = min(100.0, (overall_done / total_job_dur) * 100.0) if total_job_dur > 0 else 0.0

            # ETA: sisa waktu keseluruhan
            remaining_job_dur = total_job_dur - overall_done
            effective_speed   = max(0.01, _state["speed"])
            eta_sec = remaining_job_dur / effective_speed

            if progress_callback:
                progress_callback(SegmentProgress(
                    seg_num=seg_num,
                    total_segs=total_segs,
                    seg_pct=round(seg_pct, 2),
                    overall_pct=round(overall_pct, 2),
                    fps=_state["fps"],
                    speed=_state["speed"],
                    eta_sec=round(max(0.0, eta_sec), 1),
                    current_output=seg.output_path,
                ))

        # --- Jalankan satu segmen ---
        try:
            render_segment(
                input_path=job.input_path,
                output_path=seg.output_path,
                start_sec=seg.start_sec,
                duration_sec=seg.duration_sec,
                zoom_crop_pct=seg.zoom_crop_pct,
                preset=job.preset,
                watermark_cfg=job.watermark_cfg,
                log_callback=log_callback,
                progress_callback=_on_seg_progress,
                cancel_event=cancel_event,
            )
        except RuntimeError as exc:
            job.error = str(exc)
            job.end_time = time.monotonic()
            _log(f"[job] ERROR pada segmen {seg_num}: {exc}")
            raise

        # Segmen selesai; akumulasikan durasi
        completed_dur += seg.duration_sec

        # Kirim snapshot 100% segmen ini
        if progress_callback:
            overall_pct = min(100.0, (completed_dur / total_job_dur) * 100.0) if total_job_dur > 0 else 100.0
            progress_callback(SegmentProgress(
                seg_num=seg_num,
                total_segs=total_segs,
                seg_pct=100.0,
                overall_pct=round(overall_pct, 2),
                fps=_state["fps"],
                speed=_state["speed"],
                eta_sec=0.0,
                current_output=seg.output_path,
            ))

        _log(f"[job] Segmen {seg_num}/{total_segs} selesai → {seg.output_path.name}")

    job.end_time = time.monotonic()
    elapsed = job.elapsed_sec

    _log(f"[job] Job '{job.job_id}' SELESAI dalam {elapsed:.1f}s. "
         f"Output: {job.output_dir}")

    # Kirim progres final 100%
    if progress_callback:
        progress_callback(SegmentProgress(
            seg_num=total_segs,
            total_segs=total_segs,
            seg_pct=100.0,
            overall_pct=100.0,
            fps=_state["fps"],
            speed=_state["speed"],
            eta_sec=0.0,
            current_output=job.segments[-1].output_path if job.segments else Path("."),
        ))
