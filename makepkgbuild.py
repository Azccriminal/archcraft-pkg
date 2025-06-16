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


def parse_makepkgbuild(filepath):
    data = {}
    build_commands = []
    in_build = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
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
                val = [v.strip('"').strip("'") for v in val[1:-1].split(',')]  # Virgüle göre böl
            else:
                val = val.strip('"').strip("'")
            data[key] = val
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

    variables, build_commands = parse_makepkgbuild(filepath)
    if "upstream" not in variables:
        print("[ERR] upstream missing")
        sys.exit(1)
    
    # Upstream listesini al ve ortam değişkenlerini çöz
    raw_upstreams = variables["upstream"]
    if isinstance(raw_upstreams, str):
        # Parçala
        upstream_list = [v.strip() for v in raw_upstreams]
    else:
        upstream_list = raw_upstreams
    
    # Eğer upstream tek string içindeyse virgüle göre böl (örnek: "data://file/{PATH_ENV}/src/makepkgbuild.py,data://file/{PATH_ENV}/docs/archcraft-pkg.7,...")
    if len(upstream_list) == 1 and ',' in upstream_list[0]:
        upstream_list = [v.strip() for v in upstream_list[0].split(',')]
    
    # Ortam değişkenlerini al (dışardan export edilmiş)
    env_vars = dict(os.environ)

    # upstream içindeki {PATH_ENV}, {HOME_ENV} gibi değişkenleri çöz
    resolved_upstreams = []
    for url in upstream_list:
        resolved_url = url
        for k,v in env_vars.items():
            resolved_url = resolved_url.replace(f"{{{k}}}", v)
        resolved_url = resolved_url.replace("{PATH_ENV}", cwd)
        resolved_url = resolved_url.replace("{HOME_ENV}", env_vars.get("HOME", os.path.expanduser("~")))
        resolved_upstreams.append(resolved_url)

    run_build(build_commands, resolved_upstreams, tor_socks=args.tor_socks)

    if args.clean_cache:
        cache_dir = os.path.join(cwd, "build_cache")
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir)
            print(f"[INFO] Cache cleaned: {cache_dir}")
if __name__ == "__main__":
    main()
