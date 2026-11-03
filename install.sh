#!/usr/bin/env bash
# Install the native published package. No credentials or shell settings change.
set -euo pipefail
umask 077

readonly repository="akkaz/quotabar"
release_tag=""
download_directory=""
package_format="auto"

die() { printf 'QuotaBar: %s\n' "$*" >&2; exit 1; }
usage() {
    cat <<'EOF'
Usage: bash install.sh [--version VERSION] [--format auto|deb|rpm] [--download-only DIRECTORY]

Install the latest QuotaBar release on GNOME 48-51 using apt or Fedora dnf.
  --format auto|deb|rpm        Auto-detect the OS, or select a package format.
  --version VERSION           Select a release, e.g. 0.2.1 or v0.2.1.
  --download-only DIRECTORY   Verify and save the native package without installing it.
  --help                     Show this help.

Installation uses sudo -A with your existing SUDO_ASKPASS or a Zenity password
dialog. It never logs you out, changes GNOME settings, or installs provider CLIs.
EOF
}

while (($#)); do
    case "$1" in
        --version)
            (($# >= 2)) || die '--version needs a value.'
            release_tag="v${2#v}"; shift 2 ;;
        --download-only)
            (($# >= 2)) || die '--download-only needs a directory.'
            [[ -n "$2" ]] || die '--download-only needs a directory.'
            download_directory="$2"; shift 2 ;;
        --format)
            (($# >= 2)) || die '--format needs auto, deb or rpm.'
            package_format="$2"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *) die "Unknown option: $1. Use --help." ;;
    esac
done

if [[ -n "$release_tag" && ! "$release_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    die 'Invalid version; use a release such as v0.2.1.'
fi
[[ "$(uname -s)" == Linux ]] || die 'This installer requires Linux.'
for command in curl python3 sha256sum; do
    command -v "$command" >/dev/null || die "Missing $command. Install it with your package manager first."
done
[[ "$package_format" =~ ^(auto|deb|rpm)$ ]] || die 'Invalid package format: use auto, deb or rpm.'
if [[ "$package_format" == auto ]]; then
    os_id="$(python3 -c 'import platform; print(platform.freedesktop_os_release().get("ID", ""))')"
    case "$os_id" in
        fedora) package_format="rpm" ;;
        ubuntu|debian|linuxmint|pop) package_format="deb" ;;
        *) die 'Unsupported distribution. Use --format with --download-only to retrieve a package.' ;;
    esac
fi
if [[ "$package_format" == rpm ]]; then
    package_tool="rpm"
    package_manager="dnf"
else
    package_tool="dpkg-deb"
    package_manager="apt-get"
fi
command -v "$package_tool" >/dev/null || die "Missing $package_tool. Install it with your package manager first."

if [[ -z "$download_directory" ]]; then
    ((EUID != 0)) || die 'Run this installer as your desktop user, without sudo.'
    [[ ! -e /run/ostree-booted ]] || die 'Fedora Atomic needs rpm-ostree layering; this dnf installer supports regular Fedora Workstation.'
    for command in "$package_manager" sudo gnome-shell; do
        command -v "$command" >/dev/null || die "Missing $command. Installation requires $package_manager and GNOME 48-51."
    done
    shell_version="$(gnome-shell --version)"
    [[ "$shell_version" =~ ^GNOME\ Shell\ (48|49|50|51)(\.|$) ]] || die "GNOME 48-51 is required; found: $shell_version. No changes made."
    [[ -z "${XDG_CURRENT_DESKTOP:-}" || "${XDG_CURRENT_DESKTOP^^}" == *GNOME* ]] || die 'QuotaBar needs an active GNOME desktop; KDE Plasma is not supported.'
    user_extension="${XDG_DATA_HOME:-${HOME}/.local/share}/gnome-shell/extensions/quotabar@akkaz.dev"
    [[ ! -e "$user_extension" ]] || die 'A user-installed QuotaBar ZIP would hide system-package updates. Remove that copy before using this installer (see README).'
fi

task_tmp="$(mktemp -d "${TMPDIR:-/tmp}/quotabar-install.XXXXXX")"
trap 'rm -rf -- "$task_tmp"' EXIT
fetch() {
    curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --connect-timeout 15 --max-time 120 --retry 2 --output "$2" "$1"
}

if [[ -z "$release_tag" ]]; then
    fetch "https://api.github.com/repos/${repository}/releases/latest" "$task_tmp/release.json"
    release_tag="$(python3 - "$task_tmp/release.json" <<'PY'
import json, re, sys
try:
    tag = json.load(open(sys.argv[1]))["tag_name"]
    if not isinstance(tag, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError()
except (OSError, ValueError, KeyError, TypeError):
    sys.exit("QuotaBar: invalid GitHub release metadata.")
print(tag)
PY
    )"
fi

version="${release_tag#v}"
if [[ "$package_format" == rpm ]]; then
    filename="quotabar-${version}-1.noarch.rpm"
else
    filename="quotabar_${version}-1_all.deb"
fi
base_url="https://github.com/${repository}/releases/download/${release_tag}"
printf 'Downloading QuotaBar %s…\n' "$version"
fetch "$base_url/$filename" "$task_tmp/$filename"
fetch "$base_url/SHA256SUMS" "$task_tmp/SHA256SUMS"

# Select exactly one expected filename. Never execute arbitrary manifest paths.
expected="$(python3 - "$task_tmp/SHA256SUMS" "$filename" <<'PY'
import re, sys
rows = [line.split() for line in open(sys.argv[1])]
matches = [row[0] for row in rows if len(row) == 2 and row[1] == sys.argv[2]]
if len(matches) != 1 or not re.fullmatch(r"[a-fA-F0-9]{64}", matches[0]):
    sys.exit("QuotaBar: missing, duplicate or invalid package checksum.")
print(matches[0])
PY
)"
if ! (cd "$task_tmp" && printf '%s  %s\n' "$expected" "$filename" | sha256sum --check --status); then
    die 'Checksum mismatch. Nothing was installed.'
fi
if [[ "$package_format" == rpm ]]; then
    rpm --checksig --nosignature "$task_tmp/$filename" >/dev/null || die 'RPM digest verification failed.'
    [[ "$(rpm -qp --qf '%{NAME}' "$task_tmp/$filename")" == quotabar ]] || die 'Unexpected RPM package name.'
    [[ "$(rpm -qp --qf '%{VERSION}-%{RELEASE}' "$task_tmp/$filename")" == "$version-1" ]] || die 'Unexpected RPM package version.'
    [[ "$(rpm -qp --qf '%{ARCH}' "$task_tmp/$filename")" == noarch ]] || die 'Unexpected RPM package architecture.'
else
    [[ "$(dpkg-deb --field "$task_tmp/$filename" Package)" == quotabar ]] || die 'Unexpected Debian package name.'
    [[ "$(dpkg-deb --field "$task_tmp/$filename" Version)" == "$version-1" ]] || die 'Unexpected Debian package version.'
    [[ "$(dpkg-deb --field "$task_tmp/$filename" Architecture)" == all ]] || die 'Unexpected Debian package architecture.'
fi
printf 'SHA-256 and package metadata verified.\n'

if [[ -n "$download_directory" ]]; then
    mkdir -p -- "$download_directory"
    cp -- "$task_tmp/$filename" "$task_tmp/SHA256SUMS" "$download_directory/"
    printf 'Saved to %s. Nothing was installed.\n' "$download_directory"
    exit 0
fi

if [[ -n "${SUDO_ASKPASS:-}" ]]; then
    [[ -x "$SUDO_ASKPASS" ]] || die 'SUDO_ASKPASS is not executable. Configure a working graphical password helper.'
elif command -v zenity >/dev/null && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    cat > "$task_tmp/askpass" <<'EOF'
#!/bin/sh
exec zenity --password --title='Install QuotaBar' --text='Enter your password to install the verified QuotaBar package.'
EOF
    chmod 700 "$task_tmp/askpass"
    export SUDO_ASKPASS="$task_tmp/askpass"
else
    die 'A graphical password helper is required. Install Zenity or configure SUDO_ASKPASS, then retry. The verified package can also be downloaded with --download-only.'
fi

# Authentication failures stop here; never fall back to bypassing sudo prompts.
sudo -A "$package_manager" install -y "$task_tmp/$filename"
cat <<'EOF'

QuotaBar installed.
1. Open QuotaBar from Applications, or run: quotabar settings
2. Enable “Mostra nel pannello e ai prossimi accessi” and connect your accounts.
3. If the bar is missing or still shows an older version, log out and back in
   when convenient. Your current session has not been restarted.
EOF
