"""
backend/ffmpeg_engine.py
========================
Lapisan rendah yang berkomunikasi langsung dengan binary FFmpeg/FFprobe.

Tanggung jawab:
  - Menemukan binary ffmpeg dan ffprobe di sistem.
  - Mengambil metadata video (durasi, resolusi, fps, codec) via ffprobe.
  - Menyusun dan mengeksekusi perintah FFmpeg untuk satu segmen,
    termasuk filtergraph kompleks:
      * Blur background (9:16 vertical canvas)
      * Foreground highlight tersinkronisasi
      * Anti-copyright zoom/crop
      * Watermark teks drawtext
  - Mem-parse output stderr FFmpeg secara real-time untuk laporan progres.
  - Mendukung hardware acceleration (NVENC / VideoToolbox / AMF) dengan
    fallback otomatis ke software encode.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from backend.config import (
    BLUR_CHROMA_POWER,
    BLUR_CHROMA_RADIUS,
    BLUR_LUMA_POWER,
    BLUR_LUMA_RADIUS,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_HWACCEL_CONFIG,
    DEFAULT_WATERMARK_CONFIG,
    FFMPEG_HANG_TIMEOUT,
    FOREGROUND_MAX_HEIGHT,
    FOREGROUND_MAX_WIDTH,
    HWAccelConfig,
    RenderPreset,
    WatermarkConfig,
)


# ---------------------------------------------------------------------------
# Tipe callback
# ---------------------------------------------------------------------------

LogCallback      = Callable[[str], None]
ProgressCallback = Callable[[float], None]   # 0.0–100.0, progres segmen ini


# ---------------------------------------------------------------------------
# Dataclass hasil probe
# ---------------------------------------------------------------------------

@dataclass
class VideoInfo:
    """Metadata video dari ffprobe."""
    path:       Path
    duration:   float          # detik (float)
    width:      int
    height:     int
    fps:        float
    video_codec: str
    audio_codec: str
    has_audio:  bool


# ---------------------------------------------------------------------------
# Pencarian binary
# ---------------------------------------------------------------------------

def _search_binary(name: str) -> Optional[str]:
    """
    Cari binary di PATH, lalu di lokasi umum Windows/macOS/Linux.
    Kembalikan path absolut atau None jika tidak ditemukan.
    """
    found = shutil.which(name)
    if found:
        return found

    # Lokasi alternatif umum
    candidates: list[str] = []
    if os.name == "nt":
        candidates = [
            rf"C:\ffmpeg\bin\{name}.exe",
            rf"C:\Program Files\ffmpeg\bin\{name}.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "ffmpeg", "bin", f"{name}.exe"),
        ]
    else:
        candidates = [
            f"/usr/local/bin/{name}",
            f"/usr/bin/{name}",
            f"/opt/homebrew/bin/{name}",
            f"/opt/local/bin/{name}",
            os.path.expanduser(f"~/bin/{name}"),
            os.path.expanduser(f"~/.local/bin/{name}"),
        ]

    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return None


def find_ffmpeg() -> str:
    """
    Kembalikan path binary ffmpeg.
    Raise FileNotFoundError jika tidak ditemukan.
    """
    path = _search_binary("ffmpeg")
    if not path:
        raise FileNotFoundError(
            "Binary 'ffmpeg' tidak ditemukan. "
            "Pastikan FFmpeg terinstall dan tersedia di PATH."
        )
    return path


def find_ffprobe() -> str:
    """
    Kembalikan path binary ffprobe.
    Raise FileNotFoundError jika tidak ditemukan.
    """
    path = _search_binary("ffprobe")
    if not path:
        raise FileNotFoundError(
            "Binary 'ffprobe' tidak ditemukan. "
            "Pastikan FFmpeg (termasuk ffprobe) terinstall dan tersedia di PATH."
        )
    return path


# ---------------------------------------------------------------------------
# Probe video
# ---------------------------------------------------------------------------

def probe_video(video_path: Path) -> VideoInfo:
    """
    Ambil metadata video menggunakan ffprobe.
    Kembalikan VideoInfo.
    Raise RuntimeError jika file tidak valid atau ffprobe gagal.
    """
    ffprobe = find_ffprobe()

    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(video_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ffprobe timeout saat membaca: {video_path}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe binary tidak ditemukan.") from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe gagal (kode {result.returncode}):\n{result.stderr}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Output ffprobe bukan JSON valid:\n{result.stdout}") from exc

    streams = data.get("streams", [])
    fmt     = data.get("format", {})

    # Ambil durasi dari format terlebih dahulu, fallback ke stream
    duration_str = fmt.get("duration", "0")
    try:
        duration = float(duration_str)
    except ValueError:
        duration = 0.0

    width  = 0
    height = 0
    fps    = 0.0
    video_codec = "unknown"
    audio_codec = "unknown"
    has_audio   = False

    for stream in streams:
        codec_type = stream.get("codec_type", "")

        if codec_type == "video" and width == 0:
            width  = int(stream.get("width",  0))
            height = int(stream.get("height", 0))
            video_codec = stream.get("codec_name", "unknown")

            # Hitung fps dari r_frame_rate atau avg_frame_rate
            for fps_key in ("r_frame_rate", "avg_frame_rate"):
                fps_str = stream.get(fps_key, "")
                if fps_str and fps_str not in ("0/0", "0"):
                    try:
                        num, den = fps_str.split("/")
                        _fps = float(num) / float(den)
                        if _fps > 0:
                            fps = _fps
                            break
                    except (ValueError, ZeroDivisionError):
                        pass

            # Durasi stream lebih akurat untuk beberapa container
            if duration == 0.0:
                try:
                    duration = float(stream.get("duration", "0"))
                except ValueError:
                    pass

        elif codec_type == "audio":
            has_audio   = True
            audio_codec = stream.get("codec_name", "unknown")

    if duration <= 0:
        raise RuntimeError(
            f"Durasi video tidak dapat dibaca atau nol: {video_path}"
        )
    if width <= 0 or height <= 0:
        raise RuntimeError(
            f"Resolusi video tidak valid ({width}x{height}): {video_path}"
        )

    return VideoInfo(
        path=video_path,
        duration=duration,
        width=width,
        height=height,
        fps=fps if fps > 0 else 25.0,
        video_codec=video_codec,
        audio_codec=audio_codec,
        has_audio=has_audio,
    )


# ---------------------------------------------------------------------------
# Deteksi hardware acceleration
# ---------------------------------------------------------------------------

def _test_hw_encoder(codec: str) -> bool:
    """
    Uji apakah encoder HW tersedia dengan encoding frame dummy.
    Kembalikan True jika berhasil.
    """
    try:
        ffmpeg = find_ffmpeg()
    except FileNotFoundError:
        return False

    cmd = [
        ffmpeg,
        "-loglevel", "error",
        "-f", "lavfi", "-i", "nullsrc=s=128x128:d=0.1",
        "-c:v", codec,
        "-frames:v", "1",
        "-f", "null",
        "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def detect_available_hwaccel(cfg: HWAccelConfig = DEFAULT_HWACCEL_CONFIG) -> Optional[str]:
    """
    Uji hardware encoder satu per satu berdasarkan konfigurasi.
    Kembalikan nama encoder HW pertama yang berhasil, atau None (software).
    """
    candidates: list[tuple[bool, str]] = []

    if cfg.try_nvenc:
        candidates.append((True, "h264_nvenc"))
    if cfg.try_videotoolbox:
        candidates.append((True, "h264_videotoolbox"))
    if cfg.try_amf:
        candidates.append((True, "h264_amf"))

    for _enabled, codec in candidates:
        if _enabled and _test_hw_encoder(codec):
            return codec

    return None   # fallback ke software


# ---------------------------------------------------------------------------
# Penyusun filtergraph
# ---------------------------------------------------------------------------

def _build_filtergraph(
    src_width:        int,
    src_height:       int,
    zoom_crop_pct:    float,
    watermark_cfg:    WatermarkConfig,
) -> str:
    """
    Susun string filtergraph FFmpeg lengkap untuk satu pass render.

    Stream input diasumsikan:
      [0:v]  = stream video dari sumber
      [0:a]  = stream audio dari sumber (jika ada)

    Urutan filter:
      1. Split input video menjadi dua cabang: bg (background) dan fg (foreground).
      2. Background path:
         a. Scale ke canvas penuh (cover, aspect ratio dipertahankan dengan crop).
         b. Blur lebih (boxblur).
      3. Foreground path:
         a. Hitung ukuran setelah zoom/crop anti-copyright.
         b. Scale ke FOREGROUND_MAX_WIDTH x FOREGROUND_MAX_HEIGHT (fit/pad).
         c. Overlay di tengah canvas background.
      4. Watermark drawtext di atas hasil overlay.

    Kembalikan string filter_complex.
    """
    canvas_w = CANVAS_WIDTH
    canvas_h = CANVAS_HEIGHT
    fg_max_w = FOREGROUND_MAX_WIDTH
    fg_max_h = FOREGROUND_MAX_HEIGHT

    # --- Hitung faktor zoom/crop ---
    # zoom_crop_pct = persentase yang di-crop dari SETIAP sisi
    # Misal 7% -> crop 7% dari kiri, 7% dari kanan, 7% atas, 7% bawah
    # Resulting crop area = (100 - 2*pct)% dari dimensi asli
    crop_factor = 1.0 - (zoom_crop_pct / 100.0) * 2
    crop_factor = max(0.70, min(1.0, crop_factor))   # clamp 70%–100%

    # Ukuran crop area dalam piksel (berdasarkan dimensi sumber)
    crop_w_expr = f"trunc(iw*{crop_factor:.6f}/2)*2"
    crop_h_expr = f"trunc(ih*{crop_factor:.6f}/2)*2"
    # Offset agar crop terpusat
    crop_x_expr = f"(iw-{crop_w_expr})/2"
    crop_y_expr = f"(ih-{crop_h_expr})/2"

    # --- Background: scale cover 9:16 lalu blur ---
    # Scale agar memenuhi canvas dari sisi terpendek (cover behavior):
    # Gunakan scale2ref atau scale dengan force_original_aspect_ratio=increase lalu crop
    bg_scale = (
        f"scale={canvas_w}:{canvas_h}"
        f":force_original_aspect_ratio=increase"
        f":flags=lanczos"
    )
    bg_crop  = f"crop={canvas_w}:{canvas_h}"
    bg_blur  = (
        f"boxblur="
        f"luma_radius={BLUR_LUMA_RADIUS}:luma_power={BLUR_LUMA_POWER}"
        f":chroma_radius={BLUR_CHROMA_RADIUS}:chroma_power={BLUR_CHROMA_POWER}"
    )

    # --- Foreground: crop anti-copyright -> scale fit ke kotak tengah ---
    fg_crop   = f"crop={crop_w_expr}:{crop_h_expr}:{crop_x_expr}:{crop_y_expr}"
    fg_scale  = (
        f"scale={fg_max_w}:{fg_max_h}"
        f":force_original_aspect_ratio=decrease"
        f":flags=lanczos"
    )
    # Pad agar ukuran persis fg_max_w x fg_max_h (letterbox transparan -> hitam)
    fg_pad    = (
        f"pad={fg_max_w}:{fg_max_h}"
        f":(ow-iw)/2:(oh-ih)/2"
        f":color=black"
    )

    # Posisi overlay foreground di tengah canvas
    overlay_x = f"({canvas_w}-{fg_max_w})/2"
    overlay_y = f"({canvas_h}-{fg_max_h})/2"

    # --- Watermark drawtext ---
    wm = watermark_cfg
    font_part   = f"fontfile='{wm.font_file}'" if wm.font_file else "font='Sans'"
    bold_part   = ":style='Bold'" if wm.font_bold and not wm.font_file else ""
    shadow_part = (
        f":shadowcolor={wm.shadow_color}"
        f":shadowx={wm.shadow_x}"
        f":shadowy={wm.shadow_y}"
    )
    box_part = ""
    if wm.box_enabled:
        box_part = (
            f":box=1"
            f":boxcolor={wm.box_color}"
            f":boxborderw={wm.box_border_w}"
        )

    # Escape teks watermark untuk drawtext (apostrof dan backslash)
    safe_text = wm.text.replace("\\", "\\\\").replace("'", "\\'")

    drawtext = (
        f"drawtext="
        f"{font_part}"
        f":text='{safe_text}'"
        f":fontsize={wm.font_size}"
        f":fontcolor={wm.font_color}"
        f"{bold_part}"
        f":x={wm.x_expr}"
        f":y={wm.y_expr}"
        f"{shadow_part}"
        f"{box_part}"
    )

    # --- Susun filter_complex lengkap ---
    # Gunakan label stream bernama agar mudah dibaca
    filtergraph = (
        # Cabangkan input video menjadi dua
        f"[0:v]split=2[bg_raw][fg_raw];"

        # Background pipeline
        f"[bg_raw]{bg_scale},{bg_crop},{bg_blur}[bg_blurred];"

        # Foreground pipeline
        f"[fg_raw]{fg_crop},{fg_scale},{fg_pad}[fg_ready];"

        # Overlay foreground di atas background
        f"[bg_blurred][fg_ready]overlay={overlay_x}:{overlay_y}[composite];"

        # Tambahkan watermark
        f"[composite]{drawtext}[vout]"
    )

    return filtergraph


# ---------------------------------------------------------------------------
# Parser progres FFmpeg dari stderr
# ---------------------------------------------------------------------------

# Contoh baris stderr FFmpeg:
#   frame=  123 fps= 45 q=28.0 size=    1024kB time=00:00:04.92 bitrate=1705.5kbits/s speed=1.80x
_PROGRESS_RE = re.compile(
    r"frame=\s*(?P<frame>\d+)"
    r".*?fps=\s*(?P<fps>[0-9.]+)"
    r".*?time=(?P<time>\d{2}:\d{2}:\d{2}[.,]\d+)"
    r".*?speed=\s*(?P<speed>[0-9.]+)x",
    re.IGNORECASE,
)


def _parse_time_to_seconds(time_str: str) -> float:
    """Konversi string 'HH:MM:SS.ms' ke detik float."""
    time_str = time_str.replace(",", ".")
    parts = time_str.split(":")
    try:
        h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
    except (IndexError, ValueError):
        return 0.0


def _parse_progress_line(line: str) -> Optional[dict]:
    """
    Parse satu baris stderr FFmpeg.
    Kembalikan dict {frame, fps, elapsed_sec, speed} atau None.
    """
    match = _PROGRESS_RE.search(line)
    if not match:
        return None
    try:
        return {
            "frame":       int(match.group("frame")),
            "fps":         float(match.group("fps")),
            "elapsed_sec": _parse_time_to_seconds(match.group("time")),
            "speed":       float(match.group("speed")),
        }
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Fungsi inti: render_segment
# ---------------------------------------------------------------------------

def render_segment(
    input_path:        Path,
    output_path:       Path,
    start_sec:         float,
    duration_sec:      float,
    zoom_crop_pct:     float,
    preset:            RenderPreset,
    watermark_cfg:     WatermarkConfig         = DEFAULT_WATERMARK_CONFIG,
    hwaccel_cfg:       HWAccelConfig           = DEFAULT_HWACCEL_CONFIG,
    log_callback:      Optional[LogCallback]   = None,
    progress_callback: Optional[ProgressCallback] = None,
    cancel_event:      Optional[threading.Event]  = None,
) -> None:
    """
    Render satu segmen video dengan filtergraph lengkap.

    Parameter
    ---------
    input_path      : File video sumber.
    output_path     : File output segmen.
    start_sec       : Titik mulai potong (detik).
    duration_sec    : Durasi segmen (detik).
    zoom_crop_pct   : Persentase crop per-sisi untuk anti-copyright (5–10).
    preset          : RenderPreset yang berisi codec, crf, dll.
    watermark_cfg   : Konfigurasi teks watermark.
    hwaccel_cfg     : Konfigurasi hardware acceleration.
    log_callback    : Dipanggil dengan string log setiap baris stderr.
    progress_callback : Dipanggil dengan float 0.0–100.0 kemajuan segmen ini.
    cancel_event    : threading.Event; jika set, proses FFmpeg akan dihentikan.

    Raise
    -----
    RuntimeError    : Jika FFmpeg keluar dengan kode error.
    """

    def _log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    ffmpeg_bin = find_ffmpeg()

    # --- Probe info video sumber ---
    info = probe_video(input_path)
    _log(f"[probe] {input_path.name}: {info.width}x{info.height}, "
         f"{info.duration:.2f}s, {info.fps:.2f}fps")

    # --- Deteksi HW encoder jika preset memintanya ---
    effective_vcodec = preset.video_codec
    if "nvenc" in preset.video_codec or "videotoolbox" in preset.video_codec or "amf" in preset.video_codec:
        hw = detect_available_hwaccel(hwaccel_cfg)
        if hw is None:
            _log(f"[hwaccel] Encoder HW '{preset.video_codec}' tidak tersedia, "
                 f"fallback ke libx264.")
            effective_vcodec = "libx264"
        else:
            effective_vcodec = hw
            _log(f"[hwaccel] Menggunakan encoder HW: {effective_vcodec}")
    else:
        _log(f"[codec] Menggunakan encoder: {effective_vcodec}")

    # --- Bangun filtergraph ---
    filtergraph = _build_filtergraph(
        src_width=info.width,
        src_height=info.height,
        zoom_crop_pct=zoom_crop_pct,
        watermark_cfg=watermark_cfg,
    )
    _log(f"[filtergraph] {filtergraph[:120]}{'...' if len(filtergraph) > 120 else ''}")

    # --- Susun perintah FFmpeg ---
    cmd: list[str] = [
        ffmpeg_bin,
        "-y",                        # Timpa output tanpa tanya
        "-ss",  f"{start_sec:.3f}",  # Seek sebelum input (fast seek)
        "-i",   str(input_path),
        "-t",   f"{duration_sec:.3f}",
        "-filter_complex", filtergraph,
        "-map", "[vout]",
    ]

    # Audio
    if info.has_audio:
        cmd += ["-map", "0:a"]
        cmd += ["-c:a", preset.audio_codec]
        if preset.audio_codec != "copy":
            cmd += ["-b:a", preset.audio_bitrate]
    else:
        cmd += ["-an"]

    # Video codec dan quality
    cmd += ["-c:v", effective_vcodec]

    # CRF hanya untuk software encoder
    is_software = effective_vcodec in ("libx264", "libx265", "libvpx-vp9")
    if is_software and preset.crf > 0:
        cmd += ["-crf", str(preset.crf)]

    cmd += ["-preset", preset.preset]
    cmd += ["-pix_fmt", preset.pixel_format]

    if preset.threads > 0:
        cmd += ["-threads", str(preset.threads)]

    # Extra flags dari preset (pasangan datar)
    if preset.extra_flags:
        cmd += preset.extra_flags

    # Progress pipe: minta FFmpeg mengirim data progres ke stderr terstruktur
    cmd += ["-progress", "pipe:2"]

    cmd += [str(output_path)]

    _log(f"[cmd] {' '.join(cmd)}")

    # --- Jalankan FFmpeg ---
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Gagal menjalankan FFmpeg: {exc}") from exc

    _log(f"[start] PID={proc.pid}, output={output_path.name}")

    # Perkiraan total frame segmen untuk kalkulasi persen
    estimated_frames = max(1, int(duration_sec * info.fps))
    last_progress_pct = 0.0
    last_activity_time = time.monotonic()

    # Baca stderr baris per baris (non-blocking via thread reader)
    stderr_lines: list[str] = []
    stderr_lock  = threading.Lock()
    eof_event    = threading.Event()

    def _stderr_reader() -> None:
        """Thread pembaca stderr FFmpeg."""
        assert proc.stderr is not None
        for line in proc.stderr:
            line = line.rstrip("\n")
            with stderr_lock:
                stderr_lines.append(line)
        eof_event.set()

    reader_thread = threading.Thread(target=_stderr_reader, daemon=True)
    reader_thread.start()

    # Loop monitoring utama
    while True:
        # Cek permintaan cancel
        if cancel_event is not None and cancel_event.is_set():
            _log("[cancel] Cancel diminta, menghentikan FFmpeg...")
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise RuntimeError("Render dibatalkan oleh pengguna.")

        # Drain baris stderr
        with stderr_lock:
            lines_to_process = list(stderr_lines)
            stderr_lines.clear()

        for line in lines_to_process:
            _log(f"[ffmpeg] {line}")
            parsed = _parse_progress_line(line)
            if parsed:
                last_activity_time = time.monotonic()
                pct = min(100.0, (parsed["elapsed_sec"] / duration_sec) * 100.0)
                if pct > last_progress_pct:
                    last_progress_pct = pct
                    if progress_callback:
                        progress_callback(pct)

        # Cek timeout hang
        if time.monotonic() - last_activity_time > FFMPEG_HANG_TIMEOUT:
            _log(f"[timeout] FFmpeg tidak merespons selama {FFMPEG_HANG_TIMEOUT}s, membunuh proses.")
            proc.kill()
            raise RuntimeError(f"FFmpeg timeout setelah {FFMPEG_HANG_TIMEOUT} detik.")

        # Cek apakah proses sudah selesai
        retcode = proc.poll()
        if retcode is not None:
            # Tunggu reader selesai
            eof_event.wait(timeout=5.0)
            # Drain sisa
            with stderr_lock:
                for line in stderr_lines:
                    _log(f"[ffmpeg] {line}")
            break

        time.sleep(0.1)

    if proc.returncode != 0:
        raise RuntimeError(
            f"FFmpeg keluar dengan kode {proc.returncode}. "
            f"Periksa log untuk detail error."
        )

    # Pastikan progress 100% terkirim
    if progress_callback:
        progress_callback(100.0)

    _log(f"[done] Segmen selesai: {output_path.name}")
