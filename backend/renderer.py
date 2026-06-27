"""
backend/renderer.py
─────────────────────────────────────────────────────────────────────────────
Voidclip.mov — Renderer: primary facade between the frontend and all backend
               systems.

The frontend (MainWindow, RenderPanel) interacts exclusively with this class.
It never imports ffmpeg_engine, video_processor, or queue_manager directly.

Public interface (matched to MainWindow._wire_signals and button slots)
────────────────────────────────────────────────────────────────────────
    renderer.initialise()                   — reset to clean state
    renderer.get_state() → QueueState       — current state snapshot
    renderer.add_sources(paths)             — enqueue one or more source files
    renderer.start()                        — begin processing the queue
    renderer.pause()                        — pause after current segment
    renderer.resume()                       — resume from pause
    renderer.stop()                         — abort processing
    renderer.set_preset(name)               — change render preset
    renderer.set_subtitle_mode(mode)        — change subtitle handling
    renderer.set_on_log(cb)                 — register log callback
    renderer.set_on_progress(cb)            — register progress callback
    renderer.set_on_state_changed(cb)       — register state callback

Thread safety
─────────────
All public methods are safe to call from the Qt main thread.
Callbacks are invoked from the background worker thread — the MainWindow
uses Qt Signals (sig_log, sig_progress, sig_state) as the cross-thread
bridge, which is why the callbacks simply emit() those signals.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, List, Optional

from backend.config import DEFAULT_PRESET, DEFAULT_SUBTITLE_MODE
from backend.logger import get_logger
from backend.queue_manager import QueueManager, QueueState
from backend.video_processor import ProcessorPool

log = get_logger(__name__)

# Callback type aliases
LogCb      = Callable[[str], None]
ProgressCb = Callable[[int, int, float, float, float, float, float], None]
StatusCb   = Callable[[QueueState], None]


class Renderer:
    """
    Top-level application facade.

    Owns:
      - one QueueManager  (in-memory job list)
      - one ProcessorPool (background worker thread)

    Does NOT own any Qt objects — stays framework-agnostic.
    """

    def __init__(self) -> None:
        self._qm:   QueueManager   = QueueManager()
        self._pool: ProcessorPool  = ProcessorPool(self._qm)

        # Registered callbacks
        self._on_log:      Optional[LogCb]      = None
        self._on_progress: Optional[ProgressCb] = None
        self._on_state:    Optional[StatusCb]   = None

        # Active settings
        self._preset_name:   str = DEFAULT_PRESET
        self._subtitle_mode: str = DEFAULT_SUBTITLE_MODE.value

        # Wire pool callbacks
        self._pool._log_cb      = self._dispatch_log
        self._pool._progress_cb = self._dispatch_progress
        self._pool._status_cb   = self._dispatch_state

        log.debug("Renderer created")

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """
        Reset to a clean idle state.

        Called at startup and by the Refresh button.
        Clears all jobs from the queue; does NOT touch the filesystem.
        """
        # Stop any running pool gracefully (instant for idle, no-op if idle)
        if self._pool.is_alive():
            self._pool.stop()
            # Give the thread a moment to exit; don't block the UI
            threading.Thread(
                target=self._wait_for_pool, daemon=True
            ).start()

        self._qm.hard_reset()
        self._pool = ProcessorPool(self._qm)
        self._pool._log_cb      = self._dispatch_log
        self._pool._progress_cb = self._dispatch_progress
        self._pool._status_cb   = self._dispatch_state
        self._pool.set_preset(self._preset_name)
        self._pool.set_subtitle_mode(self._subtitle_mode)

        self._dispatch_state(QueueState.IDLE)
        log.info("Renderer initialised — queue cleared")

    def _wait_for_pool(self) -> None:
        """Background helper: wait for the old pool thread to die."""
        if self._pool._thread:
            self._pool._thread.join(timeout=5.0)

    # ── Queue management ────────────────────────────────────────────────────

    def add_sources(self, paths: List[Path]) -> None:
        """
        Enqueue one or more video source files.

        Duplicate paths (already in queue as PENDING) are silently ignored.
        """
        existing = {
            j.source_path
            for j in self._qm.all_jobs()
        }
        added = 0
        for p in paths:
            p = Path(p)
            if not p.exists():
                self._dispatch_log(f"⚠  Skipping missing file: {p.name}")
                log.warning("add_sources: path does not exist: %s", p)
                continue
            if p in existing:
                self._dispatch_log(f"   Already queued: {p.name}")
                continue
            self._qm.enqueue(p)
            self._dispatch_log(f"   Queued: {p.name}")
            existing.add(p)
            added += 1

        log.info("add_sources: %d file(s) enqueued", added)

    # ── Processing control ──────────────────────────────────────────────────

    def start(self) -> None:
        """
        Begin processing all queued jobs.

        If the pool is already running (e.g. called twice), the second call
        is a no-op — the pool handles this gracefully.
        """
        if self._pool.is_alive():
            log.debug("Renderer.start() called but pool is already running")
            return

        pending = self._qm.pending_count()
        if pending == 0:
            self._dispatch_log("⚠  No files queued — import some videos first")
            log.warning("start() called with empty queue")
            return

        log.info("Renderer.start() — %d job(s) pending", pending)
        self._pool.start()

    def pause(self) -> None:
        """
        Request pause after the currently running segment finishes.

        The UI state will update to PAUSED automatically once the segment
        completes (emitted from the VideoProcessor loop).
        """
        if not self._pool.is_alive():
            log.debug("pause() ignored — pool not running")
            return
        log.info("Renderer.pause()")
        self._pool.pause()
        self._dispatch_log("⏸  Pause requested — finishing current segment…")

    def resume(self) -> None:
        """Release pause hold and continue to the next segment."""
        if not self._pool.is_alive():
            log.debug("resume() ignored — pool not running")
            return
        log.info("Renderer.resume()")
        self._pool.resume()
        self._dispatch_log("▶  Resuming…")

    def stop(self) -> None:
        """
        Abort all processing.  The running FFmpeg process is terminated and
        partial output is discarded.  The queue is reset to IDLE.
        """
        if not self._pool.is_alive():
            # Already idle — just make sure state is correct
            self._qm.reset()
            self._dispatch_state(QueueState.IDLE)
            return
        log.info("Renderer.stop()")
        self._dispatch_log("⏹  Stop requested…")
        self._pool.stop()

    # ── Settings ────────────────────────────────────────────────────────────

    def set_preset(self, name: str) -> None:
        self._preset_name = name
        self._pool.set_preset(name)
        log.info("Preset changed to '%s'", name)

    def set_subtitle_mode(self, mode: str) -> None:
        self._subtitle_mode = mode
        self._pool.set_subtitle_mode(mode)
        log.info("Subtitle mode changed to '%s'", mode)

    # ── Callback registration ───────────────────────────────────────────────

    def set_on_log(self, cb: LogCb) -> None:
        """
        Register a callback for log messages.
        cb(msg: str)
        """
        self._on_log = cb

    def set_on_progress(self, cb: ProgressCb) -> None:
        """
        Register a callback for progress updates.
        cb(seg_num, total, seg_pct, overall_pct, fps, speed, eta)
        """
        self._on_progress = cb

    def set_on_state_changed(self, cb: StatusCb) -> None:
        """
        Register a callback for queue-state changes.
        cb(state: QueueState)
        """
        self._on_state = cb

    # ── State introspection ─────────────────────────────────────────────────

    def get_state(self) -> QueueState:
        return self._qm.state

    def get_queue_snapshot(self):
        """Return a QueueSnapshot for advanced UI inspection."""
        return self._qm.snapshot()

    # ── Internal dispatchers ────────────────────────────────────────────────
    # These are the actual functions wired into ProcessorPool.
    # They forward to whatever the frontend registered via set_on_*().

    def _dispatch_log(self, msg: str) -> None:
        if self._on_log:
            try:
                self._on_log(msg)
            except Exception as exc:
                log.warning("log_cb raised: %s", exc)

    def _dispatch_progress(
        self,
        seg_num:     int,
        total:       int,
        seg_pct:     float,
        overall_pct: float,
        fps:         float,
        speed:       float,
        eta:         float,
    ) -> None:
        if self._on_progress:
            try:
                self._on_progress(seg_num, total, seg_pct, overall_pct, fps, speed, eta)
            except Exception as exc:
                log.warning("progress_cb raised: %s", exc)

    def _dispatch_state(self, state: QueueState) -> None:
        if self._on_state:
            try:
                self._on_state(state)
            except Exception as exc:
                log.warning("state_cb raised: %s", exc)
