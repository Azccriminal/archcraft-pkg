import os
import sys
import re
import shutil
import argparse
import subprocess
import requests
from urllib.parse import urlparse
from ftplib import FTP

def resolve_path_env(path, env_vars=None):
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    path = path.replace("{PATH_ENV}", cwd)
    path = path.replace("{HOME_ENV}", home)
    if env_vars:
        for k, v in env_vars.items():
            path = path.replace(f"{{{k}}}", v)
    return os.path.expandvars(path)

def fetch_file(src_path, dest_path):
    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"Source file not found: {src_path}")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copyfile(src_path, dest_path)
    print(f"[FILE] Copied: {src_path} → {dest_path}")

def fetch_http(url, dest_path, proxies=None):
    r = requests.get(url, proxies=proxies)
    r.raise_for_status()
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(r.content)
    print(f"[HTTP] Downloaded: {url} → {dest_path}")

def fetch_ftp(url, dest_path):
    parsed = urlparse(url)
    ftp_host = parsed.hostname
    ftp_path = parsed.path
    ftp = FTP(ftp_host)
    ftp.login()
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        ftp.retrbinary(f"RETR {ftp_path}", f.write)
    ftp.quit()
    print(f"[FTP] Downloaded: {url} → {dest_path}")

def fetch_onion(url, dest_path, tor_socks=None):
    parsed = urlparse(url)
    hostname = parsed.hostname
    port = parsed.port or 80
    path = parsed.path or "/"
    proxies = None
    if tor_socks:
        proxies = {
            "http": f"socks5h://{tor_socks}",
            "https": f"socks5h://{tor_socks}"
        }
    full_url = f"http://{hostname}{path}"
    r = requests.get(full_url, proxies=proxies)
    r.raise_for_status()
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(r.content)
    print(f"[ONION] Downloaded: {full_url} → {dest_path}")

def fetch_p2p(url, dest_path):
    raise NotImplementedError("P2P protocol not implemented")

