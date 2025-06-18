from setuptools import setup
import os

entry_points = {
    'console_scripts': [
        'makepkgbuild = makepkgbuild:main',
        'apkg = archcraftpkg:main',
    ],
}

# Dosyaların varlığını kontrol et
for f in ['src/makepkgbuild.py', 'src/archcraftpkg.py']:
    if not os.path.exists(f):
        raise FileNotFoundError(f"{f} not found.")

setup(
    name='archcraft-pkg',
    version='1.0.0',
    description='Custom Archcraft MAKEPKGBUILD tool using setuptools',
    author='Zaman Huseynli',
    author_email='zamanhuseynli23@gmail.com',
    license='GPLv3',
    py_modules=['makepkgbuild', 'archcraftpkg'],
    package_dir={'': 'src'},
    entry_points=entry_points,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Topic :: Software Development :: Build Tools',
    ],
    install_requires=[],  # Eğer gereksinim varsa buraya ekle
    include_package_data=True,
    data_files=[
        ('share/man/man7', ['docs/archcraft-pkg.7']),
        ('share/doc/archcraft-pkg', ['docs/Archcraft-pkg.pdf']),
    ],
)

