"""
pipeline.py — chevren ana pipeline
YouTube URL veya yerel dosya → Türkçe SRT
"""
import gc
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(APP_DIR))

import cache
import config

CHUNK_SIZE = 150

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

def _transcribe(wav: Path) -> str:
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

def _translate(srt_en: str) -> str:
    import google.generativeai as genai
    api_key = config.get("gemini_api_key")
    if not api_key:
        raise ValueError("Gemini API key eksik. 'chevren setup' ile ekleyin.")
    genai.configure(api_key=api_key)
    model     = genai.GenerativeModel(config.get("gemini_model"))
    blocks    = _parse_srt(srt_en)
    chunks    = [blocks[i:i + CHUNK_SIZE] for i in range(0, len(blocks), CHUNK_SIZE)]
    tr_all    = []
    for ci, chunk in enumerate(chunks, 1):
        print(f"  Çeviri: {ci}/{len(chunks)}")
        prompt = (
            "Translate English SRT to Turkish. "
            "Keep timestamps and numbers exactly. "
            "Output ONLY the translated SRT.\n\n"
            + _blocks_to_srt(chunk)
        )
        try:
            tr_text  = model.generate_content(prompt).text.strip()
            tr_text  = tr_text.replace("```srt", "").replace("```", "").strip()
            tr_chunk = _parse_srt(tr_text)
            while len(tr_chunk) < len(chunk):
                tr_chunk.append(chunk[len(tr_chunk)])
            tr_all.extend(tr_chunk)
        except Exception as e:
            print(f"  Chunk {ci} hatası: {e}")
            tr_all.extend(chunk)
    return _blocks_to_srt(tr_all)

def _extract_video_id(source: str) -> str:
    if source.startswith("http"):
        import re
        m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", source)
        return m.group(1) if m else source.split("/")[-1][:11]
    return Path(source).stem[:40]

def run(source: str, workdir: Path) -> Path:
    video_id = _extract_video_id(source)

    if cache.exists(video_id):
        print(f"Cache bulundu: {video_id}")
        return cache.path(video_id)

    print(f"İşleniyor: {source}")
    workdir.mkdir(parents=True, exist_ok=True)

    wav    = _extract_audio(source, workdir)
    srt_en = _transcribe(wav)
    srt_tr = _translate(srt_en)

    cache.write(video_id, srt_tr)
    print(f"Tamamlandı → {cache.path(video_id)}")
    return cache.path(video_id)
