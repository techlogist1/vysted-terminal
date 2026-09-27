# batch-12/W3-as-of-on-the-ratings-consensus (set-59.md) — rc1-battery-21, round 5-recheck

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar :52361.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-068 | Sidecar side (live): `GET /earnings/AAPL/history\|surprises\|estimates` and `GET /earnings/upcoming`. Frontend side (source re-check, no vitest run — battery role never runs vitest suites): `src/store/analyst-ratings.ts`, `src/store/earnings.ts`, `src/modules/analyst-ratings/AnalystRatingsPanel.tsx`. | All 4 sidecar earnings envelopes now carry a live `as_of` timestamp on the wire (previously none of the 3 named response models had one). Both frontend stores now pair each cached slice with `fetchedAt` (client) + `asOf` (server) and gate reads on a 15-min TTL (`isFresh`); a dedicated `refresh()` bypasses the TTL — the panel's Retry button now calls `refresh()`, not the same short-circuited accessor Load uses — and the panel renders "As of `<asOf\|fetchedAt>`" next to the data. Matches fix_shape (TTL + refresh + displayed timestamp) on both layers. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
