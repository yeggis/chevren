"""
cli.py — chevren komut satırı arayüzü
"""

import argparse
import locale
import os
import subprocess
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(APP_DIR))

import cache
import config
import pipeline


def _is_turkish() -> bool:
    lang = os.environ.get("LANG", "") or locale.getlocale()[0] or ""
    return lang.lower().startswith("tr")


def _help_text() -> str:
    if _is_turkish():
        return """
Chevren — video altyazı aracı

KULLANIM:
  chevren <url veya dosya>              Altyazı oluştur ve izle
  chevren setup                         İlk kurulum sihirbazı
  chevren config <anahtar> <değer>      Ayar değiştir
  chevren cache list                    Kayıtlı altyazıları listele
  chevren cache clear                   Cache'i temizle

ÖRNEKLER:
  chevren https://youtube.com/watch?v=xxx
  chevren film.mp4
  chevren config whisper_model medium
  chevren config gemini_api_key ANAHTARIM

SEÇENEKLER:
  --from   Kaynak dil (varsayılan: en)
  --to     Hedef dil (varsayılan: tr)
  --no-play  Sadece SRT üret, mpv açma
  --version  Versiyon bilgisi
"""
    return """
Chevren — video subtitle tool

USAGE:
  chevren <url or file>                 Generate subtitles and play
  chevren setup                         First-time setup wizard
  chevren config <key> <value>          Change a setting
  chevren cache list                    List cached subtitles
  chevren cache clear                   Clear cache

EXAMPLES:
  chevren https://youtube.com/watch?v=xxx
  chevren movie.mp4
  chevren config whisper_model medium
  chevren config gemini_api_key MYKEY

OPTIONS:
  --from   Source language (default: en)
  --to     Target language (default: tr)
  --no-play  Generate SRT only, do not open mpv
  --version  Version info
"""


def cmd_setup():
    print("Chevren kurulum sihirbazı\n")
    cfg = config.load()

    import getpass

    existing = "●●●●●●●●" if cfg.get("gemini_api_key") else "boş"
    key = getpass.getpass(f"Gemini API key [{existing}]: ").strip()
    if key:
        cfg["gemini_api_key"] = key

    detected = config.detect_hardware()["whisper_model"]
    current = cfg.get("whisper_model", detected)
    model = input(f"Whisper modeli [{detected} önerilen, şu an: {current}]: ").strip()
    cfg["whisper_model"] = model if model else detected
    player = input(f"Oynatıcı [{cfg.get('player', 'mpv')}]: ").strip()
    if player:
        cfg["player"] = player

    config.save(cfg)
    print("\nAyarlar kaydedildi.")
    print(f"Donanım: {config.hardware_summary()}")
    _enable_server_service()


def _enable_server_service():
    import shutil

    if not shutil.which("systemctl"):
        return
    service = Path.home() / ".config/systemd/user/chevren-server.service"
    service.parent.mkdir(parents=True, exist_ok=True)
    system_service = Path("/usr/lib/systemd/user/chevren-server.service")
    if system_service.exists() and not service.exists():
        import shutil as sh

        sh.copy(system_service, service)
    result = subprocess.run(
        ["systemctl", "--user", "enable", "--now", "chevren-server"],
        capture_output=True,
    )
    if result.returncode == 0:
        print("chevren-server servisi aktif edildi.")
    else:
        print(
            "Servis aktif edilemedi, manuel olarak çalıştırın: systemctl --user enable --now chevren-server"
        )


def cmd_config(args):
    if len(args) < 2:
        print("Kullanım: chevren config <anahtar> <değer>")
        sys.exit(1)
    config.set_key(args[0], args[1])
    print(f"{args[0]} = {args[1]}")


def cmd_cache(args):
    if not args or args[0] == "list":
        entries = cache.list_all()
        if not entries:
            print("Cache boş.")
            return
        for e in entries:
            print(f"{e['video_id']}  {e['size_kb']} KB  {e['path']}")
    elif args[0] == "clear":
        n = cache.clear()
        print(f"{n} dosya silindi.")
    else:
        print(f"Bilinmeyen alt komut: {args[0]}")


def cmd_run(source: str, no_play: bool):
    workdir = Path(tempfile.mkdtemp(prefix="chevren_"))
    player = config.get("player") or "mpv"
    mpv_started = False

    def on_ready(srt_path: Path):
        nonlocal mpv_started
        if no_play or mpv_started:
            return
        try:
            subprocess.Popen(
                [
                    player,
                    source,
                    f"--sub-file={srt_path}",
                    "--sub-visibility=yes",
                    "--input-ipc-server=/tmp/chevren-mpv-socket",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            print(f"▶ {player} açılıyor")
            mpv_started = True
        except FileNotFoundError:
            print(f"mpv bulunamadı. SRT: {srt_path}")

    srt = pipeline.run_streaming(source, workdir, on_ready=on_ready)

    if no_play:
        print(f"SRT: {srt}")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(_help_text())
        return

    if sys.argv[1] == "--version":
        print("chevren 0.1.0")
        return

    if sys.argv[1] == "setup":
        cmd_setup()
        return

    if sys.argv[1] == "config":
        cmd_config(sys.argv[2:])
        return

    if sys.argv[1] == "cache":
        cmd_cache(sys.argv[2:])
        return

    no_play = "--no-play" in sys.argv
    source = next((a for a in sys.argv[1:] if not a.startswith("-")), None)

    if not source:
        print(_help_text())
        return

    cmd_run(source, no_play)


if __name__ == "__main__":
    main()
