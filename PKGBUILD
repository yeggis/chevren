# Maintainer: yeggis <yeggis@users.noreply.github.com>
pkgname=chevren
pkgver=1.0.13
pkgrel=1
pkgdesc="Turkish subtitle generator for YouTube videos and local files"
arch=('x86_64')
url="https://github.com/yeggis/chevren"
license=('MIT')
depends=(
  'python'
  'python-pytorch-cuda'
  'ffmpeg'
  'yt-dlp'
  'mpv'
)
makedepends=('python-pip' 'python-virtualenv')
source=("$pkgname-$pkgver.tar.gz::https://github.com/yeggis/$pkgname/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=("d8173478e76698ee61e19a12c1c8432d8647673b997b404e29b1a6cc490e0d63")

package() {
  cd "$srcdir/$pkgname-$pkgver"

  install -dm755 "$pkgdir/usr/share/$pkgname"
  cp -r src "$pkgdir/usr/share/$pkgname/"

  python -m venv "$srcdir/venv"
  "$srcdir/venv/bin/pip" install \
    faster-whisper google-genai \
    "urllib3>=2.0" \
    "charset-normalizer>=3.0" \
    --no-compile \
    --quiet

  python3 -c "
import os
bindir = '$srcdir/venv/bin'
for f in os.listdir(bindir):
    if any(ord(c) > 127 for c in f):
        os.remove(os.path.join(bindir, f))
"

  find "$srcdir/venv/bin" -type f \
    -exec sed -i "s|$srcdir/venv|/usr/share/$pkgname/venv|g" {} \; 2>/dev/null || true
  sed -i "s|$srcdir/venv|/usr/share/$pkgname/venv|g" "$srcdir/venv/pyvenv.cfg"

  cp -r "$srcdir/venv" "$pkgdir/usr/share/$pkgname/venv"

  install -Dm755 chevren "$pkgdir/usr/share/$pkgname/chevren"
  install -dm755 "$pkgdir/usr/bin"
  ln -sf "/usr/share/$pkgname/chevren" "$pkgdir/usr/bin/chevren"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
