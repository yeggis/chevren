# CHEVREN — TAM PROJE CONTEXT DOSYASI

> Bu dosya, Chevren projesinin kaynak kodlarının tamamını yapay zeka sistemlerine
> (Claude, ChatGPT, Gemini vb.) aktarmak amacıyla oluşturulmuştur.
> Oluşturulma tarihi: 2026-04-15 | Sürüm: v1.0.19

---

## 📋 PROJE ÖZETİ

**Chevren**, YouTube videoları ve yerel dosyalar için yerel AI altyazı pipeline'ıdır.
Sesi yerel olarak Whisper ile metne dönüştürür, Gemini API ile Türkçeye çevirir ve
altyazıyı MPV'de canlı olarak gösterir. Tarayıcı eklentisi YouTube'a direkt
entegre olur. Tamamen ücretsiz (free Gemini API key yeterli), tamamen yerel.

**Mimari Akış:**
```
YouTube URL / Yerel Dosya
         │
         ▼
   yt-dlp  ──►  ffmpeg  ──►  faster-whisper (yerel STT, CUDA)
                                       │
                               segmentler (generator, lazy)
                                       │
                      _KeyPool: Gemini API  ←─ çoklu key havuzu
                               (parça parça çeviri, streaming)
                                       │
                               SRT dosyasına anlık yazma
                                       │
                  ┌────────────────────┴────────────────────┐
                  ▼                                         ▼
           MPV (sub-file)                       Firefox Eklentisi
           canlı altyazı yenileme               overlay renderer
                  │
           chevren-server (Rust/Axum)
           HTTP :7373 — pipeline durumu,
           altyazı yenileme, MPV IPC köprüsü
```

**Teknoloji Yığını:**
- **Python** (`src/`): Ana pipeline (faster-whisper, google-genai)
- **Rust** (`server/`): Axum + Tokio tabanlı yerel HTTP sunucusu (:7373)
- **JavaScript** (`extension/`): Firefox WebExtensions API
- **Lua** (`chevren.lua`): MPV script entegrasyonu

**Mevcut sürüm:** v1.0.19 (Python pkg: 1.0.11, Extension: 0.1.2, Server: 0.1.0)
**Lisans:** MIT | **GitHub:** yeggis/chevren (private)
**Sistem:** Linux (Arch-tabanlı öncelikli), CUDA destekli NVIDIA GPU

---

## 📁 DİZİN YAPISI

```
chevren/
├── src/                     ← Python Core
│   ├── cache.py             - SRT önbellekleme
│   ├── cli.py               - Komut satırı arayüzü + setup wizard
│   ├── config.py            - Ayar yönetimi (JSON, donanım tespiti)
│   └── pipeline.py          - Ana pipeline (Whisper + Gemini + MPV)
├── server/                  ← Rust HTTP Server (Axum)
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs          - Router + CORS + dinleyici :7373
│       ├── mpv.rs           - MPV Unix IPC socket köprüsü
│       ├── state.rs         - Paylaşımlı pipeline durumu (Arc<Mutex>)
│       └── routes/
│           ├── mod.rs
│           ├── status.rs         - GET /status
│           ├── pipeline_status.rs - POST /pipeline/status
│           ├── open.rs           - POST /open, POST /generate
│           ├── subtitle.rs       - GET/DELETE /subtitle/:id, POST /subtitle/reload
│           ├── mpv_cmd.rs        - POST /mpv/command
│           └── restart.rs        - POST /restart
├── extension/               ← Firefox Extension
│   ├── manifest.json        - MV3, gecko ID: chevren@yeggis
│   ├── background.js        - Service worker, log + alarm poll
│   ├── content.js           - YouTube DOM enjeksiyonu, overlay, self-healing
│   └── popup/
│       ├── popup.html       - 280px karanlık UI, 2 sekme (Durum/Log)
│       ├── popup.js         - Status poll + log render + restart
│       ├── log.html         - Tam ekran log görünümü
│       └── log.js           - Storage listener, auto-scroll
├── conductor/               ← Proje yönetimi dokümanları
│   ├── product.md
│   ├── tech-stack.md
│   ├── workflow.md
│   ├── tracks.md
│   └── code_styleguides/general.md
├── server/systemd/
│   └── chevren-server.service  - Systemd user service (Restart=on-failure)
├── docs/
│   └── updates.json         - Firefox addon güncelleme manifest
├── tests/
│   └── test_quota_callback.py - Kota callback mock testi
├── chevren.lua              - MPV Lua script (polling + sub-add)
├── chevren.install          - Arch: post_install/upgrade/remove hooks
├── PKGBUILD                 - Arch AUR paket tanımı
├── Makefile                 - aur-update + release hedefleri
├── pyproject.toml           - Python paket tanımı
├── requirements.txt         - Sabitlenmiş bağımlılık sürümleri
├── install.py               - Evrensel Python kurulum scripti
├── install.sh               - Bash kurulum scripti (distro-aware)
├── CLAUDE.md                - Claude için oturum handoff şablonu
├── GEMINI.md                - Gemini CLI için proje kuralları
├── README.md                - İngilizce dokümantasyon
└── README-tr.md             - Türkçe dokümantasyon
```

---

## 🔑 KRİTİK KURALLAR (AI Asistanlar İçin)

