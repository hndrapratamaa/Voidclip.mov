"""
backend/ffmpeg_engine.py
─────────────────────────────────────────────────────────────────────────────
Voidclip.mov — FFmpeg engine: probe, segment planning, filtergraph, encode

Responsibilities
────────────────
1. `probe_video`        — extract duration, width, height, fps via ffprobe
2. `plan_segments`      — deterministic random slice plan (240–300 s each)
3. `build_filtergraph`  — assemble the 9:16 complex filtergraph string
4. `stream_copy_cut`    — fast lossless trim to a temp file (pre-encode step)
5. `encode_segment`     — full quality encode of a trimmed temp segment

Filtergraph pipeline (per segment)
────────────────────────────────────
[0:v] ──► scale to 1080×1920 (fill, crop overflow)
       ──► boxblur(20) ─────────────────────────────────────► [bg]
[0:v] ──► scale to fit inside 1080×(1920-margin) with zoom  ► [fg]
[bg][fg] overlay=centred ──► drawtext watermark ────────────► [out]
[0:a] ──────────────────────────────────────────────────────► [aout]
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Tuple

from backend.config import (
    BLUR_CHROMA_POWER,
    BLUR_LUMA_POWER,
    CANVAS_H,
    CANVAS_W,
    FFMPEG_BIN,
    FFPROBE_BIN,
    SEGMENT_MAX_DURATION,
    SEGMENT_MIN_DURATION,
    TEMP_DIR,
    WATERMARK_FONT,
    WATERMARK_OPACITY,
    WATERMARK_SIZE,
    WATERMARK_TEXT,
    WATERMARK_Y_RATIO,
    ZOOM_MAX,
    ZOOM_MIN,
)
from backend.logger import get_logger

log = get_logger(__name__)


# ── Binary resolution ───────────────────────────────────────────────────────

def _resolve_bin(override: Optional[str], name: str) -> str:
    if override:
        return override
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(
        f"'{name}' not found on PATH. Install FFmpeg or set {name.upper()}_BIN in config.py"
    )


def ffmpeg_bin() -> str:
    return _resolve_bin(FFMPEG_BIN, "ffmpeg")


def ffprobe_bin() -> str:
    return _resolve_bin(FFPROBE_BIN, "ffprobe")


# ── Probe result ────────────────────────────────────────────────────────────

@dataclass
class VideoInfo:
    path:       Path
    duration:   float          # seconds
    width:      int
    height:     int
    fps:        float
    has_audio:  bool = True
    codec:      str  = "unknown"

    @property
    def aspect(self) -> float:
        return self.width / max(self.height, 1)

    @property
    def is_landscape(self) -> bool:
        return self.width >= self.height


# ── Segment descriptor ──────────────────────────────────────────────────────

@dataclass
class SegmentPlan:
    index:      int
    start:      float   # seconds into the source
    duration:   float   # requested duration (may be shorter at end of file)
    zoom:       float   # cinematic zoom factor for this segment


# ── 1. Probe ────────────────────────────────────────────────────────────────

def probe_video(path: Path) -> VideoInfo:
    """
    Run ffprobe and return a VideoInfo.  Raises RuntimeError on failure.
    """
    cmd = [
        ffprobe_bin(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    log.debug("ffprobe: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffprobe failed on {path.name}: {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ffprobe timed out on {path.name}") from exc

    data = json.loads(result.stdout)

    # ── Extract video stream ───────────────────────────────────────────────
    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise RuntimeError(f"No video stream found in {path.name}")

    audio_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
        None,
    )

    # Duration: prefer format-level, fall back to stream-level
    raw_duration = (
        data.get("format", {}).get("duration")
        or video_stream.get("duration")
        or "0"
    )
    duration = float(raw_duration)

    # FPS: avg_frame_rate is a fraction string like "30000/1001"
    fps_str = video_stream.get("avg_frame_rate", "30/1")
    try:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 30.0
    except (ValueError, ZeroDivisionError):
        fps = 30.0

    codec = video_stream.get("codec_name", "unknown")
    w     = int(video_stream.get("width", 1920))
    h     = int(video_stream.get("height", 1080))

    info = VideoInfo(
        path=path,
        duration=duration,
        width=w,
        height=h,
        fps=fps,
        has_audio=audio_stream is not None,
        codec=codec,
    )
    log.info(
        "Probed '%s': %.1fs, %dx%d, %.2f fps, audio=%s, codec=%s",
        path.name, duration, w, h, fps, info.has_audio, codec,
    )
    return info


# ── 2. Segment planning ─────────────────────────────────────────────────────

def plan_segments(
    info: VideoInfo,
    seed: Optional[int] = None,
) -> List[SegmentPlan]:
    """
    Divide the video into segments of random duration between
    SEGMENT_MIN_DURATION and SEGMENT_MAX_DURATION seconds.

    The last segment is always included even if shorter than the minimum.

    Each segment also gets a randomly sampled cinematic zoom factor.
    """
    rng = random.Random(seed)   # seeded for reproducibility if needed
    segments: List[SegmentPlan] = []
    cursor = 0.0
    idx    = 0

    while cursor < info.duration:
        raw_dur = rng.uniform(SEGMENT_MIN_DURATION, SEGMENT_MAX_DURATION)
        actual_dur = min(raw_dur, info.duration - cursor)

        if actual_dur < 10.0:
            # Tail too short to be useful — skip
            log.debug("Skipping tail segment of %.1f s at %.1f s", actual_dur, cursor)
            break

        zoom = rng.uniform(ZOOM_MIN, ZOOM_MAX)

        segments.append(
            SegmentPlan(
                index=idx,
                start=cursor,
                duration=actual_dur,
                zoom=zoom,
            )
        )
        cursor += actual_dur
        idx    += 1

    log.info("Planned %d segments for '%s'", len(segments), info.path.name)
    return segments


# ── 3. Complex filtergraph builder ──────────────────────────────────────────

def build_filtergraph(info: VideoInfo, seg: SegmentPlan) -> str:
    """
    Return the -filter_complex string for the 9:16 vertical canvas.

    Pipeline
    ────────
    Step A — Background layer
        Scale input so it *fills* the full 1080×1920 canvas (cover mode),
        then apply heavy boxblur.

    Step B — Foreground layer
        Scale input to maximally fit *within* a safe inner width/height,
        apply the per-segment cinematic zoom/crop, center-crop to the
        exact foreground dimensions.

    Step C — Composite
        Overlay foreground centred on blurred background.

    Step D — Watermark
        drawtext at bottom-centre with configurable opacity.
    """
    cw, ch = CANVAS_W, CANVAS_H          # 1080 × 1920
    src_w,  src_h  = info.width, info.height

    # ── Step A: background scale (cover fill 1080×1920) ───────────────────
    # The scale filter uses 'force_original_aspect_ratio=increase' to ensure
    # the frame covers the full canvas, then we centrecrop any overflow.
    bg_scale = (
        f"scale={cw}:{ch}:force_original_aspect_ratio=increase,"
        f"crop={cw}:{ch}"
    )
    bg_blur = (
        f"boxblur=luma_radius={BLUR_LUMA_POWER}:luma_power=1"
        f":chroma_radius={BLUR_CHROMA_POWER}:chroma_power=1"
    )

    # ── Step B: foreground dimensions with zoom ────────────────────────────
    # The foreground fits inside the canvas width while preserving aspect.
    # zoom factor crops INTO the frame (removes outer margin).
    zoom = seg.zoom  # e.g. 0.07 → 7% crop on each axis

    # Maximum foreground height is the full canvas height (we allow vertical fill)
    # We scale the source so width == CANVAS_W, then take a centred crop.
    # For landscape source (common case): fit by width first.
    if src_w > 0 and src_h > 0:
        # Scale to fit canvas width exactly
        scale_h = int(round(src_h * cw / src_w))
        fg_scale_w = cw
        fg_scale_h = scale_h if scale_h > 0 else ch

        # Apply zoom: crop (1-zoom) of each dimension from centre
        crop_factor = 1.0 - zoom
        fg_crop_w = int(round(fg_scale_w * crop_factor))
        fg_crop_h = int(round(fg_scale_h * crop_factor))

        # Clamp to canvas bounds
        fg_crop_w = min(fg_crop_w, cw)
        fg_crop_h = min(fg_crop_h, ch)
    else:
        fg_scale_w, fg_scale_h = cw, ch
        fg_crop_w,  fg_crop_h  = cw, ch

    fg_scale = f"scale={fg_scale_w}:{fg_scale_h}"
    # crop=w:h:x:y  — centred crop
    fg_crop  = f"crop={fg_crop_w}:{fg_crop_h}"

    # ── Overlay position: centre on canvas ────────────────────────────────
    overlay_x = f"(main_w-overlay_w)/2"
    overlay_y = f"(main_h-overlay_h)/2"

    # ── Step D: watermark ─────────────────────────────────────────────────
    wm_y = int(ch * WATERMARK_Y_RATIO)
    # alpha as hex: 0.55 → 0x8C
    alpha_hex = format(int(WATERMARK_OPACITY * 255), "02X")
    wm_color  = f"white@{WATERMARK_OPACITY:.2f}"

    # Escape special characters in watermark text for FFmpeg drawtext
    wm_text = WATERMARK_TEXT.replace("'", r"\'").replace(":", r"\:")

    # Font file: try to use system font; drawtext can fall back to built-in.
    # We do NOT hard-code a path — let ffmpeg resolve the font by family name.
    watermark_filter = (
        f"drawtext="
        f"text='{wm_text}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize={WATERMARK_SIZE}:"
        f"fontcolor={wm_color}:"
        f"x=(w-text_w)/2:"
        f"y={wm_y}:"
        f"shadowcolor=black@0.40:"
        f"shadowx=2:shadowy=2"
    )

    # ── Assemble filter_complex ────────────────────────────────────────────
    filtergraph = (
        # Background: scale → blur → [bg]
        f"[0:v]{bg_scale},{bg_blur}[bg];"
        # Foreground: scale → zoom-crop → [fg]
        f"[0:v]{fg_scale},{fg_crop}[fg];"
        # Composite: bg + fg → watermark → [vout]
        f"[bg][fg]overlay={overlay_x}:{overlay_y},"
        f"{watermark_filter}[vout]"
    )

    log.debug(
        "Filtergraph built for segment %d (zoom=%.2f%%): fg=%dx%d → crop=%dx%d",
        seg.index, zoom * 100, fg_scale_w, fg_scale_h, fg_crop_w, fg_crop_h,
    )
    return filtergraph


# ── 4. Stream-copy cut (fast pre-cut) ──────────────────────────────────────

def stream_copy_cut(
    source: Path,
    seg:    SegmentPlan,
    tmp_dir: Path = TEMP_DIR,
) -> Path:
    """
    Perform a fast stream-copy trim of the source video.

    This creates a lossless temporary file containing only the segment's
    time window.  The encode step then operates on this shorter file,
    which is faster (no need for ffmpeg to seek through the whole source
    on every frame).

    Returns the path to the trimmed temp file.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{source.stem}_seg{seg.index:04d}_cut"
    tmp_path = tmp_dir / f"{stem}.mkv"   # MKV tolerates stream-copy better

    cmd = [
        ffmpeg_bin(),
        "-y",                           # overwrite if exists
        "-ss", f"{seg.start:.3f}",
        "-i", str(source),
        "-t",  f"{seg.duration:.3f}",
        "-c",  "copy",                  # stream copy — no re-encode
        "-avoid_negative_ts", "make_zero",
        str(tmp_path),
    ]

    log.debug("Stream-copy cut cmd: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Stream-copy cut failed for segment {seg.index}: "
            f"{result.stderr[-800:].strip()}"
        )

    log.debug("Stream-copy cut done → %s (%.1f MB)", tmp_path.name, tmp_path.stat().st_size / 1e6)
    return tmp_path


