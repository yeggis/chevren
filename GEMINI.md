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

## Genel Kurallar
- Her kod değişikliğinden sonra, dosyaya yazmadan önce şu kontrolleri yap ve sonuçlarını listele: hata yolları (geçici vs kalıcı), nil/boş değer kontrolü, edge case, mevcut kodla uyum. Kontrol listesini göstermeden dosyaya yazma.

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

## oh-my-gemini Configuration

### Hooks
oh-my-gemini uses Gemini CLI's hook system for deterministic behavior:
- ✅ **Security gates**: blocks dangerous commands (e.g. `rm -rf /`).
- ✅ **Auto-verification**: runs lint/typecheck after code changes.
- ✅ **Context injection**: injects git history, Conductor state, and relevant files into the prompt.
- ✅ **Git checkpoints**: ensures clean state before file modifications.

### Commands
- `/omg:status` - Show current state (GEMINI.md, Conductor tracks, hooks).
- `/omg:plan` - Enter plan mode with full OMG context.
- `/omg:review` - Code review of current changes against the plan.
- `/omg:autopilot` - Autonomous task execution for quick tasks.
- `/omg:track` - Start a new Conductor track for a feature.
- `/omg:implement` - Execute current plan task by task.

### Customization
Create `.gemini/omg-config.json` to customize:
```json
{
  "autoVerification": { "enabled": true },
  "security": { "gitCheckpoints": true },
  "phaseGates": { "strict": false }
}
```

## Teknik Notlar
- Zen profil: ~/.zen/glevivig.Default
- Cookie: ~/.config/chevren/cookies.txt (Netscape formatı)
- Tasarım: Konsept B (action bar altı strip) — minimal, bilgi yoğun
- STREAM_CHUNK=30, CONTEXT_SIZE=5 — chunk sınırı kopuk cümleler için önceki 5 blok [context] prefix
- Blok sayısı kayması: Gemini N girdi → N±1 çıktı dönebilir, yapısal limit
- Çeviri parse: regex r"^\s*(\d+)\s*[.):-]\s*(.*)" — Gemini format varyantlarını yakalar
- debug_save_transcript: config'de false — true yapılınca {video_id}.en.srt cache'e kaydedilir
- protected_names: config listesi, prompt'a eklenir, sponsor/özel isim halüsinasyonlarına karşı
