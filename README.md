<div align="center">

# Voidclip.mov

**Automated Video Processing Workstation**

*Ngedit video kagak ribet, cuy!*

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.7+-41CD52?style=flat-square&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-required-007808?style=flat-square&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-informational?style=flat-square)](https://github.com/hndrapratamaa/Voidclip.mov)

Konversi otomatis video panjang (film, series, dokumenter) jadi klip portrait 9:16 yang siap upload ke TikTok, Instagram Reels, dan YouTube Shorts — tanpa encode ulang manual, satu klik langsung beres.

</div>

---

## Fitur Utama

- **Render Pipeline 2-Tahap** — stream-copy cut (cepat, tanpa re-encode) → style render di klip pendek
- **Dual-layer filtergraph** — background blur 1080×1920 + foreground zoom 5% + watermark otomatis
- **Auto Segmentasi** — potong 4–5 menit per part, acak presisi per-video (tidak random asal)
- **Render Queue** — proses banyak episode sekaligus, pause/resume/stop real-time
- **Auto Upload** — pyautogui script buat nge-upload hasil ke TikTok otomatis (via `Auto Up`)
- **Terminal Log** — log terminal bergaya dengan warna dan bahasa Depok
- **Dark / Light Mode** — liquid glass UI, toggle di topbar
- **Desktop Shortcut** — launcher `.desktop` buat Xubuntu XFCE + Plank, tanpa buka terminal

---

## Quick Start

```bash
# 1. Clone repo
git clone https://github.com/hndrapratamaa/Voidclip.mov.git
cd Voidclip.mov

# 2. Install FFmpeg (wajib, sistem-level)
sudo apt install ffmpeg          # Ubuntu/Debian/Xubuntu
# brew install ffmpeg            # macOS

# 3. Buat virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 4. Install dependencies Python
pip install -r requirements.txt

# 5. Jalankan
python app.py
# atau langsung:
./run.sh
```

---

## Cara Pakai

1. **Import video** — klik `⬇ IMPORT` di panel kiri, pilih file sumber (`.mp4`, `.mkv`, dll.)
2. **Pilih video** — klik nama file di daftar
3. **Klik `▶ MULAI RENDER`** — sistem otomatis potong, render, dan simpan hasil
4. **Preview** — double-klik file hasil di panel kanan untuk putar langsung
5. **Auto Upload** — klik `⬆ AUTO UP`, atur deskripsi & hashtag, klik Start Script

Hasil tersimpan di folder `output/` dengan struktur:

```
output/
└── Nama Episode/
    ├── Nama Episode | Part 001.mp4
    ├── Nama Episode | Part 002.mp4
    └── ...
```

---

## Struktur Proyek

```
Voidclip.mov/
├── app.py                          ← Entry point utama
├── run.sh                          ← Launcher shell (untuk .desktop shortcut)
├── Voidclip.desktop                ← Shortcut app (Xubuntu XFCE / Plank)
├── requirements.txt
│
├── backend/
│   ├── config.py                   ← Semua konstanta, path, render preset
│   ├── logger.py                   ← Setup logging (file rotate + console)
│   ├── lang_id.py                  ← Semua string UI (Bahasa Indonesia/Depok)
│   ├── ffmpeg_engine.py            ← Pipeline FFmpeg: probe, cut, filtergraph, encode
│   ├── queue_manager.py            ← In-memory job queue, state machine render
│   ├── renderer.py                 ← Facade utama yang dipanggil GUI
│   ├── video_processor.py          ← ProcessorPool: background worker thread
│   ├── template_store.py           ← Penyimpanan hashtag template (JSON)
│   ├── autoup_config.py            ← Konfigurasi koordinat Auto Upload
│   └── database.py                 ← No-op shim (arsitektur sudah full RAM+JSON)
│
├── frontend/
│   ├── main_window.py              ← Jendela utama, layout, signal wiring
│   ├── render_panel.py             ← Stat boxes, progress bar, tombol kontrol
│   ├── sidebar_left.py             ← Manajemen video input
│   ├── sidebar_right.py            ← Output gallery + video player (QTreeView)
│   ├── theme.py                    ← Liquid glass QSS, dark/light mode
│   ├── settings.py                 ← Dialog render preset & subtitle mode
│   ├── about_dialog.py             ← Dialog info aplikasi
│   ├── mini_window.py              ← Floating mini window (legacy)
│   ├── controller.py               ← AutoUpController (koordinasi worker + UI)
│   ├── worker.py                   ← AutoUpWorker (QThread pyautogui)
│   ├── widgets/
│   │   ├── terminal_log.py         ← Terminal custom: warna, blink cursor, depokin()
│   │   └── icon_button.py          ← IconButton & IconButtonGroup reusable
│   └── auto_up/
│       ├── controller.py           ← AutoUp controller (versi modular)
│       ├── worker.py               ← AutoUp worker thread
│       └── mini_window.py          ← Floating window Auto Upload
│
├── assets/
│   ├── icons/                      ← Icon app (SVG, PNG 48px, 128px, 256px)
│   └── themes/                     ← dark.qss (legacy, sekarang via theme.py)
│
├── input/                          ← Taruh video sumber di sini [tidak di-push]
├── output/                         ← Hasil render [tidak di-push]
├── cache/                          ← File temp cut sementara [tidak di-push]
└── logs/                           ← Log aplikasi [tidak di-push]
```

---

## Pipeline Render

```
Video Sumber (.mp4 / .mkv / dll.)
        │
        ▼
  [ Probe & Planning ]
  ffprobe → durasi, resolusi, fps
  plan_segments() → potong acak 4–5 menit per part
        │
        ▼ (per segmen)
  [ Tahap 1: Stream-Copy Cut ]          ← cepat, tanpa re-encode
  ffmpeg -ss START -t DUR -c copy → cache/cut_jobX_segY.mkv
        │
        ▼
  [ Tahap 2: Style Render ]
  filter_complex:
    [input] → scale 1080×1920 (cover) → boxblur(20) → watermark → [bg]
    [input] → scale fit → zoom 5% → crop center               → [fg]
    [bg][fg] → overlay center                                  → [out]
        │
        ▼
  output/NamaEpisode/NamaEpisode | Part 001.mp4
        │
  cache/cut_*.mkv otomatis dihapus setelah encode selesai
```

---

## Render Preset

| Preset | Codec | CRF | Keterangan |
|---|---|---|---|
| H264 — Fast (CRF 23) | libx264 | 23 | Default, cepat, ukuran wajar |
| H264 — Quality (CRF 18) | libx264 | 18 | Kualitas tinggi, lebih besar |
| H265 — Efficient (CRF 24) | libx265 | 24 | Hemat ukuran |
| H265 — Quality (CRF 20) | libx265 | 20 | Kualitas max, encode lambat |
| VP9 — Web (CQ 30) | libvpx-vp9 | 30 | Output `.webm`, cocok web |

---

## Shortcut Desktop (Xubuntu XFCE + Plank)

```bash
# Install launcher ke menu aplikasi
cp Voidclip.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/Voidclip.desktop

# Update database menu (optional)
update-desktop-database ~/.local/share/applications/
```

Setelah itu:
- Cari "Voidclip.mov" di Whisker Menu
- Klik kanan ikon di Plank setelah dijalankan → **Keep in Dock**

Atau drag file `~/.local/share/applications/Voidclip.desktop` langsung ke Plank.

---

## Auto Upload (Auto Up)

Fitur opsional yang menggunakan `pyautogui` untuk otomatisasi klik upload ke TikTok Studio.

```bash
pip install pyautogui pyperclip
```

**Cara pakai:**
1. Buka folder episode hasil render via tombol `📂 SET FOLDER EPISODE`
2. Klik `⬆ AUTO UP` — jendela floating Aciona muncul
3. Isi deskripsi & hashtag di notepad
4. Klik `Start Script` — aplikasi otomatis klik-klik upload satu per satu

> **Catatan:** Koordinat klik (`autoup_config.py`) dikalibrasi untuk resolusi dan browser layout tertentu. Sesuaikan `COORD_*` di `backend/autoup_config.py` kalau posisi tombol di browser lo berbeda.

---

## Dependencies

```
PySide6>=6.7.0          # GUI framework
opencv-python>=4.10.0   # Image processing
av>=13.0.0              # PyAV (FFmpeg Python bindings)
psutil>=6.0.0           # System monitoring
send2trash>=1.8.3       # Safe file deletion
Pillow>=10.4.0          # Thumbnail utils
xxhash>=3.4.1           # File hashing cepat
colorlog>=6.8.2         # Colored console log

# Opsional (Auto Upload)
pyautogui               # Otomatisasi klik
pyperclip               # Clipboard paste
```

---

## Kontribusi & Kontak

- GitHub: [@hndrapratamaa](https://github.com/hndrapratamaa)
- Repo: [github.com/hndrapratamaa/Voidclip.mov](https://github.com/hndrapratamaa/Voidclip.mov)
- Issues: [laporin bug di sini](https://github.com/hndrapratamaa/Voidclip.mov/issues)
- Traktir bos: [paypal.me/hndrapratamaa](https://paypal.me/hndrapratamaa)

---

## License

MIT License — bebas pakai, modifikasi, dan distribusi. Gratis selamanya blay.
