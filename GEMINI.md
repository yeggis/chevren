## chevren Projesi

YouTube video çevirisi için lokal pipeline + Firefox extension + MPV entegrasyonu.
GitHub: yeggis/chevren (private) | Mevcut versiyon: v1.0.19
Dil: Python (src/) + Rust (server/) + JavaScript (extension/)

## Roller
Gemini CLI uygulama ajanıdır: dosya yaz, düzenle, komut çalıştır.
Mimari kararlar Claude'dan gelir, Gemini uygular.

## Kritik İş Kuralları
- Fish shell: heredoc kullanma, echo/printf kullan
- git commit mesajları İngilizce
- git push öncesi: git pull --rebase origin main
- Server binary manuel kopyalanır: sudo cp server/target/release/chevren-server /usr/local/bin/chevren-server
- Server manuel başlatma: systemctl --user stop chevren-server && /usr/local/bin/chevren-server
- PKGBUILD: pkgver değişince pkgrel=1 sıfırla; AUR workflow: önce git push, sonra make aur-update
- paru cache sorunu: rm -rf ~/.cache/paru/clone/chevren
- Tag yeniden oluşturulunca: rm -f chevren-*.tar.gz, sonra updpkgsums
- requirements.txt tek kaynak — bağımlılık versiyonu buradan yönetilir
- Çok dilli strateji: source_lang/target_lang config'den beslenir, hardcode dil kodu ekleme
- Whisper standart transkripsiyon aracı — YouTube transkript desteği kalıcı olarak kaldırıldı

## Proje Yapısı
chevren/
├── src/
│   ├── cache.py
│   ├── cli.py
│   ├── config.py
│   └── pipeline.py
├── server/src/          ← Rust, MPV IPC
│   ├── main.rs
│   ├── mpv.rs
│   └── routes/
├── extension/           ← Firefox extension
│   ├── content.js
│   ├── manifest.json
│   └── popup/
├── PKGBUILD
├── Makefile
├── pyproject.toml
└── requirements.txt

## Teknik Notlar
- Zen profil: ~/.zen/glevivig.Default
- Cookie: ~/.config/chevren/cookies.txt (Netscape formatı)
- Tasarım: Konsept B (action bar altı strip) — minimal, bilgi yoğun
- STREAM_CHUNK=30, CONTEXT_SIZE=5 — chunk sınırı kopuk cümleler için önceki 5 blok [context] prefix
- Blok sayısı kayması: Gemini N girdi → N±1 çıktı dönebilir, yapısal limit
- Çeviri parse: regex r"^\s*(\d+)\s*[.):-]\s*(.*)" — Gemini format varyantlarını yakalar
- debug_save_transcript: config'de false — true yapılınca {video_id}.en.srt cache'e kaydedilir
- protected_names: config listesi, prompt'a eklenir, sponsor/özel isim halüsinasyonlarına karşı

## Bekleyen Görevler
1. MPV altyazı titreme fix — Lua script (mpv/chevren.lua), MPV IPC üzerinden chunk ekleme
2. Kota göstergesi — 429'da _status(stage="translating", message="...kotası bitti") emit et
3. Log popup kaybolma — background script veya content.js mesajıyla çözülecek
4. ext-v0.1.2 AMO release — overlay navigation fix içeriyor
5. Prompt bağlam iyileştirmesi — çeviri kalitesi (C adımı)
