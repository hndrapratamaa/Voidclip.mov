"""
backend/config.py
─────────────────────────────────────────────────────────────────────────────
Voidclip.mov — Central configuration & constants

All tunable values live here. Frontend modules import APP_NAME, APP_VERSION,
INPUT_DIR, OUTPUT_DIR, RENDER_PRESETS, SubtitleMode, and
SUPPORTED_VIDEO_EXTENSIONS directly from this file.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import enum
from pathlib import Path

# ── Application identity ──────────────────────────────────────────────────
APP_NAME    = "Voidclip.mov"
APP_VERSION = "1.0.0"

# ── Directory layout ───────────────────────────────────────────────────────
# Resolve relative to this config file so the app works from any CWD.
_ROOT   = Path(__file__).resolve().parent.parent   # project root
INPUT_DIR  = _ROOT / "input"
OUTPUT_DIR = _ROOT / "output"
LOGS_DIR   = _ROOT / "logs"
TEMP_DIR   = _ROOT / ".tmp"

# Ensure essential directories exist at import time
for _d in (INPUT_DIR, OUTPUT_DIR, LOGS_DIR, TEMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Video support ──────────────────────────────────────────────────────────
SUPPORTED_VIDEO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m4v",
})

# ── Segment slicing bounds (seconds) ──────────────────────────────────────
SEGMENT_MIN_DURATION: int = 240   # 4 minutes
SEGMENT_MAX_DURATION: int = 300   # 5 minutes

# ── Canvas dimensions (9:16 vertical) ─────────────────────────────────────
CANVAS_W: int = 1080
CANVAS_H: int = 1920

# ── Cinematic reframing zoom range (applied to foreground layer) ───────────
ZOOM_MIN: float = 0.05   # 5 %  crop factor
ZOOM_MAX: float = 0.10   # 10 % crop factor

# ── Watermark ─────────────────────────────────────────────────────────────
WATERMARK_TEXT: str  = "Voidclip.mov"
WATERMARK_FONT: str  = "Arial"          # must be available on host system
WATERMARK_SIZE: int  = 42
WATERMARK_OPACITY: float = 0.55         # 0.0 – 1.0
WATERMARK_Y_RATIO: float = 0.88         # vertical position as fraction of canvas height

# ── Background blur ───────────────────────────────────────────────────────
BLUR_LUMA_POWER: int = 20   # boxblur luma radius
BLUR_CHROMA_POWER: int = 10  # boxblur chroma radius (gentler to hide artefacts)

# ── SubtitleMode enum ─────────────────────────────────────────────────────
class SubtitleMode(str, enum.Enum):
    KEEP    = "keep"
    BURN    = "burn"
    DISABLE = "disable"

# ── Render presets ─────────────────────────────────────────────────────────
# Each preset maps to an ffmpeg encoding argument dict.
# Keys: video_codec, crf, preset, audio_codec, audio_bitrate, pixel_format,
#       extra_vargs (list of extra video stream args), container
RENDER_PRESETS: dict[str, dict] = {
    "H264 — Fast (CRF 23)": {
        "video_codec":   "libx264",
        "crf":           23,
        "preset":        "fast",
        "audio_codec":   "aac",
        "audio_bitrate": "192k",
        "pixel_format":  "yuv420p",
        "extra_vargs":   ["-movflags", "+faststart"],
        "container":     "mp4",
    },
    "H264 — Quality (CRF 18)": {
        "video_codec":   "libx264",
        "crf":           18,
        "preset":        "slow",
        "audio_codec":   "aac",
        "audio_bitrate": "256k",
        "pixel_format":  "yuv420p",
        "extra_vargs":   ["-movflags", "+faststart"],
        "container":     "mp4",
    },
    "H265 — Efficient (CRF 24)": {
        "video_codec":   "libx265",
        "crf":           24,
        "preset":        "medium",
        "audio_codec":   "aac",
        "audio_bitrate": "192k",
        "pixel_format":  "yuv420p10le",
        "extra_vargs":   ["-tag:v", "hvc1"],
        "container":     "mp4",
    },
    "H265 — Quality (CRF 20)": {
        "video_codec":   "libx265",
        "crf":           20,
        "preset":        "slow",
        "audio_codec":   "aac",
        "audio_bitrate": "256k",
        "pixel_format":  "yuv420p10le",
        "extra_vargs":   ["-tag:v", "hvc1"],
        "container":     "mp4",
    },
    "VP9 — Web (CQ 30)": {
        "video_codec":   "libvpx-vp9",
        "crf":           30,
        "preset":        None,          # VP9 uses -quality instead
        "audio_codec":   "libopus",
        "audio_bitrate": "192k",
        "pixel_format":  "yuv420p",
        "extra_vargs":   ["-b:v", "0", "-quality", "good", "-cpu-used", "2"],
        "container":     "webm",
    },
}

# Default active preset name — must be a key in RENDER_PRESETS
DEFAULT_PRESET: str = "H264 — Fast (CRF 23)"
DEFAULT_SUBTITLE_MODE: SubtitleMode = SubtitleMode.KEEP

# ── FFmpeg probe / binary ──────────────────────────────────────────────────
# Set to None to let the engine search PATH automatically.
FFMPEG_BIN:  str | None = None   # e.g. "/usr/local/bin/ffmpeg"
FFPROBE_BIN: str | None = None   # e.g. "/usr/local/bin/ffprobe"

# ── Template store ─────────────────────────────────────────────────────────
TEMPLATES_FILE: Path = _ROOT / "backend" / "templates.json"

# ── Progress reporting ─────────────────────────────────────────────────────
# Minimum seconds between progress callback emissions to avoid GUI flooding.
PROGRESS_THROTTLE_S: float = 0.25