- **Fish shell**: heredoc kullanma, echo/printf kullan
- **git commit**: mesajları İngilizce olmalı
- **git push öncesi**: `git pull --rebase origin main`
- **Server binary** manuel kopyalanır: `sudo cp server/target/release/chevren-server /usr/local/bin/chevren-server`
- **PKGBUILD**: `pkgver` değişince `pkgrel=1` sıfırla
- **AUR workflow**: önce `git push`, sonra `make aur-update`
- **requirements.txt** tek kaynak — bağımlılık versiyonu buradan yönetilir
- **Whisper**: standart transkripsiyon aracı — YouTube transkript desteği kalıcı kaldırıldı
- **Çok dilli strateji**: `source_lang`/`target_lang` config'den beslenir, hardcode dil kodu ekleme
- **server/src/routes/pipeline_status.rs** ana status merkezidir
- **MPV IPC**: `send_command_with_response` event satırlarını atlar, `"error"` alanı içeren yanıtı döner
- **Extension Self-Healing**: YouTube DOM'u güncellediğinde strip kaybolursa `updateStrip` `tryInjectAll` ile geri yükler
- **paru cache sorunu**: `rm -rf ~/.cache/paru/clone/chevren`
- **Tag yeniden oluşturulunca**: `rm -f chevren-*.tar.gz`, sonra `updpkgsums`

---

## 📊 API ENDPOINT TABLOSU

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/status?v={video_id}` | Pipeline durum sorgulama |
| POST | `/pipeline/status` | Python pipeline → server durum bildirimi |
| POST | `/open` | MPV'de aç (senkron, SRT bekler) |
| POST | `/generate` | Eklentiden pipeline başlat (async) |
| GET | `/subtitle/:id` | SRT içeriği döner |
| DELETE | `/subtitle/:id` | Cache'den SRT siler |
| POST | `/subtitle/reload` | MPV'ye altyazı yenile komutu gönder |
| POST | `/mpv/command` | Keyfi MPV IPC komutu gönder |
| POST | `/restart` | Server'ı yeniden başlat (systemd kaldırır) |

---

## 📦 BAĞIMLILIKLAR

**Python:**
- `faster-whisper==1.2.1` — yerel konuşma tanıma
- `google-genai==1.70.0` — Gemini API
- `urllib3==2.6.3`
- `charset-normalizer==3.4.6`
- `prompt-toolkit>=3.0` — setup wizard TUI
- `platformdirs>=4.0` — config dizini tespiti

**Rust:**
- `axum 0.7` — web framework
- `tokio 1` (full) — async runtime
- `serde/serde_json 1` — JSON
- `tower-http 0.5` (cors) — CORS middleware
- `directories 5` — XDG cache path
- `tracing/tracing-subscriber` — loglama
- `url 2` — URL parsing
- `anyhow 1` — hata yönetimi

---

---

## 📄 DOSYA İÇERİKLERİ

---

### Dosya: `src/cache.py`

```python
"""
cache.py — chevren cache yönetimi
Video ID bazlı SRT saklama ve okuma
"""
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "chevren"

def _ensure() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def path(video_id: str) -> Path:
    return CACHE_DIR / f"{video_id}.srt"

def exists(video_id: str) -> bool:
    return path(video_id).exists()

def read(video_id: str) -> str:
    return path(video_id).read_text(encoding="utf-8")

def write(video_id: str, content: str) -> None:
    _ensure()
    path(video_id).write_text(content, encoding="utf-8")

def list_all() -> list[dict]:
    _ensure()
    entries = []
    for f in sorted(CACHE_DIR.glob("*.srt"), key=lambda x: x.stat().st_mtime, reverse=True):
        entries.append({
            "video_id": f.stem,
            "path":     str(f),
            "size_kb":  round(f.stat().st_size / 1024, 1),
        })
    return entries

def clear() -> int:
    _ensure()
    files = list(CACHE_DIR.glob("*.srt"))
    for f in files:
        f.unlink()
    return len(files)
```

---

### Dosya: `src/config.py`

```python
"""
config.py — chevren ayar yönetimi
"""

import json
from pathlib import Path

from platformdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("chevren"))
CONFIG_FILE = CONFIG_DIR / "config.json"


def detect_hardware() -> dict:
    info = {
        "gpu_name": "CPU",
        "vram_gb": 0,
        "device": "cpu",
        "compute_type": "int8",
        "whisper_model": "base",
    }
    try:
        import torch

        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            vram_gb = props.total_memory / (1024**3)
            info.update(
                {
                    "gpu_name": torch.cuda.get_device_name(0),
                    "vram_gb": round(vram_gb, 1),
                    "device": "cuda",
                }
            )
            if vram_gb >= 10:
                info["whisper_model"] = "large-v3-turbo"
                info["compute_type"] = "float16"
            elif vram_gb >= 7:
                info["whisper_model"] = "large-v3-turbo"
                info["compute_type"] = "int8"
            elif vram_gb >= 5:
                info["whisper_model"] = "medium"
            elif vram_gb >= 3:
                info["whisper_model"] = "small"
    except Exception:
        pass
    return info


def _build_defaults() -> dict:
    hw = detect_hardware()
    return {
        "gemini_api_keys": [],
        "gemini_api_key": "",
        "gemini_model": "gemini-2.5-flash-lite",
        "whisper_model": hw["whisper_model"],
        "whisper_device": hw["device"],
        "compute_type": hw["compute_type"],
        "player": "mpv",
        "source_lang": "en",
        "target_lang": "tr",
        "debug_save_transcript": False,
        "_gpu_name": hw["gpu_name"],
        "_vram_gb": hw["vram_gb"],
    }

def load() -> dict:
    defaults = _build_defaults()
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return {**defaults, **saved}
        except Exception:
            pass
    return defaults


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_api_keys() -> list[str]:
    """Tüm API key'leri liste döner. Eski tek-key formatıyla uyumlu."""
    cfg = load()
    keys = cfg.get("gemini_api_keys")
    if keys and isinstance(keys, list):
        return [k for k in keys if k]
    single = cfg.get("gemini_api_key", "")
    return [single] if single else []


def get(key: str):
    return load().get(key)


def set_key(key: str, value) -> None:
    cfg = load()
    cfg[key] = value
    save(cfg)


