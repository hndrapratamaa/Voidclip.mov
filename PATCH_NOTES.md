# Voidclip.mov — STEP 1.1 Patch (bug fixes + desktop shortcut)

## ✨ UPDATE (v2.1): Watermark band + zoom 5% + auto-preview

Berdasarkan `process.py` referensi dan detail yang lo jelasin:

**1. Foreground zoom 5% (presisi, bukan estimasi).**
Sebelumnya pakai angka px tetap (`740`) kayak script lama. Sekarang dihitung
persis: `lebar_output × 1.05`. Tinggi foreground juga dihitung eksplisit di
Python (bukan `-2` auto dari ffmpeg) supaya posisi watermark band bisa
presisi ke foreground, berapa pun rasio video sumbernya.

**2. Watermark "Voidclip.mov" di strip blur 50px, rata kiri, NEMPEL di atas foreground.**
Beda dari script lama yang nempel di pojok kanan atas FRAME PENUH —
sekarang watermark digambar di layer background (sebelum di-overlay sama
foreground), persis di tengah strip blur 50px tepat sebelum foreground
mulai. Posisinya dihitung otomatis berdasarkan tinggi foreground, jadi
selalu nempel pas di manapun foreground itu jatuh (tested di beberapa
rasio: 16:9, portrait, ultra-wide — semua aman, termasuk kasus tepi kalau
foreground penuh nutup frame).

**3. Font watermark auto-detect.**
`backend/config.py` sekarang punya `resolve_watermark_font()` yang nyari
font Bold sistem (Liberation/DejaVu/Droid/dll, persis daftar dari
referensi). Kalau nggak ketemu font sama sekali, watermark di-skip secara
aman (bukan bikin command ffmpeg invalid).

**4. Audio sync (`aresample=async=1`).**
Ditambahkan balik sesuai pola referensi, supaya audio tetap selaras kalau
ada drift kecil dari proses cut+filter.

**5. Auto-refresh Output Gallery.**
Sebelumnya galeri output (preview) di kanan cuma update kalau klik tombol
↻ manual. Sekarang otomatis refresh setiap 1 segmen selesai render — jadi
hasil baru langsung muncul di preview tanpa perlu klik apa-apa.

**6. Cleanup folder temp — tetap real-time per-segmen** (sesuai keputusan
lo): begitu 1 segmen selesai di-style-render, file cut mentahnya langsung
dihapus dari `cache/` — bukan nunggu semua segmen 1 video kelar dulu. Ini
lebih hemat disk space dibanding pola `process.py` lama.

File yang diubah: `backend/config.py`, `backend/ffmpeg_engine.py`,
`frontend/main_window.py`.

---

## UPDATE (v2.0): Render pipeline diredesign jadi 2 tahap

Berdasarkan referensi script lama lo yang terbukti stabil, render pipeline
sekarang dipecah jadi 2 tahap, bukan satu command FFmpeg raksasa:

**Tahap 1 — Cut (stream-copy, cepat):**
Motong segmen dari file sumber pakai `-c:v copy -c:a copy` (tanpa
re-encode, hampir instan). Durasi hasil potongan divalidasi — kalau
melenceng lebih dari 3 detik dari target (karena keyframe alignment di
video panjang), otomatis di-retry dengan re-encode supaya presisi.

**Tahap 2 — Style render (filter di clip pendek):**
Filter blur-background + sharp-foreground sekarang dijalankan di clip yang
SUDAH dipotong pendek (4-5 menit), bukan langsung seek+filter di file
sumber 1+ jam. Filtergraph-nya juga disederhanakan mengikuti pendekatan
`force_original_aspect_ratio=increase` dari referensi — lebih sedikit
kemungkinan bug dibanding split-label approach sebelumnya.

**Kenapa ini lebih stabil:**
- Seek (`-ss`) sekarang hanya terjadi di Tahap 1 yang simpel (stream-copy),
  tidak lagi bercampur dengan filter_complex yang kompleks dalam satu
  command — mengurangi permukaan untuk exit-code 255 jenis apapun.
- Re-encode fallback otomatis kalau stream-copy melenceng durasi.
- File temporary (`cut_jobX_segY.mp4`) disimpan di folder `cache/` dan
  otomatis dihapus setelah Tahap 2 selesai (berhasil ATAU gagal).

**Catatan:** subtitle burn-in (`subtitle_mode = "burn"`) masih didukung di
Tahap 2. Mode "keep" (copy subtitle stream asli) untuk sementara
dinonaktifkan di pipeline baru ini — kalau video lo butuh subtitle asli
dipertahankan, kabari saya supaya saya tambahkan lagi di Tahap 1.

File yang diubah: `backend/ffmpeg_engine.py` (rewrite besar),
`backend/video_processor.py`.

---

## UPDATE (v1.3): Exit code 255 untuk SEMUA segmen — FIXED

Dua bug ditemukan dari log terakhir:

**Bug A — Pesan error FFmpeg yang sebenarnya ke-potong.**
Sebelumnya kode cuma nampilin baris 1–19 dari ekor stderr. FFmpeg selalu
nulis info stream input duluan, baru pesan error fatal-nya di paling
**akhir** — jadi yang muncul di log cuma info video (`Stream #0:0...`),
sedangkan baris error sebenarnya kepotong. Sekarang kode nampilin baris
**terakhir** (bukan pertama) dari detail error, jadi pesan error sungguhan
sekarang kebaca.

