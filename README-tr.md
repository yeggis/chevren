<div align="center">
<img src="https://raw.githubusercontent.com/yeggis/chevren/main/docs/logo.png" alt="Chevren" width="120" />

# Chevren

**Yerel Whisper transkripsiyon + Gemini API çevirisi → Türkçe altyazı**

[![AUR](https://img.shields.io/badge/AUR-chevren-blue?logo=archlinux&logoColor=white)](https://aur.archlinux.org/packages/chevren)
[![Firefox Eklentisi](https://img.shields.io/badge/Firefox-Eklenti%20v0.1.4-orange?logo=firefox)](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.4)
[![Lisans](https://img.shields.io/badge/lisans-MIT-green)](LICENSE)
[![Sürüm](https://img.shields.io/badge/sürüm-1.0.20-brightgreen)](https://github.com/yeggis/chevren/releases)

🇬🇧 [English README](README.md)

</div>

---

## Ne Yapar?

Chevren, bir YouTube videosu veya yerel dosyayı izlerken sesi yerel olarak Whisper ile metne dönüştürür, Gemini API aracılığıyla Türkçeye çevirir ve altyazıları gerçek zamanlı olarak ekranda gösterir. Bulut tabanlı konuşma tanıma servisi gerektirmez; yalnızca ücretsiz bir Gemini API anahtarı yeterlidir.

- 🎤 **Yerel transkripsiyon** — faster-whisper ile (CUDA destekli GPU hızlandırma)
- 🌍 **Çeviri** — Gemini API üzerinden (parça parça, streaming)
- 📺 **Oynatma** — MPV'de canlı altyazı enjeksiyonu
- 🦊 **Firefox eklentisi** — YouTube'da tek tıkla altyazı oluşturma; sayfa içi durum göstergesi ve overlay renderer
- 🌐 **Çok dilli destek** — TR/EN dil değiştirme; transkript ve çeviri ayrı önbellek dosyalarında

---

## Mimari

```
YouTube URL / Yerel Dosya
         │
         ▼
   yt-dlp  ──►  ffmpeg  ──►  faster-whisper (yerel STT, CUDA)
                                      │
                              segmentler (generator, lazy)
                                      │
                              Gemini API  ←─ çoklu key havuzu
                              (parça parça çeviri, streaming)
                                      │
                              SRT dosyasına anlık yazma
                              (en.srt transkript, tr.srt çeviri)
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                  MPV (sub-file)           Firefox Eklentisi
                  canlı altyazı yenileme   glassmorphism overlay
                         │                dil değiştirme (TR/EN)
                  chevren-server (Rust/Axum)
                  HTTP :7373 — pipeline durumu,
                  altyazı yenileme, MPV IPC köprüsü,
                  iptal endpoint'i
```

Rust sunucusu hafif bir yerel HTTP daemon'dur. Python pipeline'ı ilerleme durumunu `POST /pipeline/status` ile sunucuya bildirir; eklenti `GET /status`'u poll ederek arayüzü günceller.

---

## Kurulum

### Arch Linux / CachyOS / Manjaro — AUR

```bash
paru -S chevren
# ya da
yay -S chevren
```

### Diğer Linux dağıtımları

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
python install.py
```

Kurulum scripti Debian/Ubuntu, Fedora ve openSUSE'yi destekler. Dağıtımınızı otomatik algılar ve uygun paket yöneticisini kullanır.

```bash
python install.py --dry-run    # değişiklik yapmadan önizle
python install.py --skip-deps  # sadece Python bağımlılıkları, sistem paketlerini atla
python install.py --help
```

> Shell tabanlı ortamlar için `install.sh` de kullanılabilir.

### Bağımlılıklar

| Paket | Amaç |
|---|---|
| `python` ≥ 3.10 | Çalışma ortamı |
| `python-pytorch-cuda` | GPU hızlandırmalı Whisper |
| `ffmpeg` | Ses çıkarma |
| `yt-dlp` | YouTube indirme |
| `mpv` | Video oynatma |

Python bağımlılıkları (`faster-whisper`, `google-genai`, `prompt-toolkit` vb.) `requirements.txt` ve `pyproject.toml` üzerinden yönetilir.

---

## İlk Kurulum

```bash
chevren setup
```

Ok tuşu ile gezilen etkileşimli bir kurulum sihirbazı aşağıdaki adımları yönlendirir:

1. **Gemini API anahtarları** — bir veya birden fazla key ekleyin; kota dolunca Chevren otomatik olarak diğerine geçer. Ücretsiz key: [Google AI Studio](https://aistudio.google.com/app/apikey)
2. **Whisper modeli** — algılanan VRAM'e göre otomatik önerilir. `tiny`'den `large-v3-turbo`'ya kadar seçenek vardır.
3. **Ana Gemini modeli** — varsayılan `gemini-2.5-flash-lite`; fallback zinciri yapılandırılabilir.
4. **Oynatıcı** — MPV varsayılan ve tam desteklenen tek seçenektir.
5. **Cookie kurulumu** — opsiyonel, yaş kısıtlı veya üye içerikli videolar için gereklidir.

Bireysel ayarları doğrudan da değiştirebilirsiniz:

```bash
chevren config gemini_api_key ANAHTARINIZ
chevren config whisper_model large-v3-turbo
```

---

## Cookie Kurulumu (Opsiyonel)

Yaş kısıtlı veya üyelik gerektiren videolar için gereklidir. Chevren cookie kaynağını şu sırayla arar:

1. `~/.config/chevren/cookies.txt` (Netscape formatı) — tarayıcı eklentisiyle manuel dışa aktarılmış
2. `browser` config anahtarı — örn. `chevren config browser firefox`
3. Zen Browser otomatik algılama (en büyük profile göre)
4. Firefox / Librewolf otomatik algılama

**Otomatik desteklenen tarayıcılar:** Firefox, Zen Browser, Librewolf

> ⚠️ Linux'ta Chrome/Edge: keyring şifrelemesi (`kwallet`/`gnome-keyring`) otomatik cookie çıkarmayı engeller. Dosyayı manuel dışa aktarıp `~/.config/chevren/cookies.txt` konumuna yerleştirin.

---

## Kullanım

```bash
chevren https://www.youtube.com/watch?v=VIDEO_ID   # YouTube
chevren /yol/dosya.mp4                             # yerel dosya
chevren --no-play https://...                      # sadece SRT üret
chevren cache list                                 # önbelleği listele
chevren cache clear                                # önbelleği temizle
chevren --help
```

Altyazılar `~/.cache/chevren/<video_id>/` dizini altında `en.srt` (transkript) ve `tr.srt` (çeviri) olarak önbelleğe alınır. Aynı URL tekrar çalıştırıldığında önbellekten anında sunulur.

---

## Firefox Eklentisi

YouTube video başlığının altına bir durum şeridi ve oynatıcı kontrollerine videoyu MPV'de açmak için bir ▶ düğmesi ekler.

**Firefox (önerilen) — AMO üzerinden kurulum:**
1. [Releases sayfasından](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.4) `chevren.xpi` dosyasını indirin
2. Firefox'ta `about:addons` sayfasını açın
3. Dişli ikonu → "Eklentiyi Dosyadan Yükle" → `chevren.xpi` seçin

**Chromium tabanlı tarayıcılar (Chrome, Edge, Brave, Helium) — manuel kurulum:**
1. [Releases sayfasından](https://github.com/yeggis/chevren/releases/tag/ext-v0.1.4) `chevren-extension-chrome.zip` dosyasını indirip açın
2. `chrome://extensions` sayfasını açın → "Geliştirici modu"nu etkinleştirin
3. "Paketlenmemiş öğe yükle" → açtığınız klasörü seçin

> ⚠️ Chromium tabanlı tarayıcılar otomatik güncelleme almaz — her güncellemede manuel yeniden kurulum gerekir.

**Durum şeridi ne yapar:**
- Boşta → tıklayarak altyazı oluşturmayı başlatın
- İndirme / Transkripsiyon / Çeviri → aşama etiketiyle animasyonlu ilerleme çubuğu
- Hazır → tıklayarak sayfa içi overlay'i açın/kapatın; altyazılar YouTube oynatıcısının üzerinde oynatmayla senkronize görünür
- Yeni çeviri parçaları geldikçe overlay canlı olarak güncellenir
- **Ayarlar paneli (⚙ Ayarlar):** dil seçimi (TR/EN), MPV'de aç, aktif pipeline'ı iptal et, önbellekteki altyazıyı sil
- **Overlay kontrolleri:** sürükleyerek konumlandırın, kaydırarak yazı boyutunu ayarlayın, çift tıklayarak sıfırlayın, Alt+C ile açın/kapatın
- Overlay cam efektli (glassmorphism) tasarım kullanır; YouTube kontrolleri görünüp kaybolurken konumu otomatik ayarlanır

Eklenti popup'ı sunucu durumunu, aktif pipeline aşamasını ve kaydırılabilir bir log gösterir. Yeniden başlatma düğmesi (↺) yerel sunucuya `POST /restart` gönderir; sunucu temiz şekilde çıkar ve systemd tarafından yeniden başlatılır.

---

## Çoklu Key ve Model Fallback

Chevren birden fazla Gemini API anahtarını destekler. `429 RESOURCE_EXHAUSTED` yanıtı alındığında aynı model için bir sonraki anahtara geçer. O modelin tüm anahtarları tükenirse şu zincir üzerinden devam eder:

```
gemini-2.5-flash → gemini-2.5-flash-lite → gemini-3.1-flash-lite-preview → gemini-3-flash-preview
```

Hiçbir parça sessizce atlanmaz; her key ve model tükenirse o parça İngilizce bırakılır.

---

## Sistem Gereksinimleri

- **İşletim Sistemi:** Linux (Arch tabanlı, Debian/Ubuntu, Fedora, openSUSE)
- **GPU:** CUDA destekli NVIDIA — CPU modu çalışır ancak çok daha yavaştır
- **Python:** 3.10+
- **Ekran:** Wayland veya X11

---

## Katkı

Pull request'ler memnuniyetle karşılanır. Büyük değişiklikler için lütfen önce bir issue açın.

```bash
git clone https://github.com/yeggis/chevren.git
cd chevren
# değişikliklerinizi yapın
git commit -m "feat: açıklama"
git pull --rebase origin main
git push
```

---

## Lisans

[MIT](LICENSE) © 2026 yeggis

<div align="center">

[🐛 Hata Bildirimi](https://github.com/yeggis/chevren/issues) · [💡 Özellik İsteği](https://github.com/yeggis/chevren/issues) · [📦 AUR Paketi](https://aur.archlinux.org/packages/chevren)

</div>