def hardware_summary() -> str:
    cfg = load()
    gpu = cfg.get("_gpu_name", "CPU")
    vram = cfg.get("_vram_gb", 0)
    return f"{gpu} · {vram} GB VRAM" if vram else "CPU"
```

---

### Dosya: `src/pipeline.py`

```python
"""
pipeline.py — chevren ana pipeline
YouTube URL veya yerel dosya → Türkçe SRT
"""

import gc
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(APP_DIR))

import json as _json

import cache
import config

CHUNK_SIZE = 150
STREAM_CHUNK = 30  # streaming modunda kaç segment birikince çeviri başlasın
CONTEXT_SIZE = 5   # chunk başına önceki chunk'tan kaç blok context eklenir


def _status(**kw):
    import json
    import urllib.request

    print(f"STATUS: {kw}", flush=True)

    try:
        data = json.dumps(kw).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:7373/pipeline/status",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _parse_srt(content: str) -> list[dict]:
    blocks = []
    for block in content.strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) >= 3:
            blocks.append(
                {"num": lines[0], "ts": lines[1], "text": "\n".join(lines[2:])}
            )
    return blocks


def _blocks_to_srt(blocks: list[dict]) -> str:
    lines = []
    for b in blocks:
        lines += [b["num"], b["ts"], b["text"], ""]
    return "\n".join(lines)


COOKIE_FILE = Path.home() / ".config" / "chevren" / "cookies.txt"


def _detect_cookie_browser():
    """
    Cookie kaynağını döner. Öncelik sırası:
    1. ~/.config/chevren/cookies.txt varsa → ("file", path)
    2. Config'de browser ayarı varsa → ("browser", değer)
    3. Zen otomatik algıla → ("browser", "firefox:/profil")
    4. Firefox/Librewolf → ("browser", "firefox")
    5. Hiçbiri → (None, None)
    """
    browser = config.get("browser")
    if COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 0:
        return ("file", str(COOKIE_FILE))
    if browser:
        return ("browser", browser)
    zen_dir = Path.home() / ".zen"
    if zen_dir.exists():
        best, best_size = None, 0
        for profile in zen_dir.iterdir():
            if not profile.is_dir():
                continue
            cookies_file = profile / "cookies.sqlite"
            if cookies_file.exists():
                size = cookies_file.stat().st_size
                if size > best_size:
                    best_size = size
                    best = profile
        if best:
            return ("browser", f"firefox:{best}")
    import shutil

    for b in ["firefox", "librewolf"]:
        if shutil.which(b):
            return ("browser", b)
    return (None, None)


def _yt_dlp_args(source: str, output: str) -> list:
    base = [
        "yt-dlp",
        "-f",
        "140/m4a/bestaudio[ext=m4a]/bestaudio",
        source,
        "-o",
        output,
    ]
    kind, value = _detect_cookie_browser()
    if kind == "file":
        return base + ["--cookies", value]
    elif kind == "browser":
        return base + ["--cookies-from-browser", value]
    return base


def _yt_dlp_cookie_args() -> list:
    """MPV için --ytdl-raw-options cookie argümanları döner."""
    kind, value = _detect_cookie_browser()
    if kind == "file":
        return [f"--ytdl-raw-options=cookies={value}"]
    elif kind == "browser":
        return [f"--ytdl-raw-options=cookies-from-browser={value}"]
    return []


def _extract_audio(source: str, workdir: Path) -> Path:
    wav = workdir / "audio.wav"
    if source.startswith("http"):
        m4a = workdir / "audio.m4a"
        subprocess.run(_yt_dlp_args(source, str(m4a)), check=True)
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(m4a), "-ar", "16000", "-ac", "1", str(wav)],
            check=True,
        )
    else:
        subprocess.run(
            ["ffmpeg", "-y", "-i", source, "-ar", "16000", "-ac", "1", str(wav)],
            check=True,
        )
    return wav


GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-flash",              # 1. primary (en iyi kalite, 20 RPD)
    "gemini-2.5-flash-lite",         # 2. hafif versiyon, aynı nesil (20 RPD)
    "gemini-3.1-flash-lite-preview", # 3. en yüksek kota (500 RPD) — kota kurtarıcı
    "gemini-3-flash-preview",        # 4. son çare (20 RPD)
]

def _protected_names_rule() -> str:
    """config'deki protected_names listesinden prompt kuralı üretir."""
    names = config.get("protected_names") or []
    if not names:
        return ""
    return f" Do NOT translate or alter these proper nouns: {', '.join(names)}."


class _KeyPool:
    """Çoklu API key + model rotasyonu.
    Kota dolunca önce diğer key'lere geçer (aynı model),
    tüm key'ler tükenince bir sonraki modele düşer."""
    def __init__(self, keys: list[str], base_model: str):
        from google import genai
        if not keys:
            raise ValueError("Gemini API key eksik. 'chevren setup' ile ekleyin.")
        self.base_model = base_model
        self._clients = [genai.Client(api_key=k) for k in keys]
        self._n = len(keys)
        self._exhausted: dict[str, set[int]] = {}
        self._key_idx = 0
    def _model_list(self) -> list[str]:
        seen, result = set(), []
        for m in [self.base_model] + GEMINI_FALLBACK_MODELS:
            if m not in seen:
                seen.add(m)
                result.append(m)
        return result
    def _keys_for(self, model: str) -> list[int]:
        ex = self._exhausted.get(model, set())
        return [i for i in range(self._n) if i not in ex]
    @property
    def current_model(self) -> str | None:
        for m in self._model_list():
            if self._keys_for(m):
                return m
        return None
    @property
    def client(self):
        return self._clients[self._key_idx]
    def label(self, model: str) -> str:
        return f"key[{self._key_idx}]/{model}"
    def exhaust_current_key(self, model: str) -> bool:
        """Aktif key'i bu model için tüket.
        Aynı modelde başka key varsa ona geç → True.
        Yoksa bir sonraki modele düş → True.
        Hiçbir şey kalmadıysa → False."""
        self._exhausted.setdefault(model, set()).add(self._key_idx)
        remaining = self._keys_for(model)
        if remaining:
            self._key_idx = remaining[0]
            print(f"  key rotasyonu → key[{self._key_idx}] (model: {model})")
            return True
        for m in self._model_list():
            avail = self._keys_for(m)
            if avail:
                self._key_idx = avail[0]
                print(f"  model rotasyonu: {model} → {m} key[{self._key_idx}]")
                return True
        return False


