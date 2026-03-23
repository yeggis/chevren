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
