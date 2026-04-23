# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-22)

**Core value:** Physicians can quickly see what new drugs and new indications have been approved and access the complete prescribing information they need to make prescribing decisions.
**Current focus:** Phase 4: Automation & Deployment

## Current Position

Phase: 4 of 4 (Automation & Deployment)
Plan: 2 of 2 complete
Status: Phase Complete
Last activity: 2026-04-23 — Plan 04-02 complete (pipeline automation with systemd timer)

Progress: [█████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: ~10 min/plan
- Total execution time: ~2.5 hours (Phase 1 ~2h, Phase 2 ~20min)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Data Pipeline | 2 | ~2h | ~1h |
| 2. Site Shell & Index | 2 | ~20min | ~10min |
| 3. Drug Detail Pages | 2 | ~27min | ~14min |
| 4. Automation & Deployment | 2/2 | ~24min | ~12min |

**Recent Trend:**
- Last 5 plans: Phase 1 Plans 01-02, Phase 2 Plans 01-02 (all complete)
- Trend: Accelerating — Phase 2 was ~10x faster than Phase 1

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: NMEs + SUPPL approvals mixed in single list with type flag (core differentiator)
- [Init]: Static site with Python pipeline (no frameworks, no Node.js)
- [Init]: systemd timer for weekly data refresh (not cron)
- [Phase 1]: Only EFFICACY SUPPL code represents new indications (TYPE 1-10 are ORIG)
- [Phase 1]: Added date-range filter to API queries for efficiency
- [Phase 2]: Card layout on mobile for drug table (not horizontal scroll)
- [Phase 2]: System auto-detect + manual toggle for dark mode (localStorage)
- [Phase 3-01]: Regex-based HTML sanitizer (no external deps), slug collision detection via app number digits
- [Phase 3-02]: Native <details> for collapsible sections, root_path for subdirectory asset paths
- [Phase 4-02]: Weekly pipeline automation with systemd timer, Pushover failure notifications, no-change detection

### Pending Todos

None yet.

### Blockers/Concerns

- ~~Phase 1 needs SUPPL efficacy classification values verified against real openFDA data~~ — RESOLVED: only EFFICACY code
- ~~Phase 3 needs label HTML sanitization strategy tested against real FDA label data~~ — RESOLVED: regex-based sanitizer implemented and passing all tests
- ~~Phase 3 detail pages need correct asset paths from drugs/ subdirectory~~ — RESOLVED: root_path variable in base.html

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-23
Stopped at: Phase 4 Plan 02 complete — all phases done
Resume file: None (milestone complete)