def _translate_chunk(
    pool: "_KeyPool", blocks: list[dict], chunk_index: int,
    context: list[dict] | None = None,
    on_quota_event=None,
) -> list[dict]:
    """Bir segment grubunu çevirir. Kota bitince key/model rotasyonu yapar,
    chunk asla atlanmaz — tüm key+model combolar tükenirse İngilizce bırakır.
    context: önceki chunk'tan son N blok — çevrilmez, sadece bağlam için."""
    import re

    texts = [b["text"] for b in blocks]
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))

    _pn = _protected_names_rule()
    if context:
        ctx_lines = "\n".join(f"[context] {b['text']}" for b in context)
        prompt_body = ctx_lines + "\n" + numbered
        prompt = (
            "Translate each NUMBERED line to Turkish."
            + _pn
            + " Lines starting with [context] are for reference only — DO NOT translate them. "
            "Output ONLY the numbered translations, one per line, using EXACTLY this format: N. translation "
            "(number, dot, space, text). No bold, no parentheses, no extra lines, no explanation. "
            "Example: '1. Hello world' → '1. Merhaba dünya'.\n\n" + prompt_body
        )
    else:
        prompt = (
            "Translate each numbered line to Turkish."
            + _pn
            + " Output ONLY the translations, one per line, using EXACTLY this format: N. translation "
            "(number, dot, space, text). No bold, no parentheses, no extra lines, no explanation. "
            "Example: '1. Hello world' → '1. Merhaba dünya'.\n\n" + numbered
        )

    attempt = 0
    while True:
        model = pool.current_model
        if model is None:
            print(f"  Chunk {chunk_index}: tüm key ve modeller tükendi, İngilizce bırakıldı.")
            return blocks
        print(f"  Chunk {chunk_index}: [{pool.label(model)}] deneniyor...")
        try:
            tr_text = pool.client.models.generate_content(
                model=model, contents=prompt
            ).text.strip()

            tr_lines = {}
            for line in tr_text.splitlines():
                line = line.strip()
                if not line:
                    continue
                m = re.match(r"^\**\s*(\d+)\s*[.):\-]\**\s*(.*)", line)
                if m:
                    val = m.group(2).rstrip("*").strip()
                    if val:
                        tr_lines[int(m.group(1))] = val
            if len(tr_lines) != len(blocks):
                print(f"  ⚠ Chunk {chunk_index}: {len(blocks)} girdi → {len(tr_lines)} çıktı")
            return [
                {**b, "text": tr_lines.get(i + 1, b["text"])}
                for i, b in enumerate(blocks)
            ]

        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                print(f"  Chunk {chunk_index}: [{pool.label(model)}] kota doldu → rotasyon")
                if not pool.exhaust_current_key(model):
                    print(f"  Chunk {chunk_index}: tüm key ve modeller tükendi, İngilizce bırakıldı.")
                    if on_quota_event:
                        on_quota_event(exhausted=True, model=None, label=None)
                    return blocks
                new_model = pool.current_model
                if on_quota_event:
                    on_quota_event(exhausted=False, model=new_model, label=pool.label(new_model))
                attempt = 0
                continue
            if "503" in err or "UNAVAILABLE" in err:
                wait = 10 * (attempt + 1)
                print(f"  Chunk {chunk_index}: [{pool.label(model)}] servis meşgul, {wait}s bekleniyor...")
                time.sleep(wait)
                continue
            attempt += 1
            if attempt >= 3:
                print(f"  Chunk {chunk_index}: [{pool.label(model)}] 3 denemede başarısız → model değiştir")
                if not pool.exhaust_current_key(model):
                    print(f"  Chunk {chunk_index}: tüm key ve modeller tükendi, İngilizce bırakıldı.")
                    return blocks
                attempt = 0
                continue
            match = re.search(r"retryDelay.*?(\d+)s", err)
            wait = int(match.group(1)) + 2 if match else 5 * attempt
            print(f"  Chunk {chunk_index}: hata (deneme {attempt}/3): {e}")
            print(f"  {wait} saniye bekleniyor...")
            time.sleep(wait)


def _make_quota_callback(video_id: str):
    def cb(exhausted: bool, model, label):
        if exhausted:
            _status(
                stage="translating",
                video_id=video_id,
                message="Tüm API kotaları doldu, çeviri İngilizce bırakılıyor.",
            )
        else:
            _status(
                stage="translating",
                video_id=video_id,
                message=f"Kota doldu → {label} deneniyor",
            )
    return cb


def _translate(srt_en: str, video_id: str = "") -> str:
    pool = _KeyPool(config.get_api_keys(), config.get("gemini_model"))
    blocks = _parse_srt(srt_en)
    chunks = [blocks[i : i + CHUNK_SIZE] for i in range(0, len(blocks), CHUNK_SIZE)]
    tr_all = []
    for ci, chunk in enumerate(chunks, 1):
        print(f"  Çeviri: {ci}/{len(chunks)}")
        ctx = tr_all[-CONTEXT_SIZE:] if tr_all else None
        tr_all.extend(_translate_chunk(pool, chunk, ci, context=ctx, on_quota_event=_make_quota_callback(video_id)))
    return _blocks_to_srt(tr_all)


