#!/usr/bin/env python3
"""
install.py — Chevren evrensel kurulum scripti
Linux (Arch/Debian/Fedora/openSUSE) ve Windows desteklenir.
"""

import os
import sys

# Windows konsolunda UTF-8 zorla (emoji için)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import argparse
import platform
import shutil
import subprocess
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        prog="install.py",
        description="Chevren kurulum scripti — Linux ve Windows destekler.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python install.py                  # Normal kurulum
  python install.py --dry-run        # Sadece ne yapılacağını göster
  python install.py --skip-deps      # Sistem paketlerini atla, sadece Python kur
  python install.py --dry-run --skip-deps
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hiçbir şey kurma, sadece yapılacakları göster.",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Sistem bağımlılıklarını (ffmpeg, mpv, yt-dlp) atla.",
    )
    return parser.parse_args()


def run(cmd, check=True, dry_run=False):
    print(f"$ {' '.join(cmd)}")
    if dry_run:
        print("  (dry-run: atlandı)")
        return
    return subprocess.run(cmd, check=check)


def is_root():
    if platform.system() == "Windows":
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin()
    return os.geteuid() == 0


def maybe_sudo(cmd):
    if is_root():
        return cmd
    if shutil.which("sudo"):
        return ["sudo"] + cmd
    return cmd


def detect_distro():
    if platform.system() == "Windows":
        return "windows"
    try:
        text = Path("/etc/os-release").read_text()
        info = {}
        for line in text.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                info[k] = v.strip().strip('"')
        distro_id = info.get("ID", "")
        id_like = info.get("ID_LIKE", "")
        if "arch" in distro_id or "arch" in id_like:
            return "arch"
        if "debian" in distro_id or "ubuntu" in distro_id or "debian" in id_like:
            return "debian"
        if "fedora" in distro_id or "fedora" in id_like:
            return "fedora"
        if "opensuse" in distro_id or "suse" in id_like:
            return "opensuse"
    except Exception:
        pass
    return "unknown"


def get_fedora_version():
    """
    Fedora sürümünü /etc/os-release'den okur.
    platform.release() kernel sürümü verir (örn: 6.8.0-...), işimize yaramaz.
    Bize "40", "41" gibi Fedora sürüm numarası lazım.
    """
    try:
        text = Path("/etc/os-release").read_text()
        for line in text.splitlines():
            if line.startswith("VERSION_ID="):
                return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return None


def install_linux_deps(distro, dry_run=False):
    print(f"\n📦 Sistem bağımlılıkları kuruluyor ({distro})...")

    if distro == "arch":
        run(
            maybe_sudo(
                [
                    "pacman",
                    "-Sy",
                    "--noconfirm",
                    "python",
                    "python-pip",
                    "ffmpeg",
                    "yt-dlp",
                    "mpv",
                ]
            ),
            dry_run=dry_run,
        )

    elif distro == "debian":
        run(maybe_sudo(["apt", "update"]), dry_run=dry_run)
        run(
            maybe_sudo(
                [
                    "apt",
                    "install",
                    "-y",
                    "python3",
                    "python3-pip",
                    "ffmpeg",
                    "yt-dlp",
                    "mpv",
                ]
            ),
            dry_run=dry_run,
        )

    elif distro == "fedora":
        fedora_ver = get_fedora_version()
        if fedora_ver:
            rpm_fusion_url = (
                "https://download1.rpmfusion.org/free/fedora/"
                f"rpmfusion-free-release-{fedora_ver}.noarch.rpm"
            )
            run(
                maybe_sudo(["dnf", "install", "-y", rpm_fusion_url]),
                check=False,
                dry_run=dry_run,
            )
        else:
            print("⚠️  Fedora sürümü belirlenemedi, RPM Fusion atlandı.")
        run(
            maybe_sudo(
                [
                    "dnf",
                    "install",
                    "-y",
                    "python3",
                    "python3-pip",
                    "ffmpeg",
                    "yt-dlp",
                    "mpv",
                ]
            ),
            dry_run=dry_run,
        )

    elif distro == "opensuse":
        print("⚠️  openSUSE: ffmpeg için Packman deposu gerekebilir.")
        run(
            maybe_sudo(
                [
                    "zypper",
                    "install",
                    "-y",
                    "python3",
                    "python3-pip",
                    "ffmpeg",
                    "yt-dlp",
                    "mpv",
                ]
            ),
            check=False,
            dry_run=dry_run,
        )

    else:
        print("⚠️  Dağıtım tanınamadı, sistem bağımlılıkları atlandı.")


