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
sha256sums=('4f52819ff14948519c27e6b32dd06e1d08dfd29f78688e054158dd5188846702')

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
