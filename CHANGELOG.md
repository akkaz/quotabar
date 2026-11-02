# Changelog

## 0.4.0 — 2026-11-02

- Native Fedora Workstation binary RPM and source RPM, built from upstream sources.
- One-line installer selects apt/.deb or dnf/.rpm and verifies native package
  identity, version, architecture and checksums before requesting privileges.
- GNOME 48–51 support, including the orientation API required by GNOME 51.
- Provider login supports Fedora's Ptyxis, GNOME Console and GNOME Terminal.
- Fedora CI covers native package build, DNF install/removal, native imports and
  an isolated GNOME panel/popup using synthetic DEMO data.

## 0.3.1 — 2026-11-02

- Recover immediately when Claude Code renews credentials after an authentication
  failure, instead of waiting for an old error's hour-long backoff.
- Check authentication recovery every minute while keeping provider rate-limit
  backoff intact. Credentials remain owned and refreshed by the official CLI.
- Never show cached percentages as current after a failed or stale reading;
  retain last-good data privately for recovery and hide expired quota windows.
- Apply the same freshness rules when another reader holds the cache lock.
- Subscription usage is account-wide, including activity on other computers.

## 0.3.0 — 2026-10-31

- Choose Claude's 5-hour limit, weekly limit, or both in the panel.
- Older settings that hid the weekly limit keep their previous 5-hour-only mode.
- Customize available, warning and critical colors with native color pickers;
  reset to theme-aware automatic colors with one click.
- Share the palette between panel and popup, with adaptive readable percentage text.
- Separate General and Appearance settings tabs.

## 0.2.1 — 2026-10-31

- First public release, with English/Italian documentation and a one-line installer.
- Installer verifies release checksums and Debian package identity before requesting privileges.
- Automated build workflow and installer regression coverage.
- Popup limits use a subtle background tint and matching percentage color,
  sharing the panel's remaining-quota thresholds and adapting to the Shell theme.
- Larger popup meters and slightly emphasized percentages improve readability.

## 0.2.0 — 2026-10-31

- Separate inline Claude meters for the 5-hour and weekly quota; one Codex meter.
- Provider logos replace panel names by default; names remain available in settings.
- Green, amber and red reflect remaining quota, independently of the used/remaining display mode.
- Provider icon provenance and CC0 notice included in source and packages.

## 0.1.0 — 2026-10-30

- First original GNOME 48 implementation: inline usage bars and reset times.
- Native account setup and preferences, with login through official CLIs.
- Official Codex account protocol and read-only Claude usage polling.
- Private usage cache, error backoff, stale indicators, and offline demo.
- .deb, self-contained extension ZIP, and source distribution builds.