def _renumber(blocks: list[dict], start: int) -> list[dict]:
    """Blokları verilen numaradan itibaren yeniden numaralandırır."""
    return [{**b, "num": str(start + i)} for i, b in enumerate(blocks)]


def _append_srt(srt_path: Path, blocks: list[dict]) -> None:
    """SRT dosyasına yeni blokları ekler."""
    with open(srt_path, "a", encoding="utf-8") as f:
        for b in blocks:
            f.write(f"{b['num']}\n{b['ts']}\n{b['text']}\n\n")


def _reload_mpv_subs(srt_path: Path):
    """chevren-server üzerinden MPV altyazısını günceller."""
    try:
        import json
        import urllib.request

        data = json.dumps({"path": str(srt_path)}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:7373/subtitle/reload",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


def _extract_video_id(source: str) -> str:
    if source.startswith("http"):
        import re
        m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", source)
        return m.group(1) if m else source.split("/")[-1][:11]
    return Path(source).stem[:40]


def run(source: str, workdir: Path) -> Path:
    """Eski toplu mod — geriye dönük uyumluluk için korundu."""
    video_id = _extract_video_id(source)
    if cache.exists(video_id):
        print(f"Cache bulundu: {video_id}")
        return cache.path(video_id)
    print(f"İşleniyor: {source}")
    workdir.mkdir(parents=True, exist_ok=True)
    wav = _extract_audio(source, workdir)
    srt_en = _transcribe_full(wav)
    srt_tr = _translate(srt_en, video_id=video_id)
    cache.write(video_id, srt_tr)
    print(f"Tamamlandı → {cache.path(video_id)}")
    return cache.path(video_id)


def _transcribe_full(wav: Path) -> str:
    """Tüm WAV'ı Whisper'a verir, SRT string döner."""
    from faster_whisper import WhisperModel

    model = WhisperModel(
        config.get("whisper_model"),
        device=config.get("whisper_device"),
        compute_type=config.get("compute_type"),
    )
    segments, _ = model.transcribe(
        str(wav), language="en", beam_size=5, vad_filter=True
    )
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(
            f"{i}\n{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}\n{seg.text.strip()}\n"
        )
    del model
    gc.collect()
    return "\n".join(lines)


def run_streaming(source: str, workdir: Path, on_ready=None) -> Path:
    """
    Streaming mod — Whisper segment ürettikçe Gemini'ye gönderir,
    SRT dosyasına anında yazar.
    on_ready: SRT dosyası ilk kez hazır olunca çağrılır (mpv'yi açmak için)
              Signature: on_ready(srt_path: Path)
    """
    video_id = _extract_video_id(source)
    try:
        return _run_streaming_inner(source, workdir, video_id, on_ready)
    except Exception as e:
        import traceback
        msg = traceback.format_exc().strip().splitlines()[-1]
        print(f"PIPELINE HATA: {msg}", flush=True)
        _status(stage="error", video_id=video_id, message=msg)
        raise


def _run_streaming_inner(source: str, workdir: Path, video_id: str, on_ready=None) -> Path:
    from faster_whisper import WhisperModel
    if cache.exists(video_id):
        print(f"Cache bulundu: {video_id}")
        srt_path = cache.path(video_id)
        if on_ready:
            on_ready(srt_path)
        _status(stage="ready", video_id=video_id)
        return srt_path
    print(f"İşleniyor: {source}", flush=True)
    workdir.mkdir(parents=True, exist_ok=True)
    source_lang = config.get("source_lang") or "en"
    pool = _KeyPool(config.get_api_keys(), config.get("gemini_model"))
    _status(stage="downloading", video_id=video_id)
    wav = _extract_audio(source, workdir)
    _status(stage="transcribing", video_id=video_id)
    model = WhisperModel(
        config.get("whisper_model"),
        device=config.get("whisper_device"),
        compute_type=config.get("compute_type"),
    )
    segments, _ = model.transcribe(
        str(wav), language=source_lang, beam_size=5, vad_filter=True
    )
    srt_path = cache.path(video_id)
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("", encoding="utf-8")
    pending = []
    seg_count = 0
    blk_count = 0
    chunk_num = 0
    ready_sent = False
    translated = []
    debug_lines = [] if config.get("debug_save_transcript") else None
    for seg in segments:
        seg_count += 1
        pending.append(
            {
                "num": str(seg_count),
                "ts": f"{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}",
                "text": seg.text.strip(),
            }
        )
        if debug_lines is not None:
            debug_lines.append(
                f"{seg_count}\n{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}\n{seg.text.strip()}\n"
            )
        if len(pending) >= STREAM_CHUNK:
            chunk_num += 1
            print(f"  Çeviri: chunk {chunk_num} ({seg_count} segment işlendi)")
            ctx = [{"text": b["text"]} for b in translated[-CONTEXT_SIZE:]] if translated else None
            translated = _translate_chunk(pool, pending, chunk_num, context=ctx, on_quota_event=_make_quota_callback(video_id))
            translated = _renumber(translated, blk_count + 1)
            _append_srt(srt_path, translated)
            _status(stage="translating", chunk=chunk_num, video_id=video_id)
            _reload_mpv_subs(srt_path)
            blk_count += len(translated)
            pending.clear()
            if not ready_sent and on_ready:
                on_ready(srt_path)
                ready_sent = True

    if debug_lines is not None:
        debug_path = cache.path(video_id).with_name(f"{video_id}.en.srt")
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text("\n".join(debug_lines), encoding="utf-8")
    if pending:
        chunk_num += 1
        print(f"  Çeviri: chunk {chunk_num} (son)")
        ctx = [{"text": b["text"]} for b in translated[-CONTEXT_SIZE:]] if translated else None
        translated = _translate_chunk(pool, pending, chunk_num, context=ctx, on_quota_event=_make_quota_callback(video_id))
        translated = _renumber(translated, blk_count + 1)
        _append_srt(srt_path, translated)
        _status(stage="translating", chunk=chunk_num, video_id=video_id)
        _reload_mpv_subs(srt_path)

    del model
    gc.collect()
    cache.write(video_id, srt_path.read_text(encoding="utf-8"))
    if not ready_sent and on_ready:
        on_ready(srt_path)
    _status(stage="ready", video_id=video_id)
    print(f"Tamamlandı → {srt_path}")
    return srt_path
```

---

### Dosya: `src/cli.py`

> 525 satır. Komut satırı arayüzü + `chevren setup` sihirbazı.
> `prompt_toolkit` tabanlı ok-tuşu navigasyonlu TUI (_pick fonksiyonu).
> Alt komutlar: `setup`, `config <key> <value>`, `cache list/clear`, `<url/file> [--no-play]`.
> `cmd_run` → `pipeline.run_streaming` çağırır, `on_ready` ile MPV'yi açar.
> `_is_turkish()` ile LANG env'e göre yardım metnini otomatik Türkçe/İngilizce sunar.

```python
# [Uzun dosya - temel fonksiyon imzaları]
def main() -> None: ...          # entry point: sys.argv parse
def cmd_setup() -> None: ...     # interaktif kurulum sihirbazı
def cmd_config(args) -> None: ...# config key value yaz
def cmd_cache(args) -> None: ... # cache list / clear
def cmd_run(source, no_play) -> None: # streaming pipeline başlat
def _pick(title, items, current_idx, extra_prompt) -> int|str|None: # TUI seçici
def _setup_cookies() -> None: ...     # cookie kurulum yönlendirmesi
def _enable_server_service() -> None: # systemd user service aktif et
```

---

### Dosya: `extension/manifest.json`

```json
{
  "manifest_version": 3,
  "name": "Chevren",
  "version": "0.1.2",
  "description": "YouTube videolarını Türkçe altyazıyla izle",

  "browser_specific_settings": {
    "gecko": {
      "id": "chevren@yeggis",
      "strict_min_version": "142.0",
      "update_url": "https://yeggis.github.io/chevren/updates.json",
      "data_collection_permissions": {
        "required": ["none"],
        "optional": []
      }
    }
  },

  "permissions": ["activeTab", "storage", "alarms"],

  "host_permissions": [
    "http://localhost:7373/*",
    "https://www.youtube.com/*"
  ],

  "content_scripts": [{
    "matches": ["https://www.youtube.com/*"],
    "js": ["content.js"],
    "run_at": "document_idle"
  }],

  "web_accessible_resources": [{
    "resources": ["popup/log.html", "popup/log.js"],
    "matches": ["<all_urls>"]
  }],

  "background": { "service_worker": "background.js" },

  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/icon16.png", "32": "icons/icon32.png",
      "48": "icons/icon48.png", "128": "icons/icon128.png"
    }
  }
}
```

---

### Dosya: `extension/background.js`

```javascript
const SERVER = "http://localhost:7373";
const MAX_LOG = 200;
const STORAGE_KEY = "chevren_logs";

