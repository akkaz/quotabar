# QuotaBar

<!-- impeccable:product-schema 1 -->

## Platform

Linux desktop, GNOME Shell 48–51 on Ubuntu/Debian and Fedora Workstation. This native shell surface
does not fit the web/iOS/Android platform enum.

## Stack

Native GNOME JavaScript (GJS/St for the panel, GTK 4/Libadwaita for settings)
and a bounded Python 3 standard-library helper. Implementation choice following
the user's instruction to build our own project. No Electron or hosted backend.

## Users

Linux users with Codex and/or Claude subscriptions who want to see available
quota without opening a terminal command or a provider's usage page.

## Product Purpose

Show usage bars, percentages, and reset countdowns in the top panel, launch
automatically at login, provide a small graphical configuration, and distribute
installable .deb packages with open source code.

## Capabilities and Constraints

- Original implementation. Other repositories may inform API/schema research;
  the user explicitly chose a project of our own over adopting a small project.
- Screenshot supplied by the user fixes a compact, inline information display.
- Provider login uses the unmodified official CLI and the browser.
- Codex data comes from the official app-server account protocol.
- Claude usage polling uses a non-public endpoint and may require maintenance.
- CLI credentials stay in their existing locations. QuotaBar does not renew or
  write Claude credentials; expired Claude sessions require the CLI/login.
- Polling is near real time: default Codex 60s, Claude 180s. Countdown is local.
- Quotas are account-wide, including other devices. Stale/error percentages
  must be hidden, and renewed CLI credentials must unblock authentication retries.
- A plan with only one quota window must not be shown as two windows.
- No credentials, account identifiers, conversations or telemetry in artifacts.
- Native Fedora RPM packaging uses the same source and preferences as the Debian
  package; the installer selects apt or dnf. KDE and Fedora Atomic need separate work.

## Brand Commitments

QuotaBar is a provisional project name, chosen during implementation. Native
GNOME appearance; no implied endorsement by OpenAI or Anthropic.

## Panel refinement requested 2026-10-31

Claude gets two meters (5 hours and weekly), Codex one. Provider logos replace
full names by default. Meter color follows remaining quota regardless of which
percentage mode is displayed. These are user-approved changes to the native system.

## Configurable appearance requested 2026-10-31

Claude can show 5 hours, weekly only, or both in the panel. Users can customize
the three quota-state colors and restore the automatic theme-aware palette.
The detailed menu retains all actual quota windows.
