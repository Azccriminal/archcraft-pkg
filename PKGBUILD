# Maintainer: Zaman Huseynli <zamanhuseynli23@gmail.com>
# Backup contact: admin@azccriminal.space

pkgname=archcraft-pkg
pkgver=1.0.0
pkgrel=1
pkgdesc="archcraft-pkg Alternative realtime crafting header coop reactivable and file-timesnapshot package utility."
arch=('any')
license=('GPL3')
depends=('pyinstaller' 'python')
source=(
  "src/makepkgbuild.py"
  "src/archcraftpkg.py"
  "docs/archcraft-pkg.7"
  "docs/Archcraft-pkg.pdf"
)
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP')

build() {
  pyinstaller --onefile src/makepkgbuild.py --distpath "$srcdir/dist"
  pyinstaller --onefile src/archcraftpkg.py --distpath "$srcdir/dist"
}

package() {
  install -Dm755 "$srcdir/dist/makepkgbuild" "$pkgdir/usr/bin/makepkgbuild"
  install -Dm755 "$srcdir/dist/archcraftpkg" "$pkgdir/usr/bin/apkg"

  install -Dm644 "docs/archcraft-pkg.7" "$pkgdir/usr/share/man/man7/archcraft-pkg.7"
  install -Dm644 "docs/Archcraft-pkg.pdf" "$pkgdir/usr/share/doc/archcraft-pkg/Archcraft-pkg.pdf"
}