let lastStage = null;
let lastChunk = null;

function ts() {
  return new Date().toTimeString().slice(0, 8);
}

async function addLog(msg, cls = "") {
  const result = await chrome.storage.local.get(STORAGE_KEY);
  const logs = result[STORAGE_KEY] || [];
  logs.push({ time: ts(), msg, cls });
  if (logs.length > MAX_LOG) logs.shift();
  await chrome.storage.local.set({ [STORAGE_KEY]: logs });
}

function stageInfo(data) {
  switch (data.stage) {
    case "idle":         return { text: "bekliyor", cls: "" };
    case "downloading":  return { text: "ses indiriliyor — yt-dlp", cls: "working" };
    case "transcribing": return { text: "transkript oluşturuluyor — whisper", cls: "working" };
    case "translating":  return { text: `çeviri — parça ${data.chunk ?? "?"}/${data.chunk_max ?? "?"}`, cls: "working" };
    case "ready":        return { text: "altyazı hazır ✓", cls: "done" };
    case "error":        return { text: `hata: ${data.message || "bilinmeyen"}`, cls: "err" };
    default:             return { text: data.stage, cls: "" };
  }
}

async function poll() {
  try {
    const res = await fetch(`${SERVER}/status`);
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();

    const { text, cls } = stageInfo(data);
    if (data.stage !== lastStage) {
      await addLog(text, cls);
      lastStage = data.stage;
      lastChunk = data.chunk;
    } else if (data.stage === "translating" && data.chunk !== lastChunk) {
      await addLog(text, cls);
      lastChunk = data.chunk;
    }
  } catch {
    if (lastStage !== "__offline__") {
      await addLog("server'a ulaşılamadı", "err");
      lastStage = "__offline__";
    }
  }
}

// Service worker'da setInterval çalışmaz, alarm API kullan
chrome.alarms.create("chevren-poll", { periodInMinutes: 1 / 60 }); // ~1 saniye
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "chevren-poll") poll();
});

