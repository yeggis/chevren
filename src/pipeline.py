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
MERGE_MIN_DURATION = 1.5   # saniyeden kısa segmentleri birleştir
MERGE_MIN_CHARS = 42       # karakterden kısa segmentleri birleştir
LOOKAHEAD = 3              # çift yönlü window için ileri/geri kaç blok


def _status(**kw):
    import json
    import urllib.request

    # Terminale de yazmaya devam etsin (debug için)
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


def _parse_duration(ts: str) -> float:
    """'HH:MM:SS,mmm --> HH:MM:SS,mmm' → saniye cinsinden süre."""
    start, end = ts.split(" --> ")
    def _to_sec(t):
        h, m, s_ms = t.strip().split(":")
        s, ms = s_ms.replace(",", ".").split(".")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    return _to_sec(end) - _to_sec(start)


def _max_chars(ts: str) -> int:
    """Segment süresiyle orantılı max karakter limiti (Netflix ~17 cps)."""
    return max(42, int(_parse_duration(ts) * 17))


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


def _fetch_thumbnail(source: str, video_id: str, workdir: Path) -> bool:
    """Thumbnail indirir veya ffmpeg ile üretir. Başarılıysa True döner."""
    import shutil
    dest = cache.thumb_path(video_id)
    if dest.exists():
        return True

    # YouTube: yt-dlp ile thumbnail indir
    if source.startswith("http"):
        thumb_tmp = workdir / "thumb"
        try:
            args = [
                "yt-dlp",
                "--no-playlist",
                "--write-thumbnail",
                "--skip-download",
                "--convert-thumbnails", "jpg",
                "-o", str(thumb_tmp),
                source,
            ]
            kind, value = _detect_cookie_browser()
            if kind == "file":
                args += ["--cookies", value]
            elif kind == "browser":
                args += ["--cookies-from-browser", value]
            subprocess.run(args, check=True, capture_output=True)
            # yt-dlp thumb.jpg veya thumb.webp.jpg gibi üretebilir
            candidates = list(workdir.glob("thumb*.jpg"))
            if candidates:
                shutil.copy(candidates[0], dest)
                return True
        except Exception:
            pass

    # Fallback: ffmpeg ile 10. saniyeden kare al
    # YouTube için m4a zaten indirildi, yerel dosya için source kullan
    video_source = str(workdir / "audio.m4a") if source.startswith("http") else source
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", "10",
                "-i", video_source,
                "-vframes", "1",
                "-q:v", "2",
                str(dest),
            ],
            check=True, capture_output=True,
        )
        return dest.exists()
    except Exception:
        return False


