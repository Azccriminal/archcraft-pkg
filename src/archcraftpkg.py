import subprocess
import tempfile
import os
import urllib.request
import sys
import tarfile
import glob
import shutil
import platform
import json
import re
from pathlib import Path

RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"

CACHE_DIR = Path.home() / ".cache" / "archcraft-pkg"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

VERSION = "1.0"
AUTHOR = "Zaman Huseynli"
ORG = "Azccriminal Unlimited Organization"

KEYRING_PATH = "/etc/archcraft/keyring"
MIRRORLIST = "/etc/archcraft/mirrorpkglist"
PKG_DB = Path("/var/lib/apkg/installed")
os.makedirs(PKG_DB, exist_ok=True)

def get_arch():
    arch = platform.machine().lower()
    if arch == "x86_64":
        return "x86_64"
    if arch == "any":
        return "any"
    return arch

def ntp_sync():
    print("⏳ Synchronizing system time with NTP...")
    cmds = [
        ["ntpdate", "-q", "pool.ntp.org"],
        ["ntpdate", "pool.ntp.org"],
        ["chronyc", "makestep"]
    ]
    for cmd in cmds:
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"✅ Time synchronized using: {' '.join(cmd)}")
            return
        except Exception:
            continue
    print("⚠ Warning: NTP synchronization failed or no supported tool found.")

def read_mirrors(target_repo=None, release_type=None, query_string=None):
    arch = get_arch()
    mirrors = []
    current_repo = None
    current_release = None

    if not os.path.exists(MIRRORLIST):
        sys.stderr.write(f"{RED}{BOLD}ERROR:{RESET} Mirror list file '{MIRRORLIST}' not found!\n")
        sys.exit(1)  

    with open(MIRRORLIST, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("@"):
                continue
            if line.startswith("#repo="):
                current_repo = line.split("=", 1)[1].strip()
            elif line.startswith("#repopkgreleasedate="):
                current_release = line.split("=", 1)[1].strip().upper()
            elif line.startswith("SERVER="):
                if (not target_repo or current_repo == target_repo) and \
                   (not release_type or current_release == release_type):
                    url = line.split("=", 1)[1].replace("$arch", arch).rstrip("/")
                    if query_string:
                        if "?" in url:
                            url += "&" + query_string
                        else:
                            url += "?" + query_string
                    mirrors.append(url)
    return mirrors


def get_files_json(mirror_url):
    url = mirror_url.rstrip('/') + "/files.json"
    try:
        output = subprocess.check_output([
            "curl", "-sL",
            "-A", "Mozilla/5.0 (X11; Linux x86_64) archcraft-pkg/1.0",
            url
        ])
        return json.loads(output.decode("utf-8"))
    except subprocess.CalledProcessError as e:
        print(f"⚠ files.json read failed via curl: {url} (exit code: {e.returncode})")
        return None
    except json.JSONDecodeError as je:
        print(f"⚠ JSON parse error: {url} ({je})")
        return None

def get_autoindex_file_list(mirror_url):
    try:
        with urllib.request.urlopen(mirror_url) as resp:
            html = resp.read().decode("utf-8")
        files = re.findall(r'<a href="([^"/][^"]*)">', html)
        return [{"name": f, "type": "file"} for f in files]
    except Exception as e:
        print(f"⚠ Autoindex directory listing failed: {mirror_url} ({e})")
        return None

def download_file(url, filename):
    output_path = CACHE_DIR / filename
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) archcraft-pkg/1.0"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response, open(output_path, 'wb') as out_file:
            out_file.write(response.read())
        print(f"✔ Downloaded {filename} to {output_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")
        return False

def download_from_mirrors(pkg, sig, target_repo=None, release_type=None, query_string=None, use_autoindex=False):
    mirrors = read_mirrors(target_repo, release_type, query_string)
    for mirror in mirrors:
        print(f"\U0001F310 Trying mirror: {mirror}")
        file_list = None
        if use_autoindex:
            file_list = get_autoindex_file_list(mirror)
        else:
            file_list = get_files_json(mirror)

        if not file_list:
            print(f"⚠ Package list not found, trying direct download: {mirror}")
        else:
            if not any(entry.get("name") == pkg for entry in file_list):
                print(f"⚠ Package {pkg} not found in mirror {mirror}, trying next...")
                continue

        pkg_url = f"{mirror.rstrip('/')}/{pkg}"
        sig_url = f"{mirror.rstrip('/')}/{sig}"

        success_pkg = download_file(pkg_url, pkg)
        success_sig = download_file(sig_url, sig)

        if success_pkg and success_sig:
            return True
        else:
            print(f"❌ Mirror failed: {mirror}")
    return False

def import_keyring(gpg_dir):
    for asc in os.listdir(KEYRING_PATH):
        if asc.endswith(".asc"):
            subprocess.run(["gpg", "--homedir", gpg_dir, "--import", os.path.join(KEYRING_PATH, asc)], check=True)

def verify(pkg, gpg_dir):
    subprocess.run(["gpg", "--homedir", gpg_dir, "--verify", pkg + ".sig", pkg], check=True)

