"""
backend/__init__.py
===================
Paket backend Voidclip — video processing pipeline stateless berbasis FFmpeg.
"""

from backend.config import (
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
    DEFAULT_PRESET_NAME,
    DEFAULT_WATERMARK_CONFIG,
    DEFAULT_ZOOM_CONFIG,
    INPUT_DIR,
    OUTPUT_DIR,
    CACHE_DIR,
    RENDER_PRESETS,
    RenderPreset,
    WatermarkConfig,
    ZoomConfig,
)
from backend.ffmpeg_engine import (
    VideoInfo,
    find_ffmpeg,
    find_ffprobe,
    probe_video,
    render_segment,
    detect_available_hwaccel,
)
from backend.video_processor import (
    JobSpec,
    SegmentSpec,
    SegmentProgress,
    prepare_job,
    run_job,
)
from backend.renderer import (
    RenderRequest,
    RenderController,
    RenderControllerQt,
    create_controller,
    run_blocking,
)

__all__ = [
    # config
    "CANVAS_WIDTH", "CANVAS_HEIGHT",
    "DEFAULT_PRESET_NAME", "DEFAULT_WATERMARK_CONFIG", "DEFAULT_ZOOM_CONFIG",
    "INPUT_DIR", "OUTPUT_DIR", "CACHE_DIR",
    "RENDER_PRESETS", "RenderPreset", "WatermarkConfig", "ZoomConfig",
    # ffmpeg_engine
    "VideoInfo", "find_ffmpeg", "find_ffprobe", "probe_video",
    "render_segment", "detect_available_hwaccel",
    # video_processor
    "JobSpec", "SegmentSpec", "SegmentProgress", "prepare_job", "run_job",
    # renderer
    "RenderRequest", "RenderController", "RenderControllerQt",
    "create_controller", "run_blocking",
]
