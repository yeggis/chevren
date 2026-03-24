"""
pipeline.py — chevren ana pipeline
YouTube URL veya yerel dosya → Türkçe SRT
"""
import gc
import time
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(APP_DIR))

import cache
import config

CHUNK_SIZE = 150
STREAM_CHUNK = 30  # streaming modunda kaç segment birikince çeviri başlasın


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h,  ms = divmod(ms, 3_600_000)
    m,  ms = divmod(ms, 60_000)
    s,  ms = divmod(ms, 1_000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def _parse_srt(content: str) -> list[dict]:
    blocks = []
    for block in content.strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) >= 3:
            blocks.append({
                "num":  lines[0],
                "ts":   lines[1],
                "text": "\n".join(lines[2:])
            })
    return blocks


def _blocks_to_srt(blocks: list[dict]) -> str:
    lines = []
    for b in blocks:
        lines += [b["num"], b["ts"], b["text"], ""]
    return "\n".join(lines)


def _extract_audio(source: str, workdir: Path) -> Path:
    wav = workdir / "audio.wav"
    if source.startswith("http"):
        m4a = workdir / "audio.m4a"
        subprocess.run(["yt-dlp", "-f", "140", source, "-o", str(m4a)], check=True)
        subprocess.run(["ffmpeg", "-y", "-i", str(m4a), "-ar", "16000", "-ac", "1", str(wav)], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-i", source, "-ar", "16000", "-ac", "1", str(wav)], check=True)
    return wav

GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash",
]

def _translate_chunk(client, model_name: str, blocks: list[dict], chunk_index: int) -> list[dict]:
    """Bir segment grubunu Türkçe'ye çevirir, hata durumunda retry yapar."""
    prompt = (
        "Translate English SRT to Turkish. "
        "Keep timestamps and numbers exactly. "
        "Output ONLY the translated SRT.\n\n"
        + _blocks_to_srt(blocks)
    )
    models_to_try = [model_name] + [m for m in GEMINI_FALLBACK_MODELS if m != model_name]
    max_retries = 3
    for model in models_to_try:
        for attempt in range(max_retries):
            try:
                tr_text = client.models.generate_content(model=model, contents=prompt).text.strip()
                tr_text = tr_text.replace("```srt", "").replace("```", "").strip()
                tr_chunk = _parse_srt(tr_text)
                while len(tr_chunk) < len(blocks):
                    tr_chunk.append(blocks[len(tr_chunk)])
                return tr_chunk
            except Exception as e:
                err = str(e)
                is_quota = "429" in err or "RESOURCE_EXHAUSTED" in err
                print(f"  Chunk {chunk_index} hatası [{model}] (deneme {attempt+1}/{max_retries}): {e}")
                if is_quota:
                    print(f"  Kota doldu, sonraki modele geçiliyor...")
                    break
                if attempt < max_retries - 1:
                    import re
                    match = re.search(r'retryDelay.*?(\d+)s', err)
                    wait = int(match.group(1)) + 2 if match else 5 * (attempt + 1)
                    print(f"  {wait} saniye bekleniyor...")
                    time.sleep(wait)
                else:
                    break
    print(f"  Chunk {chunk_index} tüm modeller denendi, İngilizce bırakıldı.")
    return blocks

def _translate(srt_en: str) -> str:
    """Eski toplu çeviri — geriye dönük uyumluluk için korundu."""
    from google import genai
    api_key = config.get("gemini_api_key")
    if not api_key:
        raise ValueError("Gemini API key eksik. 'chevren setup' ile ekleyin.")
    client     = genai.Client(api_key=api_key)
    model_name = config.get("gemini_model")
    blocks     = _parse_srt(srt_en)
    chunks     = [blocks[i:i + CHUNK_SIZE] for i in range(0, len(blocks), CHUNK_SIZE)]
    tr_all     = []
    for ci, chunk in enumerate(chunks, 1):
        print(f"  Çeviri: {ci}/{len(chunks)}")
        tr_all.extend(_translate_chunk(client, model_name, chunk, ci))
    return _blocks_to_srt(tr_all)


