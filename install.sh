#!/usr/bin/env bash
# ============================================================
#  Chevren — Evrensel Kurulum Scripti
#  Desteklenen: Arch/CachyOS · Debian/Ubuntu · Fedora/RHEL · openSUSE
#  Versiyon: 1.0.13
# ============================================================

set -euo pipefail

# ── Renkler ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ── Yardımcı Fonksiyonlar ────────────────────────────────────
info()    { echo -e "${BLUE}${BOLD}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}${BOLD}[ OK ]${NC}  $*"; }
warn()    { echo -e "${YELLOW}${BOLD}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}${BOLD}[ERR ]${NC}  $*" >&2; }
die()     { error "$*"; exit 1; }

banner() {
cat << 'EOF'

  ██████╗██╗  ██╗███████╗██╗   ██╗██████╗ ███████╗███╗   ██╗
 ██╔════╝██║  ██║██╔════╝██║   ██║██╔══██╗██╔════╝████╗  ██║
 ██║     ███████║█████╗  ██║   ██║██████╔╝█████╗  ██╔██╗ ██║
 ██║     ██╔══██║██╔══╝  ╚██╗ ██╔╝██╔══██╗██╔══╝  ██║╚██╗██║
 ╚██████╗██║  ██║███████╗ ╚████╔╝ ██║  ██║███████╗██║ ╚████║
  ╚═════╝╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝

  Evrensel Kurulum Scripti — v1.0.13
EOF
}

# ── Distro Algılama ──────────────────────────────────────────
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        # shellcheck source=/dev/null
        source /etc/os-release
        DISTRO_ID="${ID:-unknown}"
        DISTRO_ID_LIKE="${ID_LIKE:-}"
    else
        die "/etc/os-release bulunamadı. Desteklenmeyen sistem."
    fi

    # Aile belirleme
    case "$DISTRO_ID" in
        arch|cachyos|endeavouros|garuda|manjaro)
            PKG_FAMILY="arch" ;;
        debian|ubuntu|linuxmint|pop|elementary|zorin|kali)
            PKG_FAMILY="debian" ;;
        fedora|rhel|centos|rocky|alma|nobara)
            PKG_FAMILY="fedora" ;;
        opensuse*|sles)
            PKG_FAMILY="opensuse" ;;
        *)
            # ID_LIKE ile ikinci şans
            if echo "$DISTRO_ID_LIKE" | grep -q "arch";    then PKG_FAMILY="arch"
            elif echo "$DISTRO_ID_LIKE" | grep -q "debian"; then PKG_FAMILY="debian"
            elif echo "$DISTRO_ID_LIKE" | grep -q "fedora\|rhel"; then PKG_FAMILY="fedora"
            elif echo "$DISTRO_ID_LIKE" | grep -q "suse";  then PKG_FAMILY="opensuse"
            else die "Tanınmayan distro: $DISTRO_ID. Lütfen issue açın: https://github.com/kullanici/chevren/issues"
            fi ;;
    esac

    info "Distro tespit edildi: ${BOLD}${DISTRO_ID}${NC} (aile: ${PKG_FAMILY})"
}

# ── Paket Yöneticisi Wrapper'ları ────────────────────────────
pkg_install_arch()    { sudo pacman -S --needed --noconfirm "$@"; }
pkg_install_debian()  { sudo apt-get install -y "$@"; }
pkg_install_fedora()  { sudo dnf install -y "$@"; }
pkg_install_opensuse(){ sudo zypper install -y "$@"; }

pkg_install() {
    case "$PKG_FAMILY" in
        arch)     pkg_install_arch    "$@" ;;
        debian)   pkg_install_debian  "$@" ;;
        fedora)   pkg_install_fedora  "$@" ;;
        opensuse) pkg_install_opensuse "$@" ;;
    esac
}

# ── Sistem Güncellemesi ──────────────────────────────────────
update_repos() {
    info "Paket listesi güncelleniyor..."
    case "$PKG_FAMILY" in
        arch)     sudo pacman -Sy --noconfirm ;;
        debian)   sudo apt-get update -qq ;;
        fedora)   sudo dnf check-update -q || true ;;
        opensuse) sudo zypper refresh -q ;;
    esac
    ok "Paket listesi güncellendi."
}