**Bug B — `-c:s copy` tanpa subtitle stream apapun.**
Ini akar masalah exit code 255-nya. Command render selalu nambahin
`-map 0:s? -c:s copy` kalau subtitle_mode = "keep" (default), TANPA cek
apakah videonya benar-benar punya subtitle track. File "Teach You a
Lesson - S1 E4.mp4" cuma punya 1 video stream, nol subtitle — dan
`-c:s copy` tanpa stream subtitle yang ke-map bikin FFmpeg exit fatal di
beberapa versi. Sekarang `-c:s copy` cuma dipasang kalau `info.subtitle_tracks`
benar-benar tidak kosong.

File yang diubah: `backend/ffmpeg_engine.py`, `backend/video_processor.py`.

---

## UPDATE (v1.2): Render gagal instan untuk SEMUA segmen — FIXED

**Root cause:** Filtergraph FFmpeg punya bug — `split=2[v][v]` ngasih nama
label yang **sama** (`[v]`) ke dua output stream. FFmpeg nggak terima dua
pad dengan nama identik, jadi langsung reject command-nya dan exit error
**sebelum sempat decode/encode 1 frame pun**. Itu kenapa semua 16 segmen
gagal dalam waktu ~1 detik masing-masing — bukan masalah file video atau
performa, tapi command FFmpeg-nya invalid dari awal.

Fix: label di-rename jadi unik (`[vbg]` dan `[vfg]`).

Sekalian dibenerin: sebelumnya pesan error di log cuma nunjukin command
yang dijalankan, stderr asli dari FFmpeg (yang sebenarnya nyimpen alasan
gagalnya) ke-swallow karena `str(CalledProcessError)` secara default tidak
menyertakan stderr. Sekarang stderr FFmpeg lengkap (sampai 2000 karakter
terakhir) ditangkap dan ditampilkan di terminal log kalau ada error lagi
ke depannya — jadi kalau ada masalah baru, pesannya bakal jelas, bukan
kepotong di command doang.

File yang diubah: `backend/ffmpeg_engine.py`, `backend/video_processor.py`.

---

## Apa yang diperbaiki (v1.1)

### 1. 🔴 GUI freeze saat klik "START RENDER" (FIXED)
**Root cause:** Sebelumnya, hashing file + `ffprobe` + scene-detection (full
decode pass, bisa sampai 2 menit per video) jalan **langsung di GUI thread**
sebelum render worker thread sempat start. Makin banyak video yang dipilih,
makin lama GUI-nya freeze total — button kelihatan "ngga ada perubahan",
terminal log kosong, karena Qt event loop-nya keblok.

**Fix:** Semua proses persiapan (hash, probe, scene-detect) sekarang jalan
**di background thread**, bukan di GUI thread. Klik "START RENDER" langsung
balik instan, lalu button berubah jadi "⏳ PREPARING…" sambil proses jalan
di belakang. Status terminal log juga langsung muncul real-time.

File yang diubah: `backend/queue_manager.py`, `backend/renderer.py`,
`frontend/main_window.py`, `frontend/render_panel.py`.

### 2. Window kebesaran / kebawah layar (FIXED — applied properly this time)
Window sekarang dihitung dari `availableGeometry()` layar (otomatis exclude
panel Xfce + dock Plank), pakai 88% dari area itu, dan auto-center.

File: `backend/config.py`, `frontend/main_window.py`.

### 3. Error `ModuleNotFoundError` jadi pesan jelas (FIXED — applied properly)
`app.py` sekarang cek dependency dulu sebelum start, kasih instruksi
`pip install -r requirements.txt` kalau ada yang belum terinstall, daripada
traceback panjang yang membingungkan.

### 4. Silent crash / unexplained errors (FIXED)
Sebelumnya ada beberapa `except Exception: pass` yang nelan error tanpa
jejak — termasuk di callback log/state. Sekarang semua exception dicatat ke
`logs/voidclip.log`, dan kalau worker thread crash karena bug tak terduga,
GUI akan menampilkan pesan error di terminal log, bukan diam saja.

## Setup awal (sekali saja)

```bash
cd Voidclip.mov
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x run.sh
```

## Bikin shortcut/launcher di Xubuntu (XFCE) + Plank

1. **Sesuaikan path** di dua file ini kalau folder project lo bukan di
   `/home/hndrapratamaa/Voidclip.mov`:
   - `run.sh` (otomatis detect lokasinya sendiri, biasanya tidak perlu diubah)
   - `Voidclip.desktop` → ubah baris `Exec=` dan `Path=`

2. **Install launcher ke menu aplikasi:**
   ```bash
   mkdir -p ~/.local/share/applications
   cp Voidclip.desktop ~/.local/share/applications/
   chmod +x ~/.local/share/applications/Voidclip.desktop
   ```
   Setelah ini, "Voidclip.mov" akan muncul di app menu Whisker Menu dan bisa
   dicari lewat search.

3. **Pin ke Plank:**
   - Buka app menu, cari "Voidclip.mov"
   - Klik kanan ikonnya di Plank setelah dijalankan sekali → "Keep in Dock"

   Atau drag langsung file `~/.local/share/applications/Voidclip.desktop` ke
   Plank dock.

4. Kalau ikon muncul generic/blank, itu karena belum ada custom icon — app
   masih pakai ikon sistem `video-x-generic`. Tinggal taruh file `icon.png`
   di `assets/icons/` dan update baris `Icon=` di `Voidclip.desktop` dengan
   path absolut ke file itu kalau mau ikon custom.

## Testing setelah update

```bash
source .venv/bin/activate
python app.py
```

Pilih beberapa video di sidebar kiri → klik START RENDER. Sekarang harus
**langsung responsif** (button berubah jadi "PREPARING…" instan), dan log
terminal mulai muncul detik itu juga — bukan freeze diam selama beberapa
menit seperti sebelumnya.
