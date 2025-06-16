# Maintainer: Zaman Huseynli <zamanhuseynli23@gmail.com>
# Backup contact: admin@azccriminal.space

pkgname=archcraft-pkg
pkgver=1.0.0
pkgrel=1
pkgdesc="Custom Archcraft MAKEPKGBUILD tool using PyInstaller"
arch=('any')
license=('GPL3')
depends=('pyinstaller' 'python')
source=(
  "src/makepkgbuild.py"
  "docs/archcraft-pkg.7"
  "docs/Archcraft-pkg.pdf"
)
md5sums=('SKIP' 'SKIP' 'SKIP')  

build() {
  pyinstaller --onefile src/makepkgbuild.py --distpath "$srcdir/dist"
}

package() {
  install -Dm755 "$srcdir/dist/makepkgbuild" "$pkgdir/usr/bin/makepkgbuild"

  install -Dm644 "docs/archcraft-pkg.7" "$pkgdir/usr/share/man/man7/archcraft-pkg.7"
  install -Dm644 "docs/Archcraft-pkg.pdf" "$pkgdir/usr/share/doc/archcraft-pkg/Archcraft-pkg.pdf"
}