# ── Python Kontrolü ──────────────────────────────────────────
ensure_python() {
    info "Python 3.10+ kontrol ediliyor..."

    # python3 mevcut mu?
    if ! command -v python3 &>/dev/null; then
        info "Python3 kuruluyor..."
        case "$PKG_FAMILY" in
            arch)     pkg_install python ;;
            debian)   pkg_install python3 python3-pip python3-venv ;;
            fedora)   pkg_install python3 python3-pip ;;
            opensuse) pkg_install python3 python3-pip ;;
        esac
    fi

    # Versiyon kontrolü
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

    if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ]]; then
        die "Python 3.10+ gerekli, bulunan: $PY_VER"
    fi

    ok "Python $PY_VER hazır."
}

# ── Sistem Bağımlılıkları ────────────────────────────────────
install_system_deps() {
    info "Sistem bağımlılıkları kuruluyor (ffmpeg, yt-dlp, mpv)..."

    case "$PKG_FAMILY" in
        arch)
            pkg_install ffmpeg yt-dlp mpv
            ;;
        debian)
            pkg_install ffmpeg mpv
            # yt-dlp: Ubuntu/Debian depolarındaki versiyon genellikle eski
            if ! command -v yt-dlp &>/dev/null; then
                info "yt-dlp pip ile kuruluyor (depo versiyonu eski olabilir)..."
                python3 -m pip install --user --upgrade yt-dlp
            else
                warn "yt-dlp mevcut ama güncel olmayabilir. 'yt-dlp -U' ile güncelleyebilirsiniz."
            fi
            ;;
        fedora)
            # RPM Fusion gerekebilir (ffmpeg için)
            if ! rpm -q rpmfusion-free-release &>/dev/null; then
                warn "RPM Fusion Free etkinleştiriliyor (ffmpeg için gerekli)..."
                sudo dnf install -y \
                    "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm" \
                    || warn "RPM Fusion kurulamadı, ffmpeg eksik kalabilir."
            fi
            pkg_install ffmpeg mpv
            # yt-dlp Fedora reposunda var (nobara'da da)
            pkg_install yt-dlp || {
                warn "yt-dlp depodan kurulamadı, pip kullanılıyor..."
                python3 -m pip install --user --upgrade yt-dlp
            }
            ;;
        opensuse)
            # Packman reposu olmadan ffmpeg kısıtlı gelir
            warn "openSUSE: Tam ffmpeg için Packman reposu önerilir."
            warn "Packman: https://en.opensuse.org/SDB:Installing_codecs_from_Packman_repository"
            pkg_install ffmpeg mpv
            python3 -m pip install --user --upgrade yt-dlp
            ;;
    esac

    ok "Sistem bağımlılıkları hazır."
}

# ── CUDA Tespiti ─────────────────────────────────────────────
detect_cuda() {
    CUDA_AVAILABLE=false
    CUDA_VERSION=""

    if command -v nvidia-smi &>/dev/null; then
        CUDA_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1 || true)
        if [[ -n "$CUDA_VERSION" ]]; then
            CUDA_AVAILABLE=true
            info "NVIDIA GPU tespit edildi (sürücü: $CUDA_VERSION)"
        fi
    fi

    if [[ "$CUDA_AVAILABLE" == false ]]; then
        warn "NVIDIA GPU / CUDA tespit edilemedi. CPU modu kullanılacak."
    fi
}

# ── PyTorch Kurulumu ─────────────────────────────────────────
install_pytorch() {
    info "PyTorch kuruluyor..."

    # Arch: pytorch paketi repoda var, pip ile çakışmayı önle
    if [[ "$PKG_FAMILY" == "arch" ]]; then
        if pacman -Qq python-pytorch &>/dev/null 2>&1; then
            ok "PyTorch zaten Arch reposundan kurulu."
            return
        fi
        if pacman -Qq python-pytorch-cuda &>/dev/null 2>&1; then
            ok "PyTorch CUDA zaten Arch reposundan kurulu."
            return
        fi
    fi

    # Diğer distrolarda pip ile
    if [[ "$CUDA_AVAILABLE" == true ]]; then
        info "PyTorch CUDA sürümü pip ile kuruluyor..."
        python3 -m pip install --user \
            torch torchvision torchaudio \
            --index-url https://download.pytorch.org/whl/cu124
    else
        info "PyTorch CPU sürümü pip ile kuruluyor..."
        python3 -m pip install --user \
            torch torchvision torchaudio \
            --index-url https://download.pytorch.org/whl/cpu
    fi

    ok "PyTorch kuruldu."
}

