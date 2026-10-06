# batch-10/W7-panels-marketplace

Candidate `4c6dfe8c` (rc1-cand worktree). Own sidecar `127.0.0.1:52340`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-078 | `grep -rn "alpha_vantage\|AlphaVantage\|alphavantage" sidecar/` + `grep alpha_vantage sidecar/requirements.txt`. | 0 hits in `sidecar/` source; 0 hits in `requirements.txt` — the non-existent fallback is not referenced or claimed anywhere in code. | holds |
| R15-DATA-004 | (already re-run live in set-0, same candidate/sidecar — not repeated here.) | See `set-0.md`: `held_percent_insiders`/`held_percent_institutions` correctly `flagged` against the NSE shareholding filing. | holds (see set-0) |
| R15-DATA-005 | `GET /fundamentals/VERTEX`. | `shares_outstanding: 74,012,189` (pre-rights) and `market_cap: 460,355,808` (post-rights basis) still coexist in one payload, but `field_meta.book_value.status: "flagged"`, reason: "shares outstanding 74,012,189 disagrees by 50% with the 148,024,376 shares implied by market cap / price ... may sit on a stale share count (e.g. before a rights issue) ... kept, flagged" — the mismatch is now surfaced, not silently divided through. | holds |
| R15-DOCS-004 | grep `docs/redesign/PRODUCT_DESIGN_DECISIONS.md:1-6` + `styles/tokens.css`. | Doc's line 3 now carries `> **SUPERSEDED (R15-DOCS-004):** §0–§7, §9, §10 describe the "Warm Graphite" palette ... reversed twice ...`; `tokens.css` matches the live pure-neutral + peach (`#161616`, `#fab283`) system, not the doc's stale amber/warm values. | holds |
| R15-DOCS-005 | `grep docs/BLUEPRINT.md:20` + `wc -l`/import count `src/modules/index.ts`. | Doc: "20 modules shipped in 0.9 (see §4 for the full ~37-module v1.0 roadmap)" — no longer claims "~38 modules" as the current count; `src/modules/index.ts` has 21 module imports wired into `vystedModules[]`, consistent with "20 modules" (one import is the registrar itself). | holds |
| R15-CODE-PLATFORM-024 | `cat src-tauri/capabilities/default.json` + `grep tauri-plugin-fs src-tauri/Cargo.toml package.json`. | `permissions: ["core:default", "notification:default", "shell:allow-open"]` — no `fs:*` permission; 0 hits for `tauri-plugin-fs` anywhere. (The cert's third listed permission, `global-shortcut:allow-is-registered`, is no longer present — outside this entry's scope, which is specifically the absence of raw filesystem access; not investigated further here per the entry's own repro.) | holds |

**Set result: 6/6 holds.**