def extract(pkg):
    # pkg: tam dosya yolu değil, sadece dosya adı bekleniyor
    pkg_path = CACHE_DIR / pkg

    tar_path = CACHE_DIR / pkg.replace(".zst", "")
    try:
        subprocess.run(["zstd", "-d", "-f", str(pkg_path), "-o", str(tar_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Zstd decompression failed: {e}")
        raise

    with tarfile.open(tar_path, "r:") as tar:
        files = tar.getnames()
        tar.extractall(path=CACHE_DIR)

    os.remove(tar_path)

    # Ana dizini tespit et
    top_level_dirs = set(f.split('/')[0] for f in files if '/' in f)
    if len(top_level_dirs) == 1:
        extract_dir = CACHE_DIR / list(top_level_dirs)[0]
    else:
        extract_dir = CACHE_DIR

    return files, extract_dir



def install(pkgname, repo=None, release=None, no_secure=False, query_string=None, ntp_sync_flag=False, use_autoindex=False):
    if ntp_sync_flag:
        ntp_sync()

    pkg = f"{pkgname}.pkg.tar.zst"
    sig = pkg + ".sig"

    pkg_path = CACHE_DIR / pkg
    sig_path = CACHE_DIR / sig

    # Download the package and its signature
    if not no_secure:
        if not download_from_mirrors(pkg, sig, repo, release, query_string, use_autoindex):
            print("❌ Failed to download the package or signature.")
            sys.exit(1)

        with tempfile.TemporaryDirectory() as gpg_dir:
            import_keyring(gpg_dir)
            try:
                verify(str(pkg_path), gpg_dir)
            except subprocess.CalledProcessError:
                print("❌ PGP verification failed!")
                sys.exit(1)
    else:
        mirrors = read_mirrors(repo, release, query_string)
        success = False
        for mirror in mirrors:
            try:
                print(f"\U0001F310 Trying mirror without PGP: {mirror}")
                urllib.request.urlretrieve(f"{mirror.rstrip('/')}/{pkg}", str(pkg_path))
                success = True
                print("⚠ Warning: Downloaded without PGP signature verification!")
                break
            except Exception as e:
                print(f"❌ Mirror failed: {e}")
        if not success:
            print("❌ Failed to download the package.")
            sys.exit(1)

    # Extract package
    files, extract_dir = extract(pkg)

    # Save the file list to PKG_DB
    os.makedirs(PKG_DB, exist_ok=True)
    pkgdb_file = PKG_DB / pkgname
    with pkgdb_file.open("w") as f:
        for path in files:
            f.write(f"/{path}\n")

    # Ask user whether to continue with makepkgbuild
    user_input = input(f"📦 Is the package buildcrafting? [y/N]: ").strip().lower()
    if user_input == "y":
        try:
            print(f"🔧 Running makepkgbuild in {extract_dir} ...")
            subprocess.run(["makepkgbuild"], cwd=str(extract_dir), check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ makepkgbuild failed: {e}")
            sys.exit(1)
    else:
        print("⛔ Installation cancelled by user.")
        sys.exit(0)

    print(f"✅ Installed: {pkgname}")


def remove(pkgname):
    dbfile = os.path.join(PKG_DB, pkgname)
    if not os.path.exists(dbfile):
        print("❌ Package not found in database.")
        return

    confirm = input("Packaging deleted All? [y/N]: ").strip().lower()
    if confirm != "y":
        print("⛔ Removal cancelled.")
        return

    print(f"🗑 Removing package: {pkgname}")

    with open(dbfile, "r") as f:
        for path in f.readlines():
            path = path.strip()
            if path.startswith("~"):
                path = os.path.expanduser(path)

            if os.path.basename(path) == pkgname:
                print(f"⚠ Skipping deletion of '{path}' because its name matches the package name.")
                continue

            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        os.remove(path)
                    print(f"✔ Deleted: {path}")
                except Exception as e:
                    print(f"⚠ Error deleting {path}: {e}")
            else:
                print(f"⚠ Path does not exist (already deleted?): {path}")

    try:
        os.remove(dbfile)
    except Exception as e:
        print(f"⚠ Failed to remove package database record: {e}")
        return

    print(f"✅ Package removed: {pkgname}")

def list_keyring():
    print("🔑 /etc/archcraft/keyring:")
    asc_files = glob.glob(os.path.join(KEYRING_PATH, "*.asc"))

    if not asc_files:
        print("⚠ WARNING: No keyring files found!")
        print("📦 Installing archcraft-keyring package...")
        try:
            subprocess.run(["sudo","apkg", "install", "archcraft-keyring"], check=True)
            print("✅ Installation completed.")
        except subprocess.CalledProcessError:
            print("❌ Error: Failed to install the package!")
        return

    for asc in asc_files:
        print(" -", os.path.basename(asc))

def search(pkgname, repo=None, release=None, query_string=None, use_autoindex=False):
    mirrors = read_mirrors(repo, release, query_string)

    for mirror in mirrors:
        if not use_autoindex:
            files_json = get_files_json(mirror)
            if files_json:
                for entry in files_json:
                    if entry.get("name") == f"{pkgname}.pkg.tar.zst":
                        print(f"✅ FOUNDED PACKAGE : {pkgname}")
                        return

        # Fallback: Doğrudan URL kontrolü
        url = f"{mirror}/{pkgname}.pkg.tar.zst"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    print(f"✅ FOUNDED PACKAGE : {pkgname}")
                    return
        except Exception:
            continue

    print("❌ Package not found in mirrors.")

def remove_cache():
    cache_dir = os.path.expanduser("~/.cache/archcraft-pkg")
    if os.path.exists(cache_dir):
        print(f"🗑 Removing cache directory: {cache_dir}")
        shutil.rmtree(cache_dir)
        print("✅ Cache cleared.")
    else:
        print("Cache directory does not exist.")

def snapshot_save(filename):
    packages = os.listdir(PKG_DB)
    with open(filename, "w") as f:
        for pkg in packages:
            f.write(pkg + "\n")
    print(f"📦 Snapshot saved to {filename}")

def snapshot_load(filename, repo=None, release=None, no_secure=False, query_string=None, ntp_sync_flag=False):
    if not os.path.exists(filename):
        print(f"❌ Snapshot file not found: {filename}")
        return
    with open(filename, "r") as f:
        pkgs = [line.strip() for line in f if line.strip()]
    for pkg in pkgs:
        print(f"📦 Installing from snapshot: {pkg}")
        install(pkg, repo, release, no_secure, query_string, ntp_sync_flag)


def print_help():
    print(f"apkg - archcraft-pkg Alternative realtime crafting header coop reactivable and file-timesnapshot package utility. v{VERSION}")
    print(f"Author: {AUTHOR} ({ORG})\n")
    print("Usage:")
    print("  apkg <command> <package|filename> [options]\n")
    print("Commands:")
    print("  install <package>           Install a package")
    print("  remove <package>            Remove a package")
    print("  search <package>            Search for a package")
    print("  --list-keyring              List keys in keyring")
    print("  snapshot save <filename>    Save current snapshot")
    print("  snapshot load <filename>    Load a snapshot\n")
    print("Options:")
    print("  --repo=core|community       Specify repository")
    print("  --release=STABLE|UNSTABLE   Specify release channel")
    print("  --no-secure                 Skip PGP verification")
    print("  --query=param=value[...]    Extra query parameters")
    print("  --ntp-sync                  Sync time with NTP server before operation")
    print("  --autoindex                 Use autoindex mirror feature\n")
    print(" --remove-cache               Removed cacheing files.\n")
    print("Other:")
    print("  --help                     Show this help message and exit")
    print("  --version                  Show version information and exit")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print_help()
        sys.exit(0)

    if sys.argv[1] == "--version":
        print_version()
        sys.exit(0)

    # cmd olarak --remove-cache yi de dahil ettik
    cmd = sys.argv[1]

    pkgname_or_file = None
    repo = None
    release = None
    no_secure = False
    query_string = None
    ntp_sync_flag = False
    use_autoindex = False

    # --remove-cache komut olduğundan ayrı işlem yapacağız, bu yüzden argümanlardan almayız
    # Diğer parametreleri argümanlardan alalım
    for arg in sys.argv[2:]:
        if arg == "--autoindex":
            use_autoindex = True
        elif arg.startswith("--repo="):
            repo = arg.split("=", 1)[1]
        elif arg.startswith("--release="):
            release = arg.split("=", 1)[1].upper()
        elif arg == "--no-secure":
            no_secure = True
        elif arg.startswith("--query="):
            query_string = arg.split("=", 1)[1]
        elif arg == "--ntp-sync":
            ntp_sync_flag = True
        else:
            pkgname_or_file = arg

    if cmd == "install" and pkgname_or_file:
        install(pkgname_or_file, repo, release, no_secure, query_string, ntp_sync_flag, use_autoindex)
    elif cmd == "remove" and pkgname_or_file:
        remove(pkgname_or_file)
    elif cmd == "search" and pkgname_or_file:
        search(pkgname_or_file, repo, release, query_string)
    elif cmd == "--list-keyring":
        list_keyring()
    elif cmd == "snapshot" and pkgname_or_file:
        if pkgname_or_file == "save":
            if len(sys.argv) < 4:
                print("❌ Missing snapshot filename for save.")
                sys.exit(1)
            snapshot_save(sys.argv[3])
        elif pkgname_or_file == "load":
            if len(sys.argv) < 4:
                print("❌ Missing snapshot filename for load.")
                sys.exit(1)
            snapshot_load(sys.argv[3], repo, release, no_secure, query_string, ntp_sync_flag)
        else:
            print("❌ Invalid snapshot command. Use 'save' or 'load'.")
    elif cmd == "--remove-cache":
        remove_cache()
        sys.exit(0)
    else:
        print("❌ Invalid command or missing package name.")
        print_help()
        sys.exit(1)
