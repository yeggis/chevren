# Maintainer: yeggis <yeggis@users.noreply.github.com>
pkgname=chevren
pkgver=1.0.0
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
makedepends=('python-pip')
source=("$pkgname-$pkgver.tar.gz::https://github.com/yeggis/$pkgname/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('9755124664337052b45e582f434f4937618099ef687f018e2b30773d9cb4f409')

package() {
  cd "$srcdir/$pkgname-$pkgver"

  # Ana dizin
  install -dm755 "$pkgdir/usr/share/$pkgname"
  cp -r src "$pkgdir/usr/share/$pkgname/"

  # Çalıştırılabilir script
  install -Dm755 chevren "$pkgdir/usr/share/$pkgname/chevren"

  # PATH'e sembolik link
  install -dm755 "$pkgdir/usr/bin"
  ln -sf "/usr/share/$pkgname/chevren" "$pkgdir/usr/bin/chevren"

  # Lisans
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
