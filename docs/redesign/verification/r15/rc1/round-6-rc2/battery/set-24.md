# set-24 batch-6/W5-host-actions-portfolio (rc1-battery-12, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-011 | pinned test grep: parity table (host-actions.test.ts:1661-1792) + parseHostAction bound at enqueue (proposed-changes.ts:102) (raw: raw/set-24/R15-CODE-FRONTEND-011.txt) | tests+source present | ci_pinned |
| R15-CODE-FRONTEND-007 | pinned test grep: P5 accept-targets-bound-portfolio (host-actions.test.ts:1835, :1862); portfolioId bound in intent (raw: raw/set-24/R15-CODE-FRONTEND-007.txt) | present | ci_pinned |
| R15-CODE-FRONTEND-009 | pinned test host-actions.test.ts:1416 (save_screen saves recipe, says replaced) (raw: raw/set-24/R15-CODE-FRONTEND-009.txt) | present | ci_pinned |
| R15-CODE-FRONTEND-010 | pinned test host-actions.test.ts:1458 (run:true runs once) (raw: raw/set-24/R15-CODE-FRONTEND-010.txt) | present | ci_pinned |
| R15-AGENT-042 | pinned tests host-actions.test.ts:1291 + PortfolioPanel.test.tsx:162 (publishes holding ids) (raw: raw/set-24/R15-AGENT-042.txt) | present | ci_pinned |
| R15-DATA-088 | pinned tests portfolios.test.ts:49-74 (restore drops bad qty/neg cost) + host-actions.test.ts:1271 (raw: raw/set-24/R15-DATA-088.txt) | present | ci_pinned |
| R15-CODE-FRONTEND-012 | pinned test host-actions.test.ts:1210 (no fetch); grep of host-actions.ts/portfolios.ts for portfolio/positions|syncPositionToSidecar|sidecarPositionId -> exit 1, no hits (raw: raw/set-24/R15-CODE-FRONTEND-012.txt) | present | ci_pinned |
| R15-DATA-089 | same pinned test; grep -rn syncPositionToSidecar|sidecarPositionId|portfolioUrl src -> no hits (raw: raw/set-24/R15-DATA-089.txt) | present | ci_pinned |
| R15-CODE-PLATFORM-022 | own repro grep addPosition|updatePosition|deletePosition in src: only portfolios.test.ts comment + test mock; portfolios.ts exports no client (raw: raw/set-24/R15-CODE-PLATFORM-022.txt) | no production importer/client | holds |

No vitest/GUI run by role rule; frontend entries are certified by the named vitest nodes (heavy lane runs them).
COVERAGE: 24/24 ids raw; no raw: none
