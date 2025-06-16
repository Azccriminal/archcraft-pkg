# Archcraft-Pkg

**Alternative realtime crafting header coop reactivable and file-timesnapshot package builder**

Developed by **Azccriminal Unlimited Organization**  
Contact: [admin@azccriminal.space](mailto:admin@azccriminal.space)

---

## 📖 Name

**archcraft-pkg** — Alternative realtime crafting header coop reactivable and file-timesnapshot package system.

---

## 🧾 Synopsis

```bash
archcraft-pkg [OPTIONS] COMMAND [ARGS]
```

---

## 📦 Description

`archcraft-pkg` is a package structure developed for universal Linux distribution package management.  
It supports universal usage across all Linux distributions and other operating systems.

Unlike traditional Arch-based tools such as `pacman` or `makepkg`,  
**archcraft-pkg** is developed independently and follows a unique package distribution architecture.

---

## 📁 Package Structure

The package integrity model is based on the **MAKEPKGBUILD** configuration foundation.

Unlike `PKGBUILD`,  
**MAKEPKGBUILD** allows OS-level tools to install packages universally on any supported OS.

> ⚠️ For security reasons, only "building-craft" tools are recommended at the OS level,  
though many tools remain free to use.

---

## 💡 Philosophy

**MAKEPKGBUILD** aims to provide wide and flexible installation options for all operating systems.

Pragma methods and functions specific to distributions can be defined, including custom installations targeting particular OS environments using:

```bash
#PARAGMA : OS
```

You can specify the target operating system using the `PARAGMA` parameter:

```bash
__PARAGMAS__=(
  "OS=cowhead"
)
```

Custom installation is supported for each OS as long as the instructions are correctly written.  
Yes — it is supported by **super cow powers** 🐮✨

---

## 🔧 Key Features (v1.0)

### 1. `setup` Command

A special installation command named `setup` has been added.  
It behaves similarly to the Unix `install` command, supporting permission modes and destination points.

```bash
setup -Dm755 data_env1:src:/etc/archcraft
```

---

### 2. P2P Onion HTTP Source Download

Support for downloading sources via **P2P onion HTTP** is included.

Using the `data://` protocol, packages can be compiled and installed over desired networks.

> 🔐 Security patch verification is **strongly recommended** for all downloaded packages.

---

### 3. `BUILD()` Command

Installation can be configured using system installation commands.

Supported build directives (for security):
- `build-in-craft`
- `build-on-craft`

Non-security builds may allow full system command usage.

---

### 4. Git and Checksum Verification

You can update or verify packages using `GITCHECK` and `CHECKSUM`.

```bash
GITCHECK="https://github.com/azccriminal/makepkgbuild.git@v1.0"

CHECKSUM=(
  "src/makepkgbuild.py:deadc0de0000000000000000000000000000000000000000000000000000000000"
)
```

Supported checksum algorithms:
- `md5`
- `sha1`
- `sha256`
- and more...

---

## 📜 License

This project is open source.  
All official rights belong to **Azccriminal Unlimited Organization**.

---

## 🔍 See Also

- [`makepkg(1)`](https://man.archlinux.org/man/makepkg.1)
- [`pacman(8)`](https://man.archlinux.org/man/pacman.8)
- [`install(1)`](https://man7.org/linux/man-pages/man1/install.1.html)

---

## 👨‍💻 Author

**Azccriminal Unlimited Organization**

---

## 🐛 Bugs

Please report bugs to:  
📧 [admin@azccriminal.space](mailto:admin@azccriminal.space)

---
