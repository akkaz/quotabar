# Contributing to QuotaBar

Bug reports, compatibility work and small focused pull requests are welcome.
Please describe the problem before proposing a broad rewrite.

## Local setup

The build uses system packages, not npm or pip. On an apt-based development
machine, use your graphical package manager or, with SUDO_ASKPASS configured:

```bash
sudo -A apt install python3 gjs gir1.2-adw-1 gir1.2-gtk-4.0 libglib2.0-bin dpkg-dev desktop-file-utils
```

A GNOME 48 desktop is required to run the indicator. Automated checks and the
package build can run without a live GNOME session.

```bash
/usr/bin/python3 scripts/check.py
bash -n install.sh
/usr/bin/python3 scripts/build.py
sh scripts/run.sh snapshot --demo
sh scripts/run.sh settings
```

Installer tests use synthetic local Debian packages and a mocked downloader;
they never access the network or invoke real privileged commands. Provider tests
use synthetic data, including checks for token expiry and credential redaction.

## Where things live

| Path | Responsibility |
| --- | --- |
| `extension/extension.js` | GNOME panel and expanded menu |
| `extension/presentation.js` | Shared formatting, window selection and colors |
| `extension/ui.js` | Native preferences and account connection |
| `quotabar/providers.py` | Provider-specific, read-only quota access |
| `quotabar/cache.py` | Private cache, request intervals and backoff |
| `install.sh` | Release download, verification and apt installation |
| `scripts/build.py` | Packages, source archive and checksums |

## Testing the interface

Use DEMO mode and a separate GNOME 48 VM or development session. A nested shell
alone is not complete isolation: use a separate D-Bus session, runtime, config,
data and cache directories. Never restart or log out someone else's active
session to validate a change.

Look at the actual panel, popup and preferences after UI changes. Exercise
available, warning, exhausted, unknown and stale quotas; both percentage modes;
keyboard navigation; and extension enable/disable cleanup. Tests and synthetic
screenshots do not prove fresh provider login or every desktop theme.

Do not claim support for another GNOME major version by changing metadata alone.
Validate its APIs, styling, install/update flow and actual rendering first.

## Reporting a bug

Include your distribution, `gnome-shell --version`, QuotaBar version, provider,
steps to reproduce, and the visible error. State whether DEMO is also affected.
Remove account names and personal information from screenshots.

Never attach CLI credential files, access/refresh tokens, authorization headers,
private account responses, or an unredacted configuration directory.

## Pull requests and releases

Keep unrelated changes separate. Describe the reason, resulting behavior, and
relevant checks. Preserve the native desktop appearance and consistent colors.

For a release, keep `quotabar/__init__.py`, `extension/metadata.json` and
`scripts/build.py` versions in sync, and increment the extension's integer
version. Update the changelog and pinned documentation examples. Build from a
clean commit, verify `dist/SHA256SUMS`, and publish all three archives plus the
manifest under a matching `vX.Y.Z` GitHub release. `install.sh` uses that release's
tag, never a guessed artifact from a moving branch.

By contributing, you license your code under MIT. Provider marks retain their
separate asset licenses and trademark ownership.
