## $(date +%Y-%m-%d) - [Added tooltips to icon-only buttons]
**Learning:** Found multiple interactive elements in GTK UI (GtkMenuButton, tag remove button) missing tooltip descriptions, hindering accessibility for screen readers and new users.
**Action:** When adding or modifying GTK UI templates (.ui files) or programmatic widgets, always check for and add a `tooltip-text` property to icon-only buttons.
