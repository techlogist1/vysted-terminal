# CLAUDE.md single-commit audit (Stage D item 5)

Auditor pass, 07:08 IST 26 Sep. Repo `/Users/lokavyasingh/Documents/dev/vysted-terminal`,
branch `004-r4-experience-rebuild`, HEAD `917d2438`. Candidate commit under audit:
`c1e9164c` on `origin/worktree-agent-r15-version-0.9.0` (branch also carries `517da226`,
the version bump, which does not touch `CLAUDE.md`). Base commit for the CLAUDE.md diff:
`3d64ca17`.

Every row's "true at HEAD" column is evidence read directly from a file in this pass — where
a claim could not be independently verified, that is stated instead of assumed.

## Item table

| Item | Branch CLAUDE.md says (line, at `c1e9164c`) | True at HEAD (evidence) | Status | Fix |
|---|---|---|---|---|
| (a) held 3 Sep hunk | `c1e9164c` diff inserts the "OpenAI chat-completions has two tool-time 400 traps" gotcha verbatim, 9 lines, right after the MCP-boundary bullet in Gotchas → Copilot & sidecar code | `git diff -- CLAUDE.md` in the main worktree (local, uncommitted) is exactly the same 9-line insertion, byte-for-byte (`git diff --stat -- CLAUDE.md` → `1 file changed, 9 insertions(+)`; confirmed against the scratchpad-saved `claude-md-local.diff`) | covered | none |
| (b) `docs/redesign/CLAUDE_MD_PROPOSAL.md` applied | See sub-rows below — the R8/R13/relicense/D81 proposal sections are applied near-verbatim; three R7-era Gotchas items are not carried over | Mixed — see sub-rows | **partial** | apply the two still-current gaps below; treat the rest of the dropped R7 material as correctly stale (confirm before merge) |
| (b.1) Stack — Next.js → Vite | `CLAUDE.md` (branch) line 28-31: "Vite 8 + React 19 + TypeScript (single-page shell...)" | `package.json`: `"vite": "^8.0.16"`, `"react": "19.2.6"`, no `next` dependency; `vite.config.ts` exists, no `next.config.*`; register `R15-DOCS-003` (medium, `blocked_tier4`) names exactly this drift and is closed by this commit | covered | none |
| (b.2) Stack — JetBrains Mono self-hosting note | absent from branch `CLAUDE.md` Stack section entirely | `package.json:60` `"@fontsource/jetbrains-mono": "^5.2.8"`; `styles/tokens.css:94-98` — `--font-jetbrains-mono` defined there, imported/self-hosted in `src/main.tsx` per the file's own comment | **missing** | append the one clause to the Frontend bullet (see addendum diff) |
| (b.3) R8 — `wait_for_port_with_retries` | branch line ~139: "call `crate::wait_for_port_with_retries` (45 s × 2 ...)" | matches proposal's R8 section verbatim | covered | none |
| (b.4) R13 — attended-safe smoke-test line | branch Verification-gates section: "spawns each built sidecar on an ephemeral port, TCP-probes MCP binds, and asserts `/health` version + `/agents` count + `/mcp/status`... attended-safe..." | matches proposal's R13 section verbatim | covered | none |
| (b.5) Relicense (2026-09-23 proposal) | branch Decision-authority §1: "PolyForm Strict 1.0.0 + commercial license (relicensed 23 Sep 2026; plugin contract + example plugin Apache-2.0, see `LICENSING.md`)" | see item (e) below — fully verified against `LICENSE`, `COMMERCIAL_LICENSE.md`, `LICENSING.md`, `LICENSE-APACHE` at HEAD | covered | none |
| (b.6) D81 trading-removal edits (layout, Tier-1 line, §6.5 bullets, plugin-contract wording, Copilot gotcha, credentials section, Frontend gotcha, reference docs) | all eight sub-edits from the proposal's "2026-09-23 proposal — trading removed" section are present in the `c1e9164c` diff | see item (g) below — fully verified against HEAD's empty `sidecar/services/brokers`, `plugins/` listing, absence of `kill_switch.{py,rs}`, and `sidecar/tests/test_no_trading_surface.py` | covered | none |
| (b.7) Gotchas → Frontend — Vite watcher ignore patterns | absent from branch `CLAUDE.md` | `vite.config.ts:22-27` — `server.watch.ignored` lists exactly `**/.claude/**`, `**/out/**`, `**/sidecar/**`, `**/src-tauri/**`, `**/graphify-out/**`, with a comment explaining the mid-session-reload failure mode the proposal describes; this is a real, still-true trap, not one of the commit message's named "stale R7 items" | **missing** | add the one bullet (see addendum diff) |
| (b.8) Gotchas → Frontend/Copilot — tauri-plugin-mcp bridge wedge after Vite HMR, WKWebView stale-JS full-restart, `layout-templates.ts` registered-id gotcha, frontend control-keys-via-`options`, composer depth-slider default, `transform.code` workflow node, `save_workflow` MCP-only listing | none of these seven proposal items appear in the `c1e9164c` diff | **not independently re-verified for current truth in this pass** — the commit message names only four R7 items as deliberately dropped-as-stale ("search-tier header names, dev-signing cert, BSE counts, rig-only notes"); these seven are not among them, so their omission is undocumented | **unverifiable** (currency not checked) | lead should spot-check each against HEAD before the merge — if still true, fold in; if superseded, name them in the commit message the way the other four are named, so a silent drop doesn't read as a miss |
| (c) this run's Gotchas lessons | branch Gotchas gained: keychain dev-keystore reconciliation, `ADAPTER_OPTION_KEYS` allowlist, keyless-local-lane known-limitation, `deserializeWorkspace` non-layout-slices restore order (R15-LIFECYCLE-002), plugin-catalog `CATALOG_ROWS` rewrite, OpenAI 400-trap gotcha (item a) | `docs/redesign/KEYCHAIN_DEV_SIGNING.md:3,8,18,25-27` confirms the dev-keystore mechanism; `sidecar/services/llm/__init__.py:72` defines `ADAPTER_OPTION_KEYS`; register `R15-LIFECYCLE-002` (status `fixed`) matches the new Frontend-gotcha bullet; `src/lib/marketplace.ts:59-`, `:39,46,51` confirm `CATALOG_ROWS`/`panelComponents` replace `PLUGIN_COMPANIONS` exactly as `docs/redesign/verification/r15/stage-d/FACTS.md:83` (R15-DOCS-015) describes | covered | none — **except** the rig-pointer lesson from `REHEARSAL.md`, which is an R15-diagnosed lesson from the bundle rehearsal and is NOT carried into `c1e9164c`; see item (f) |
| (d) stale — Model assignment | branch lines 127-130: Opus lead / Sonnet mechanical / **`Haiku` — log parsing, high-volume mechanical scanning** — unchanged by `c1e9164c` (no hunk touches this section) | `docs/redesign/verification/r15/tooling/r15-fanout.js:12,14,19` hard-refuses any stage/item whose model matches `/haiku|fast/i` ("Haiku / the fast tier are never used"); `docs/redesign/verification/vysted-r15-run-state.md` — every ROUTING CHANGE entry (1 through 5, the last one in effect) states "never Haiku, never the fast tier"; the run's actual three-tier practice is Sonnet-default / Opus-judgement / Fable-rare-escalation, with Haiku categorically banned | **wrong** | replace the Haiku bullet (see addendum diff) |
| (d) stale — Stack | see (b.1) | see (b.1) | covered | none |
| (e) licence line | branch Decision-authority §1: "PolyForm Strict 1.0.0 + commercial license (relicensed 23 Sep 2026; plugin contract + example plugin Apache-2.0, see `LICENSING.md`)" | `LICENSE:1` = "PolyForm Strict License 1.0.0"; `COMMERCIAL_LICENSE.md:7-19` confirms the two-path model (PolyForm Strict noncommercial / commercial for everything else); `LICENSING.md:40-52` — the Apache-2.0 carve-out lists exactly `types/plugin.ts`, `types/plugin-runtime.ts`, `plugins/example/index.ts`, `plugins/example/example.test.ts`, `plugins/example/manifest.json`, matching "plugin contract + example plugin Apache-2.0" precisely; `LICENSE-APACHE` exists at repo root; `docs/redesign/DECISIONS_FOR_OPERATOR.md:725-740` (§5.4) independently states the AGPL line at old `CLAUDE.md:57-58` was stale, and that "the fix is already committed as `c1e9164c`... there `CLAUDE.md:59` reads 'PolyForm Strict'" | covered | none |
| (f) rig pointer + owner name | branch `CLAUDE.md` (Visual verification, line 330 at this sha — line 325 in the sha `NEW_LOWS_DRAFT.md` cites, drift explained by unrelated Gotchas insertions above it): "Quartz path (`/tmp/rigcap.py`, matched on `kCGWindowOwnerName == \"vysted-terminal\"`) instead" — **`c1e9164c` does not touch this section at all** | `docs/redesign/verification/r15/stage-c/lows/NEW_LOWS_DRAFT.md:55-69` (R15-DOCS-026, low, Tier-4, open) and `docs/redesign/verification/r15/stage-d/bundle-rehearsal/REHEARSAL.md:70-71,112-115` both record the same real observation from an actual release-bundle launch: the CGWindow owner name is the display name `Vysted Terminal`, not `vysted-terminal`; and `/tmp/rigcap.py` was never checked into the repo / does not exist on a clean machine | **missing** | correct the owner-name match string and drop the dead helper pointer (see addendum diff); `NEW_LOWS_DRAFT.md`'s own note flags this fix must ride the operator's single CLAUDE.md commit, which is exactly what this addendum is for |
| (g) trading removed permanently (D81) | branch: `src-tauri/` layout line drops "kill-switch"; `plugins/` line drops `brokers`; Decision-authority §1 states D81 removed trading permanently; §6.5 collapses to one line naming `sidecar/tests/test_no_trading_surface.py`; "Read-only trading-wrapper plugins" → "Read-only wrapper plugins"; Copilot gotcha drops "orders still never auto-apply"; "Broker & credentials" → "Credentials", Kite Connect + granular-broker-reads bullets deleted; reference-docs line drops `docs/BROKER_INTEGRATIONS.md` | `git ls-files sidecar/services/brokers` → 0 files (directory has no tracked contents at HEAD); `git ls-files plugins` → only `example`, `openbb-mcp`, `vysted-lenses`, `vysted-news`, `yfinance` (no brokers plugin); `sidecar/services/kill_switch.py` and `src-tauri/src/kill_switch.rs` both return "No such file" at their real (non-worktree-cache) paths; `sidecar/tests/test_no_trading_surface.py` exists; `docs/redesign/verification/r15/stage-d/CURRENT_STATE.draft.md:38-46,210-341,657-659` independently states "Trading removed permanently (D81, `a122dbf6`, 23 Sep 2026)... no broker/Kite service code, tools, routes or docs" and "`kill_switch.rs` was deleted with trading (D81)" | covered | none |