# ── 5. Encode segment ──────────────────────────────────────────────────────

def encode_segment(
    tmp_source:     Path,
    output_path:    Path,
    info:           VideoInfo,
    seg:            SegmentPlan,
    preset_cfg:     dict,
    subtitle_mode:  str = "keep",
    progress_cb:    Optional[Callable[[float, float, float], None]] = None,
    stop_flag:      Optional[Callable[[], bool]] = None,
) -> None:
    """
    Full-quality encode of *tmp_source* to *output_path*.

    Parameters
    ──────────
    tmp_source   : output of stream_copy_cut() for this segment
    output_path  : final destination .mp4 (or .webm) file
    info         : VideoInfo of the *original* source (for filtergraph dims)
    seg          : SegmentPlan for this segment (carries zoom)
    preset_cfg   : one entry from RENDER_PRESETS
    subtitle_mode: "keep" | "burn" | "disable"
    progress_cb  : called with (seg_pct: float, fps: float, speed: float)
    stop_flag    : callable returning True if the encode should be aborted

    The function blocks until FFmpeg exits or *stop_flag* returns True.
    On abort, the partial output file is deleted.
    Raises RuntimeError on failure.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filtergraph = build_filtergraph(info, seg)

    vcodec  = preset_cfg["video_codec"]
    crf     = preset_cfg["crf"]
    enc_preset = preset_cfg.get("preset")
    acodec  = preset_cfg["audio_codec"]
    abitrate = preset_cfg["audio_bitrate"]
    pix_fmt = preset_cfg["pixel_format"]
    extra   = preset_cfg.get("extra_vargs", [])

    cmd: List[str] = [
        ffmpeg_bin(),
        "-y",
        "-i", str(tmp_source),
    ]

    # Audio: if source has no audio, generate silence
    if not info.has_audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]

    cmd += [
        "-filter_complex", filtergraph,
        "-map", "[vout]",
        "-map", "0:a?" if info.has_audio else "1:a",
        "-c:v", vcodec,
        "-crf", str(crf),
    ]

    if enc_preset:
        cmd += ["-preset", enc_preset]

    cmd += [
        "-pix_fmt", pix_fmt,
        "-c:a", acodec,
        "-b:a", abitrate,
    ]
    cmd += extra

    # Subtitle handling
    if subtitle_mode == "disable":
        cmd += ["-sn"]
    elif subtitle_mode == "burn":
        # Burning subtitles requires a separate subtitles filter — placeholder
        # for now; burn mode falls back to keep (complex to implement generically)
        log.warning("Subtitle burn mode not yet implemented — falling back to keep")
        cmd += ["-c:s", "copy"] if subtitle_mode != "disable" else ["-sn"]
    else:
        # keep: copy subtitle streams if present
        cmd += ["-c:s", "copy"]

    # Progress via stderr pipe
    cmd += [
        "-progress", "pipe:2",
        "-stats_period", "0.5",
        str(output_path),
    ]

    log.info("Encoding segment %d → %s", seg.index, output_path.name)
    log.debug("Encode cmd: %s", " ".join(cmd))

    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    total_frames = max(1, int(info.fps * seg.duration))
    _parse_and_stream_progress(proc, total_frames, seg.duration, progress_cb, stop_flag)

    proc.wait()

    if stop_flag and stop_flag():
        log.info("Encode of segment %d aborted by stop flag", seg.index)
        output_path.unlink(missing_ok=True)
        return

    if proc.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"FFmpeg encode failed for segment {seg.index} "
            f"(exit {proc.returncode})"
        )

    log.info(
        "Segment %d encoded → %s (%.1f MB)",
        seg.index,
        output_path.name,
        output_path.stat().st_size / 1e6,
    )


# ── Progress parser ─────────────────────────────────────────────────────────

_KV_RE = re.compile(r"^(\w+)=(.+)$")


def _parse_and_stream_progress(
    proc:         subprocess.Popen,
    total_frames: int,
    total_secs:   float,
    progress_cb:  Optional[Callable[[float, float, float], None]],
    stop_flag:    Optional[Callable[[], bool]],
) -> None:
    """
    Read FFmpeg's `-progress pipe:2` key=value lines from *proc.stderr*
    and call *progress_cb(seg_pct, fps, speed)* on each 'progress=...' line.

    Also polls *stop_flag* and terminates *proc* if requested.
    """
    if proc.stderr is None:
        return

    kv: dict[str, str] = {}

    for raw_line in proc.stderr:
        if stop_flag and stop_flag():
            try:
                proc.terminate()
            except OSError:
                pass
            return

        line = raw_line.strip()
        m = _KV_RE.match(line)
        if m:
            kv[m.group(1)] = m.group(2)

        if line.startswith("progress="):
            # A complete progress block has been emitted
            try:
                frame    = int(kv.get("frame",   "0"))
                fps_val  = float(kv.get("fps",   "0"))
                speed_s  = kv.get("speed", "0x").rstrip("x")
                speed    = float(speed_s) if speed_s.replace(".", "").isdigit() else 0.0
                seg_pct  = min(100.0, (frame / total_frames) * 100.0)

                if progress_cb:
                    progress_cb(seg_pct, fps_val, speed)
            except (ValueError, ZeroDivisionError):
                pass
            kv.clear()