def _renumber(blocks: list[dict], start: int) -> list[dict]:
    """Blokları verilen numaradan itibaren yeniden numaralandırır."""
    return [{**b, "num": str(start + i)} for i, b in enumerate(blocks)]


def _append_srt(srt_path: Path, blocks: list[dict]) -> None:
    """SRT dosyasına yeni blokları ekler."""
    with open(srt_path, "a", encoding="utf-8") as f:
        for b in blocks:
            f.write(f"{b['num']}\n{b['ts']}\n{b['text']}\n\n")


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
    wav    = _extract_audio(source, workdir)
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
    segments, _ = model.transcribe(str(wav), language="en", beam_size=5, vad_filter=True)
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(f"{i}\n{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}\n{seg.text.strip()}\n")
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
    from google import genai
    from faster_whisper import WhisperModel

    video_id = _extract_video_id(source)
    if cache.exists(video_id):
        print(f"Cache bulundu: {video_id}")
        srt_path = cache.path(video_id)
        if on_ready:
            on_ready(srt_path)
        return srt_path

    print(f"İşleniyor: {source}")
    workdir.mkdir(parents=True, exist_ok=True)

    # Ses indir
    wav = _extract_audio(source, workdir)

    # Gemini client hazırla
    api_key = config.get("gemini_api_key")
    if not api_key:
        raise ValueError("Gemini API key eksik. 'chevren setup' ile ekleyin.")
    client     = genai.Client(api_key=api_key)
    model_name = config.get("gemini_model")

    # Whisper modelini yükle
    model = WhisperModel(
        config.get("whisper_model"),
        device=config.get("whisper_device"),
        compute_type=config.get("compute_type"),
    )
    segments, _ = model.transcribe(str(wav), language="en", beam_size=5, vad_filter=True)

    # SRT dosyasını hazırla (boş)
    srt_path = cache.path(video_id)
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("", encoding="utf-8")

    pending    = []   # henüz çevrilmemiş İngilizce bloklar
    seg_count  = 0    # toplam segment sayısı
    blk_count  = 0    # SRT'ye yazılan toplam blok sayısı
    chunk_num  = 0    # çeviri chunk sayacı
    ready_sent = False

    for seg in segments:
        seg_count += 1
        pending.append({
            "num":  str(seg_count),
            "ts":   f"{_fmt_ts(seg.start)} --> {_fmt_ts(seg.end)}",
            "text": seg.text.strip()
        })

        # STREAM_CHUNK kadar segment birikince çevir ve yaz
        if len(pending) >= STREAM_CHUNK:
            chunk_num += 1
            print(f"  Çeviri: chunk {chunk_num} ({seg_count} segment işlendi)")
            translated = _translate_chunk(client, model_name, pending, chunk_num)
            translated = _renumber(translated, blk_count + 1)
            _append_srt(srt_path, translated)
            blk_count += len(translated)
            pending.clear()

            # İlk chunk hazır olunca mpv'yi başlat
            if not ready_sent and on_ready:
                on_ready(srt_path)
                ready_sent = True

    # Kalan segmentleri çevir
    if pending:
        chunk_num += 1
        print(f"  Çeviri: chunk {chunk_num} (son)")
        translated = _translate_chunk(client, model_name, pending, chunk_num)
        translated = _renumber(translated, blk_count + 1)
        _append_srt(srt_path, translated)

    del model
    gc.collect()

    # Cache'e kaydet
    cache.write(video_id, srt_path.read_text(encoding="utf-8"))

    # Eğer on_ready hiç çağrılmadıysa (çok kısa video) şimdi çağır
    if not ready_sent and on_ready:
        on_ready(srt_path)

    print(f"Tamamlandı → {srt_path}")
    return srt_path