# ── Python Paketleri ─────────────────────────────────────────
install_python_deps() {
    info "Python bağımlılıkları kuruluyor (faster-whisper, google-genai)..."

    # pip güncel mi?
    python3 -m pip install --user --upgrade pip --quiet

    python3 -m pip install --user \
        "faster-whisper>=1.0.3" \
        "google-genai>=1.0.0"

    ok "Python bağımlılıkları kuruldu."
}

# ── Chevren Kurulumu ─────────────────────────────────────────
install_chevren() {
    info "Chevren kuruluyor..."

    INSTALL_DIR="${HOME}/.local/share/chevren"
    BIN_DIR="${HOME}/.local/bin"
    CONFIG_DIR="${HOME}/.config/chevren"

    # Dizinleri oluştur
    mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$CONFIG_DIR"

    # Kaynak: script'in bulunduğu dizin
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Ana dosyaları kopyala
    if [[ -f "$SCRIPT_DIR/chevren.py" ]]; then
        cp "$SCRIPT_DIR/chevren.py" "$INSTALL_DIR/"
        ok "chevren.py kopyalandı → $INSTALL_DIR/"
    else
        warn "chevren.py bulunamadı. Sadece bağımlılıklar kuruldu."
        warn "Chevren'i şuradan klonlayın: git clone https://github.com/kullanici/chevren"
        warn "Sonra tekrar çalıştırın: bash install.sh"
        return
    fi

    # Wrapper script oluştur
    cat > "$BIN_DIR/chevren" << WRAPPER
#!/usr/bin/env bash
exec python3 "${INSTALL_DIR}/chevren.py" "\$@"
WRAPPER
    chmod +x "$BIN_DIR/chevren"

    # Varsayılan config oluştur (yoksa)
    if [[ ! -f "$CONFIG_DIR/config.toml" ]] && [[ -f "$SCRIPT_DIR/config.toml.example" ]]; then
        cp "$SCRIPT_DIR/config.toml.example" "$CONFIG_DIR/config.toml"
        ok "Varsayılan config → $CONFIG_DIR/config.toml"
    fi

    ok "Chevren → $INSTALL_DIR"
    ok "Çalıştırıcı → $BIN_DIR/chevren"
}

# ── PATH Kontrolü ────────────────────────────────────────────
check_path() {
    BIN_DIR="${HOME}/.local/bin"
    if ! echo "$PATH" | grep -q "$BIN_DIR"; then
        warn "'${BIN_DIR}' PATH'inizde yok!"
        warn "Aşağıdaki satırı shell config dosyanıza ekleyin:"
        echo ""
        echo "  # ~/.bashrc veya ~/.zshrc veya ~/.config/fish/config.fish"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
    fi
}

# ── Kurulum Özeti ────────────────────────────────────────────
print_summary() {
    echo ""
    echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  Chevren başarıyla kuruldu! 🎉          ${NC}"
    echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Distro   : ${BOLD}${DISTRO_ID}${NC}"
    echo -e "  CUDA     : ${BOLD}$([ "$CUDA_AVAILABLE" == true ] && echo "✅ Aktif ($CUDA_VERSION)" || echo "❌ CPU modu")${NC}"
    echo -e "  Config   : ${BOLD}${HOME}/.config/chevren/${NC}"
    echo ""
    echo -e "  Kullanım : ${BOLD}chevren [URL]${NC}"
    echo ""
    echo -e "  Sorun mu var? → ${BLUE}https://github.com/kullanici/chevren/issues${NC}"
    echo ""
}

# ── Ana Akış ─────────────────────────────────────────────────
main() {
    banner
    echo ""

    # Root ile çalıştırma uyarısı
    if [[ "$EUID" -eq 0 ]]; then
        warn "Root olarak çalışıyor! Kullanıcı kurulumu için root KULLANMAYIN."
        warn "Sistem paketi kurulumu için sudo yeterli. Devam ediliyor..."
    fi

    detect_distro
    update_repos
    ensure_python
    install_system_deps
    detect_cuda
    install_pytorch
    install_python_deps
    install_chevren
    check_path
    print_summary
}

main "$@"
