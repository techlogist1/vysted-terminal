# Mockups

Pillow-rendered **stand-ins**, not real screenshots. They approximate a
panel's populated-state layout (column widths, sortable headers, tab nav)
before a live capture exists — never evidence of what the app actually
renders. See this repo's `CLAUDE.md` visual verification protocol for what
counts as a real screenshot.

## Files

Relocated here (R15-DOCS-012) from `docs/screenshots/v0.6.0/teammate-e/`
and `docs/screenshots/v0.6.0/teammate-sc/`, where they sat unlabeled next to
real captures from other Phase 6 teammates. The `mock-` prefix makes the
distinction unmistakable at a glance; the never-overwrite rule for
`docs/screenshots/v<tag>/` protects real captures, not these.

- `mock-earnings-calendar-{1920x1080,2560x1440}.png`
- `mock-analyst-ratings-{1920x1080,2560x1440}.png`
- `mock-screener-panel-{1920x1080,2560x1440}.png`

All six are also in the retired v0.6.0-era amber/charcoal palette
(superseded by the zinc + cool-indigo system — see this repo's `CLAUDE.md`
Gotchas), a further reason they can never stand in for a current release's
verification screenshots.

Their generator scripts (`scripts/render_phase_6_e_screenshots.py`,
`scripts/render_phase_6_sc_screenshots.py`) are deleted (R15-CODE-PLATFORM-064):
they depended on an undeclared `Pillow`, and `load_font` only tried
Windows font paths, silently collapsing every requested size to
`ImageFont.load_default()` on macOS/Linux — three "distinct" font sizes
that were actually identical. Dead v0.6.0 tooling; not worth fixing in
place. A real screenshot still requires a live `pnpm tauri dev` session
captured via chrome-devtools MCP, per `CLAUDE.md`'s visual verification
protocol.
