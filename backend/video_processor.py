from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional

from backend.config import OUTPUT_DIR, RENDER_PRESETS, DEFAULT_PRESET, TEMP_DIR
from backend.ffmpeg_engine import (
    VideoInfo,
    SegmentPlan,
    encode_segment,
    plan_segments,
    probe_video,
    stream_copy_cut,
)
from backend.logger import get_logger
from backend.queue_manager import JobRecord, QueueManager, QueueState

log = get_logger(__name__)

LogCb      = Callable[[str], None]
ProgressCb = Callable[[int, int, float, float, float, float, float], None]
StatusCb   = Callable[[QueueState], None]


class VideoProcessor:
    def __init__(
        self,
        job:           JobRecord,
        queue_manager: QueueManager,
        preset_name:   str       = DEFAULT_PRESET,
        subtitle_mode: str       = "keep",
        log_cb:        Optional[LogCb]      = None,
        progress_cb:   Optional[ProgressCb] = None,
        status_cb:     Optional[StatusCb]   = None,
    ) -> None:
        self.job           = job
        self.qm            = queue_manager
        self.preset_name   = preset_name
        self.subtitle_mode = subtitle_mode
        self._log_cb       = log_cb
        self._progress_cb  = progress_cb
        self._status_cb    = status_cb

        self._pause_event: threading.Event = threading.Event()
        self._pause_event.set()

        self._stop_flag:  threading.Event = threading.Event()

        self._live_fps:   float = 0.0
        self._live_speed: float = 0.0
        self._start_time: float = 0.0

    def pause(self) -> None:
        log.info("Pause requested for job '%s'", self.job.filename)
        self._pause_event.clear()

    def resume(self) -> None:
        log.info("Resume requested for job '%s'", self.job.filename)
        self._pause_event.set()
        self.qm.transition_running()
        self._emit_status(QueueState.RUNNING)

    def stop(self) -> None:
        log.info("Stop requested for job '%s'", self.job.filename)
        self._stop_flag.set()
        self._pause_event.set()

    def is_stop_requested(self) -> bool:
        return self._stop_flag.is_set()

    def run(self) -> None:
        self._start_time = time.monotonic()
        source = self.job.source_path
        self._log(f"▶  Starting: {source.name}")

        try:
            info = probe_video(source)
        except Exception as exc:
            self._fail(f"Probe failed: {exc}")
            return

        self._log(
            f"   Duration: {info.duration:.1f}s  |  "
            f"{info.width}×{info.height}  |  {info.fps:.2f} fps"
        )

        segments: List[SegmentPlan] = plan_segments(info)
        if not segments:
            self._fail("No processable segments found (video too short?).")
            return

        self.qm.set_segments(self.job, len(segments))
        self._log(f"   Planned {len(segments)} segment(s)")

        preset_cfg = RENDER_PRESETS.get(
            self.preset_name,
            list(RENDER_PRESETS.values())[0],
        )
        container = preset_cfg.get("container", "mp4")

        out_dir = OUTPUT_DIR / source.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        for seg in segments:
            if self._stop_flag.is_set():
                self._log("⏹  Stopped before segment %d" % seg.index)
                break

            if not self._pause_event.is_set():
                self._log("⏸  Holding — waiting for resume…")
                self.qm.transition_paused()
                self._emit_status(QueueState.PAUSED)
                self._pause_event.wait()
                if self._stop_flag.is_set():
                    self._log("⏹  Stopped during pause hold")
                    break
                self._log("▶  Resuming from segment %d" % seg.index)

            seg_label = f"[{seg.index + 1}/{len(segments)}]"
            self._log(
                f"   {seg_label} Cutting  {seg.start:.1f}s + {seg.duration:.1f}s  "
                f"(zoom {seg.zoom*100:.1f}%)"
            )

            try:
                tmp_cut = stream_copy_cut(source, seg, TEMP_DIR)
            except Exception as exc:
                self._log(f"   {seg_label} ✘ Cut failed: {exc}")
                log.warning("Stream-copy cut error for seg %d: %s", seg.index, exc)
                continue

            clean_base = re.sub(r'S(\d+)\s+E(\d+)', r'S\1E\2', source.stem)
            actual_part = self.job.segments_done + 1
            out_filename = f"{clean_base} Part {actual_part:03d}.{container}"
            output_path  = out_dir / out_filename

            self._log(f"   {seg_label} Encoding → {out_filename}")
            seg_start_time = time.monotonic()

            def _progress_inner(
                seg_pct: float,
                fps:     float,
                speed:   float,
                _seg=seg,
                _segs=segments,
                _seg_start=seg_start_time,
            ) -> None:
                self._live_fps   = fps
                self._live_speed = speed
                done_segs    = self.job.segments_done
                overall_pct  = (
                    (done_segs + seg_pct / 100.0) / max(len(_segs), 1)
                ) * 100.0
                frames_left = max(0.0, 100.0 - seg_pct) / 100.0 * info.fps * _seg.duration
                eta         = (frames_left / fps) if fps > 0 else 0.0
                self._emit_progress(
                    seg_num=_seg.index + 1,
                    total=len(_segs),
                    seg_pct=seg_pct,
                    overall_pct=overall_pct,
                    fps=fps,
                    speed=speed,
                    eta=eta,
                )

            try:
                encode_segment(
                    tmp_source    = tmp_cut,
                    output_path   = output_path,
                    info          = info,
                    seg           = seg,
                    preset_cfg    = preset_cfg,
                    subtitle_mode = self.subtitle_mode,
                    progress_cb   = _progress_inner,
                    stop_flag     = self.is_stop_requested,
                )
            except Exception as exc:
                self._log(f"   {seg_label} ✘ Encode error: {exc}")
                log.error("Encode error seg %d: %s", seg.index, exc, exc_info=True)
                continue
            finally:
                try:
                    tmp_cut.unlink(missing_ok=True)
                except OSError:
                    pass

            if self._stop_flag.is_set():
                self._log(f"   {seg_label} Encode aborted by stop")
                break

            self.qm.increment_segment(self.job)
            elapsed_seg = time.monotonic() - seg_start_time
            self._log(
                f"   {seg_label} ✔  Done  ({elapsed_seg:.1f}s)  → {output_path.name}"
            )

        if self._stop_flag.is_set():
            self.qm.mark_cancelled(self.job)
            self._log(f"⏹  Job cancelled: {source.name}")
        else:
            self.qm.mark_done(self.job)
            total_elapsed = time.monotonic() - self._start_time
            self._log(
                f"✔  Finished: {source.name}  "
                f"({self.job.segments_done}/{len(segments)} segments, "
                f"{total_elapsed:.1f}s total)"
            )

    def _log(self, msg: str) -> None:
        log.info(msg)
        if self._log_cb:
            try:
                self._log_cb(msg)
            except Exception:
                pass

    def _emit_progress(
        self,
        seg_num:     int,
        total:       int,
        seg_pct:     float,
        overall_pct: float,
        fps:         float,
        speed:       float,
        eta:         float,
    ) -> None:
        if self._progress_cb:
            try:
                self._progress_cb(seg_num, total, seg_pct, overall_pct, fps, speed, eta)
            except Exception:
                pass

    def _emit_status(self, state: QueueState) -> None:
        if self._status_cb:
            try:
                self._status_cb(state)
            except Exception:
                pass

    def _fail(self, reason: str) -> None:
        self._log(f"✘  Error: {reason}")
        self.qm.mark_failed(self.job, reason)
        log.error("Job '%s' failed: %s", self.job.filename, reason)


