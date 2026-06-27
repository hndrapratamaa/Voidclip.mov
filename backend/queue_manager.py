"""
backend/queue_manager.py
─────────────────────────────────────────────────────────────────────────────
Voidclip.mov — In-memory job queue (zero SQLite)

Design principles
─────────────────
* Pure RAM — no persistence layer whatsoever.
* `QueueState` is the single source of truth for the UI state machine.
* `JobRecord` is a frozen-ish dataclass snapshot that the Renderer and
  VideoProcessor read; the QueueManager owns all mutation.
* Thread-safe via a single `threading.Lock`.  All public methods acquire
  the lock internally, so callers never need to manage it.

State machine
─────────────
    IDLE ──► QUEUEING ──► RUNNING ──► IDLE
               │                │
               │           PAUSED ──► RUNNING
               │                │
               └────────────────┴──► IDLE  (on stop)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import enum
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ── State enum ─────────────────────────────────────────────────────────────

class QueueState(str, enum.Enum):
    IDLE      = "idle"
    QUEUEING  = "queueing"
    RUNNING   = "running"
    PAUSED    = "paused"


# ── Job status ─────────────────────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


# ── Job record (immutable snapshot) ────────────────────────────────────────

@dataclass
class JobRecord:
    """
    Represents one source video file to be processed.

    This object is created once per source file and updated in-place by the
    QueueManager.  External code should treat it as a read-only snapshot
    obtained via `QueueManager.snapshot()`.
    """
    job_id:       str       = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_path:  Path      = field(default=Path("."))
    status:       JobStatus = JobStatus.PENDING
    segments_total:   int   = 0
    segments_done:    int   = 0
    error_message:    str   = ""
    created_at:       float = field(default_factory=time.time)
    started_at:       Optional[float] = None
    finished_at:      Optional[float] = None

    # Convenience ──────────────────────────────────────────────────────────
    @property
    def filename(self) -> str:
        return self.source_path.name

    @property
    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.finished_at or time.time()
        return end - self.started_at

    def as_dict(self) -> dict:
        return {
            "job_id":         self.job_id,
            "source":         str(self.source_path),
            "status":         self.status.value,
            "segments_total": self.segments_total,
            "segments_done":  self.segments_done,
            "error":          self.error_message,
            "created_at":     self.created_at,
            "started_at":     self.started_at,
            "finished_at":    self.finished_at,
        }


# ── Queue snapshot (read-only view emitted to the UI) ──────────────────────

@dataclass
class QueueSnapshot:
    state:      QueueState
    jobs:       List[JobRecord]
    total_jobs: int
    done_jobs:  int
    failed_jobs: int

    @property
    def pending_jobs(self) -> int:
        return self.total_jobs - self.done_jobs - self.failed_jobs


# ── QueueManager ───────────────────────────────────────────────────────────

class QueueManager:
    """
    Thread-safe, stateless (RAM-only) job queue.

    The ``state`` property is the primary signal the frontend polls / receives
    via callback.  All mutation goes through this class; nothing writes job
    records directly.
    """

    def __init__(self) -> None:
        self._lock:  threading.Lock = threading.Lock()
        self._jobs:  List[JobRecord] = []
        self._state: QueueState = QueueState.IDLE

    # ── State ──────────────────────────────────────────────────────────────

    @property
    def state(self) -> QueueState:
        with self._lock:
            return self._state

    def _set_state(self, new_state: QueueState) -> None:
        """Internal — must be called with lock held."""
        self._state = new_state

    # ── Queue manipulation ─────────────────────────────────────────────────

    def enqueue(self, source_path: Path) -> JobRecord:
        """Add a new job and transition to QUEUEING if currently IDLE."""
        record = JobRecord(source_path=source_path)
        with self._lock:
            self._jobs.append(record)
            if self._state == QueueState.IDLE:
                self._set_state(QueueState.QUEUEING)
        return record

    def enqueue_many(self, paths: List[Path]) -> List[JobRecord]:
        records = []
        with self._lock:
            for p in paths:
                r = JobRecord(source_path=p)
                self._jobs.append(r)
                records.append(r)
            if self._state == QueueState.IDLE and records:
                self._set_state(QueueState.QUEUEING)
        return records

    def next_pending(self) -> Optional[JobRecord]:
        """Return the first PENDING job without removing it, or None."""
        with self._lock:
            for job in self._jobs:
                if job.status == JobStatus.PENDING:
                    return job
            return None

    def mark_running(self, job: JobRecord) -> None:
        with self._lock:
            job.status     = JobStatus.PROCESSING
            job.started_at = time.time()
            self._set_state(QueueState.RUNNING)

    def mark_done(self, job: JobRecord) -> None:
        with self._lock:
            job.status      = JobStatus.DONE
            job.finished_at = time.time()

    def mark_failed(self, job: JobRecord, error: str) -> None:
        with self._lock:
            job.status        = JobStatus.FAILED
            job.error_message = error
            job.finished_at   = time.time()

    def mark_cancelled(self, job: JobRecord) -> None:
        with self._lock:
            job.status      = JobStatus.CANCELLED
            job.finished_at = time.time()

    def set_segments(self, job: JobRecord, total: int) -> None:
        with self._lock:
            job.segments_total = total

    def increment_segment(self, job: JobRecord) -> None:
        with self._lock:
            job.segments_done += 1

    # ── Global state transitions ───────────────────────────────────────────

    def transition_running(self) -> None:
        with self._lock:
            self._set_state(QueueState.RUNNING)

    def transition_paused(self) -> None:
        with self._lock:
            self._set_state(QueueState.PAUSED)

    def transition_idle(self) -> None:
        with self._lock:
            self._set_state(QueueState.IDLE)

    def reset(self) -> None:
        """
        Cancel any pending / processing jobs and return to IDLE.
        Called by Renderer.stop() and Renderer.initialise().
        """
        with self._lock:
            for job in self._jobs:
                if job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
                    job.status      = JobStatus.CANCELLED
                    job.finished_at = time.time()
            self._set_state(QueueState.IDLE)

    def hard_reset(self) -> None:
        """Wipe all jobs and return to IDLE — used by initialise()."""
        with self._lock:
            self._jobs.clear()
            self._set_state(QueueState.IDLE)

    # ── Introspection ──────────────────────────────────────────────────────

    def snapshot(self) -> QueueSnapshot:
        with self._lock:
            jobs_copy   = list(self._jobs)
            state_copy  = self._state
        done   = sum(1 for j in jobs_copy if j.status == JobStatus.DONE)
        failed = sum(1 for j in jobs_copy if j.status == JobStatus.FAILED)
        return QueueSnapshot(
            state=state_copy,
            jobs=jobs_copy,
            total_jobs=len(jobs_copy),
            done_jobs=done,
            failed_jobs=failed,
        )

    def all_jobs(self) -> List[JobRecord]:
        with self._lock:
            return list(self._jobs)

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs if j.status == JobStatus.PENDING)

    def is_idle(self) -> bool:
        return self.state == QueueState.IDLE

    def is_running(self) -> bool:
        return self.state == QueueState.RUNNING

    def is_paused(self) -> bool:
        return self.state == QueueState.PAUSED
