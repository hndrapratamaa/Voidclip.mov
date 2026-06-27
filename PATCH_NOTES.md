# Voidclip.mov — Patch Notes

---

## v2.1 — Watermark Band + Zoom Presisi + Auto-Preview

**Pipeline perubahan utama:**

**Zoom foreground 5% (presisi kalkulasi Python).**
Sebelumnya pakai angka piksel tetap (`740`). Sekarang dihitung eksplisit:
`lebar_output × 1.05`. Tinggi foreground juga dihitung di Python (bukan `-2` auto FFmpeg)
supaya posisi watermark band presisi ke foreground di semua rasio video sumber.

**Watermark "Voidclip.mov" di strip blur 50px, rata kiri, nempel di atas foreground.**
Berbeda dari versi lama yang nempel di pojok kanan atas frame penuh — sekarang watermark
digambar di layer background sebelum di-overlay foreground, tepat di strip blur 50px.
Posisi dihitung otomatis berdasarkan tinggi foreground.

**Font watermark auto-detect.**
`backend/config.py` sekarang punya `resolve_watermark_font()` yang nyari font Bold sistem
(Liberation/DejaVu/Droid/dll). Kalau tidak ketemu font sama sekali, watermark di-skip
secara aman.

**Audio sync (`aresample=async=1`).**
Ditambahkan balik supaya audio tetap selaras kalau ada drift kecil dari proses cut+filter.

**Auto-refresh Output Gallery.**
Galeri output di panel kanan otomatis refresh setiap 1 segmen selesai render.

**Cleanup cache real-time per-segmen.**
File cut mentah di `cache/` langsung dihapus setelah 1 segmen selesai di-render — tidak
menunggu semua segmen satu video selesai. Lebih hemat disk.

File diubah: `backend/config.py`, `backend/ffmpeg_engine.py`, `frontend/main_window.py`

---

## v2.0 — Render Pipeline 2-Tahap

Pipeline render dirancang ulang menjadi 2 tahap berdasarkan referensi script yang terbukti stabil:

**Tahap 1 — Cut (stream-copy, cepat):**
Memotong segmen dari file sumber dengan `-c:v copy -c:a copy` tanpa re-encode.
Durasi hasil divalidasi — kalau melenceng lebih dari 3 detik, otomatis retry dengan re-encode.

**Tahap 2 — Style Render (filter di klip pendek):**
Filter blur-background + sharp-foreground dijalankan di klip yang sudah dipotong pendek
(4–5 menit), bukan seek+filter langsung di file sumber panjang. Filtergraph disederhanakan
dengan pendekatan `force_original_aspect_ratio=increase`.

**Kenapa lebih stabil:**
- Seek (`-ss`) hanya terjadi di Tahap 1 yang simpel, tidak bercampur `filter_complex` kompleks
- Re-encode fallback otomatis kalau stream-copy melenceng durasi
- File temp (`cut_jobX_segY.mkv`) di `cache/` otomatis dihapus setelah Tahap 2 selesai

File diubah: `backend/ffmpeg_engine.py` (rewrite besar), `backend/video_processor.py`

---

## v1.3 — Exit Code 255 Fixed

**Bug A — Pesan error FFmpeg terpotong.**
Sebelumnya kode hanya menampilkan baris awal dari stderr. FFmpeg menulis pesan error fatal
di bagian paling akhir stderr. Sekarang menampilkan baris terakhir dari stderr.

**Bug B — `-c:s copy` tanpa subtitle stream.**
Command render selalu menambah `-map 0:s? -c:s copy` meski video tidak punya subtitle track.
FFmpeg exit fatal pada beberapa versi kalau tidak ada stream yang di-map. Sekarang
`-c:s copy` hanya dipasang kalau `info.subtitle_tracks` tidak kosong.

File diubah: `backend/ffmpeg_engine.py`, `backend/video_processor.py`

---

## v1.2 — Filtergraph Invalid Fixed

**Root cause:** `split=2[v][v]` menghasilkan dua pad dengan nama label identik (`[v]`).
FFmpeg menolak command dengan pad name duplikat dan exit error sebelum decode satu frame pun.
Itu sebabnya semua segmen gagal dalam ~1 detik masing-masing.

**Fix:** Label diganti unik (`[vbg]` dan `[vfg]`).

Bonus: stderr FFmpeg lengkap (2000 karakter terakhir) sekarang ditangkap dan ditampilkan
di terminal log kalau ada error — bukan hanya command yang dijalankan.

File diubah: `backend/ffmpeg_engine.py`, `backend/video_processor.py`

---

## v1.1 — GUI Freeze & Crash Fixed

**GUI freeze saat klik START RENDER.**
Root cause: hashing file + ffprobe + scene detection jalan di GUI thread sebelum worker
thread start. Fix: semua persiapan pindah ke background thread. Klik START langsung responsif,
button berubah ke "⏳ PREPARING…" sambil proses jalan di belakang.

**Window terlalu besar / keluar layar.**
Window sekarang dihitung dari `availableGeometry()` (exclude panel Xfce + dock Plank),
88% dari area tersedia, dan auto-center.

**ModuleNotFoundError jadi pesan jelas.**
`app.py` cek dependency sebelum start dan kasih instruksi `pip install -r requirements.txt`
kalau ada yang belum terinstall.

**Silent crash / error tidak terlacak.**
Exception yang sebelumnya ditelan (`except Exception: pass`) sekarang dicatat ke
`logs/voidclip.log`. Worker thread crash menampilkan pesan error di terminal log.

File diubah: `backend/queue_manager.py`, `backend/renderer.py`,
`frontend/main_window.py`, `frontend/render_panel.py`, `backend/config.py`, `app.py`

---

## v1.0 — Rilis Awal

- Arsitektur modular: `backend/` (engine) + `frontend/` (UI)
- FFmpeg dual-layer: background blur + foreground overlay
- Queue render multi-file dengan pause/resume/stop
- Terminal log dengan warna dan bahasa khas
- Output gallery dengan video player embedded
- Auto Upload via pyautogui (modul `frontend/auto_up/`)
- Liquid glass UI theme dark/light mode
- Desktop shortcut untuk Xubuntu XFCE + Plank