def install_windows_deps(dry_run=False):
    print("\n📦 Windows bağımlılıkları kontrol ediliyor...")

    missing = []
    for tool in ["ffmpeg", "mpv", "yt-dlp"]:
        if not shutil.which(tool):
            missing.append(tool)

    if missing:
        print(f"⚠️  Eksik araçlar: {', '.join(missing)}")
        if shutil.which("winget"):
            for tool in missing:
                winget_id = {
                    "ffmpeg": "Gyan.FFmpeg",
                    "mpv": "mpv.mpv",
                    "yt-dlp": "yt-dlp.yt-dlp",
                }.get(tool)
                if winget_id:
                    run(
                        ["winget", "install", "--id", winget_id, "-e"],
                        check=False,
                        dry_run=dry_run,
                    )
        else:
            print("winget bulunamadı. Lütfen eksik araçları manuel kurun:")
            print("  ffmpeg : https://ffmpeg.org/download.html")
            print("  mpv    : https://mpv.io/installation/")
            print("  yt-dlp : https://github.com/yt-dlp/yt-dlp/releases")
    else:
        print("✅ ffmpeg, mpv, yt-dlp mevcut.")


def install_python_deps(dry_run=False):
    print("\n🐍 Python bağımlılıkları kuruluyor...")
    if Path("requirements.txt").exists():
        pip = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        if platform.system() != "Windows":
            pip.append("--break-system-packages")
        run(pip, dry_run=dry_run)
    elif Path("pyproject.toml").exists():
        print("  (requirements.txt yok, pyproject.toml kullanılıyor)")
        pip = [sys.executable, "-m", "pip", "install", "-e", "."]
        run(pip, dry_run=dry_run)
    else:
        print("⚠️  Ne requirements.txt ne pyproject.toml bulundu, atlandı.")


def install_chevren(dry_run=False):
    print("\n🔧 Chevren kuruluyor...")
    if platform.system() == "Windows":
        run([sys.executable, "-m", "pip", "install", "-e", "."], dry_run=dry_run)
    else:
        if shutil.which("make"):
            run(maybe_sudo(["make", "install"]), dry_run=dry_run)
        else:
            run([sys.executable, "-m", "pip", "install", "-e", "."], dry_run=dry_run)


def main():
    args = parse_args()

    print("=" * 50)
    print("  Chevren Kurulum Scripti")
    if args.dry_run:
        print("  ⚠️  DRY-RUN MODU — hiçbir şey kurulmayacak")
    print("=" * 50)

    system = platform.system()
    print(f"\n🖥️  Sistem: {system} {platform.release()}")

    if not args.skip_deps:
        if system == "Windows":
            install_windows_deps(dry_run=args.dry_run)
        else:
            distro = detect_distro()
            install_linux_deps(distro, dry_run=args.dry_run)
    else:
        print("\n⏭️  --skip-deps: sistem bağımlılıkları atlandı.")

    install_python_deps(dry_run=args.dry_run)
    install_chevren(dry_run=args.dry_run)

    if args.dry_run:
        print(
            "\n✅ Dry-run tamamlandı. Gerçek kurulum için --dry-run olmadan çalıştır."
        )
    else:
        print("\n✅ Kurulum tamamlandı!")
        print("   chevren --help ile başlayabilirsiniz.")


if __name__ == "__main__":
    main()
    # Exe olarak çalışınca konsol penceresi anında kapanmasın.
    # sys.frozen sadece PyInstaller exe'sinde True olur —
    # normal "python install.py" çalıştırınca bu satır işlemez.
    if getattr(sys, "frozen", False):
        input("\nKurulum tamamlandı. Çıkmak için Enter'a bas...")
