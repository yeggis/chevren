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


def _status(**kw):
    print(f"CHEVREN_STATUS:{_json.dumps(kw)}", flush=True)


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
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash",
]


class _KeyPool:
    """Çoklu API key + model rotasyonu. Kota dolunca sıradaki key/model'e geçer."""

    def __init__(self, keys: list[str], base_model: str):
        from google import genai

        if not keys:
            raise ValueError("Gemini API key eksik. 'chevren setup' ile ekleyin.")
        self.base_model = base_model
        self._clients = [genai.Client(api_key=k) for k in keys]
        self._exhausted: dict[int, set] = {i: set() for i in range(len(keys))}
        self._idx = 0

    @property
    def client(self):
        return self._clients[self._idx]

    def _available(self, idx: int) -> list[str]:
        all_m = [self.base_model] + [
            m for m in GEMINI_FALLBACK_MODELS if m != self.base_model
        ]
        return [m for m in all_m if m not in self._exhausted[idx]]

    @property
    def current_model(self) -> str | None:
        m = self._available(self._idx)
        return m[0] if m else None

    def exhaust_model(self, model: str) -> None:
        self._exhausted[self._idx].add(model)

    def advance(self) -> bool:
        """Sonraki kullanılabilir key'e geç. False → hepsi tükendi."""
        for i in range(self._idx + 1, len(self._clients)):
            if self._available(i):
                print(f"  API key rotasyonu: key[{self._idx}] → key[{i}]")
                self._idx = i
                return True
        return False

    def label(self, model: str) -> str:
        return f"key[{self._idx}]/{model}"


def _translate_chunk(
    pool: "_KeyPool", blocks: list[dict], chunk_index: int
) -> list[dict]:
    """Bir segment grubunu çevirir. Kota bitince key/model rotasyonu yapar,
    chunk asla atlanmaz — tüm key+model combolar tükenirse İngilizce bırakır."""
    import re

    texts = [b["text"] for b in blocks]
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    prompt = (
        "Translate each numbered line to Turkish. "
        "Output ONLY the translations, one per line, with the same numbers. "
        "Example: '1. Hello' → '1. Merhaba'. "
        "Do not add any other text or explanation.\n\n" + numbered
    )

    attempt = 0
    while True:
        model = pool.current_model
        if model is None:
            if not pool.advance():
                print(
                    f"  Chunk {chunk_index}: tüm key ve modeller tükendi, İngilizce bırakıldı."
                )
                return blocks
            attempt = 0
            continue

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
                m = re.match(r"^(\d+)\.\s*(.*)", line)
                if m:
                    tr_lines[int(m.group(1))] = m.group(2)

            return [
                {**b, "text": tr_lines.get(i + 1, b["text"])}
                for i, b in enumerate(blocks)
            ]

        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                print(
                    f"  Chunk {chunk_index}: [{pool.label(model)}] kota doldu → rotasyon"
                )
                pool.exhaust_model(model)
                attempt = 0
                # model yoksa advance() while başında tetiklenir
                continue

            attempt += 1
            if attempt >= 3:
                print(
                    f"  Chunk {chunk_index}: [{pool.label(model)}] 3 denemede başarısız → model değiştir"
                )
                pool.exhaust_model(model)
                attempt = 0
                continue

            match = re.search(r"retryDelay.*?(\d+)s", err)
            wait = int(match.group(1)) + 2 if match else 5 * attempt
            print(f"  Chunk {chunk_index}: hata (deneme {attempt}/3): {e}")
            print(f"  {wait} saniye bekleniyor...")
            time.sleep(wait)


def _translate(srt_en: str) -> str:
    pool = _KeyPool(config.get_api_keys(), config.get("gemini_model"))
    blocks = _parse_srt(srt_en)
    chunks = [blocks[i : i + CHUNK_SIZE] for i in range(0, len(blocks), CHUNK_SIZE)]
    tr_all = []
    for ci, chunk in enumerate(chunks, 1):
        print(f"  Çeviri: {ci}/{len(chunks)}")
        tr_all.extend(_translate_chunk(pool, chunk, ci))
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
    srt_tr = _translate(srt_en)
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
    from faster_whisper import WhisperModel
    from google import genai

    video_id = _extract_video_id(source)
    if cache.exists(video_id):
        print(f"Cache bulundu: {video_id}")
        srt_path = cache.path(video_id)
        if on_ready:
            on_ready(srt_path)
        return srt_path

    print(f"İşleniyor: {source}")
    workdir.mkdir(parents=True, exist_ok=True)

    _status(stage="downloading", video_id=video_id)
    wav = _extract_audio(source, workdir)

    pool = _KeyPool(config.get_api_keys(), config.get("gemini_model"))

    _status(stage="transcribing", video_id=video_id)
    model = WhisperModel(
        config.get("whisper_model"),
        device=config.get("whisper_device"),
        compute_type=config.get("compute_type"),
    )
    segments, _ = model.transcribe(
        str(wav), language="en", beam_size=5, vad_filter=True
    )

    srt_path = cache.path(video_id)
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("", encoding="utf-8")

    pending = []
    seg_count = 0
    blk_count = 0
    chunk_num = 0
    ready_sent = False

    for seg in segments:
        seg_count += 1
        pending.append(
            {
                "num": str(seg_count),
                "ts": f"{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}",
                "text": seg.text.strip(),
            }
        )
        if len(pending) >= STREAM_CHUNK:
            chunk_num += 1
            print(f"  Çeviri: chunk {chunk_num} ({seg_count} segment işlendi)")
            translated = _translate_chunk(pool, pending, chunk_num)
            translated = _renumber(translated, blk_count + 1)
            _append_srt(srt_path, translated)
            _status(stage="translating", chunk=chunk_num, video_id=video_id)
            _reload_mpv_subs(srt_path)
            blk_count += len(translated)
            pending.clear()
            if not ready_sent and on_ready:
                on_ready(srt_path)
                ready_sent = True

    if pending:
        chunk_num += 1
        print(f"  Çeviri: chunk {chunk_num} (son)")
        translated = _translate_chunk(
            client, model_name, pending, chunk_num, exhausted_models
        )
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