class ProcessorPool:
    def __init__(
        self,
        queue_manager: QueueManager,
        log_cb:        Optional[LogCb]      = None,
        progress_cb:   Optional[ProgressCb] = None,
        status_cb:     Optional[StatusCb]   = None,
    ) -> None:
        self.qm          = queue_manager
        self._log_cb     = log_cb
        self._progress_cb = progress_cb
        self._status_cb  = status_cb

        self._preset_name:   str = DEFAULT_PRESET
        self._subtitle_mode: str = "keep"

        self._thread:    Optional[threading.Thread]    = None
        self._active:    Optional[VideoProcessor]      = None
        self._lock:      threading.Lock                = threading.Lock()

    def set_preset(self, name: str) -> None:
        self._preset_name = name

    def set_subtitle_mode(self, mode: str) -> None:
        self._subtitle_mode = mode

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._worker,
                name="voidclip-worker",
                daemon=True,
            )
            self._thread.start()
            log.info("Worker thread started")

    def pause(self) -> None:
        with self._lock:
            p = self._active
        if p:
            p.pause()

    def resume(self) -> None:
        with self._lock:
            p = self._active
        if p:
            p.resume()

    def stop(self) -> None:
        with self._lock:
            p = self._active
        if p:
            p.stop()

    def is_alive(self) -> bool:
        with self._lock:
            return bool(self._thread and self._thread.is_alive())

    def _worker(self) -> None:
        log.info("Worker: entered job loop")
        self._emit_status(QueueState.RUNNING)

        while True:
            job = self.qm.next_pending()
            if job is None:
                log.info("Worker: no more pending jobs — exiting")
                break

            processor = VideoProcessor(
                job           = job,
                queue_manager = self.qm,
                preset_name   = self._preset_name,
                subtitle_mode = self._subtitle_mode,
                log_cb        = self._log_cb,
                progress_cb   = self._progress_cb,
                status_cb     = self._status_cb,
            )
            with self._lock:
                self._active = processor

            self.qm.mark_running(job)
            self._emit_status(QueueState.RUNNING)

            try:
                processor.run()
            except Exception as exc:
                log.error("Unexpected error in processor.run(): %s", exc, exc_info=True)

            with self._lock:
                self._active = None

            if processor.is_stop_requested():
                log.info("Worker: stop flag set — draining remaining jobs as cancelled")
                remaining = self.qm.next_pending()
                while remaining is not None:
                    self.qm.mark_cancelled(remaining)
                    remaining = self.qm.next_pending()
                break

        self.qm.transition_idle()
        self._emit_status(QueueState.IDLE)
        log.info("Worker: exited cleanly")

    def _emit_status(self, state: QueueState) -> None:
        if self._status_cb:
            try:
                self._status_cb(state)
            except Exception:
                pass