# BL-03 Reasons about you — first 0.9.1 feature

## Status

- Not in 0.9.0.
- Moved off the release line by scope change 3 on 2026-09-27.
- Branch: `feature/bl-03-reasons-about-you`.
- Base: `origin/004-r4-experience-rebuild` at `0af5afc1`.

## Summary

BL-03 makes every answer about a held name start from the user's own position.
When the owner asks about a stock they hold, the sidecar preamble adds a short,
grounded line stating the position — quantity, average cost, weight in the
marked book, and unrealised P&L — pulled from the tracked portfolio the user
already keeps by hand, with zero extra tool calls and zero extra tokens beyond
two short lines. The research brief for a held name gets a matching "Your
position" metric card, derived on the renderer from data the store and the
portfolio-context bus already carry. No broker, no order, no portfolio write,
and no new agent tool or MCP projection — the feature only reads the user's
own hand-kept holdings.

## Panel ranking and verdict

BL-03 is the panel's rank-1 survivor: `4/5/4.5` value, `4/5/4.5` moat,
`5/5/5.0` feasibility, `4/4/4.0` demo, `5/4/4.5` lifecycle, for `1.5` value
per build-day, not killed. It is the only backlog row both judges score
feasibility 5 on and both mark as a small-build candidate — Judge A ranked it
2nd, Judge B ranked it 1st, and the panel's ranking rule places it 1st
overall. The panel calls it "the one small build" of the invent phase: an S
band, 2-3 day effort reading only the tracked portfolio the user keeps by
hand, closing census finding `WLD-agent-native-ux-1` (high), with no Tier-4
file touched and no new capability surface. The backlog lists it at rank 3
overall (tier 1, size S-M, 4 days, portfolio access "reads" only, no
dependencies), sourced from opportunity `OPP-7`.

## Files in this directory

- [`SPEC.md`](./SPEC.md) — the build-ready spec, verbatim copy of
  `docs/redesign/verification/r15/invent/specs/BL-03.SPEC.md`.
- [`CRITIC.md`](./CRITIC.md) — the critic pass, verbatim copy of
  `docs/redesign/verification/r15/invent/specs/BL-03.CRITIC.md`.
- [`PANEL_VERDICT.md`](./PANEL_VERDICT.md) — the judge-panel verdict and
  backlog row, extracted verbatim from
  `docs/redesign/verification/r15/invent/PANEL.md` and
  `docs/redesign/verification/r15/invent/BACKLOG.md`.

## How to build

Start from `SPEC.md` section 4, "File ownership" — it names the two
independent writer sets (sidecar, renderer), the exact files each one owns,
and the integrator steps that follow once both merge.
