# Phase 2: Site Shell & Index Page - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 02-site-shell
**Areas discussed:** Table layout & density, Dark mode implementation

---

## Table Layout & Density

| Option | Description | Selected |
|--------|-------------|----------|
| Horizontal scroll | All 6 columns visible, scrollable container on mobile. Compact row height. | |
| Responsive hiding | Hide indication column on mobile, show it on desktop. | |
| Card layout on mobile | Convert to a card/list layout on mobile (each drug becomes a stacked card). | ✓ |

**User's choice:** Card layout on mobile
**Notes:** Initially chose horizontal scroll, then selected card layout when presented with all three options. Most work to implement but best mobile experience.

**Follow-up — Row density:**

| Option | Description | Selected |
|--------|-------------|----------|
| Comfortable (~44px) | More whitespace, easier to scan. Similar to medupdates card style. | ✓ |
| Compact (~32px) | Fits ~30 rows on screen. More data visible but harder to scan. | |

**User's choice:** Comfortable (recommended default)
**Notes:** No additional context needed — straightforward preference.

---

## Dark Mode Implementation

| Option | Description | Selected |
|--------|-------------|----------|
| System + toggle | Auto-detect prefers-color-scheme AND manual toggle with localStorage persistence. Matches medupdates site. | ✓ |
| System auto only | Only auto-detect via prefers-color-scheme. No toggle button. | |

**User's choice:** Initially chose "System auto only", then reconsidered and chose "System + toggle" after a follow-up noting the medupdates site has a toggle and physicians need manual control in clinical settings.

---

## Claude's Discretion

- Exact breakpoint for mobile card layout
- Whether to use Pico CSS as a base or go fully custom
- List.js pagination vs no pagination
- Card layout details (full card with shadow vs simple stacked list)

## Deferred Ideas

None — discussion stayed within phase scope.