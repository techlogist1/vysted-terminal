# Set: lows-P3/frontend-panels-shell-chrome (set-98) — rc1-battery-21 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-067 | pinned test exists at candidate (lows_spec.py) | DataBadges.test.tsx:36 'states synthetic in visible text...', :73 'dates EOD in the viewer's local calendar across IST midnight (R15-UI-067)' | ci_pinned (src/components/DataBadges.test.tsx) |
| R15-UI-074 | pinned test + code check | brief-layout.test.tsx:28 caps heading/prose/list at max-w-prose, table full width; brief-blocks.tsx:1007 and EquityOverviewPanel.tsx:405 apply max-w-prose | ci_pinned (src/modules/research/brief-layout.test.tsx) |
| R15-UI-066 | pinned test + code check | EmptyState.test.tsx:55 variant 'error' renders role=alert + distinct icon; EmptyState.tsx:56 role={isError ? "alert" : undefined} | ci_pinned (src/components/EmptyState.test.tsx) |

COVERAGE: 3/3 ids raw (battery/raw/set-98/); no raw: none