## Verdict

**`c1e9164c` is not sufficient as the single CLAUDE.md commit.** It correctly and
accurately carries (a), (e), (g), and the bulk of (b)/(c)/(d) — the relicense line, the D81
trading-removal edits, the Vite stack line, and the new R15-diagnosed Gotchas (keychain,
`ADAPTER_OPTION_KEYS`, keyless-local-lane, `deserializeWorkspace` slice order,
`CATALOG_ROWS`) are all verified correct against HEAD. But it is genuinely incomplete on two
of the audit's own named items:

- **(d) Model assignment is wrong, not just stale** — it still prescribes Haiku for a run
  that hard-bans Haiku at the tooling level (`r15-fanout.js`) and has stated "never Haiku"
  in every routing change since 03:52 IST 23 Sep. This is the kind of thing a fresh session
  reads as license to dispatch a banned tier.
- **(f) the rig pointer is untouched** — R15-DOCS-026 is an open, Tier-4-flagged, in-register
  low that names this exact commit as its required vehicle, and `c1e9164c` does not touch
  the Visual-verification section at all.

Plus two smaller, real gaps under (b): the JetBrains Mono Stack clause and the Vite
watcher-ignore Gotcha are both still-true facts from `CLAUDE_MD_PROPOSAL.md` that did not
make it into the commit and are not named among its explicitly-dropped stale items.