poll(); // ilk çağrı hemen
```

---

### Dosya: `extension/content.js`

> 514 satır. YouTube'a DOM enjekte eden ana script.
> **Temel özellikler:**
> - `injectStrip()`: Video başlığının altına durum şeridi (CV badge, progress bar, animasyonlar)
> - `injectMpvButton()`: Player kontrollerine MPV açma butonu
> - `startPolling()`: 1 sn'de bir `/status?v={id}` poll eder, strip günceller
> - `mountOverlay()`: Video üzerine SRT'yi overlay olarak render eder (timeupdate event)
> - `parseSrt()`: SRT text → cue nesneleri
> - `updateStrip()`: stage değerine göre UI günceller; DOM yoksa `tryInjectAll()` tetikler (self-healing)
> - URL takibi: 500ms polling ile YouTube SPA navigasyonunu yakalar, state sıfırlar
> - `onStripClick()`: idle → `/generate` POST; ready/translating → overlay toggle
> - `openInMpv()`: `/open` POST ile MPV'de açar
> - Self-healing: `updateStrip` çağrıldığında DOM elementleri yoksa `tryInjectAll` çağırır

---

### Dosya: `extension/popup/popup.html` + `popup.js`

> Eklenti popup'ı. 280px genişlik, koyu tema (#111 arkaplan, #c8a84b altın vurgu).
> **2 sekme:** "Durum" (video_id, aşama, parça, mesaj) + "Log" (zaman damgalı, renkli log listesi).
> Header'da server durumu (yeşil/kırmızı dot) + ↺ restart butonu → `POST /restart`.
> Log sekmesinde "temizle" + "↗ tam ekran" (log.html yeni sekmede açar).
> `popup.js`: 1 sn'de bir `/status` poll eder, `chrome.storage.onChanged` ile log'u dinler.

---

### Dosya: `extension/popup/log.html` + `log.js`

> Tam ekran log görünümü. Aynı dark theme.
> Üstte header (server durumu dot + temizle butonu) + durum bar (video/aşama/parça).
> `log.js`: `chrome.storage.onChanged` listener ile real-time güncelleme, auto-scroll.

---

### Dosya: `server/src/main.rs`

```rust
mod mpv;
mod routes;
mod state;

use axum::{routing::{get, post}, Router};
use tower_http::cors::{Any, CorsLayer};
use tracing_subscriber::fmt;

#[tokio::main]
async fn main() {
    fmt::init();

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let shared_state = state::new_shared();

    let app = Router::new()
        .route("/status", get(routes::status::handler))
        .route("/pipeline/status", post(routes::pipeline_status::handler))
        .route("/open", post(routes::open::handler))
        .route("/generate", post(routes::open::generate_handler))
        .route("/subtitle/reload", post(routes::subtitle::reload_handler))
        .route("/subtitle/:id",
            get(routes::subtitle::handler).delete(routes::subtitle::delete_handler))
        .route("/mpv/command", post(routes::mpv_cmd::handler))
        .route("/restart", post(routes::restart::handler))
        .with_state(shared_state)
        .layer(cors);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:7373")
        .await.expect("Port 7373 açılamadı");

    tracing::info!("chevren-server 127.0.0.1:7373 üzerinde çalışıyor");
    axum::serve(listener, app).await.unwrap();
}
```

---

### Dosya: `server/src/state.rs`

```rust
use serde::Serialize;
use std::sync::{Arc, Mutex};

#[derive(Clone, Serialize, Default)]
pub struct PipelineState {
    pub stage: String,
    pub chunk: Option<u32>,
    pub chunk_max: Option<u32>,
    pub video_id: Option<String>,
    pub message: Option<String>,
    pub sub_track_id: Option<i64>,
}

pub type SharedState = Arc<Mutex<PipelineState>>;

pub fn new_shared() -> SharedState {
    Arc::new(Mutex::new(PipelineState {
        stage: "idle".into(),
        ..Default::default()
    }))
}
```

---

### Dosya: `server/src/mpv.rs`

```rust
// /tmp/chevren-mpv.sock üzerinden MPV IPC
// send_command: fire-and-forget
// send_command_with_response: event satırlarını atlar, "error" field içeren yanıt döner
// add_subtitle: sub-add komutu → track_id döner
// reload_subtitle: sub-reload komutu (track_id ile)
// open_with_subtitle: mpv zaten çalışıyorsa sub-add, yoksa yeni mpv spawn
```

---

### Dosya: `server/src/routes/pipeline_status.rs`

```rust
// POST /pipeline/status — Python pipeline → server durum bildirimi
// Stale status koruması: farklı video_id gelirse (ve mevcut hâlâ çalışıyorsa) yok say.
// chunk_max: gelen chunk değerinin maksimumunu tutar (her zaman artar).
// stage, chunk, video_id, message alanlarını günceller.
```

---

### Dosya: `server/src/routes/open.rs`

```rust
// POST /open: MPV modu — senkron, SRT yoksa pipeline çalıştırır, sonra mpv açar
// POST /generate: Extension modu — async, hemen döner; arka planda `chevren --no-play` başlatır
// Pipeline zaten çalışıyorsa (downloading/transcribing/translating) /generate reddeder.
// Cache varsa direkt "ready" döner.
// run_pipeline_tracked: sadece `chevren --no-play` bekler; durum Python'dan HTTP ile gelir.
```

---

### Dosya: `server/src/routes/subtitle.rs`

```rust
// GET /subtitle/:id → ~/.cache/chevren/{id}.srt içeriği döner
// DELETE /subtitle/:id → dosyayı siler
// POST /subtitle/reload:
//   - sub_track_id varsa: sub-reload (mevcut track günceller)
//   - yoksa: sub-add (yeni track ekler, id'yi state'e kaydeder)
```

---

### Dosya: `server/src/routes/restart.rs`

```rust
// POST /restart → 100ms sonra process::exit(1)
// systemd Restart=on-failure ile otomatik yeniden başlar
```

---

### Dosya: `server/src/routes/status.rs`

```rust
// GET /status?v={video_id}
// video_id verilmişse:
//   - Aktif pipeline aynı video için çalışıyorsa: state döner
//   - Cache'de SRT varsa: {"stage":"ready", ...} döner
//   - Yoksa: {"stage":"idle", ...} döner
// video_id verilmemişse: tüm state direkt döner
```

---

### Dosya: `server/Cargo.toml`

```toml
[package]
name = "chevren-server"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "chevren-server"
path = "src/main.rs"

