"""
backend/config.py
=================
Konfigurasi global untuk video processing pipeline.
Berisi path direktori, render presets, dan konfigurasi default
watermark/zoom. Murni stateless — tidak ada database.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# Direktori kerja
# ---------------------------------------------------------------------------

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Direktori default bisa di-override lewat environment variable
INPUT_DIR: Path  = Path(os.getenv("VOIDCLIP_INPUT",  str(BASE_DIR / "input")))
OUTPUT_DIR: Path = Path(os.getenv("VOIDCLIP_OUTPUT", str(BASE_DIR / "output")))
CACHE_DIR: Path  = Path(os.getenv("VOIDCLIP_CACHE",  str(BASE_DIR / "cache")))

# Pastikan direktori ada saat modul dimuat
for _d in (INPUT_DIR, OUTPUT_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Konfigurasi pemotongan segmen (Intelligent Random Slicing)
# ---------------------------------------------------------------------------

SEGMENT_DURATION_MIN: int = 240   # detik  (4 menit)
SEGMENT_DURATION_MAX: int = 300   # detik  (5 menit)


# ---------------------------------------------------------------------------
# Konfigurasi canvas output (Synchronized 9:16 Vertical Layout)
# ---------------------------------------------------------------------------

CANVAS_WIDTH:  int = 1080
CANVAS_HEIGHT: int = 1920

# Blur background
BLUR_LUMA_RADIUS: int = 40   # radius boxblur pada channel luma
BLUR_CHROMA_RADIUS: int = 20  # radius boxblur pada channel chroma
BLUR_LUMA_POWER: int = 3
BLUR_CHROMA_POWER: int = 3

# Foreground: ukuran kotak highlight di tengah canvas (piksel)
# Video asli akan di-fit-scale masuk ke dalam kotak ini
FOREGROUND_MAX_WIDTH:  int = 1080
FOREGROUND_MAX_HEIGHT: int = 1080   # persegi di tengah; bisa disesuaikan


# ---------------------------------------------------------------------------
# Anti-Copyright Zoom (crop foreground 5%–10%)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ZoomConfig:
    """Konfigurasi zoom/crop foreground untuk anti-copyright detection."""
    zoom_min_pct: float = 5.0    # persen minimum crop dari sisi frame
    zoom_max_pct: float = 10.0   # persen maksimum crop dari sisi frame
    # Nilai aktual dipilih acak saat job disiapkan; disimpan di JobSpec


DEFAULT_ZOOM_CONFIG = ZoomConfig()


# ---------------------------------------------------------------------------
# Watermark
# ---------------------------------------------------------------------------

@dataclass
class WatermarkConfig:
    """Konfigurasi teks watermark via FFmpeg drawtext."""
    text:          str   = "Voidclip.mov"
    font_file:     str   = ""           # kosong = pakai font sistem (sans-serif)
    font_size:     int   = 42
    font_color:    str   = "white@0.35" # putih transparan
    font_bold:     bool  = True
    # Posisi: ekspresi FFmpeg — default: tengah horizontal, 92% dari bawah
    x_expr:        str   = "(w-text_w)/2"
    y_expr:        str   = "h*0.92"
    # Shadow tipis agar terbaca di latar apapun
    shadow_color:  str   = "black@0.25"
    shadow_x:      int   = 2
    shadow_y:      int   = 2
    box_enabled:   bool  = False
    box_color:     str   = "black@0.20"
    box_border_w:  int   = 12


DEFAULT_WATERMARK_CONFIG = WatermarkConfig()


# ---------------------------------------------------------------------------
# Render Presets
# ---------------------------------------------------------------------------

VideoCodec  = Literal["libx264", "libx265", "h264_nvenc", "hevc_nvenc",
                       "h264_videotoolbox", "hevc_videotoolbox",
                       "h264_amf", "hevc_amf"]
AudioCodec  = Literal["aac", "copy"]
PixelFormat = Literal["yuv420p", "yuv444p", "p010le"]


@dataclass
class RenderPreset:
    """Satu konfigurasi encode untuk output akhir."""
    name:          str
    video_codec:   VideoCodec   = "libx264"
    audio_codec:   AudioCodec   = "aac"
    crf:           int          = 23          # 0–51; lebih rendah = lebih bagus
    preset:        str          = "medium"    # ultrafast…veryslow
    pixel_format:  PixelFormat  = "yuv420p"
    audio_bitrate: str          = "192k"
    # Thread: 0 = auto (FFmpeg pilih sendiri)
    threads:       int          = 0
    # Extra FFmpeg output flags, list of str pasangan [-flag, value]
    extra_flags:   list[str]    = field(default_factory=list)


RENDER_PRESETS: dict[str, RenderPreset] = {
    "draft": RenderPreset(
        name="draft",
        video_codec="libx264",
        crf=28,
        preset="ultrafast",
        audio_bitrate="128k",
    ),
    "standard": RenderPreset(
        name="standard",
        video_codec="libx264",
        crf=23,
        preset="medium",
        audio_bitrate="192k",
    ),
    "high_quality": RenderPreset(
        name="high_quality",
        video_codec="libx264",
        crf=18,
        preset="slow",
        audio_bitrate="320k",
    ),
    "nvenc_fast": RenderPreset(
        name="nvenc_fast",
        video_codec="h264_nvenc",
        crf=0,                  # nvenc pakai -b:v atau -cq
        preset="p4",
        pixel_format="yuv420p",
        audio_bitrate="192k",
        extra_flags=["-cq", "23", "-b:v", "0"],
    ),
    "hevc_quality": RenderPreset(
        name="hevc_quality",
        video_codec="libx265",
        crf=22,
        preset="medium",
        pixel_format="yuv420p",
        audio_bitrate="192k",
        extra_flags=["-tag:v", "hvc1"],
    ),
}

DEFAULT_PRESET_NAME: str = "standard"


# ---------------------------------------------------------------------------
# Hardware acceleration hints
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HWAccelConfig:
    """
    Petunjuk hardware acceleration.
    Dideteksi secara runtime oleh ffmpeg_engine; flag di sini hanya default.
    """
    try_nvenc:        bool = True
    try_videotoolbox: bool = True
    try_amf:          bool = True
    # Fallback ke software jika semua HW gagal
    fallback_software: bool = True


DEFAULT_HWACCEL_CONFIG = HWAccelConfig()


# ---------------------------------------------------------------------------
# Batas progres & polling
# ---------------------------------------------------------------------------

# Interval baca stderr FFmpeg (detik) untuk parsing progress
FFMPEG_PROGRESS_POLL_INTERVAL: float = 0.25

# Timeout (detik) menunggu FFmpeg merespons sebelum dianggap hang
FFMPEG_HANG_TIMEOUT: float = 120.0
