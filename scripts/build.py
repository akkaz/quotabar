#!/usr/bin/python3
"""Build a .deb, self-contained extension ZIP, and credential-free sources."""
import hashlib
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.1"
UUID = "quotabar@akkaz.dev"
DIST = ROOT / "dist"


def copy_tree(source, destination):
    shutil.copytree(source, destination,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "gschemas.compiled"))


def main():
    DIST.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="quotabar-build-") as temporary:
        stage = Path(temporary) / "package"
        extension = stage / "usr/share/gnome-shell/extensions" / UUID
        copy_tree(ROOT / "extension", extension)
        copy_tree(ROOT / "quotabar", extension / "backend/quotabar")
        (extension / "helper.py").chmod(0o755)
        subprocess.run(["glib-compile-schemas", "--strict", str(extension / "schemas")], check=True)
        binary = stage / "usr/bin/quotabar"
        binary.parent.mkdir(parents=True)
        binary.symlink_to(f"../share/gnome-shell/extensions/{UUID}/helper.py")
        for source, destination in [
            ("packaging/quotabar.desktop", "usr/share/applications/quotabar.desktop"),
            ("packaging/quotabar.svg", "usr/share/icons/hicolor/scalable/apps/quotabar.svg"),
            ("LICENSE", "usr/share/doc/quotabar/copyright"),
            ("THIRD_PARTY_NOTICES.md", "usr/share/doc/quotabar/THIRD_PARTY_NOTICES.md"),
            ("README.md", "usr/share/doc/quotabar/README.md"),
        ]:
            target = stage / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / source, target)
        control = stage / "DEBIAN/control"
        control.parent.mkdir()
        size = sum(p.stat().st_size for p in (stage / "usr").rglob("*") if p.is_file()) // 1024 + 1
        control.write_text(f"""Package: quotabar
Version: {VERSION}-1
Section: gnome
Priority: optional
Architecture: all
Maintainer: Gio Marco Baglioni <akkaz@users.noreply.github.com>
Installed-Size: {size}
Depends: gnome-shell (>= 48~), gnome-shell (<< 49~), gjs, python3 (>= 3.10), gir1.2-adw-1 (>= 1.4), gir1.2-gtk-4.0, libglib2.0-bin, x-terminal-emulator
Description: Codex and Claude subscription usage in the GNOME top panel
 Native GNOME 48 indicator with usage bars, reset countdowns, account setup
 and automatic polling. Requires user-installed official provider CLIs.
 No telemetry, hosted backend, or credentials included.
""")
        deb = DIST / f"quotabar_{VERSION}-1_all.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(stage), str(deb)], check=True)
        archive = DIST / f"quotabar-{VERSION}.shell-extension.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for path in sorted(extension.rglob("*")):
                if path.is_file():
                    output.write(path, path.relative_to(extension))
    source = DIST / f"quotabar-{VERSION}-source.tar.gz"
    with tarfile.open(source, "w:gz") as output:
        for name in ["README.md", "README.it.md", "CONTRIBUTING.md", "install.sh", "LICENSE",
                     "THIRD_PARTY_NOTICES.md", "PRODUCT.md", "DESIGN.md", "CHANGELOG.md", ".gitignore",
                     ".github", "quotabar", "extension", "scripts", "tests", "packaging", "docs"]:
            path = ROOT / name
            if not path.exists():
                continue
            def clean(info):
                if "__pycache__" in Path(info.name).parts or info.name.endswith((".pyc", "gschemas.compiled")):
                    return None
                info.uid = info.gid = 0
                info.uname = info.gname = "root"
                return info
            output.add(path, arcname=f"quotabar-{VERSION}/{name}", filter=clean)
    files = [deb, archive, source]
    (DIST / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in files))
    for path in files:
        print(f"{path} ({path.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
