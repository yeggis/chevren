# chevren — ayar yönetimi
"""
config.py — chevren ayar yönetimi
"""
import json
from pathlib import Path

CONFIG_DIR  = Path.home() / ".config" / "chevren"
CONFIG_FILE = CONFIG_DIR / "config.json"

def detect_hardware() -> dict:
    info = {
        "gpu_name":      "CPU",
        "vram_gb":       0,
        "device":        "cpu",
        "compute_type":  "int8",
        "whisper_model": "base",
    }
    try:
        import torch
        if torch.cuda.is_available():
            props   = torch.cuda.get_device_properties(0)
            vram_gb = props.total_memory / (1024 ** 3)
            info.update({
                "gpu_name":     torch.cuda.get_device_name(0),
                "vram_gb":      round(vram_gb, 1),
                "device":       "cuda",
            })
            if vram_gb >= 10:
                info["whisper_model"] = "large-v3-turbo"
                info["compute_type"]  = "float16"
            elif vram_gb >= 7:
                info["whisper_model"] = "large-v3-turbo"
                info["compute_type"]  = "int8"
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
        "gemini_api_key":  "",
        "gemini_model":    "gemini-2.5-flash-lite",
        "whisper_model":   hw["whisper_model"],
        "whisper_device":  hw["device"],
        "compute_type":    hw["compute_type"],
        "player":          "mpv",
        "_gpu_name":       hw["gpu_name"],
        "_vram_gb":        hw["vram_gb"],
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

def get(key: str):
    return load().get(key)

def set_key(key: str, value) -> None:
    cfg = load()
    cfg[key] = value
    save(cfg)

def hardware_summary() -> str:
    cfg = load()
    gpu  = cfg.get("_gpu_name", "CPU")
    vram = cfg.get("_vram_gb", 0)
    return f"{gpu} · {vram} GB VRAM" if vram else "CPU"
