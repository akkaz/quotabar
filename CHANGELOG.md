# Changelog

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
