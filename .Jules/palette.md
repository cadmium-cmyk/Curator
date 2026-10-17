## 2026-10-17 - Add Tooltips for Icon-Only Buttons
**Learning:** In GTK 4 applications like Curator, the 'tooltip-text' property serves the dual purpose of providing visual tooltips on hover and acting as the accessible name for screen readers, effectively functioning like an aria-label in web contexts.
**Action:** Always check icon-only interactive elements (like GtkButton and GtkMenuButton) for the presence of a 'tooltip-text' property and add them when missing to ensure proper accessibility.