def _fetch_meta(source: str, video_id: str, workdir: Path) -> None:
    """Video başlığı ve süresini meta.json'a yazar."""
    if source.startswith("http"):
        try:
            args = [
                "yt-dlp",
                "--no-playlist",
                "--print", "%(title)s\t%(duration)s",
                "--skip-download",
                source,
            ]
            kind, value = _detect_cookie_browser()
            if kind == "file":
                args += ["--cookies", value]
            elif kind == "browser":
                args += ["--cookies-from-browser", value]
            out = subprocess.check_output(args, text=True).strip()
            parts = out.split("\t")
            title = parts[0] if parts else video_id
            duration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            cache.write_meta(video_id, {"title": title, "duration_sec": duration})
        except Exception:
            pass
    else:
        # Yerel dosya: ffprobe ile süre al, başlık = dosya adı
        try:
            out = subprocess.check_output(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    source,
                ],
                text=True,
            ).strip()
            duration = int(float(out)) if out else 0
            cache.write_meta(video_id, {
                "title": Path(source).stem,
                "duration_sec": duration,
            })
        except Exception:
            cache.write_meta(video_id, {"title": Path(source).stem})


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
    context_before: list[dict] | None = None,
    context_after: list[dict] | None = None,
    on_quota_event=None,
) -> list[dict]:
    """Bir segment grubunu çevirir. Kota bitince key/model rotasyonu yapar,
    chunk asla atlanmaz — tüm key+model combolar tükenirse İngilizce bırakır.
    context_before/after: önceki/sonraki chunk'tan bloklar — çevrilmez, sadece bağlam için."""
    import re

    texts = [b["text"] for b in blocks]
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))

    _pn = _protected_names_rule()

    # Timing constraint: her satır için süre ve karakter limiti
    timing_lines = []
    for i, b in enumerate(blocks):
        dur = _parse_duration(b["ts"])
        mc = _max_chars(b["ts"])
        timing_lines.append(f"{i+1}. [{dur:.1f}s, max {mc} chars] {b['text']}")
    numbered_with_timing = "\n".join(timing_lines)

    ctx_before_text = "\n".join(f"[before] {b['text']}" for b in (context_before or []))
    ctx_after_text  = "\n".join(f"[after] {b['text']}"  for b in (context_after  or []))

    parts = []
    if ctx_before_text:
        parts.append(ctx_before_text)
    parts.append(numbered_with_timing)
    if ctx_after_text:
        parts.append(ctx_after_text)
    prompt_body = "\n".join(parts)

    has_ctx = ctx_before_text or ctx_after_text
    ctx_note = (
        " Lines starting with [before] or [after] are context only — DO NOT translate them."
        if has_ctx else ""
    )
    prompt = (
        "Translate each NUMBERED line to Turkish."
        + _pn
        + ctx_note
        + " Each line shows display duration and max character limit in brackets — respect these limits."
        " Output ONLY the numbered translations, one per line, using EXACTLY this format: N. translation"
        " (number, dot, space, text). No bold, no parentheses, no extra lines, no explanation."
        " Example: '1. Hello world' → '1. Merhaba dünya'.\n\n"
        + prompt_body
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
        ctx_before = tr_all[-CONTEXT_SIZE:] if tr_all else None
        ctx_after  = chunks[ci][:LOOKAHEAD] if ci < len(chunks) else None  # ci 1-indexed, chunks 0-indexed; sadece ilk LOOKAHEAD blok
        tr_all.extend(_translate_chunk(pool, chunk, ci, context_before=ctx_before, context_after=ctx_after, on_quota_event=_make_quota_callback(video_id)))
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
    target_lang = config.get("target_lang") or "tr"
    if cache.exists(video_id, "en"):
        print(f"Cache bulundu: {video_id}")
        # target_lang SRT'si varsa onu, yoksa en.srt'i aç
        srt_path = cache.path(video_id, target_lang) if cache.exists(video_id, target_lang) else cache.path(video_id, "en")
        if on_ready:
            on_ready(srt_path)
        _status(stage="ready", video_id=video_id)
        return srt_path
    print(f"İşleniyor: {source}", flush=True)
    workdir.mkdir(parents=True, exist_ok=True)
    source_lang = config.get("source_lang") or "en"
    pool = _KeyPool(config.get_api_keys(), config.get("gemini_model"))
    cache.touch_meta(video_id, source)
    _status(stage="downloading", video_id=video_id)
    wav = _extract_audio(source, workdir)
    # Meta ve thumbnail arka planda değil, ses indirildikten hemen sonra
    _fetch_meta(source, video_id, workdir)
    _fetch_thumbnail(source, video_id, workdir)
    _status(stage="transcribing", video_id=video_id)
    model = WhisperModel(
        config.get("whisper_model"),
        device=config.get("whisper_device"),
        compute_type=config.get("compute_type"),
    )
    segments, _ = model.transcribe(
        str(wav), language=source_lang, beam_size=5, vad_filter=True
    )
    en_srt_path = cache.path(video_id, "en")
    en_srt_path.parent.mkdir(parents=True, exist_ok=True)
    en_srt_path.write_text("", encoding="utf-8")
    target_lang = config.get("target_lang") or "tr"
    do_translate = target_lang != source_lang
    tr_srt_path = cache.path(video_id, target_lang) if do_translate else None
    if tr_srt_path:
        tr_srt_path.write_text("", encoding="utf-8")
    pending = []
    translated = []
    seg_count = 0
    blk_count = 0
    chunk_num = 0
    tr_chunk_num = 0
    ready_sent = False
    debug_lines = [] if config.get("debug_save_transcript") else None

    def _flush_chunk(to_translate, is_last=False):
        """Bir EN chunk'ını yazar, gerekirse Gemini'ye gönderir, overlay'i günceller."""
        nonlocal blk_count, translated, ready_sent, tr_chunk_num, chunk_num

        chunk_num += 1
        ctx_before = [{"text": b["text"], "ts": b["ts"]} for b in translated[-LOOKAHEAD:]] if translated else None
        ctx_after_blocks = pending[STREAM_CHUNK:STREAM_CHUNK + LOOKAHEAD] if not is_last else []
        ctx_after = [{"text": b["text"], "ts": b["ts"]} for b in ctx_after_blocks] if ctx_after_blocks else None

        en_chunk = _renumber(to_translate, blk_count + 1)
        _append_srt(en_srt_path, en_chunk)
        cache.mark_lang(video_id, source_lang)

        _status(stage="transcribing", chunk=chunk_num, video_id=video_id)

        if do_translate:
            tr_chunk_num += 1
            print(f"  Çeviri: chunk {tr_chunk_num} ({seg_count} segment işlendi)")
            result = _translate_chunk(
                pool, to_translate, tr_chunk_num,
                context_before=ctx_before, context_after=ctx_after,
                on_quota_event=_make_quota_callback(video_id),
            )
            result = _renumber(result, blk_count + 1)
            _append_srt(tr_srt_path, result)
            cache.mark_lang(video_id, target_lang)
            _status(stage="translating", chunk=tr_chunk_num, video_id=video_id)

            # İlk TR chunk hazır → MPV'yi aç
            if not ready_sent and on_ready:
                on_ready(tr_srt_path)
                ready_sent = True
                _reload_mpv_subs(tr_srt_path)
            else:
                _reload_mpv_subs(tr_srt_path)
        else:
            result = en_chunk
            # Çeviri yok → EN chunk hazır olunca MPV'yi aç
            if not ready_sent and on_ready:
                on_ready(en_srt_path)
                ready_sent = True
                _reload_mpv_subs(en_srt_path)
            else:
                _reload_mpv_subs(en_srt_path)

        blk_count += len(result)
        translated = result

        # İptal kontrolü — her chunk sonrası server'a sor
        try:
            import urllib.request as _ur
            with _ur.urlopen("http://127.0.0.1:7373/cancel/check", timeout=1) as _r:
                if _r.read().decode().strip() == "cancel":
                    print("Pipeline iptal edildi.", flush=True)
                    import shutil
                    cache_dir = cache.path(video_id, "en").parent
                    if cache_dir.exists():
                        shutil.rmtree(cache_dir)
                    raise SystemExit(0)
        except SystemExit:
            raise
        except Exception:
            pass

    for seg in segments:
        seg_count += 1
        new_block = {
            "num": str(seg_count),
            "ts": f"{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}",
            "text": seg.text.strip(),
        }
        if debug_lines is not None:
            debug_lines.append(
                f"{seg_count}\n{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}\n{seg.text.strip()}\n"
            )
        # A: Segment birleştirme
        if pending:
            last = pending[-1]
            last_dur = _parse_duration(last["ts"])
            last_chars = len(last["text"])
            if last_dur < MERGE_MIN_DURATION or last_chars < MERGE_MIN_CHARS:
                last_start = last["ts"].split(" --> ")[0]
                new_end    = new_block["ts"].split(" --> ")[1]
                pending[-1] = {
                    "num":  last["num"],
                    "ts":   f"{last_start} --> {new_end}",
                    "text": last["text"] + " " + new_block["text"],
                }
                if debug_lines is not None:
                    debug_lines[-1] = (
                        f"{last['num']}\n{last_start} --> {new_end}\n"
                        f"{last['text']} {new_block['text']}\n"
                    )
                continue
        pending.append(new_block)

        # B: Lookahead buffer dolunca flush
        if len(pending) >= STREAM_CHUNK + LOOKAHEAD:
            _flush_chunk(pending[:STREAM_CHUNK])
            pending = pending[STREAM_CHUNK:]

    if debug_lines is not None:
        debug_path = cache.path(video_id, "en.debug")
        debug_path.write_text("\n".join(debug_lines), encoding="utf-8")

    # Son chunk
    if pending:
        _flush_chunk(pending, is_last=True)
        pending = []

    del model
    gc.collect()

    if not ready_sent and on_ready:
        # Hiç chunk flush olmadıysa (çok kısa video) doğru path'i seç
        fallback = tr_srt_path if (do_translate and tr_srt_path) else en_srt_path
        on_ready(fallback)
    _status(stage="ready", video_id=video_id)
    final_path = tr_srt_path if (do_translate and tr_srt_path) else en_srt_path
    print(f"Tamamlandı → {final_path}")
    return final_path
