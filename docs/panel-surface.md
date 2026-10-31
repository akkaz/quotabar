# Panel and preferences

Mode: Operate. One inline indicator, a native GNOME popup, and Libadwaita settings.

## Direction contract

THESIS: make quota and reset time readable in a glance while working, in the
compact form pinned by the user's screenshot.

OWN-WORLD: inherit the GNOME panel's type, surfaces and symbolic controls;
neutral tracks with green/amber/red fills based on remaining quota. Settings use
native Libadwaita rows and controls, without a separate visual identity.

STORY: the panel answers how much and when; the menu adds windows, models,
freshness and recovery; settings connects accounts and adjusts density.
Popup limits share the meter's semantic accent with a restrained 7% background
tint and colored percentage. Labels, reset times and the native menu stay neutral.

FIRST VIEWPORT: provider logos identify the two groups. Claude shows a short
meter, percentage and reset time for each of 5h and 7g; Codex shows one actual
quota window. The weekly toggle controls the second Claude meter; a logo toggle
restores textual names. The open menu
starts with the provider's real windows; account setup begins with activation
and the two provider buttons. DEMO and stale states are explicit.

FORM: precisely specified native panel extension, inherited GNOME system;
concept tournament is not applicable to the pinned, narrow panel form.
Seed: not applicable: pinned native extension. No seed tool ran.

FINISH: unreviewed and undocumented is unfinished; this build ends with the
finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