Because the operator's release plan requires **exactly one** CLAUDE.md commit and the lead
is instructed to never add a second one, the four fixes above cannot be a follow-up commit
without breaking that constraint. **Recommendation: the lead re-cuts the version branch —
amend/replace the `c1e9164c` commit in place (not add a second CLAUDE.md commit) using the
addendum diff below as the missing delta**, then re-verify §5.4's pointer in
`DECISIONS_FOR_OPERATOR.md` still resolves (it names the sha `c1e9164c`; a re-cut commit
will need a new sha and that line updated too — flagging this as a second-order dependency,
not fixed by this audit).

The seven R7-era Gotchas items at row (b.8) are flagged **unverifiable** in the time budget
of this audit (no tests/builds/app were run, per this audit's own off-lane rules) — the lead
should spot-check them before merge; they are not included in the addendum diff below
because their current truth was not established.

## Addendum diff

See `docs/redesign/verification/r15/stage-d/CLAUDE_MD_ADDENDUM.draft.diff` — a unified diff
against `origin/worktree-agent-r15-version-0.9.0:CLAUDE.md` (i.e., against `c1e9164c`'s own
content) carrying exactly the four fixes marked **missing**/**wrong** above: the JetBrains
Mono clause, the Haiku→banned-tier correction, the Vite watcher-ignore Gotcha, and the rig
owner-name/dead-pointer correction. Verified with `patch --dry-run` against a fresh copy of
the branch file — applies cleanly, 4 hunks.
