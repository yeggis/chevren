"""
cache.py — chevren cache yönetimi
Her video için klasör tabanlı yapı:
  ~/.cache/chevren/VIDEO_ID/
      meta.json
      en.srt
      tr.srt   (varsa)
      thumb.jpg (varsa)
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "chevren"


def _video_dir(video_id: str) -> Path:
    return CACHE_DIR / video_id


def _ensure(video_id: str) -> Path:
    d = _video_dir(video_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── SRT ──────────────────────────────────────────────────────────────────────

def path(video_id: str, lang: str = "tr") -> Path:
    """~/.cache/chevren/VIDEO_ID/LANG.srt"""
    return _video_dir(video_id) / f"{lang}.srt"


def exists(video_id: str, lang: str = "en") -> bool:
    return path(video_id, lang).exists()


def read(video_id: str, lang: str = "tr") -> str:
    return path(video_id, lang).read_text(encoding="utf-8")


def write(video_id: str, content: str, lang: str = "tr") -> None:
    d = _ensure(video_id)
    (d / f"{lang}.srt").write_text(content, encoding="utf-8")


# ── META ─────────────────────────────────────────────────────────────────────

def meta_path(video_id: str) -> Path:
    return _video_dir(video_id) / "meta.json"


def read_meta(video_id: str) -> dict:
    p = meta_path(video_id)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def write_meta(video_id: str, data: dict) -> None:
    d = _ensure(video_id)
    existing = read_meta(video_id)
    existing.update(data)
    (d / "meta.json").write_text(
        json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def touch_meta(video_id: str, source: str) -> None:
    """İlk kez cache açılınca temel alanları yazar, varsa üzerine yazmaz."""
    existing = read_meta(video_id)
    if "cached_at" not in existing:
        write_meta(video_id, {
            "video_id": video_id,
            "source": source,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "langs": [],
        })


def mark_lang(video_id: str, lang: str) -> None:
    """Meta'daki langs listesine dil ekler."""
    meta = read_meta(video_id)
    langs = meta.get("langs") or []
    if lang not in langs:
        langs.append(lang)
    write_meta(video_id, {"langs": langs})


# ── THUMBNAIL ────────────────────────────────────────────────────────────────

def thumb_path(video_id: str) -> Path:
    return _video_dir(video_id) / "thumb.jpg"


def thumb_exists(video_id: str) -> bool:
    return thumb_path(video_id).exists()


# ── LIST / CLEAR ─────────────────────────────────────────────────────────────

def list_all() -> list[dict]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for d in sorted(CACHE_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        meta = read_meta(d.name)
        en_srt = d / "en.srt"
        tr_srt = d / "tr.srt"
        size_kb = sum(f.stat().st_size for f in d.iterdir() if f.is_file()) / 1024
        entries.append({
            "video_id":  d.name,
            "title":     meta.get("title", d.name),
            "source":    meta.get("source", ""),
            "cached_at": meta.get("cached_at", ""),
            "langs":     meta.get("langs", []),
            "has_thumb": (d / "thumb.jpg").exists(),
            "en_path":   str(en_srt) if en_srt.exists() else None,
            "tr_path":   str(tr_srt) if tr_srt.exists() else None,
            "size_kb":   round(size_kb, 1),
        })
    return entries


def clear() -> int:
    import shutil
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for d in CACHE_DIR.iterdir():
        if d.is_dir():
            shutil.rmtree(d)
            count += 1
        elif d.suffix == ".srt":
            # eski flat dosyaları da temizle
            d.unlink()
    return count
