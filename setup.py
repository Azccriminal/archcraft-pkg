from setuptools import setup
import os

# Define the command-line entry point
entry_points = {
    'console_scripts': [
        'makepkgbuild = makepkgbuild:main',
    ],
}

# Ensure the script exists before proceeding
if not os.path.exists('src/makepkgbuild.py'):
    raise FileNotFoundError("src/makepkgbuild.py not found.")

setup(
    name='archcraft-pkg',
    version='1.0.0',
    description='Custom Archcraft MAKEPKGBUILD tool using setuptools',
    author='Zaman Huseynli',
    author_email='zamanhuseynli23@gmail.com',
    license='GPLv3',
    packages=[''],
    py_modules=['makepkgbuild'],
    package_dir={'': 'src'},
    entry_points=entry_points,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Topic :: Software Development :: Build Tools',
    ],
    install_requires=[],
    include_package_data=True,
    data_files=[
        ('share/man/man7', ['docs/archcraft-pkg.7']),
        ('share/doc/archcraft-pkg', ['docs/Archcraft-pkg.pdf']),
    ],
)
