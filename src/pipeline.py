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


def _fetch_youtube_transcript(source: str, workdir: Path, lang: str) -> str | None:
    """YouTube'un kendi transkriptini çeker, SRT string döner.
    Yoksa veya hata olursa None döner."""
    if not source.startswith("http"):
        return None
    if not config.get("use_youtube_transcript"):
        return None
    try:
        vtt_path = workdir / "transcript.vtt"
        args = [
            "yt-dlp",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", lang,
            "--sub-format", "vtt",
            "--skip-download",
            "--no-warnings",
            "-o", str(workdir / "transcript"),
            source,
        ]
        kind, value = _detect_cookie_browser()
        if kind == "file":
            args += ["--cookies", value]
        elif kind == "browser":
            args += ["--cookies-from-browser", value]
        result = subprocess.run(args, capture_output=True, text=True)
        # yt-dlp dosyayı {lang}.vtt veya {lang}-auto.vtt olarak kaydeder
        candidates = list(workdir.glob("transcript*.vtt"))
        if not candidates:
            return None
        vtt_content = candidates[0].read_text(encoding="utf-8")
        return _vtt_to_srt(vtt_content)
    except Exception as e:
        print(f"  YouTube transkript alınamadı: {e}")
        return None

def _vtt_to_srt(vtt: str) -> str:
    """YouTube auto-caption VTT'yi SRT'ye çevirir.

    YouTube VTT formatı: her ~2s'lik pencere için iki blok gelir:
      Blok A (~10ms): sadece tamamlanmış metin (düz, tag yok)
      Blok B (~2s):   önceki metin + yeni kelimeler (<c> tag'li)

    Strateji: sadece Blok B'leri al (süre > 50ms), her birinden
    sadece birinci satırı (tamamlanmış metin) oku."""
    import re

    def _ts_to_ms(ts: str) -> int:
        ts = ts.replace(",", ".")
        h, m, s = ts.split(":")
        return int(h) * 3_600_000 + int(m) * 60_000 + int(float(s) * 1000)

    lines = vtt.splitlines()
    segments = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"(\d{2}:\d{2}:[\d.]+)\s*-->\s*(\d{2}:\d{2}:[\d.]+)", line)
        if m:
            start_raw = m.group(1)
            end_raw = m.group(2)
            duration = _ts_to_ms(end_raw) - _ts_to_ms(start_raw)
            i += 1

            block_lines = []
            while i < len(lines) and lines[i].strip():
                block_lines.append(lines[i].strip())
                i += 1

            # Sadece uzun blokları işle (Blok B), kısa geçiş bloklarını atla
            if duration <= 50:
                continue

            # Birinci satır = tamamlanmış metin (tag'siz)
            completed = None
            for bl in block_lines:
                if not bl or bl == " ":
                    continue
                clean = re.sub(r"<[^>]+>", "", bl).strip()
                if clean:
                    completed = clean
                    break

            if completed:
                start = start_raw.replace(".", ",")
                end = end_raw.replace(".", ",")
                segments.append((start, end, completed))
        else:
            i += 1

    if not segments:
        return ""

    # Ardışık duplicate metinleri birleştir
    merged = [list(segments[0])]
    for start, end, text in segments[1:]:
        if text == merged[-1][2]:
            merged[-1][1] = end
        else:
            merged.append([start, end, text])

    lines_out = []
    for idx, (start, end, text) in enumerate(merged, 1):
        lines_out.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines_out)

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
                print(f"  Chunk {chunk_index}: [{pool.label(model)}] kota doldu → rotasyon")
                if not pool.exhaust_current_key(model):
                    print(f"  Chunk {chunk_index}: tüm key ve modeller tükendi, İngilizce bırakıldı.")
                    return blocks
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


def _translate(srt_en: str) -> str:
    pool = _KeyPool(config.get_api_keys(), config.get("gemini_model"))
    blocks = _parse_srt(srt_en)
    chunks = [blocks[i : i + CHUNK_SIZE] for i in range(0, len(blocks), CHUNK_SIZE)]
    tr_all = []
    for ci, chunk in enumerate(chunks, 1):
        print(f"  Çeviri: {ci}/{len(chunks)}")
        tr_all.extend(_translate_chunk(pool, chunk, ci))
    return _blocks_to_srt(tr_all)


def _srt_to_segments(srt: str):
    """SRT string'i streaming loop'u için segment iterator'a çevirir.
    Her eleman .text ve zaman damgası içeren basit nesne döner."""
    class _Seg:
        __slots__ = ("start", "end", "text")
        def __init__(self, start, end, text):
            self.start = start
            self.end = end
            self.text = text

    def _ts_to_sec(ts: str) -> float:
        ts = ts.replace(",", ".")
        parts = ts.split(":")
        h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s

    blocks = _parse_srt(srt)
    result = []
    for b in blocks:
        parts = b["ts"].split(" --> ")
        result.append(_Seg(_ts_to_sec(parts[0]), _ts_to_sec(parts[1]), b["text"]))
    return result

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

    # YouTube transkriptini dene
    _status(stage="downloading", video_id=video_id)
    yt_srt = _fetch_youtube_transcript(source, workdir, source_lang)

    if yt_srt:
        print("  YouTube transkripti kullanılıyor.")
        _status(stage="transcribing", video_id=video_id, message="YouTube transkripti")
        segments = _srt_to_segments(yt_srt)
        use_whisper = False
    else:
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
        use_whisper = True


    srt_path = cache.path(video_id)
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("", encoding="utf-8")
    pending = []
    seg_count = 0
    blk_count = 0
    chunk_num = 0
    ready_sent = False
    for seg in (segments if use_whisper else iter(segments)):
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
        translated = _translate_chunk(pool, pending, chunk_num)
        translated = _renumber(translated, blk_count + 1)
        _append_srt(srt_path, translated)
        _status(stage="translating", chunk=chunk_num, video_id=video_id)
        _reload_mpv_subs(srt_path)

    if use_whisper:
        del model
        gc.collect()
        cache.write(video_id, srt_path.read_text(encoding="utf-8"))
    if not ready_sent and on_ready:
        on_ready(srt_path)
    _status(stage="ready", video_id=video_id)
    print(f"Tamamlandı → {srt_path}")
    return srt_path
