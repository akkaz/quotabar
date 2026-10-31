# Validation

Target: GNOME Shell 48 on Ubuntu 25.04. First development build, 0.1.0.

Automated checks and graphical checks are recorded separately. Running unit
tests does not prove that a real panel, browser login, or login autostart works.

## Acceptance scenarios

- Both providers signed in: show actual windows and model-specific details.
- Weekly-only Codex plan: show 7g, without inventing a 5h quota.
- Provider absent, API-key account, expired session, offline, and HTTP 429:
  explain the state and preserve old data visibly.
- Manual refresh must not bypass provider backoff.
- Both providers hidden: keep a QuotaBar control that opens settings.
- Demo mode: DEMO remains visible; no provider requests.
- Open and navigate the menu and preferences by keyboard.
- Change compactness, position, remaining/used, bars and countdown.
- Enable, disable and re-enable without duplicate timers or indicators.
- Install .deb, log out/in, verify launcher, extension activation and persistence.
- Sign in through each official browser flow in a fresh profile.
- Uninstall and verify the extension and launcher disappear after session restart.

## Evidence

Executed on 2026-10-30/31:

- 13 Python tests: provider normalization, weekly-only Codex, absent versus zero
  data, model windows, backoff, stale-data preservation, private cache, token
  expiry boundary, blocked HTTP redirects, and bounded app-server cleanup.
- 13 GJS presentation assertions; native GTK/Libadwaita module imports and strict
  GSettings schema compilation. Desktop launcher validation passes.
- Authenticated reads of both real accounts with the new helper. No inference
  requests were issued.
- Actual GNOME Shell 48 rendering at 1440×900 in an isolated headless session,
  using a separate D-Bus, runtime, settings, data and cache directory. Synthetic
  DEMO data is visibly marked. Panel, popup and native preferences were captured.
- Independent visual review scored the identified clipping, informational text
  contrast, and group-description contrast fixes resolved. Final description
  contrast measured approximately 6.58:1. This verdict covers those fixes.
- Both popup actions accept native keyboard focus. Session startup restores the
  enabled extension in the isolated GNOME configuration.

Fresh browser login, installation/uninstallation in a clean VM, other desktop
resolutions/themes, and an actual user logout/login remain separate acceptance
checks. Existing-account reads do not prove a fresh authentication flow.

## 0.2.0 panel refinement

- 13 Python tests and 29 GJS presentation assertions pass. New coverage includes
  residual-quota color boundaries, color invariance between display modes,
  and the two-Claude/one-Codex selection policy.
- Actual GNOME 48 isolated renders at 1440×900 show exactly three inline meters
  and two provider logos. Synthetic fixtures deliberately exercise all three
  colors and a Codex plan with both windows, proving only one is shown inline.
- Used and remaining modes preserve the same risk colors. Switching logos off
  and on preserves all three meters. No JavaScript errors or missing SVG loads.
- Provider marks retain their original SVG paths and are separately attributed.

## 0.2.1 popup refinement

- The existing 13 Python tests, 29 GJS assertions, GTK imports, strict schema
  compilation and extension JavaScript syntax check pass.
- Actual isolated GNOME 48 rendering at 1440×900 shows four expanded synthetic
  quota windows: red, green, green and amber. Their background tints and percentage
  accents match their meter colors. No JavaScript errors or layout warnings.
- Accent text contrast on the 7% tint is at least 4.5:1 against the sampled native
  dark surface and white light-surface reference (six color/theme pairs).
- Installed-code updates require logout/login because of GNOME's module cache.
  Verification did not restart or log out the user's active desktop.

## Public distribution

- Eight installer regression tests exercise valid latest/pinned downloads,
  tampered files, duplicate checksums, wrong package identity, invalid metadata,
  invalid version arguments, and unsupported GNOME versions. Network access and
  privileged commands are mocked; checksum and Debian metadata checks are real.
- Public documentation screenshots contain synthetic DEMO data only.

## 0.3.0 configurable appearance

- 21 Python tests and 70 GJS presentation checks pass, with native GTK imports,
  strict schema compilation and JavaScript syntax checks.
- Window selection covers weekly-only, five-hour-only, both, absent requested
  windows and older weekly-toggle preferences.
- Color tests cover custom palettes, malformed values and injection attempts,
  plus readable accent text across 21 color/surface combinations.
- In isolated GNOME 48, actual native controls select each Claude mode, preserve
  the full popup, persist all three colors, update popup tints and restore the
  automatic palette. External setting changes and legacy preferences synchronize.
- The color control opens an actual visible `GtkColorChooserDialog` in the
  isolated session, rather than just changing a swatch programmatically.
