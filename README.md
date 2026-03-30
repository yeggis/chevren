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
[![Sürüm](https://img.shields.io/badge/sürüm-1.0.16-brightgreen)](https://github.com/yeggis/chevren/releases)

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

#### 🚀 Evrensel Kurulum Scripti (Önerilen)

Linux (Arch/CachyOS · Debian/Ubuntu · Fedora · openSUSE) ve **Windows** desteklenir:

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

> Script, işletim sisteminizi ve dağıtımınızı otomatik algılar, uygun paket yöneticisini kullanır.

```bash
# Sadece ne yapılacağını görmek için:
python install.py --dry-run

# Sistem paketlerini atla, sadece Python bağımlılıklarını kur:
python install.py --skip-deps

# Yardım:
python install.py --help
```

> **Linux notu:** `install.sh` hâlâ geçerlidir ve Arch/Debian/Fedora/openSUSE üzerinde çalışır.

#### Arch Linux / CachyOS / Manjaro — AUR

```bash
# paru ile
paru -S chevren
# ya da yay ile
yay -S chevren
```

#### Debian / Ubuntu

```bash
sudo apt update && sudo apt install python3 ffmpeg mpv yt-dlp
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

#### Fedora

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

> RPM Fusion Free deposu ffmpeg için otomatik etkinleştirilir.

#### openSUSE

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

> **openSUSE notu:** Packman deposu ffmpeg için gerekebilir. Script kurulumu durdurmaz, uyarı verir.

#### Windows

**Seçenek A — Exe ile kurulum (Git gerekmez):**
1. [Releases](https://github.com/yeggis/chevren/releases/latest) sayfasından `install.exe` indir
2. Çift tıkla, kurulum başlar
3. Kurulum bitince Enter'a bas

> Windows Defender uyarı verebilir: "Daha fazla bilgi" → "Yine de çalıştır"

**Seçenek B — Script ile kurulum:**
```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

> `ffmpeg`, `mpv` ve `yt-dlp` otomatik olarak `winget` aracılığıyla kurulur.

#### Bağımlılıklar

| Paket | Amaç |
|---|---|
| `python` | Ana dil |
| `python-pytorch-cuda` | GPU hızlandırmalı Whisper |
| `ffmpeg` | Ses işleme |
| `yt-dlp` | YouTube indirme |
| `mpv` | Video oynatma |

### ⚙️ Yapılandırma

#### İlk Kurulum Sihirbazı

İlk çalıştırmadan önce `chevren setup` komutunu çalıştırın:

```bash
chevren setup
```

Sihirbaz sizi adım adım yönlendirir:

1. **Gemini API anahtarı** — [Google AI Studio](https://aistudio.google.com/app/apikey)'dan ücretsiz alabilirsiniz
2. **Cookie kurulumu** — YouTube'un üye içeriklerine (age-restricted, giriş gerektiren) erişim için isteğe bağlıdır; sihirbaz kullandığınız tarayıcıya göre uygun eklenti linkini gösterir

> API anahtarını doğrudan da ayarlayabilirsiniz:
> ```bash
> chevren config gemini_api_key ANAHTARINIZ
> ```

#### 🍪 Cookie Kurulumu (İsteğe Bağlı)

Bazı YouTube videoları (yaşa kısıtlı, giriş gerektiren) için tarayıcı cookie'lerinizin Chevren'e aktarılması gerekir.

**Desteklenen tarayıcılar:** Firefox, Zen, Librewolf, Vivaldi, Opera

> ⚠️ **Chrome ve Edge (Linux):** Chromium tabanlı tarayıcılarda Linux üzerinde cookie şifrelemesi (`kwallet`/`gnome-keyring`) nedeniyle cookie aktarımı şu an çalışmamaktadır. Bu tarayıcıları kullanıyorsanız aşağıdaki manuel yöntemi tercih edin.

**Yöntem 1 — `chevren setup` ile (Önerilen):**

```bash
chevren setup
```

Sihirbaz tarayıcınızı seçmenizi ister ve uygun "Get cookies.txt" eklentisinin linkini gösterir.

**Yöntem 2 — Manuel:**

1. Tarayıcınıza uygun "Get cookies.txt LOCALLY" eklentisini yükleyin
2. YouTube'da oturum açın
3. Eklenti ile `youtube.com` cookie'lerini dışa aktarın (**Netscape formatı**)
4. Dosyayı şuraya kaydedin:
   ```
   ~/.config/chevren/cookies.txt
   ```

Chevren, bu dosyayı otomatik olarak algılar ve `yt-dlp`'ye iletir.

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

- **OS:** Arch Linux / CachyOS / Manjaro · Debian / Ubuntu · Fedora · openSUSE · **Windows 10/11**
- **GPU:** NVIDIA (CUDA destekli) — CPU modu da çalışır, yavaştır
- **Python:** 3.10+
- **Wayland / X11:** Her ikisi de desteklenir

### 🔄 Sürüm Geçmişi

| Sürüm | Tarih | Notlar |
|---|---|---|
| v1.0.16 | 2026-03-30 | PKGBUILD: cargo build + systemd servis + chevren.install hooks |
| v1.0.15 | 2026-03-30 | Cookie dosyası desteği, `chevren setup` sihirbazı, DRY refactor |
| v1.0.14 | 2026-03-28 | Windows exe desteği, release.yml düzeltildi |
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
[![Version](https://img.shields.io/badge/version-1.0.16-brightgreen)](https://github.com/yeggis/chevren/releases)

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

#### 🚀 Universal Install Script (Recommended)

Supports Linux (Arch/CachyOS · Debian/Ubuntu · Fedora · openSUSE) and **Windows**:

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

> The script auto-detects your OS and distribution, then uses the appropriate package manager.

```bash
# Preview what will be installed without making changes:
python install.py --dry-run

# Skip system packages, install Python dependencies only:
python install.py --skip-deps

# Help:
python install.py --help
```

> **Linux note:** `install.sh` remains available and works on Arch/Debian/Fedora/openSUSE.

#### Arch Linux / CachyOS / Manjaro — AUR

```bash
# using paru
paru -S chevren
# or using yay
yay -S chevren
```

#### Debian / Ubuntu

```bash
sudo apt update && sudo apt install python3 ffmpeg mpv yt-dlp
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

#### Fedora

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

> RPM Fusion Free is enabled automatically for ffmpeg.

#### openSUSE

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

> **openSUSE note:** The Packman repository may be required for ffmpeg. The install script will warn but not abort.

#### Windows

**Option A — Exe installer (no Git required):**
1. Download `install.exe` from the [Releases](https://github.com/yeggis/chevren/releases/latest) page
2. Double-click to run
3. Press Enter when installation completes

> Windows Defender may show a warning: click "More info" → "Run anyway"

**Option B — Script installation:**
```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

> `ffmpeg`, `mpv`, and `yt-dlp` are installed automatically via `winget`.

#### Dependencies

| Package | Purpose |
|---|---|
| `python` | Runtime |
| `python-pytorch-cuda` | GPU-accelerated Whisper |
| `ffmpeg` | Audio processing |
| `yt-dlp` | YouTube download |
| `mpv` | Video playback |

### ⚙️ Configuration

#### First-Time Setup Wizard

Run `chevren setup` before first use:

```bash
chevren setup
```

The wizard walks you through:

1. **Gemini API key** — get one for free at [Google AI Studio](https://aistudio.google.com/app/apikey)
2. **Cookie setup** — optional, required for age-restricted or login-gated YouTube videos; the wizard shows the correct browser extension link based on your browser choice

> You can also set the API key directly:
> ```bash
> chevren config gemini_api_key YOUR_KEY
> ```

#### 🍪 Cookie Setup (Optional)

Some YouTube videos (age-restricted, login-required) need your browser cookies to be passed to Chevren.

**Supported browsers:** Firefox, Zen, Librewolf, Vivaldi, Opera

> ⚠️ **Chrome and Edge (Linux):** Cookie extraction is currently not supported on Linux for Chromium-based browsers due to keyring encryption (`kwallet`/`gnome-keyring`). Use the manual method below or switch to a supported browser.

**Method 1 — Via `chevren setup` (Recommended):**

```bash
chevren setup
```

The wizard prompts you to select your browser and links you to the appropriate "Get cookies.txt" extension.

**Method 2 — Manual:**

1. Install the "Get cookies.txt LOCALLY" extension for your browser
2. Log in to YouTube
3. Export cookies for `youtube.com` (**Netscape format**)
4. Save the file to:
   ```
   ~/.config/chevren/cookies.txt
   ```

Chevren detects this file automatically and passes it to `yt-dlp`.

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

- **OS:** Arch Linux / CachyOS / Manjaro · Debian / Ubuntu · Fedora · openSUSE · **Windows 10/11**
- **GPU:** NVIDIA (CUDA-capable) — CPU mode works but is slower
- **Python:** 3.10+
- **Display:** Wayland or X11

### 🔄 Changelog

| Version | Date | Notes |
|---|---|---|
| v1.0.16 | 2026-03-30 | PKGBUILD: cargo build + systemd service + chevren.install hooks |
| v1.0.15 | 2026-03-30 | Cookie file support, `chevren setup` wizard, DRY refactor |
| v1.0.14 | 2026-03-28 | Windows exe support, release.yml fixed |
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
