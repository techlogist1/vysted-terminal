<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->

# Open questions for the operator

Only what the operator alone can answer. Everything the lead can re-verify or
re-run at rc2 stays in `STAGE_D_INDEX.md`'s open-questions column instead.

Source: `docs/redesign/verification/r15/stage-d/FACTS.md`, sha f444479031d7d493b7955b9af041d18e7c7a40cc.

## 1. Open Tier-4 items (DECISIONS_FOR_OPERATOR.md)

| # | Item | Smallest unblock |
|---|---|---|
| 1.1 | The "sacred" `enrich_nse_sectors.py` edit is now committed (7a1cd8f) | `git revert 7a1cd8f` |
| 1.3 | Five local, never-pushed commits were rewritten once (brief said "no history rewrite") | nothing to undo on origin; to publish the brief, remove its line from `.gitignore` and commit it |
| 1.4 | Relicensed to PolyForm Strict 1.0.0 (operator decision, given 23 Sep 2026) | `git revert <relicense commit>` (subject: `chore(license): relicense core to PolyForm Strict 1.0.0`) |
| 2.1 | Default provider lanes are unfunded — the app cannot answer on them | top up OpenRouter (negative paid balance) or fund DeepSeek-direct ($0); restart the dev stack to pick up 043850c's gpt-5.x tool-calling fix |
| 2.2 | Docker/OrbStack is not running, so SearXNG is down and research silently uses the keyless scraper | start OrbStack before judging research depth |
| 2.6 | CI has never run on 004, and the last main run failed | open a PR against main / fix the red main lint run so CI's push+pull_request triggers actually fire |
| 2.7 | GUI rig: input-idle time is not proof the operator is away | add an away-sentinel file (`~/.vysted-rig-away`, with expiry) required in addition to idle time — not added because it would make unattended runs refuse until the operator knows about it |
| 2.8 | R15-RELEASE-001 — unsigned desktop bundles (Gatekeeper/SmartScreen block every install) | at minimum set `bundle.macOS.signingIdentity: "-"` in `tauri.conf.json` for an ad-hoc seal (still needs operator sign-off, Tier-1 file); full fix needs a paid Apple Developer ID + notarization and a Windows code-signing cert |
| 2.9 | R15-RELEASE-002 — no GitHub release pipeline (tags v0.6.0..v0.8.0 have zero installable builds) | approve adding `.github/workflows/release.yml` (3-OS matrix via `tauri-apps/tauri-action`, `createUpdaterArtifacts:true`, `TAURI_SIGNING_PRIVATE_KEY` wired); also unblocks 2.10 |
| 2.10 | R15-RELEASE-003 — auto-updater is dead end-to-end | approve 2.9 first (produces latest.json/.sig), then set `createUpdaterArtifacts:true` in `tauri.conf.json`; the consumer-side `app.updater()?.check()` call is not Tier-4 and can ship independently |
| 2.11 | R15-RELEASE-004 — CI has never run on `004-r4-experience-rebuild` | open a draft PR for `004-r4-experience-rebuild` (no workflow edit needed) so the existing `pull_request` trigger runs the 3-OS matrix; fix the red main lint run first so the signal is meaningful |
| 3.4 | BLOCKED-FOR-OPERATOR (Tier-1): no edit made, operator's call | decide whether to keep the `'trading-bot'` `PluginType` literal + JSDoc examples in `types/plugin.ts` as historical precedent or remove them (contract-breaking either way); apply the queued CLAUDE.md edits in `docs/redesign/CLAUDE_MD_PROPOSAL.md` when convenient; `COMMERCIAL_LICENSE.md:36-48` broker clause left as-is, no change required |

(2.3, 2.4, 2.5 omitted — closed, superseded by D81 trading removal.)

## 2. Copyleft: bundled AGPL/GPL/LGPL/SSPL packages

Facts only, per `DEPS_LICENCES.md` — no legal conclusion drawn.

| Package | Scope | Linkage |
|---|---|---|
| openbb-core@1.6.9, openbb-economy@1.6.1, openbb-equity@1.6.1, openbb-fmp@1.6.0, openbb-fred@1.6.0, openbb-mcp-server@1.4.0, openbb-news@1.6.0, openbb-yfinance@1.6.2 | AGPL-3.0-only (OSI classifier) | bundled, frozen into the `openbb-mcp` PyInstaller binary |
| sec-edgar-mcp@1.0.8 | AGPL-3.0 | bundled, frozen into the `sec-edgar-mcp` PyInstaller binary |
| Unidecode@1.4.0 | GPL (GPLv2+ classifier) | bundled, frozen into the `sec-edgar-mcp` binary |
| frozendict@2.4.7 | LGPL v3 | bundled into both the main sidecar and `openbb-mcp` binaries |

No SSPL packages found. `r-efi@5.3.0`/`6.0.0` (MIT OR Apache-2.0 OR LGPL-2.1-or-later, via `getrandom`) is reachable only under `cfg(target_os="uefi")`, never active on this app's macOS/Windows/Linux desktop targets, and is OR-licensed so MIT/Apache-2.0 is selectable — not counted above.

## 3. LICENCE_CHECK mismatches in Tier-1 files

| Location | What | Note |
|---|---|---|
| `CLAUDE.md:57-58` | "1. **Locked** — `docs/BLUEPRINT.md` §2. Never reopen unilaterally. (Stack; AGPL-3.0 + commercial dual license; MCP server in v1.0.)" | Stale — relicensed 23 Sep 2026 to PolyForm Strict 1.0.0 + commercial (BLUEPRINT.md §2/§6.1 already updated at this sha). Fix already drafted in `docs/redesign/CLAUDE_MD_PROPOSAL.md:76`, tracked open at `DECISIONS_FOR_OPERATOR.md §3.4` ("apply the queued CLAUDE.md edits ... when convenient"). Tier-1: CLAUDE.md is itself a Tier-1 file. |

## 4. Windows

Nothing verified. No Windows build/install/smoke-test evidence exists anywhere in the repo at this sha. `RELEASE_RUNBOOK.draft.md` §10 is entirely `NEEDS-MANUAL-CHECK` with zero verified precedent.

## 5. Secrets hits classed real_or_unknown

None. `SECRETS_SCAN.md` at this sha: `real_or_unknown: 0`, `pushed_real_or_unknown: 0` (1489 commits / 7353 blobs scanned in history, 40 files in the tree). Nothing to list, pushed or otherwise.

## 6. Draft open questions that need the operator's decision

(Excludes items the lead can settle by re-running/re-checking at rc2 — those stay in `STAGE_D_INDEX.md`.)

- **README** — whether to keep the 7-provider framing (OpenRouter folded in as a broker) or add OpenRouter as an explicit 8th provider row — the registry (`sidecar/config/model_registry.json`) lists 8 provider ids at this sha; this is a product-positioning call, not a fact to re-check.
- **RELEASE_NOTES** — whether `DECISIONS_FOR_OPERATOR.md` §2.1/§2.2 (unfunded provider lanes; SearXNG down without OrbStack) belong in a public release body at all, versus staying internal-only — an editorial/disclosure call.
- **CURRENT_STATE/BLOCKERS (STATE draft)** — the bundled line "T4-ccxt-executecommand-dead + T4-bare-commandids + T4-kite-manifest-unknown-field — plugin polish" bundles a broker-specific sub-item with `T4-bare-commandids`, which may be unrelated; needs the operator (or lead, on the operator's authority) to split or explicitly resolve it rather than have it carried forward silently.
