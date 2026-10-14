# UI-6 — ProposedChangesReview (final-adv-maintainer, d38b5d1a)

Harness: scratch vitest jsdom, real `<ProposedChangesReview/>` rendered with @testing-library, real store. Evidence: UI-6/harness-gate.json.

- Old/new shown: the region "Proposed changes" renders each card with a `−` before line and a `+` after line ("Update position in the portfolio − Portfolio: unchanged + can't apply — AAPL is not in the active portfolio"; data-write AC-2 cards: "Portfolio: +TCS ×5 @ ₹3,500 (2 total)").
- Reject (clicked via `aria-label="Reject: …"`): status `rejected`, portfolio + watchlist snapshot byte-identical before/after.
- Unknown action `frobnicate_everything`: card reads "frobnicate everything − — + Unknown action — can't apply"; accept() → `failed`, status re-pends with detail `unknown action "frobnicate_everything"`, and the card then shows "Couldn't apply: unknown action … — try again." Under AUTO it is auto-attempted (kind panel) and fails the same way; nothing applied.

VERDICT UI-6: pass