def execute_shell(cmd):
    print(f"[SHELL] Executing: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"[SHELL-OUT]\n{result.stdout}")
        if result.stderr:
            print(f"[SHELL-ERR]\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        print(f"[SHELL-ERROR] Command failed: {e}\nOutput:\n{e.output}\nError:\n{e.stderr}")

def resolve_data_url(data_url):
    parsed = urlparse(data_url)
    scheme = parsed.scheme
    if scheme == "data" and parsed.netloc == "file":
        path = parsed.path
        path = resolve_path_env(path)
        return {"type": "file", "path": path}
    elif scheme in ["http", "https"]:
        return {"type": "http", "url": data_url}
    elif scheme == "ftp":
        return {"type": "ftp", "url": data_url}
    elif scheme == "onion":
        return {"type": "onion", "url": data_url}
    elif scheme == "p2p":
        return {"type": "p2p", "url": data_url}
    else:
        raise ValueError(f"Unsupported protocol: {scheme}")

def fetch_data(uri_info, dest_path, tor_socks=None):
    typ = uri_info["type"]
    if typ == "file":
        fetch_file(uri_info["path"], dest_path)
    elif typ == "http":
        fetch_http(uri_info["url"], dest_path)
    elif typ == "ftp":
        fetch_ftp(uri_info["url"], dest_path)
    elif typ == "onion":
        fetch_onion(uri_info["url"], dest_path, tor_socks=tor_socks)
    elif typ == "p2p":
        fetch_p2p(uri_info["url"], dest_path)
    else:
        raise ValueError(f"Fetch not implemented for type: {typ}")

def run_build(commands, upstreams, tor_socks=None):
    for cmd in commands:
        print(f"[BUILD] > {cmd}")
        if cmd.startswith("setup "):
            m = re.match(r'setup\s+-Dm\d+\s+(data_env(\d+):src:(\S+))', cmd)
            if not m:
                print(f"[SKIP] Unsupported setup command: {cmd}")
                continue
            full_src_uri = m.group(1)
            index = int(m.group(2))
            dest_path = m.group(3)
            if index-1 >= len(upstreams):
                print(f"[ERR] data_env{index} not in upstream list")
                continue
            data_url = upstreams[index-1]
            try:
                data_url_info = resolve_data_url(data_url)
            except Exception as e:
                print(f"[ERR] URL parse error: {e}")
                continue
            target_path = resolve_path_env(dest_path)
            try:
                fetch_data(data_url_info, target_path, tor_socks=tor_socks)
            except Exception as e:
                print(f"[ERR] Fetch failed: {e}")
        else:
            execute_shell(cmd)

def process_gitcheck(git_url_line):
    if "@" in git_url_line:
        repo_url, git_ref = git_url_line.split("@", 1)
    else:
        repo_url, git_ref = git_url_line, "HEAD"

    dest_dir = os.path.join(os.getcwd(), "gitrepo")
    if not os.path.exists(dest_dir):
        subprocess.run(["git", "clone", repo_url, dest_dir])
    subprocess.run(["git", "-C", dest_dir, "checkout", git_ref])
    print(f"[GIT] Checked out {git_ref} from {repo_url}")

def verify_checksum(file_path, expected_hash):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    actual_hash = sha256.hexdigest()
    return actual_hash.startswith(expected_hash[:8])

def process_checksum(checksums):
    for checksum in checksums:
        parts = checksum.strip().split("...")
        if len(parts) != 2:
            print(f"[WARN] Skipping invalid checksum format: {checksum}")
            continue
        expected_hash, filename = parts
        path = resolve_path_env(f"./{filename}")
        if not os.path.exists(path):
            print(f"[ERR] Checksum file not found: {filename}")
            continue
        if not verify_checksum(path, expected_hash):
            print(f"[ERR] Checksum mismatch for {filename}")
            sys.exit(1)
        print(f"[OK] Checksum verified: {filename}")

def parse_makepkgbuild(filepath):
    data = {}
    build_commands = []
    paragmas = []
    in_build = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#PARAGMA"):
                paragmas.append(s.replace("#PARAGMA", "").strip())
                continue
            if s.startswith("#"):
                continue
            if s.startswith("BUILD()"):
                in_build = True
                continue
            if in_build:
                build_commands.append(s)
                continue
            if '=' not in s:
                continue
            key, val = s.split("=", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith('(') and val.endswith(')'):
                val = [v.strip('"').strip("'") for v in val[1:-1].split(',')]
            else:
                val = val.strip('"').strip("'")
            data[key] = val
    data["__PARAGMAS__"] = paragmas
    return data, build_commands

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-sc", "--clean-cache", action="store_true")
    parser.add_argument("--tor-socks", type=str, default=None,
                        help="Tor SOCKS5 proxy address (e.g. 127.0.0.1:9050)")
    args = parser.parse_args()

    cwd = os.getcwd()
    filepath = os.path.join(cwd, "MAKEPKGBUILD")
    if not os.path.isfile(filepath):
        print(f"[ERR] MAKEPKGBUILD not found: {filepath}")
        sys.exit(1)

    # Dosyayı parse et
    variables, build_commands = parse_makepkgbuild(filepath)

    # PARAGMA işlemeleri
    for p in variables.get("__PARAGMAS__", []):
        if p.startswith("OS="):
            import platform
            current_os = platform.system().lower()
            target_os = p.split("=", 1)[1].strip().lower()
            if target_os not in current_os:
                print(f"[SKIP] This package is not intended for your OS: {current_os}")
                sys.exit(0)

    # GITCHECK işle
    if "GITCHECK" in variables:
        process_gitcheck(variables["GITCHECK"])

    # CHECKSUM işle
    if "CHECKSUM" in variables:
        checksums = variables["CHECKSUM"]
        if isinstance(checksums, str):
            checksums = [v.strip() for v in checksums.strip('()').split(',')]
        process_checksum(checksums)

    # Upstream verisi zorunlu
    if "upstream" not in variables:
        print("[ERR] upstream missing")
        sys.exit(1)

    # Upstream formatı çözümle
    raw_upstreams = variables["upstream"]
    if isinstance(raw_upstreams, str):
        upstream_list = [v.strip() for v in raw_upstreams.split(',')]
    else:
        upstream_list = raw_upstreams

    # Ortam değişkenlerini çözümle
    env_vars = dict(os.environ)
    resolved_upstreams = []
    for url in upstream_list:
        resolved_url = url
        for k, v in env_vars.items():
            resolved_url = resolved_url.replace(f"{{{k}}}", v)
        resolved_url = resolved_url.replace("{PATH_ENV}", cwd)
        resolved_url = resolved_url.replace("{HOME_ENV}", env_vars.get("HOME", os.path.expanduser("~")))
        resolved_upstreams.append(resolved_url)

    # Derleme işlemi başlat
    run_build(build_commands, resolved_upstreams, tor_socks=args.tor_socks)

    # Cache temizleme opsiyonu
    if args.clean_cache:
        cache_dir = os.path.join(cwd, "build_cache")
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir)
            print(f"[INFO] Cache cleaned: {cache_dir}")
if __name__ == "__main__":
    main()
