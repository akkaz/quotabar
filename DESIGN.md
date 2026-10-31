---
name: QuotaBar
description: Native quota meters and reset times in the GNOME panel.
colors:
  attention: "#f6c54b"
  quota-available: "rgb(34% 89% 54%)"
  quota-warning: "rgb(96% 77% 29%)"
  quota-critical: "rgb(100% 47% 41%)"
  claude-mark: "#d97757"
typography:
  title:
    fontSize: "1.15em"
    fontWeight: 700
  heading:
    fontWeight: 700
  provider-label:
    fontWeight: 600
  number:
    fontFeature: '"tnum"'
  secondary-label:
    fontSize: "0.9em"
  demo-label:
    fontSize: "0.8em"
    fontWeight: 700
rounded:
  meter: "3px"
spacing:
  window-inset: "10px"
  window: "8px"
  quota: "5px"
  related: "7px"
  providers: "18px"
components:
  inline-meter:
    rounded: "{rounded.meter}"
    width: "38px"
    height: "6px"
  popup-meter:
    rounded: "4px"
    width: "310px"
    height: "8px"
---

# Design System: QuotaBar

## Overview

**Creative North Star: "The inherited GNOME desktop"**

QuotaBar belongs to the existing desktop: a compact GNOME Shell indicator, a
standard shell popup, and GTK 4/Libadwaita preferences. The visual authority is
the inherited GNOME 48 system and the user's pinned inline usage-bar reference.
The system font, shell surfaces, native controls and focus treatments remain
authoritative; the project adds density, meters and restrained status color.

This document refreshes the original native design notes from the implemented
`extension/extension.js`, `extension/stylesheet.css` and `extension/ui.js`.
No concept seed ran and no replacement visual world was created. The panel's
surface strategy is recorded separately in `docs/panel-surface.md`.

**Key Characteristics:**

- Compact, inline quota information with a native menu for detail.
- System typography and surfaces, with a small explicit type hierarchy.
- Green, amber and red usage meters driven by remaining quota.
- Native Libadwaita rows and controls, with explicit DEMO and stale states.

## Colors

The host theme supplies foregrounds, surfaces, separators, selection and focus;
QuotaBar defines only semantic attention and usage colors in the frontmatter.
Theme-dependent values are deliberately not frozen into a light or dark palette.

### Primary

- **Attention amber:** identifies stale/error markers and the DEMO label.
- **Available green:** more than 50% remains.
- **Warning amber:** more than 20% and at most 50% remains.
- **Critical red:** at most 20% remains.
- **Light-surface variants:** green rgb(9% 45% 26%), amber rgb(62% 39% 0%),
  red rgb(78% 23% 20%) preserve contrast when the inherited foreground is dark.

### Neutral

- **Inherited foreground:** normal panel and popup text use the active Shell
  theme. Meter tracks use that foreground at 18% alpha; fills use semantic quota colors.
- **Shell secondary text:** applies 72% widget opacity and the secondary-label
  size, including reset times and freshness explanations.
- **Preferences secondary text:** retains inherited text color at 80% opacity
  for subtitles, dim labels and group descriptions. This override is scoped to
  the preferences window and removed when it closes.

**The Theme Ownership Rule.** Keep platform colors inherited unless the source
defines a semantic status color. Do not use a screenshot's resolved background
as a new project palette.

**The Text First Rule.** A meter always accompanies numerical text. Color cannot
be the only indication of quantity, stale data or synthetic values. The color always follows
remaining quota, independently of display mode. Switching to remaining mode
changes the panel fill and number, while the popup continues to show used percentage.

## Typography

The font family, base size, line height and default weight come from GNOME Shell
or GTK/Libadwaita. No bundled font or separate display face is used. Frontmatter
sizes are relative to the native parent text size, not a fixed desktop font.

- **Title:** identifies QuotaBar at the top of its popup.
- **Heading:** distinguishes provider sections without adding decorated labels.
- **Provider label:** gives Claude and Codex modest emphasis in the panel.
- **Number:** requests tabular numerals for changing percentages.
- **Secondary label:** distinguishes reset times, freshness and supporting text.
- **Demo label:** is small, bold and attention colored; synthetic data also has
  an explicit text description in the popup and preferences.

Native preferences use Libadwaita's existing row-title, subtitle and group-title
hierarchy. They do not reuse the Shell-specific type overrides.

**The Native Type Rule.** Preserve the user's system font and scaling. Add only
the relative hierarchy already evidenced in the implementation.

## Layout

The panel uses a horizontal group for each provider, identified by an 18px
symbolic logo. Each quota is its own group with `quota` spacing. Claude has
separate 5h and 7g labels, meters, percentages and countdowns; Codex has one
meter, preferring the actual weekly window when available. Textual provider
names can replace logos; compact fallback names remain `Cl` and `Cx`. Inline
labels keep their full natural width without ellipsizing. The Claude window selector chooses both, five-hour-only, or weekly-only; the
legacy weekly preference remains readable for upgrades. No missing window is invented. The indicator can be placed at the left, center or right of the panel.
When both providers are hidden, the button retains the `QuotaBar` fallback label.

