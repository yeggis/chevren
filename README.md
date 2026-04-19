[![Chevren CI](https://github.com/yeggis/chevren/actions/workflows/ci.yml/badge.svg)](https://github.com/yeggis/chevren/actions/workflows/ci.yml)

<div align="center">
<img src="https://raw.githubusercontent.com/yeggis/chevren/main/docs/logo.png" alt="Chevren" width="120" />

# Chevren

**Local Whisper transcription + Gemini API translation → Turkish subtitles**

[![AUR](https://img.shields.io/badge/AUR-chevren-blue?logo=archlinux&logoColor=white)](https://aur.archlinux.org/packages/chevren)
[![Firefox Extension](https://img.shields.io/badge/Firefox-Extension%20v0.1.2-orange?logo=firefox)](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.2)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.19-brightgreen)](https://github.com/yeggis/chevren/releases)

🇹🇷 [Türkçe README](README-tr.md)

</div>

---

## What Does It Do?

Chevren watches a YouTube video or local file, transcribes the audio locally with Whisper, translates each segment to Turkish via the Gemini API, and overlays the subtitles in real time — no cloud STT, no mandatory accounts beyond a free Gemini key.

- 🎤 **Local transcription** via faster-whisper (GPU-accelerated with CUDA)
- 🌍 **Translation** via Gemini API (streaming, chunk-by-chunk)
- 📺 **Playback** in MPV with live subtitle injection
- 狐 **Firefox extension** — one-click subtitle generation on YouTube, with an inline status strip and overlay renderer built into the page
- 🌐 **Multilingual support** — TR/EN language toggle; transcript and translation cached separately

---

## Architecture

```
YouTube URL / Local File
         │
         ▼
   yt-dlp  ──►  ffmpeg  ──►  faster-whisper (local STT, CUDA)
                                      │
                              segments (generator, lazy)
                                      │
                              Gemini API  ←─ multi-key pool
                              (chunked translation, streaming)
                                      │
                              SRT written incrementally
                              (en.srt transcript, tr.srt translation)
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                  MPV (sub-file)           Firefox Extension
                  live sub-reload          glassmorphism overlay
                         │                language toggle (TR/EN)
                  chevren-server (Rust/Axum)
                  HTTP :7373 — pipeline status,
                  subtitle reload, MPV IPC bridge,
                  cancel endpoint
```


The Rust server is a lightweight local HTTP daemon. The Python pipeline reports its progress to the server via `POST /pipeline/status`; the extension polls `GET /status` to drive the UI.

---

## Installation

### Arch Linux / CachyOS / Manjaro — AUR

```bash
paru -S chevren
# or
yay -S chevren
```

### Other Linux distributions

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

The install script supports Debian/Ubuntu, Fedora, and openSUSE. It auto-detects your distribution and uses the appropriate package manager.

```bash
python install.py --dry-run    # preview without making changes
python install.py --skip-deps  # Python deps only, skip system packages
python install.py --help
```

> `install.sh` also remains available for shell-only environments.

### Dependencies

| Package | Purpose |
|---|---|
| `python` ≥ 3.10 | Runtime |
| `python-pytorch-cuda` | GPU-accelerated Whisper |
| `ffmpeg` | Audio extraction |
| `yt-dlp` | YouTube download |
| `mpv` | Video playback |

Python dependencies (`faster-whisper`, `google-genai`, `prompt-toolkit`, …) are listed in `requirements.txt` and managed through `pyproject.toml`.

---

## First-Time Setup

```bash
chevren setup
```

An interactive TUI wizard (arrow-key navigation) walks you through:

1. **Gemini API keys** — add one or more keys; Chevren rotates between them automatically when a quota limit is hit. Free keys available at [Google AI Studio](https://aistudio.google.com/app/apikey).
2. **Whisper model** — auto-recommended based on detected VRAM. Options range from `tiny` to `large-v3-turbo`.
3. **Primary Gemini model** — defaults to `gemini-2.5-flash-lite`; fallback chain is configurable.
4. **Player** — MPV is the default and the only fully supported option.
5. **Cookie setup** — optional, needed for age-restricted or login-gated YouTube videos.

You can also set individual values directly:

```bash
chevren config gemini_api_key YOUR_KEY
chevren config whisper_model large-v3-turbo
```

---

## Cookie Setup (Optional)

Needed for age-restricted or members-only videos. Chevren checks for cookies in this order:

1. `~/.config/chevren/cookies.txt` (Netscape format) — exported manually via a browser extension
2. `browser` config key — e.g. `chevren config browser firefox`
3. Zen Browser auto-detection (largest profile by cookies.sqlite size)
4. Firefox / Librewolf auto-detection

**Supported for auto-detection:** Firefox, Zen Browser, Librewolf.

> ⚠️ Chrome/Edge on Linux: keyring encryption (`kwallet`/`gnome-keyring`) prevents automatic cookie extraction. Export manually and place the file at `~/.config/chevren/cookies.txt`.

---

## Usage

```bash
chevren https://www.youtube.com/watch?v=VIDEO_ID   # YouTube
chevren /path/to/file.mp4                          # local file
chevren --no-play https://...                      # generate SRT only
chevren cache list                                 # show cached subtitles
chevren cache clear                                # clear cache
chevren --help
```

Subtitles are cached under `~/.cache/chevren/<video_id>/` as `en.srt` (transcript) and `tr.srt` (translation). Re-running the same URL serves from cache instantly.

---

## Browser Extension

Adds a status strip below the YouTube video title and an ▶ button in the player controls to open the video in MPV.

**Firefox (recommended) — Install via AMO (v0.1.2):**
1. Download `chevren.xpi` from the [Releases page](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.2)
2. Open `about:addons` in Firefox
3. Gear icon → "Install Add-on From File" → select `chevren.xpi`

**Chromium-based browsers (Chrome, Edge, Brave) — manual install:**
1. Download and unzip the extension from the [Releases page](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.2)
2. Open `chrome://extensions` → enable "Developer mode"
3. "Load unpacked" → select the unzipped folder

> ⚠️ Chromium-based browsers work but do not receive automatic updates — manual reinstall required on each update.

**What the strip does:**
- Idle → click to start subtitle generation
- Downloading / Transcribing / Translating → animated progress bar with stage label
- Ready → click to toggle the in-page overlay; subtitles render over the YouTube player in sync with playback
- The overlay updates live as new translation chunks arrive
- **Settings panel (⚙ Ayarlar):** language toggle (TR/EN), open in MPV, cancel active pipeline, delete cached subtitles
- **Overlay controls:** drag to reposition, scroll to resize text, double-click to reset position, Alt+C to toggle
- The overlay uses a glassmorphism design and adjusts position automatically when YouTube controls appear or hide

The extension popup shows server status, active pipeline stage, and a scrollable log. A restart button (↺) sends `POST /restart` to the local server, which exits with code 1 and is restarted by systemd (`Restart=on-failure`).

---

## Multi-Key & Model Fallback

Chevren supports multiple Gemini API keys. When a `429 RESOURCE_EXHAUSTED` response is received, it rotates to the next available key for the same model. If all keys for that model are exhausted, it falls back through this chain:

```
gemini-2.5-flash → gemini-2.5-flash-lite → gemini-3.1-flash-lite-preview → gemini-3-flash-preview
```

No chunk is ever silently dropped; if every key and model is exhausted, the chunk is left in English.

---

## System Requirements

- **OS:** Linux (Arch-based, Debian/Ubuntu, Fedora, openSUSE)
- **GPU:** NVIDIA with CUDA — CPU mode works but is significantly slower
- **Python:** 3.10+
- **Display:** Wayland or X11

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first.

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
# make your changes
git commit -m "feat: description"
git pull --rebase origin main
git push
```

---

## License

[MIT](LICENSE) © 2026 yeggis

<div align="center">

[🐛 Bug Report](https://github.com/yeggis/chevren/issues) · [💡 Feature Request](https://github.com/yeggis/chevren/issues) · [📦 AUR Package](https://aur.archlinux.org/packages/chevren)

</div>
