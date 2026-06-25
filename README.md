# Voidclip.mov

Automated video processing workstation. Converts long-form video (films, series, documentaries) into portrait short-form clips ready for TikTok, Instagram Reels, and YouTube Shorts.

## Quick Start

```bash
# 1. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install FFmpeg (system-level)
# macOS:   brew install ffmpeg
# Ubuntu:  sudo apt install ffmpeg
# Windows: https://ffmpeg.org/download.html

# 4. Run
python app.py
```

## Project Structure
```
Voidclip.mov/
├── app.py                  ← Entry point
├── backend/
│   ├── config.py           ← All constants, paths, presets
│   ├── logger.py           ← Rotating file + coloured console log
│   ├── database.py         ← SQLite CRUD, schema, crash recovery
│   ├── ffmpeg_engine.py    ← FFmpeg probe, filtergraph, render
│   ├── segment_manager.py  ← Segment planning + scene detection
│   ├── video_processor.py  ← High-level orchestration
│   ├── queue_manager.py    ← Thread-safe render queue
│   └── renderer.py         ← Facade used by GUI
├── frontend/
│   ├── main_window.py      ← Root window, 3-panel layout
│   ├── sidebar_left.py     ← Input video manager
│   ├── render_panel.py     ← Live monitor + control buttons
│   ├── sidebar_right.py    ← Output gallery + video player
│   ├── settings.py         ← Preset & hashtag settings dialog
│   └── widgets/            ← Reusable custom widgets
├── assets/themes/dark.qss  ← Glassmorphism dark theme
├── input/                  ← Drop source videos here
├── output/                 ← Rendered segments appear here
└── database/voidclip.db    ← SQLite (auto-created)
```