Popup quota windows stack a label/value row, meter and reset line. Each window
has a minimum width matching its popup meter, uses `window` spacing and
`window-inset` padding. A 7% alpha wash of the meter color and a matching
percentage accent make each limit easier to scan; unknown values stay neutral.
Percentage text is 1.05em at weight 600. The uncolored native row supplies the
theme foreground used to select dark/light accents. Custom colors are validated six-digit hex values; blank settings use the
theme-aware defaults. Percentage text keeps the selected color when contrast
permits, otherwise it is mixed toward black or white until legible on the actual
menu surface and its tint. Meter fills retain the chosen color. Explanatory labels wrap with a maximum width of
340px. Native popup rows provide their own surrounding padding and separators.

Preferences open at a default size of 620 × 760px with two native pages.
General contains activation, accounts, polling and demonstration. Appearance
contains panel options and three native color pickers with
a reset action. This default window size is an initial request; it is not a
fixed minimum or a guarantee that all settings fit without scrolling.

## Elevation & Depth

GNOME Shell owns popup surfaces, separators, depth and menu focus states.
Libadwaita owns window chrome, preference group containers, controls and toasts.
QuotaBar adds no custom shadow, blur or elevation scale. Those inherited effects
may change with the host theme and should not be transcribed as project tokens.
There is no custom animation vocabulary; data and countdown updates are direct.

## Shapes

Usage meters are horizontal pills. Their radius is half their height; the two
implemented sizes are recorded as components in the frontmatter. The fill is
clipped to the clamped percentage of the full track, so a very small positive
value does not acquire an oversized rounded cap. Zero draws no fill.

All other corner radii, borders, switches, button shapes and popup geometry are
native. The original application icon uses vector geometry with three horizontal
meters. Provider marks are separate SVG assets, used only to identify the
connected services. Provenance and CC0 attribution live in THIRD_PARTY_NOTICES.md;
they are not QuotaBar branding. No raster assets are shipped.

## Components

### Inline provider group

A provider logo (or optional name) precedes its quota groups. Every displayed
quota has its own short meter, percentage and optional reset countdown. Loading or missing
data uses an em dash; an error without windows uses `!`. Stale cached values keep
their numbers and add the attention marker. Expired windows use secondary text.
The full button has an accessible name including provider/window percentages,
the used/remaining mode and synthetic-data status.

### Popup quota window

The window name is left aligned and its used percentage is aligned at the right.
The long meter and reset text sit below. Informational rows retain normal text
rendering and are not focusable actions. A reset that has elapsed is described
as awaiting a new reading rather than presented as freshly updated data.

### Popup actions

Refresh and account/settings actions are standard GNOME Shell menu items with
inherited pointer and keyboard states. Refresh is disabled during a reading and
its label describes the work in progress. A menu rebuild restores the focused
action by label when possible; no custom focus-ring treatment is introduced.

### Preferences rows and feedback

`Adw.SwitchRow` handles boolean settings. `Adw.ComboRow` selects panel position.
`Adw.ActionRow` carries native login/refresh buttons and numeric `Gtk.SpinButton`
controls; each numeric row names its activatable input. Text is literal, without
Pango markup. Read errors are stated inline or in a five-second native toast.
The account rows show available real windows and last-read age. Demo data is
explicitly described; it is never passed off as an authenticated account.

### Native evidence and limits

The supplied finish review covers actual isolated GNOME 48 captures at
1440 × 900px (`.impeccable/review/panel.png` and `preferences.png`) with synthetic
data marked DEMO. It reports the inline clipping and popup/account contrast fixes
as shipped, including a 6.58:1 group-description contrast measurement in that
captured environment. This documentation pass did not repeat that review.

Those captures do not establish all theme, text-scale, monitor-scale or keyboard
and assistive-technology combinations. Fresh browser authentication and a real
desktop logout/login remain unverified. Other GNOME versions and KDE remain
outside the confirmed compatibility scope.

The Impeccable web CSS detector cannot enforce GJS/St or GTK/Libadwaita patterns.
The v2 sidecar therefore contains native design metadata and narrative without
fabricated HTML component previews, synthetic tonal ramps or web breakpoints.
Native source inspection and actual GNOME execution remain the relevant checks.

## Do's and Don'ts

### Do:

- **Do** inherit GNOME and Libadwaita typography, surfaces and interactive states.
- **Do** keep numerical quantities and explicit state text alongside meter color.
- **Do** mark synthetic data as DEMO and preserve last-success age for stale data.
- **Do** use native preference rows and controls for new settings.
- **Do** keep actual quota windows and the panel's used/remaining mode accurate.

### Don't:

- **Don't** replace the inherited desktop with a separate web-style visual world.
- **Don't** freeze inherited theme values into a new fixed light or dark palette.
- **Don't** imply provider endorsement or use their logos as QuotaBar branding.
- **Don't** fabricate a second quota window for plans that expose only one.
- **Don't** describe isolated DEMO captures as proof of fresh login or all desktop configurations.
