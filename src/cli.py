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
    import readline  # ok tuşları + backspace için
    _ = readline  # kullanılmıyor uyarısını bastır

    # --- Gemini API Keys ---
    print("\n── Gemini API Key'leri ──────────────────────────")
    keys = config.get_api_keys()
    if keys:
        for i, k in enumerate(keys):
            masked = k[:8] + "●" * (len(k) - 8) if len(k) > 8 else "●●●●●●●●"
            print(f"  {i + 1}. {masked}")
    else:
        print("  (henüz key yok)")

    print()
    print("  a) Yeni key ekle")
    if keys:
        print("  d) Key sil")
    print("  Enter) Değiştirme")
    secim = input("\nSeçim: ").strip().lower()

    if secim == "a":
        yeni = getpass.getpass("  Yeni Gemini API key: ").strip()
        if yeni:
            keys.append(yeni)
            cfg["gemini_api_keys"] = keys
            cfg["gemini_api_key"] = keys[0]
            print(f"  ✓ Key eklendi ({len(keys)} key toplam)")
    elif secim == "d" and keys:
        sil = input(f"  Hangi key silinsin? [1-{len(keys)}]: ").strip()
        try:
            idx = int(sil) - 1
            if 0 <= idx < len(keys):
                keys.pop(idx)
                cfg["gemini_api_keys"] = keys
                cfg["gemini_api_key"] = keys[0] if keys else ""
                print("  ✓ Key silindi")
        except ValueError:
            print("  Geçersiz seçim, değiştirilmedi.")

    detected = config.detect_hardware()["whisper_model"]
    current = cfg.get("whisper_model", detected)
    whisper_models = [
        ("tiny",              "~40 MB  · en hızlı, düşük kalite"),
        ("base",              "~75 MB  · hızlı, orta kalite"),
        ("small",             "~240 MB · dengeli"),
        ("medium",            "~770 MB · iyi kalite"),
        ("large-v3",          "~1.5 GB · en iyi kalite"),
        ("large-v3-turbo",    "~810 MB · large kalitesi, daha hızlı"),
    ]
    print("\n── Whisper Modeli ───────────────────────────────")
    for name, desc in whisper_models:
        star = "★" if name == detected else " "
        curr = " ◄ şu an" if name == current else ""
        print(f"  {star} {name:<20} {desc}{curr}")
    print()
    model = input(f"  Model [{current}]: ").strip()
    cfg["whisper_model"] = model if model else current

    # --- Gemini Model Sırası ---
    print("\n── Gemini Model Sırası ──────────────────────────")
    from pipeline import GEMINI_FALLBACK_MODELS
    current_primary = cfg.get("gemini_model", GEMINI_FALLBACK_MODELS[0])
    all_models = [current_primary] + [m for m in GEMINI_FALLBACK_MODELS if m != current_primary]
    for i, m in enumerate(all_models):
        star = "★" if i == 0 else " "
        print(f"  {star} {i + 1}. {m}")
    print()
    yeni_model = input(f"  Ana model [{current_primary}]: ").strip()
    if yeni_model:
        cfg["gemini_model"] = yeni_model
    print("  (Fallback sırası otomatik: flash → flash-lite → 3-flash → 3.1-flash-lite)")

    player = input(f"Oynatıcı [{cfg.get('player', 'mpv')}]: ").strip()
    if player:
        cfg["player"] = player
    config.save(cfg)
    print("\nAyarlar kaydedildi.")
    print(f"Donanım: {config.hardware_summary()}")
    _enable_server_service()
    _setup_cookies()

def _setup_cookies():
    import shutil
    COOKIE_FILE = Path.home() / ".config" / "chevren" / "cookies.txt"

    print()
    print("─" * 50)
    print("Cookie kurulumu (opsiyonel)")
    print("─" * 50)
    print("Cookie, YouTube'da giriş yaptığınız hesabınızı")
    print("kullanarak yaş kısıtlı veya özel içerikleri")
    print("izlemenizi sağlar.")
    print()

    if COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 0:
        print(f"✓ Mevcut cookie dosyası bulundu: {COOKIE_FILE}")
        yenile = input("Yenilemek ister misiniz? [e/H]: ").strip().lower()
        if yenile != "e":
            return
        print()

    zen_dir = Path.home() / ".zen"
    if zen_dir.exists():
        for p in zen_dir.iterdir():
            if p.is_dir() and (p / "cookies.sqlite").exists():
                print("✓ Zen Browser algılandı — cookie otomatik kullanılacak.")
                print("  Cookie kurulumu gerekmez, devam ediliyor.")
                return

    for b, ad in [("firefox", "Firefox"), ("librewolf", "Librewolf")]:
        if shutil.which(b):
            print(f"✓ {ad} algılandı — cookie otomatik kullanılacak.")
            print("  Cookie kurulumu gerekmez, devam ediliyor.")
            return

    print("Tarayıcınız otomatik algılanamadı.")
    print()
    print("Tarayıcınızı seçin:")
    print("  1) Chrome / Brave / Edge / Vivaldi")
    print("  2) Firefox")
    print("  3) Zen Browser")
    print("  4) Atla")
    print()
    secim = input("Seçiminiz [1-4]: ").strip()

    if secim == "1":
        print()
        print("Chrome tabanlı tarayıcılar için:")
        print()
        print("1. Şu eklentiyi tarayıcınıza kurun:")
        print("   https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
        print()
        print("2. YouTube'a gidin ve hesabınıza giriş yapın.")
        print()
        print("3. Eklenti ikonuna tıklayın → 'Export' → dosyayı kaydedin.")
        print()
        print(f"4. Dosyayı şu konuma taşıyın:")
        print(f"   {COOKIE_FILE}")
        print()
        print(f"   Dizini oluşturmak için:")
        print(f"   mkdir -p {COOKIE_FILE.parent}")

    elif secim == "2":
        print()
        print("Firefox için:")
        print()
        print("1. Şu eklentiyi kurun:")
        print("   https://addons.mozilla.org/firefox/addon/cookies-txt/")
        print()
        print("2. YouTube'a gidin ve hesabınıza giriş yapın.")
        print()
        print("3. Eklenti ikonuna tıklayın → 'Current Site' → kaydedin.")
        print()
        print(f"4. Dosyayı şu konuma taşıyın:")
        print(f"   {COOKIE_FILE}")

    elif secim == "3":
        print()
        print("Zen Browser ~/.zen dizininde profil bulunamadı.")
        print("Zen kuruluysa bir kez açıp kapatmayı deneyin.")
        return

    else:
        print("Cookie kurulumu atlandı.")
        print("Daha sonra tekrar çalıştırmak için: chevren setup")
        return

    print()
    input("Dosyayı yerleştirdikten sonra Enter'a basın...")

    if COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 0:
        print("✓ Cookie dosyası bulundu, kurulum tamamlandı.")
    else:
        print(f"⚠ Dosya bulunamadı: {COOKIE_FILE}")
        print("  Daha sonra manuel olarak yerleştirebilirsiniz.")

def _enable_server_service():
    import shutil
    import sys

    if sys.platform == "win32":
        print("Windows'ta servis kurulumu henüz desteklenmiyor.")
        return
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
            cookie_args = pipeline._yt_dlp_cookie_args()
            subprocess.Popen(
                [
                    player,
                    source,
                    f"--sub-file={srt_path}",
                    "--sub-visibility=yes",
                    "--input-ipc-server=/tmp/chevren-mpv.sock",
                ]
                + cookie_args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            print(f"▶ {player} açılıyor")
            mpv_started = True
        except Exception as e:
            print(f"mpv açılamadı: {e}")

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
