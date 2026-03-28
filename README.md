[![Chevren CI](https://github.com/yeggis/chevren/actions/workflows/ci.yml/badge.svg)](https://github.com/yeggis/chevren/actions/workflows/ci.yml)

<div align="center">

<img src="https://raw.githubusercontent.com/yeggis/chevren/main/docs/logo.png" alt="Chevren" width="120" />

# Chevren

**🌐 Language / Dil:**
[🇹🇷 Türkçe](#-türkçe) · [🇬🇧 English](#-english)

</div>

---

## 🇹🇷 Türkçe

<div align="center">

**YouTube videoları ve yerel ses dosyaları için**
**yerel Whisper ile konuşma tanıma + Gemini API ile Türkçe altyazı üretimi**

[![AUR](https://img.shields.io/badge/AUR-chevren-blue?logo=archlinux&logoColor=white)](https://aur.archlinux.org/packages/chevren)
[![Firefox Eklentisi](https://img.shields.io/badge/Firefox-Eklenti%20v0.1.1-orange?logo=firefox)](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.1)
[![Lisans](https://img.shields.io/badge/lisans-MIT-green)](LICENSE)
[![Sürüm](https://img.shields.io/badge/sürüm-1.0.13-brightgreen)](https://github.com/yeggis/chevren/releases)

</div>

### 🎯 Ne Yapar?

Chevren, İngilizce ses içeren YouTube videolarını ve yerel dosyaları otomatik olarak Türkçeye çeviren bir araçtır. İnternet bağlantısı gerektiren büyük bulut servislerine bağımlı kalmadan:

- 🎤 Sesi **yerel olarak** Whisper ile metne dönüştürür
- 🌍 Metni **Gemini API** aracılığıyla Türkçeye çevirir
- 📺 Altyazıyı MPV üzerinden videonun üzerine yansıtır
- 🦊 Firefox eklentisi ile YouTube'da **tek tıkla** kullanıma hazır hale gelir

### 🏗️ Mimari

```
YouTube / Yerel Dosya
       │
       ▼
  yt-dlp (ses indirme)
       │
       ▼
  FFmpeg (ses işleme)
       │
       ▼
  faster-whisper (yerel STT)   ← GPU hızlandırmalı (CUDA)
       │
       ▼
  Gemini API (TR çeviri)
       │
       ▼
  MPV (altyazılı oynatma)
       │
  Firefox Eklentisi (isteğe bağlı UI katmanı)
```

### 📦 Kurulum

#### Arch Linux / CachyOS / Manjaro (Önerilen)

```bash
# paru ile AUR'dan kur
paru -S chevren

# ya da yay ile
yay -S chevren
```

#### Manuel Kurulum

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
make install
```

#### Bağımlılıklar

| Paket | Amaç |
|---|---|
| `python` | Ana dil |
| `python-pytorch-cuda` | GPU hızlandırmalı Whisper |
| `ffmpeg` | Ses işleme |
| `yt-dlp` | YouTube indirme |
| `mpv` | Video oynatma |

### ⚙️ Yapılandırma

İlk çalıştırmadan önce Gemini API anahtarınızı ayarlayın:

```bash
# ~/.config/chevren/config dosyası oluşturulur (ilk çalıştırmada)
chevren --setup

# Ya da ortam değişkeni olarak:
export GEMINI_API_KEY="sizin-api-anahtariniz"
```

> **Not:** Gemini API anahtarını [Google AI Studio](https://aistudio.google.com/app/apikey)'dan ücretsiz alabilirsiniz.

### 🚀 Kullanım

```bash
# YouTube videosu için
chevren https://www.youtube.com/watch?v=VIDEO_ID

# Yerel dosya için
chevren /yol/dosya.mp4

# Yardım
chevren --help
```

### 🦊 Firefox Eklentisi

YouTube sayfasında "Chevren ile Çevir" butonu ekleyerek tek tıkla kullanım sağlar.

**Kurulum (v0.1.1):**

1. [Releases sayfasından](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.1) `chevren.xpi` dosyasını indirin
2. Firefox'ta `about:addons` sayfasını açın
3. Dişli ikonu → "Eklentiyi Dosyadan Yükle" → `chevren.xpi`
4. Sonraki güncellemeler **otomatik** gelecektir

### 🖥️ Sistem Gereksinimleri

- **OS:** Arch Linux tabanlı dağıtımlar (CachyOS, Manjaro, EndeavourOS…)
- **GPU:** NVIDIA (CUDA destekli) — CPU modu da çalışır, yavaştır
- **Python:** 3.10+
- **Wayland / X11:** Her ikisi de desteklenir

### 🔄 Sürüm Geçmişi

| Sürüm | Tarih | Notlar |
|---|---|---|
| v1.0.13 | 2026-03-27 | AUR kararlı sürüm, pip RECORD korunuyor |
| ext-v0.1.1 | 2026-03-27 | Otomatik güncelleme altyapısı eklendi |
| ext-v0.1.0 | 2026-03-20 | İlk yayın |

### 🤝 Katkı

Pull request'ler memnuniyetle karşılanır. Büyük değişiklikler için lütfen önce bir issue açın.

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
# Değişikliklerinizi yapın
git commit -m "feat: açıklama"
git push origin main
```

### 📄 Lisans

[MIT](LICENSE) © 2026 yeggis

---

## 🇬🇧 English

<div align="center">

**Real-time English-to-Turkish subtitle generation**
**using local Whisper STT + Gemini API translation**

[![AUR](https://img.shields.io/badge/AUR-chevren-blue?logo=archlinux&logoColor=white)](https://aur.archlinux.org/packages/chevren)
[![Firefox Extension](https://img.shields.io/badge/Firefox-Extension%20v0.1.1-orange?logo=firefox)](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.1)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.13-brightgreen)](https://github.com/yeggis/chevren/releases)

</div>

### 🎯 What Does It Do?

Chevren automatically transcribes English audio from YouTube videos and local files, then translates it into Turkish subtitles in real time — without relying on cloud-heavy services:

- 🎤 Transcribes audio **locally** via Whisper (GPU-accelerated)
- 🌍 Translates to Turkish using the **Gemini API**
- 📺 Overlays subtitles on the video via MPV
- 🦊 A Firefox extension provides **one-click** integration on YouTube

### 🏗️ Architecture

```
YouTube / Local File
       │
       ▼
  yt-dlp (audio download)
       │
       ▼
  FFmpeg (audio processing)
       │
       ▼
  faster-whisper (local STT)   ← GPU-accelerated (CUDA)
       │
       ▼
  Gemini API (TR translation)
       │
       ▼
  MPV (playback with subtitles)
       │
  Firefox Extension (optional UI layer)
```

### 📦 Installation

#### Arch Linux / CachyOS / Manjaro (Recommended)

```bash
# Install from AUR using paru
paru -S chevren

# or using yay
yay -S chevren
```

#### Manual Installation

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
make install
```

#### Dependencies

| Package | Purpose |
|---|---|
| `python` | Runtime |
| `python-pytorch-cuda` | GPU-accelerated Whisper |
| `ffmpeg` | Audio processing |
| `yt-dlp` | YouTube download |
| `mpv` | Video playback |

### ⚙️ Configuration

Set up your Gemini API key before first use:

```bash
# A config file will be created at ~/.config/chevren/config
chevren --setup

# Or set as an environment variable:
export GEMINI_API_KEY="your-api-key-here"
```

> **Note:** Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 🚀 Usage

```bash
# For a YouTube video
chevren https://www.youtube.com/watch?v=VIDEO_ID

# For a local file
chevren /path/to/file.mp4

# Help
chevren --help
```

### 🦊 Firefox Extension

Adds a "Translate with Chevren" button on YouTube pages for one-click subtitle generation.

**Installation (v0.1.1):**

1. Download `chevren.xpi` from the [Releases page](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.1)
2. Open `about:addons` in Firefox
3. Gear icon → "Install Add-on From File" → select `chevren.xpi`
4. Future updates will be delivered **automatically**

### 🖥️ System Requirements

- **OS:** Arch-based distributions (CachyOS, Manjaro, EndeavourOS…)
- **GPU:** NVIDIA (CUDA-capable) — CPU mode works but is slower
- **Python:** 3.10+
- **Display:** Wayland or X11

### 🔄 Changelog

| Version | Date | Notes |
|---|---|---|
| v1.0.13 | 2026-03-27 | Stable AUR release, pip RECORD preserved |
| ext-v0.1.1 | 2026-03-27 | Auto-update infrastructure added |
| ext-v0.1.0 | 2026-03-20 | Initial release |

### 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
# Make your changes
git commit -m "feat: description"
git push origin main
```

### 📄 License

[MIT](LICENSE) © 2026 yeggis

---

<div align="center">

Made with ❤️ for Turkish-speaking Linux users

[🐛 Bug Report](https://github.com/yeggis/chevren/issues) · [💡 Feature Request](https://github.com/yeggis/chevren/issues) · [📦 AUR Package](https://aur.archlinux.org/packages/chevren)

</div>