[dependencies]
axum = "0.7"
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tower-http = { version = "0.5", features = ["cors"] }
directories = "5"
tracing = "0.1"
tracing-subscriber = "0.3"
url = "2"
anyhow = "1"
```

---

### Dosya: `PKGBUILD`

```bash
# Maintainer: yeggis <yeggis@users.noreply.github.com>
pkgname=chevren
pkgver=1.0.19
pkgrel=3
pkgdesc="Turkish subtitle generator for YouTube videos and local files"
arch=('x86_64')
url="https://github.com/yeggis/chevren"
license=('MIT')
install=chevren.install
depends=('python' 'python-pytorch-cuda' 'ffmpeg' 'yt-dlp' 'mpv')
makedepends=('python-pip' 'python-virtualenv' 'rust' 'cargo')
source=("$pkgname-$pkgver.tar.gz::https://github.com/yeggis/$pkgname/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('b487447ef6182c2db059e052639e02f76010b7f007ed5b7c5885b943b7f07416')

# build(): cargo build --release
# package(): venv oluştur, pip install requirements.txt, shebang düzelt,
#            src/ kopyala, chevren wrapper kur, chevren-server binary kur,
#            systemd user service kur
```

---

### Dosya: `Makefile`

```makefile
aur-update:
    updpkgsums
    git add PKGBUILD && git commit -m "chore: update sha256sums"
    git pull --rebase
    makepkg --printsrcinfo > .SRCINFO
    cp PKGBUILD .SRCINFO ../chevren-aur/
    # chevren-aur'a push

release:
    rm -f dist/chevren-extension.zip
    mkdir -p dist
    cd extension && zip -r ../dist/chevren-extension.zip . -x "*.zip"
```

---

### Dosya: `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "chevren"
version = "1.0.11"
description = "YouTube videolarını yerel Whisper + Gemini ile Türkçe altyazıya çevirir"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }

dependencies = [
    "faster-whisper>=1.0",
    "google-generativeai>=0.8",
    "platformdirs>=4.0",
    "urllib3>=2.0",
    "charset-normalizer>=3.0",
    "prompt-toolkit>=3.0",
]

[project.scripts]
chevren = "cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-dir]
"" = "src"
```

---

### Dosya: `requirements.txt`

```
faster-whisper==1.2.1
google-genai==1.70.0
urllib3==2.6.3
charset-normalizer==3.4.6
```

---

### Dosya: `chevren.lua`

```lua
-- MPV Lua script — dosya yüklenince otomatik çeviri başlatır
-- on_file_loaded():
--   1. video_id al (URL veya filename[:40])
--   2. POST /generate → pipeline başlat (arka planda)
--   3. 1.5sn'de bir /status?v={id} poll et
--   4. stage=="ready" olunca: sub-add cache_file → MPV'ye yükle
-- Timeout: 600 saniye
```

---

### Dosya: `chevren.install`

```bash
post_install()  { systemctl --user enable --now chevren-server 2>/dev/null || true; }
post_upgrade()  { systemctl --user restart chevren-server 2>/dev/null || true; }
post_remove()   { systemctl --user disable --now chevren-server 2>/dev/null || true; }
```

---

### Dosya: `server/systemd/chevren-server.service`

```ini
[Unit]
Description=Chevren HTTP server
After=network.target

[Service]
ExecStart=/usr/bin/chevren-server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

---

### Dosya: `docs/updates.json`

```json
{
  "addons": {
    "chevren@yeggis": {
      "updates": [
        {"version": "0.1.0", "update_link": "...ext-v0.1.0/chevren.xpi"},
        {"version": "0.1.1", "update_link": "...ext-v0.1.1/chevren.xpi"}
      ]
    }
  }
}
```

---

### Dosya: `tests/test_quota_callback.py`

```python
"""Kota callback mekanizmasını mock ile test eder — gerçek API çağrısı yapmaz."""
# Test 1: _translate_chunk → on_quota_event callback'i tetikliyor mu?
#   MockPool: generate_content her zaman 429 fırlatır
#   Beklenilen: events listesinde >= 1 olay
# Test 2: _make_quota_callback → _status'u doğru parametrelerle çağırıyor mu?
#   cb(exhausted=False, ...) → stage="translating", "Kota doldu" message
#   cb(exhausted=True, ...)  → stage="translating", "İngilizce" message
```

---

### Dosya: `LICENSE`

MIT License — Copyright (c) 2026 yeggis

---

## 🔄 BEKLEYEN SORUNLAR (Son Güncellemeden)

1. **Log popup kaybolma** — background script veya content.js mesajıyla çözülecek
2. **ext-v0.1.2 AMO release** — overlay navigation fix içeriyor
3. **Prompt bağlam iyileştirmesi** — çeviri kalitesi (C adımı)

---

## ✅ SON OTURUMDA TAMAMLANANLAR

- `src/pipeline.py`: Gemini kota dolumu ve model rotasyonu durumlarını yakalayıp `_status` üzerinden bildiren callback yapısı kuruldu
- `extension/content.js`:
  - "translating" aşamasında gelen özel mesajların (kota uyarısı vb.) gösterimi sağlandı
  - YouTube SPA navigasyonu sonrası silinen arayüz elemanlarını polling döngüsü içinde otomatik yeniden enjekte eden "self-healing" mekanizması eklendi

---

*Bu dosya otomatik olarak oluşturulmuştur. Kaynak: /home/yeggiss/Genel/projects/chevren*
