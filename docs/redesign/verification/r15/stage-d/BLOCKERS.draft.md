<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->
# Blockers & Known Issues

Lead-level open items as of 0.9.0 candidate f4444790. Each release rolls its
carry-forwards into this file; resolved items become `~~struck through~~`.
See `CHANGELOG.md` and `docs/PHASE_N_HANDOFF.md` for per-phase context. The
pre-R15 header line this replaced read "as of v0.8.0"; the R15 open-items
section immediately below is the current top-of-file truth.

## R15 open items (as of 0.9.0 candidate f4444790)

Sourced from `docs/redesign/DECISIONS_FOR_OPERATOR.md` and
`docs/redesign/verification/vysted-r15-register.json`; see
`docs/CURRENT_STATE.md` §0.0 for the version/licence/Stage-C summary. This
section is additive — everything below it in this file is unchanged R15
carry-forward history except where explicitly struck through.

- **0.9.0 bump not made** — `package.json:3`, `src-tauri/Cargo.toml:3`,
  `src-tauri/tauri.conf.json:4`, `sidecar/app.py:327`,
  `src/lib/plugin-bootstrap.ts:37` are `0.8.0` (FACTS §versions); after
  editing run
  `cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml`
  (CLAUDE.md §Versioning) and grep for stale `0.8.0` strings.

### Open Tier-4 decisions (need the operator)

One-line unblocks read verbatim from `DECISIONS_FOR_OPERATOR.md`:

- **1.1** — the "sacred" `enrich_nse_sectors.py` edit is now committed
  (`7a1cd8f`). Unblock: `git revert 7a1cd8f`.
- **1.3** — five local, never-pushed commits were rewritten once (the brief
  said "no history rewrite"). Unblock: nothing to undo on origin; to publish
  the brief, remove its line from `.gitignore` and commit it.
- **1.4** — relicensed to PolyForm Strict 1.0.0 (operator decision, given 23
  Sep 2026). Unblock: `git revert <relicense commit>` (subject:
  `chore(license): relicense core to PolyForm Strict 1.0.0`).
- **2.1** — the operator's default provider lanes are unfunded — the app
  cannot answer on them. Unblock: top up OpenRouter (negative paid balance)
  or fund DeepSeek-direct ($0); restart the dev stack to pick up `043850c`'s
  gpt-5.x tool-calling fix.
- **2.2** — Docker/OrbStack is not running, so SearXNG is down and research
  silently uses the keyless scraper. Unblock: start OrbStack before judging
  research depth.
- **2.6** — CI has never run on 004, and the last `main` run failed.
  Unblock: open a PR against `main` / fix the red `main` lint run so CI's
  push+pull_request triggers actually fire.
- **2.7** — GUI rig: input-idle time is not proof the operator is away.
  Unblock: add an away-sentinel file (`~/.vysted-rig-away`, with expiry)
  required in addition to idle time — not added because it would make
  unattended runs refuse until the operator knows about it.
- **2.8** — `R15-RELEASE-001` — unsigned desktop bundles (Gatekeeper/
  SmartScreen block every install). Unblock: at minimum set
  `bundle.macOS.signingIdentity: "-"` in `tauri.conf.json` for an ad-hoc seal
  (still needs operator sign-off, Tier-1 file); full fix needs a paid Apple
  Developer ID + notarization and a Windows code-signing cert.
- **2.9** — `R15-RELEASE-002` — no GitHub release pipeline (tags
  v0.6.0..v0.8.0 have zero installable builds). Unblock: approve adding
  `.github/workflows/release.yml` (3-OS matrix via `tauri-apps/tauri-action`,
  `createUpdaterArtifacts:true`, `TAURI_SIGNING_PRIVATE_KEY` wired); also
  unblocks 2.10.
- **2.10** — `R15-RELEASE-003` — auto-updater is dead end-to-end. Unblock:
  approve 2.9 first (produces `latest.json`/`.sig`), then set
  `createUpdaterArtifacts:true` in `tauri.conf.json`; the consumer-side
  `app.updater()?.check()` call is not Tier-4 and can ship independently.
- **2.11** — `R15-RELEASE-004` — CI has never run on
  `004-r4-experience-rebuild`. Unblock: open a draft PR for
  `004-r4-experience-rebuild` (no workflow edit needed) so the existing
  `pull_request` trigger runs the 3-OS matrix; fix the red `main` lint run
  first so the signal is meaningful.
- **3.4** — BLOCKED-FOR-OPERATOR (Tier-1): no edit made, the operator's call.
  Unblock: decide whether to keep the `trading-bot` `PluginType` literal +
  JSDoc examples in `types/plugin.ts` as historical precedent or remove them
  (contract-breaking either way); apply the queued CLAUDE.md edits in
  `docs/redesign/CLAUDE_MD_PROPOSAL.md` when convenient;
  `COMMERCIAL_LICENSE.md:36-48` broker clause left as-is, no change required.

### Open non-Tier-4 operator items

From `DECISIONS_FOR_OPERATOR.md` §3, "New items from Stage C — trading
removal (D81)". Not Tier-4-blocked, but open (not yet acted on):

- **3.1** — UNSURE-1, user-side leftovers after upgrade (no code reads any of
  it; nothing purged): `~/.vysted-terminal/audit_log.db`, orphaned
  OS-keychain `broker:<id>:*` BYOK secrets, the old
  `broker:_meta:first-launch-tos` ack, and unreachable sidecar plugin-store
  rows for the 7 broker plugin ids. Unblock: approve a one-time "remove
  leftover broker credentials" purge step plus a CHANGELOG note on manually
  deleting `audit_log.db` and the keychain entries.
- **3.2** — first-launch terms rewrite (was on the §6.5 surface, includes
  licence wording): the dialog body changes from broker-connect framing to
  research-only terms. Unblock: review the exact copy in
  `src/modules/safety/DisclaimerFlow.tsx` before it ships (flagged Tier-4 by
  R15-UI-041).
- **3.3** — accepted agent-write safety gaps (stated in
  `docs/SAFETY_ARCHITECTURE.md`, not silently dropped): no durable record of
  agent writes beyond `action_ledger.py`'s 10-minute TTL
  (R15-CODE-FRONTEND-013), and no stop control for AUTO beyond reject or
  run-cancel (R15-CODE-FRONTEND-008). No unblock proposed — accepted gaps.

(1.2, 2.3, 2.4, 2.5 are CLOSED/SUPERSEDED — removed with the trading feature,
D81; 3.1, 3.2, 3.3 are open non-Tier-4 items, listed above; 3.5 and 3.6 are
done-and-revertable Stage C batch decisions, not Tier-4-blocked. All stay
recorded in `DECISIONS_FOR_OPERATOR.md`, not duplicated here beyond the
above.)

### Open register entries, by subsystem

Open **high** (3): `R15-AGENT-007` (agent-runtime), `R15-AGENT-017`
(llm-adapters), `R15-LEAD-022` (resolver). Open **critical**: none.

Open **medium** (114), grouped by subsystem:

- **agent-runtime:** R15-AGENT-049, R15-CODE-AGENT-008, R15-CODE-AGENT-009,
  R15-LIFECYCLE-025
- **agent-tools-catalog-ledger:** R15-AGENT-046, R15-AGENT-083,
  R15-CODE-AGENT-013
- **backtest:** R15-CODE-PLATFORM-029, R15-CODE-PLATFORM-030,
  R15-LIFECYCLE-015, R15-UI-010, R15-UI-011
- **disclosures-witnesses:** R15-RESEARCH-030
- **error-layer:** R15-DATA-061, R15-UI-015
- **frontend-panels-agent-shell:** R15-AGENT-053, R15-AGENT-082,
  R15-AGENT-088, R15-UI-052, R15-UI-084
- **frontend-panels-data-surfaces:** R15-UI-024, R15-UI-050, R15-UI-083,
  R15-UI-091
- **frontend-panels-shell-chrome:** R15-CROSS-PLATFORM-004, R15-DATA-092,
  R15-DOCS-003, R15-DOCS-004, R15-DOCS-005, R15-UI-018, R15-UI-027,
  R15-UI-047, R15-UI-058, R15-UI-085, R15-UI-086, R15-UI-087
- **frontend-stores:** R15-CODE-FRONTEND-016, R15-UI-016, R15-UI-048
- **fundamentals-profile:** R15-DATA-048, R15-DATA-054, R15-DATA-055,
  R15-DATA-080, R15-DATA-095, R15-DATA-096, R15-UI-059
- **host-actions-proposed-changes:** R15-AGENT-084, R15-DOCS-016
- **llm-adapters:** R15-AGENT-050, R15-CODE-AGENT-005
- **llm-adapters-and-errors:** R15-LEAD-018
- **macro-quant:** R15-DATA-087, R15-UI-028, R15-UI-051, R15-UI-053
- **market-data-providers-1:** R15-CROSS-PLATFORM-003, R15-DATA-053,
  R15-DATA-066, R15-DATA-071, R15-DATA-073, R15-DATA-077, R15-DATA-078,
  R15-DATA-079, R15-DOCS-018, R15-LEAD-013, R15-LEAD-016, R15-LEAD-023,
  R15-LIFECYCLE-021, R15-LIFECYCLE-026
- **market-data-providers-2:** R15-DATA-062, R15-DATA-065
- **market-data-providers-3:** R15-DATA-068, R15-DATA-069, R15-UI-032
- **plugins:** R15-AGENT-057, R15-CODE-PLATFORM-012, R15-CODE-PLATFORM-013,
  R15-CODE-PLATFORM-014, R15-CODE-PLATFORM-015, R15-CODE-PLATFORM-071,
  R15-CODE-PLATFORM-072, R15-DATA-094, R15-DOCS-015, R15-UI-033
- **portfolio:** R15-CODE-PLATFORM-021, R15-CODE-PLATFORM-023
- **research-depth-iter-deep:** R15-RESEARCH-027
- **research-extraction-synthesis:** R15-AGENT-063, R15-CROSS-PLATFORM-002
- **research-retrieval-relevance:** R15-CODE-RESEARCH-004,
  R15-LIFECYCLE-018, R15-RESEARCH-028
- **resolver:** R15-DATA-052, R15-DATA-059
- **rust-core:** R15-CODE-PLATFORM-010, R15-CODE-PLATFORM-024,
  R15-CODE-PLATFORM-025
- **safety-audit:** R15-CODE-FRONTEND-013, R15-UI-044
- **screener:** R15-DOCS-017, R15-RESEARCH-025
- **scripts-build:** R15-CODE-PLATFORM-026, R15-CODE-PLATFORM-027,
  R15-CODE-PLATFORM-028, R15-CODE-PLATFORM-073, R15-CROSS-PLATFORM-001,
  R15-DOCS-002, R15-RELEASE-005, R15-RELEASE-006, R15-RELEASE-007
- **workflow-engine:** R15-CODE-PLATFORM-017
- **workspace-layout:** R15-LIFECYCLE-024, R15-UI-088
- **mcp-servers:** R15-AGENT-064

### Needs a GUI to verify

`R15-CODE-AGENT-001`, `R15-LIFECYCLE-001`, `R15-LIFECYCLE-008`,
`R15-UI-009`, `R15-UI-022`, `R15-UI-025` — no GUI/webview access in this
Stage D wave's lanes; carry forward to an operator or rig session.

### MCP cold-bind (`--onedir`) — still open at this sha

The true fix for the ~34s cold-bind (see "Phase 9 UC1 residual" and "Phase
9.5 UC1 update" below) has not landed as of `f4444790` — no `--onedir`
packaging change or `bundle.externalBin` restructuring is present in
`src-tauri/tauri.conf.json` or the ensure scripts at this sha. Carries
forward unchanged; see those sections for the detail.

## Phase 10 carry-forwards (operator validation + deferred build)

Phase 10 (copilot + integrations + Claude-after-dark + bug fixes) shipped
green on `main` (`ci-local` exit 0, §6.5 9/9, smoke exit 0). Items left:

1. **Visual sign-off is the operator's.** The harness can't drive the Tauri
   webview with real data, and macOS screen capture degraded to an
   `SCContentFilter` failure mid-session. Eyeball the populated-state shots at
   both resolutions per the CLAUDE.md visual protocol — specifically the
   **coral-vs-loss-red** legibility (fallback negative `#d6493a` pre-approved),
   that **Fraunces** loads (not the Georgia fallback), and the boot/Settings/
   News/Portfolio fixes. (A clean boot + Settings + populated Portfolio were
   confirmed early in the session before capture broke.)
2. **Live copilot demo needs a BYOK key.** The tool loop is proven end-to-end
   with a mocked provider (`sidecar/tests/test_tool_loop_e2e.py`); a real answer
   needs a key in Settings → AI Providers. Gemini/Ollama tool paths are
   confidence-6-7 (built from the SDK shapes, unverifiable without a live key) —
   verify multi-round tool use on a real Gemini/Ollama key.
3. ~~**Live Kite OAuth round-trip needs a real Zerodha app** (api_key/secret +
   the registered redirect `http://127.0.0.1:43117/kite/callback`). The exchange
   - read paths are unit-tested + curl-verifiable; the browser handshake is
     operator-manual.~~ **CLOSED — removed with feature (D81, `a122dbf6`, 23
     Sep 2026).** No Kite/broker OAuth path exists any more; confirmed no
     broker/Kite service code remains under `sidecar/` or `src/` at `f4444790`.
4. ~~**Kite `request_token` Rust-loopback auto-capture — deferred.** v1 is manual
   paste of the redirect URL. The Rust loopback listener (auto-capture) needs
   sha2 + an HTTP client + a browser-opener crate — a cross-OS build/clippy
   surface `ci-local` can't verify; do it attended if wanted. Dhan/Angel granular
   `positions_info`/`holdings_info`/`margins_info` splits also deferred (the GET
   routes fall back to `account_info()` for them today).~~ **CLOSED — removed
   with feature (D81, `a122dbf6`, 23 Sep 2026).** No Kite request_token flow
   and no Dhan/Angel granular reads exist any more; the broker layer is gone.
5. **Copilot roster depth — deferred.** Built: live tool loop + context + a
   clickable persona strip + bare-text routing. Deferred (architected in
   `docs/research/phase-10/blueprint-copilot.md`): the `GET /agents/roster`
   metadata endpoint + 3-pane roster panel + hard `delegate_to_persona` hand-off.
6. **Customizability follow-ups — deferred.** Built: persistent watchlist +
   integrations hub + terminal-driving copilot + themeable design. Deferred
   (`docs/research/phase-10/blueprint-customizability.md`): data-source/connector
   hub (wiring the currently-inert DataSource registry), panel gallery, saved
   screens, command-palette-as-action-driver.

## v0.8.0 → Phase 9 carry-forwards (operator manual Mac test)

Phase 8 deep-audit findings that are best exercised by a human operator
running the Tauri shell with real credentials + macOS:

1. **BYOK provider keys (L8 deferred).** Each provider (Anthropic /
   OpenAI / Google / Groq / Mistral / Cohere / Ollama) needs first-token-
   latency measurement (deferred from L6 perf baseline). Procedure in
   `docs/PHASE_8_PERF_BASELINE.md` "Agent first-token latency" section.
2. **Broker paper-mode connect (L9 deferred).** Alpaca paper most
   accessible; remaining 6 brokers need failure-state UX verification
   where credentials missing. **Note:** even after F1 fix, the 4 non-
   India broker adapters (Alpaca, IB, OANDA, ccxt-exec) are not in
   `BUNDLED_PLUGINS` or `bootstrap_default_adapters` (T4-brokers-not-
   registered + X-broker-bootstrap-india-only). Phase 9 to confirm + fix.
   **CLOSED — removed with feature (D81, 23 Sep 2026).** Trading was
   removed from the product permanently; no broker adapter exists to
   verify or register.
3. **Workflow + backtest cross-cutting (L10 deferred).** Verify F1 fix
   for openbb-mcp deadlock actually unblocks the chain in production
   (test_rebuilt sidecar showed openbb-mcp "unavailable" gracefully — the
   underlying deadlock still needs a real fix).
4. **Tradesa V2 6-state capture** with real Supabase project. T1 wrote
   the procedure (`docs/PHASE_8_VISUAL_REGRESSION_REPORT.md` Part B).
5. **Light theme audit** + **axe-core a11y audit** + **Lighthouse perf**
   against the live Tauri shell.
6. **macOS code-signing shake-out** (Apple Developer ID or ad-hoc).
7. **The openbb-mcp + sec-edgar-mcp startup deadlock root cause.** F1
   port-bind probe converts silent failure to clean degradation, but the
   underlying deadlock (likely PyInstaller `_MEIPASS` + Windows handle
   inheritance per CLAUDE.md Gotcha) still needs a real fix. Investigate
   the openbb-mcp-server / sec-edgar-mcp packages' streamable-http
   transport for the deadlock site. Phase 9/10 investigation target.
   **Phase-9 UC1 update:** partially addressed at the Rust supervisor
   level — see "Phase 9 UC1 residual" below.

## Phase 9 UC1 residual — MCP cold-boot bind latency (Rust supervisor)

**Status:** improved, NOT fully closed. Owner: Phase-9 `worktree-agent-rs`.

### What the Phase-9 fix did (robustly fixable at the supervisor)

`src-tauri/src/{lib,openbb_mcp,sec_edgar_mcp}.rs`:

1. **Raised the per-attempt bind budget** from a flat 15s to
   `MCP_PORT_WAIT_SECS = 30s` (`lib.rs`), with a **bounded retry**
   (`MCP_PORT_WAIT_ATTEMPTS = 2`) via the new `wait_for_port_with_retries`
   helper. The wait short-circuits on first TCP connect, so a fast/warm
   boot still returns in well under a second; only a genuinely slow cold
   boot consumes the extra budget. The retry gives the SAME cold child a
   second window — it does NOT respawn (the failure mode is slow `_MEI*`
   extraction + heavy imports, not a dead process). Worst case before
   declaring unavailable: ~60s per MCP.
2. **Parallelized the two MCP spawns** (`lib.rs` `setup`): previously
   `openbb_mcp::spawn` then `sec_edgar_mcp::spawn` ran sequentially, each
   blocking the setup thread for its full bind budget back to back
   (~30s+ serial under the old 15s × 2; would have been ~120s serial under
   the new budget). They now run on two threads and `join` before the main
   sidecar spawn (the `VYSTED_*_MCP_PORT` env vars must be settled first),
   so the two cold PyInstaller extractions OVERLAP. Net cold worst case is
   roughly halved vs. serial. The two threads `app.manage(...)` disjoint
   state types, and the disjoint env-var writes are serialized by Rust's
   internal `std::env` lock — no shared-state contention.
3. **Minimized the bind-vs-spawn TOCTTOU**: each spawn still calls
   `pick_free_port()` as its first line, immediately before its own
   `Command::spawn` (we did NOT pre-pick both ports up front, which would
   widen the window between port selection and reclaim).
4. **Graceful degradation preserved**: a final bind failure still kills
   the child, removes the env var, registers `port=0`, and returns `Ok` —
   openbb falls back to yfinance, sec routes return 501. Startup is never
   made fatal by an MCP failure. Diagnostics retain the Phase-8 UC1
   references and now name the budget + this BLOCKERS entry.

### The residual (NOT closable from the Rust supervisor)

The TRUE root cause is upstream subprocess cold-boot behaviour: a
PyInstaller `--onefile` binary must extract its `_MEI*` temp dir and
import heavy packages (openbb-platform extensions / sec-edgar
streamable-http) before it can `bind()`. Under cold disk cache, high I/O,
or Windows AV / Search-Indexer file-lock contention on the freshly
extracted files, that prologue can be slow and variable. The supervisor
can only _wait longer_ and _fail gracefully_; it cannot make the child
bind faster. So the nondeterminism is reduced (a 30s × 2 budget covers the
observed worst case far better than 15s × 1) but a pathologically slow
machine can still exceed it and degrade.

### Concrete repro recipe

1. Cold machine state: reboot, or evict the binary from OS file cache
   (e.g. on Windows after a fresh `pnpm sidecars:build`, before any prior
   launch warmed the `_MEI*` extraction).
2. Add I/O pressure: launch the app while a full AV scan / Windows Search
   indexer pass / large file copy is hammering the disk that holds
   `%TEMP%` / `src-tauri/binaries/`.
3. Observe `[openbb-mcp]` / `[sec-edgar-mcp]` logs: on a slow boot you may
   see the `not bound … after attempt 1/2 … retrying` line, then either a
   late `subprocess healthy on 127.0.0.1:<port>` (recovered within budget)
   or the `did not bind … treating as unavailable` degrade line.
4. On degrade: `/fundamentals|/macro|/screener|/earnings`/analyst routes
   fall back to yfinance; `/sec` routes return 501 — no crash.
5. **Relaunch** the app: with the `_MEI*` extraction now warm in cache it
   binds promptly. This warm-vs-cold delta is the signature of the
   residual.

### Recommended real fix (future phase, upstream of the supervisor)

Attack the cold-boot prologue, not the wait budget: (a) PyInstaller
`--onedir` instead of `--onefile` for the MCP sidecars eliminates the
per-launch `_MEI*` extraction (the dominant cold cost) at the price of a
folder bundle — check against the §`bundle.externalBin` packaging model;
(b) investigate whether the openbb-mcp-server / sec-edgar-mcp
streamable-http transport can defer heavy extension imports until first
tool call so `bind()` happens early; (c) a one-time post-install "warm"
launch that pre-extracts `_MEI*`. Each is out of scope for the Rust-only
UC1 sprint and out of the `worktree-agent-rs` file ownership. Carry to the
same investigation target as carry-forward #7 above.

## Phase 9.5 UC1 update — empirical bind times + budget bump + bind gate

**Status:** materially improved + now gate-detected; the `--onedir` true fix is
the remaining carry-forward.

### What Phase 9.5 measured (macOS M1, `scripts`-style isolated probe)

| sidecar       | binary size | cold bind  | warm bind |
| ------------- | ----------- | ---------- | --------- |
| openbb-mcp    | 49 MB       | **34.2 s** | 13.6 s    |
| sec-edgar-mcp | 81 MB       | **33.6 s** | 24.6 s    |

Both bind at ~34 s cold _in isolation_ — right at the old 30 s per-attempt edge
(only the retry, 60 s total, saved them). The audit's asymmetry (openbb UP,
sec-edgar DOWN on both boots) is **disk-I/O contention**: at app boot the two
`_MEI*` extractions run CONCURRENTLY (parallelized in `lib.rs` setup), so the
larger sec-edgar (81 MB) loses the extraction race and overruns 60 s, while the
smaller openbb (49 MB) fits. Not an openbb-vs-sec code difference — a size /
contention difference.

### What Phase 9.5 changed (low-risk, verifiable)

1. `MCP_PORT_WAIT_SECS` 30 → **45** (`src-tauri/src/lib.rs`); total 45 × 2 = 90 s.
   Near-free: `wait_for_port_with_retries` short-circuits the instant the port
   binds, so warm/fast boots are unaffected — only a genuinely dead sidecar
   waits the larger ceiling. Gives the contended cold sec-edgar bind real
   headroom over its ~34 s isolated cost.
2. `scripts/smoke-test-sidecars.mjs` now **TCP-probes the MCP port bind**
   (90 s budget) instead of only checking "process alive after 10 s" — this
   closes the documented L3/L4 gap and makes the gate catch the exact UC1
   silent-non-bind failure (process up, never listening).

### The residual (deferred, NOT done this unattended run) — the TRUE fix

`--onedir` PyInstaller packaging for the two MCP sidecars eliminates the
per-launch `_MEI*` extraction (the dominant cold cost), which would make the
bind near-instant and remove the contention race entirely. It was **deliberately
not attempted in the unattended Phase-9.5 run** because it requires changing
Tauri's `bundle.externalBin` (single-file) to a bundled resource **folder** plus
the Rust spawn path (`sec_edgar_mcp.rs` / `openbb_mcp.rs`) to resolve the inner
executable — and a bundle-config mistake would be **uncaught by `pnpm ci-local`**
(which never runs `tauri build`), surfacing only at the operator's build. Given
sec-edgar already degrades gracefully (501) when unbound, the risk/reward of an
unverifiable bundling rearchitecture overnight was poor. Deferring imports was
also ruled out: the heavy `edgartools` import happens inside the upstream
`sec_edgar_mcp.server` module load, before it binds — can't bind-before-import
without forking upstream. **Recommended next step (attended):** convert both MCP
sidecars to `--onedir`, bundle as resources, point the Rust `Command::new` at the
inner exe, then verify a full `tauri build` + GUI cold-boot binds promptly.

## v0.8.0 → v0.8.x polish carry-forwards (S2 + S3 findings)

From Phase 8 audit. Per-finding detail in
`docs/PHASE_8_BUG_CATALOG.md` and the 5 teammate audit docs.

### S1 deferred (test-only — feature works, test gap is the bug)

1. **T5-safety-store-reset-ks** — `resetKillSwitch()` (`src/store/safety.ts:
230`) entirely untested. The POST body field `reAck: true` has never been
   asserted; camelCase/snake_case drift would permanently lock the kill
   switch with no test catching it. §6.5-adjacent.
   **CLOSED — removed with feature (D81, 23 Sep 2026).** No kill switch
   exists; nothing to reset or test.
2. **T5-broker-base-invalid-order-type** — `propose_order()` raises
   `BrokerError` on invalid `order_type` but test only covers invalid
   `side` and zero quantity. §6.5-adjacent.
   **CLOSED — removed with feature (D81, 23 Sep 2026).** No order path
   exists; nothing to test.

   Both were test-additions; feature itself worked. Superseded by D81.

### S2 — fix in v0.8.x

1. **T2-mypy-llm-override** — 4 LLM adapter `stream_chat` signatures
   incompatible with ABC. Remove `async` from ABC declaration.
2. **T2-mypy-macro-provider-literal** + **T2-mypy-fred-frequency-literal** —
   annotate `PROVIDER` and frequency/seasonal-adjustment params as
   `Literal[...]` instead of `str`.
3. ~~**T2-autobahn-cve** — `autobahn==19.11.2` has CVE-2020-35678 in an
   unused code path (`KiteTicker` WebSocket; we use REST). Pin
   `autobahn>=20.12.3` as cheap insurance.~~ **CLOSED — removed with feature
   (D81, `a122dbf6`, 23 Sep 2026).** `autobahn` is no longer a dependency
   anywhere at `f4444790` (confirmed: no match in any `requirements*.txt`);
   it existed only for the deleted `KiteTicker` path.
4. **T3-significant-drop-scrutinee** — 3 `kill()` closures hold MutexGuard
   through `if let Some(...)`. Extract `.take()` to local binding.
5. **T4-brokers-not-registered** — register the 7 broker plugins in
   `BUNDLED_PLUGINS` (or document the deferred dynamic-load path).
   Pairs with `bootstrap_default_adapters` extension to non-India brokers.
   **CLOSED — removed with feature (D81, 23 Sep 2026).** The 7 broker
   plugins and `bootstrap_default_adapters` are deleted, not merely
   unregistered.
6. **T4-connection-keychain + T4-settings-dialog-keychain** — Tradesa V2
   plugin reaches into `@/lib/keychain` + `@/lib/sidecar-client`. Should
   use `PluginConfig.sidecarBaseUrl` + `PluginConfig.secrets`. Part of
   v0.6.6+ Tradesa V2 work.
7. **T5-openbb-mcp-provider-fallback-paths** — yfinance fallback path
   untested at registry level. Add coverage. Pairs with the deadlock fix
   (#7 above).
8. **L3-smoke-test-empty-data-gap + L4 smoke-test enhancements** —
   extend `scripts/smoke-test-sidecars.mjs` to TCP-probe MCP subprocess
   ports + verify load-bearing endpoints (`/agents` count > 0).
9. **D-7 BLUEPRINT drift** — update §10 UC2/UC4 to acknowledge the v0.7.0/
   v0.8.0 MCP subprocess gap + the F1 port-bind probe degradation. Or
   wait until the underlying deadlock is actually fixed (carry-forward #7).
10. **D-4 BLUEPRINT drift** — §4 Module 7 light-theme overclaim. Either
    update BLUEPRINT or implement light theme (v1.1).

### S3 — polish (no functional break)

- **L11-form-fields-missing-id-name** (10 form fields)
- **L11-aria-label-coverage-low** (4 of ~30 components)
- **L11-keyboard-handlers-minimal** (custom keyboard shortcuts not
  implemented)
- **L3-fastmcp-fastmcp-slim-double-pin** — redundant copy-metadata entry
  in `scripts/ensure-openbb-mcp-sidecar.mjs`.
- **T4-ccxt-executecommand-dead** + **T4-bare-commandids** +
  **T4-kite-manifest-unknown-field** — plugin polish
- **T5-monte-carlo-zero-coverage** + **T5-vitest-config-no-coverage-block**
- **D-3 BLUEPRINT drift** — `HOST_VERSION = "0.6.5"` updated in v0.8.0
  release commit; ensure version-bump checklist covers `src/lib/plugin-
bootstrap.ts:39` going forward.
- **T1 visual polish** — header titlebar absent across all captures;
  watchlist order (AAPL last not first); cockpit/ subfolder coverage gaps.
- **L11-color-contrast-not-audited** — Phase 9 axe-core/Lighthouse.

### S4 — Phase 9/10/v1.x carry-forwards (no fix this sprint)

- **T3-glib-unsound + T3-rand-unsound** — Linux-only transitive
  advisories (wry→gtk, keyring→zbus). Awaiting upstream fixes.
- **D-4 light theme** — v1.1 BLUEPRINT carry-forward.
- **UC1-canvas-chart-renders observation** — Playwright real-event suite
  for canvas-interactive features is v0.5.1+ carry-forward (unchanged).
- **UC6 stretch goal** — plugin-ecosystem year-2. v1.x territory.
- **UC7 (multi-broker aggregation)** — **CLOSED — removed with feature (D81,
  23 Sep 2026).** Trading was removed from the product permanently; there is
  no broker to aggregate.

## v0.7.0 → Phase 10 carry-forwards (launch ops — explicit non-scope in Phase 7)

1. **Code signing.** SignPath.io free-tier Windows OSS application;
   Apple Developer ID or ad-hoc Mac signing + `terminal.vysted.com/install/mac`
   bypass docs; Linux unsigned (AppImage + `.deb`).
2. **Tauri auto-updater wiring.** Pubkey present in `tauri.conf.json`
   from v0.5.0; `createUpdaterArtifacts: false` — flip to true and wire
   the GitHub Releases publish path.
3. **Distribution channels.** Homebrew cask submission, AppImage build
   - `.deb` build, GitHub Releases workflow + signed-bundle upload.
4. **`terminal.vysted.com` landing page.** Separate private repo
   (operator-owned). Download buttons, screenshots, getting-started
   docs.
5. **LICENSE flip + COMMERCIAL_LICENSE.md promotion + CLA bot.** Dual-
   license activation; `cla-assistant` GitHub App on PRs.
6. **First-launch TOS dialog.** BLUEPRINT customization #1 + §6.5 #8
   touchpoint. Grouped with LICENSE flip per the Phase 7 operator
   decision.
7. **v1.0.0 narrative + launch announcement.** Tag v1.0.0; post.

## v0.7.0 → v0.6.6+ Tradesa V2 carry-forwards

Same shape as the v0.6.5 carry-forwards section below; documented in
`docs/PHASE_6.5_HANDOFF.md` §3 and unchanged by v0.7.0.

1. Realtime SSE proxy (replaces per-panel polling).
2. Write capability (manual position close, pause-bot, approve
   tuning-proposal) — Tier-4 design per surface.
3. MCP tool exposure for the brain-decision log.
4. Anon-key + Auth migration when Tradesa V2 ships v0.1.7.0 RLS.
5. Optional Bybit Demo position enrichment.
6. Live `pnpm tauri dev` Tradesa V2 populated-state screenshot pass
   (Phase 9 operator-led session).

## v0.7.0 → v0.8 polish carry-forwards

1. **CI sidecar-smoke-test step.** Run the built `vysted-sidecar`
   binary + curl `/health` in CI so a `cf96031`-class
   `PackageNotFoundError-at-runtime` fails CI instead of shipping
   silently. The lesson from v0.7.0 F6/F7 — every data-bearing panel
   in v0.6.5 was broken in production and CI couldn't catch it.
2. **Default watchlist re-order.** Put AAPL first so the bundled
   default matches the visual convention's "AAPL primary anchor"
   (currently AAPL is at position 6 in `src/modules/watchlist/`).
3. **Full cockpit-shape re-capture for Phase 6 modules.** Macro / SEC
   / Earnings / Analyst Ratings / Screener / Quant in the canonical
   5-panel + AI Assistant cockpit at both required resolutions.
   Deferred to Phase 9 operator-led session per
   `docs/screenshots/v0.7.0/README.md`.
4. **Tradesa V2 first-ever populated capture.** Needs real Supabase
   project; operator-led (item #6 above also).
5. **CI runtime budget review.** PyInstaller --onefile builds of all
   three sidecars cold-cache make each CI workflow take ~20-25 min.
   Cache the binaries (keyed on requirements.txt hash) so CI is fast
   again.

---

(Pre-v0.7.0 historical content follows; preserved for context. The
v0.6.x sections below were the canonical carry-forward list at their
respective release time. New phase leads append above, not within.)

Lead-level open items as of v0.6.0. Per-teammate Phase-6 self-reports
(BLOCKERS-M.md surfaced T3-M-1 — the `fred-mcp-server` Node.js pivot;
F / Q / E / Sc surfaced none in-build) were aggregated here at integration
and removed from teammate worktrees; salient detail preserved in the merge
commit messages, `CHANGELOG.md` v0.6.0 entry, and `docs/PHASE_6_HANDOFF.md`.

## Phase-6.x follow-ups (cosmetic / forward-looking)

### 1. ~~Teammate Sc screener frontend~~ — RESOLVED in v0.6.1

The frontend (`src/store/screener.ts` + the three panels +
`screenerModule` in `src/modules/index.ts` + 24 new Vitest tests + a
Pillow-rendered populated-state screenshot pair) shipped in v0.6.1
under the lead-completion tag. Backend at v0.6.0 was untouched;
contract held.

### 2. Live `pnpm tauri dev` re-capture across all four Phase 6 modules

Combines the v0.6.0 carry-forwards "Teammate Q populated-state
screenshots" + "Live Tauri capture for E + F screenshots" + the v0.6.1
"Sc populated-state screenshots are Pillow stand-ins" into one
operator-session task.

What ships today (v0.6.1):

- **Teammate Q** — no screenshots in `docs/screenshots/v0.6.0/teammate-q/`.
- **Teammate E** — Pillow stand-ins, shape-for-shape matching the React
  layout (validated by 25 Vitest tests + 60 backend tests).
- **Teammate F** — Pillow stand-ins + HTML demo, same situation.
- **Teammate Sc** — Pillow stand-ins from v0.6.1 lead-completion.

Live re-capture procedure (operator-led):

1. One-time: `pnpm sec-edgar-mcp-sidecar:build` (PyInstaller compile,
   ~ several minutes; required because F's MCP subprocess is only
   reachable from inside the Tauri shell).
2. `pnpm tauri dev` — Tauri launches the WebView + the main sidecar +
   the openbb-mcp subprocess + the sec-edgar-mcp subprocess.
3. Open each Phase 6 panel via cmd+K:
   - Option Pricer (AAPL 220 Jun-2026 call via BS / Binomial / MC +
     Greeks dashboard)
   - Bond Pricer (10y US Treasury at 4.25% YTM)
   - Yield Curve panel (bootstrapped US Treasury curve 1mo→30y)
   - Earnings Calendar (5-day window with AAPL / MSFT / NVDA / GOOGL /
     META + consensus EPS + dispersion)
   - Analyst Ratings (AAPL: 12 individual analyst tracks + ratings
     history + price target chart)
   - SEC Filings (AAPL: last 10 filings mixed forms + 10-K sections
     view + insider transactions tab with 20+ Form 4 entries)
   - Screener (default criteria → 6-8 names from S&P 500)
4. Capture each at 1920×1080 AND 2560×1440 via chrome-devtools MCP
   `resize_page` + `take_screenshot`.

Why this is deferred from v0.6.1: the headless capture path requires a
new dev-mode browser-side sidecar-port fallback (the current
`src/lib/sidecar-client.ts::getSidecarBaseUrl` only works inside Tauri).
Adding that fallback would change Phase 1 foundation code that has been
stable for 6 releases — real scope creep. The Pillow stand-ins match
the live shapes 1:1 (validated by component tests against the same
React trees); the live re-capture is cosmetic polish, not a regression
risk.

### 3. ~~Tradesa V2 full plugin~~ — RESOLVED (READ-ONLY) in v0.6.5

v0.6.5 ships the wrapper plugin (`plugins/tradesa-v2/`) READ-ONLY
against Tradesa V2's Supabase remote-sync project — 7 panels (Live
Positions / Trade History & P&L / Brain Decisions / Sentinel & Safety /
Heartbeat & Health / Settings & Drift / Self-Tuning · Discovery ·
Reflection) + `TradesaBotStatusStrip` + `TradesaSettingsDialog`. Three
defense-in-depth layers enforce read-only: provider has no write methods
(audit-tested), router has no non-GET routes (audit-tested), plugin's
`supportsControlPlane=false` (contract-level gate). The wrapper is the
canonical reference for the "Trading-System Wrapper" plugin pattern
documented in `docs/PLUGIN_DEVELOPMENT.md` — TauricResearch and future
trading-system plugins mirror the same shape.

Carry-forward to v0.6.6+ (see §"Phase 6.5 → v0.6.6 carry-forwards" below):
real-time SSE proxy, write capability, MCP tool exposure, anon-key + Auth
migration when Tradesa V2 ships v0.1.7.0 RLS, Bybit Demo position
enrichment, operator-led live `pnpm tauri dev` screenshot pass.

## Phase 6.5 → v0.6.6 carry-forwards

### 1. Realtime SSE proxy (Tier-3 deferral from v0.6.5)

v0.6.5 ships polling-only (per-panel cadences: 10s positions / 30s
decisions / 60s settings / 5min trade-history / 120s meta-agents).
v0.6.6 candidate: sidecar-side WebSocket subscription to Supabase
`postgres_changes` on the live tables, SSE fan-out to the frontend
store. Polling fallback when Realtime is unavailable. Replaces the
current polling cadences for `trades` / `decisions` / `bot_health` /
`kill_switch_events`. Adds an asyncio-task lifecycle the v0.6.5 wrapper
explicitly avoided per scope.

### 2. Write capability — Tier-4 design required per surface

Manual position close, pause-bot toggle from the Health panel, approve
tuning-proposal from MetaAgentsPanel. Each is a Tier-4 design — must
route through propose→confirm flow + §6.5 audit log + AI-order gate.
The `sidecar/services/agent_tools/registry_v0_6_5.py` aggregator slot
exists for write tools when this lands. The frontend `plugins/tradesa-v2/
connection.ts` would gain a `WriteOps` interface (separate from the
current `TradingBotReadAdapter`).

**CLOSED — removed with feature (D81, 23 Sep 2026).** The enabling
infrastructure this item depended on (the propose→confirm flow, the §6.5
order audit log, the AI-order gate, and the `registry_v0_6_5.py` slot
itself) is deleted with trading. Tradesa V2 stays read-only permanently;
no write capability for it will land.

### 3. MCP tool exposure for the brain-decision log

Surface Tradesa V2's `decisions` stream as a Vysted MCP tool so the
chat sidebar can summarize / query the bot's recent decisions
("ask the AI sidebar to explain why the bot held overnight"). Chat-
sidebar integration risk; out of v0.6.5 scope. Implementation path:
new MCP tool in `sidecar/services/mcp_server.py` calling the existing
`tradesa_v2_provider.list_decisions()` via the same in-process ASGI
transport pattern the Phase 3 MCP tools use.

### 4. Anon-key + Auth migration (Tradesa V2 v0.1.7.0 dependency)

When Tradesa V2 ships its v0.1.7.0 RLS rollout, the wrapper swaps from
the current service-role-key header path to an anon-key + Supabase
JWT path. Vysted-side API surface unchanged; the `TradesaSettingsDialog`
gains a Supabase sign-in flow instead of the service-role-key field.
Watch `techlogist1/tradesa` `infra/migrations/v017*.sql` + their
`CHANGES.md` for the rollout signal.

### 5. Bybit Demo position enrichment (optional)

Read directly from Bybit V5 for live tick-level position data the bot
doesn't write to Supabase (entry tick, current mark, unrealized P&L
without the polling lag of the Vysted-side cache). Optional Bybit Demo
credentials in keychain — pre-planned via
`pluginSecret("tradesa-v2", "bybit-demo-api-key")` /
`pluginSecret("tradesa-v2", "bybit-demo-api-secret")` (NOT consumed
in v0.6.5).

### 6. Live `pnpm tauri dev` populated-state screenshot pass

v0.6.5 ships with test-confirmed rendering verified by 39 + 20 Vitest
tests. Operator-led full re-capture (7 panels × healthy/offline/
unauth × 1920×1080 + 2560×1440 = 42 screenshots) follows the v0.6.0
BLOCKERS.md §2 pattern. Procedure: `pnpm tauri dev`; cmd+K each
Tradesa V2 panel; chrome-devtools MCP `resize_page` + `take_screenshot`
× 2 resolutions; save to `docs/screenshots/v0.6.5/`. Deferred because
(a) live capture needs a real Tradesa V2 Supabase project for the
healthy state, (b) graceful-degradation paths are non-trivial to drive
headlessly without ad-hoc network blockers, (c) test artifacts confirm
the shapes 1:1 with what live capture would show.

## Resolved in v0.6.1

- **Teammate Sc screener frontend** (v0.6.0 carry-forward #1) — shipped:
  `src/store/screener.ts` + `src/modules/screener/{ScreenerPanel,
ScreenerCriteriaBuilder,ScreenerResultsTable,index}.tsx` + 24 Vitest
  tests + Pillow-rendered populated-state screenshots + module registry
  uncomment + `module-registry.test.ts` updated.

## Resolved in v0.6.0

The v0.5.0 carry-forwards that v0.6.0 addressed:

- **Phase 5.1 #2 (Tradesa V2 full plugin)** — re-deferred to v0.6.5
  per Tier-3 (see follow-up §3 above).

## Resolved in v0.5.0

The v0.4.0 carry-forwards explicitly addressed:

- **OpenBB Windows `subprocess.Popen` deadlock** — already resolved in
  v0.4.0 (`openbb-mcp.rs` Tauri-Rust-spawn pattern). v0.5.0 confirms the
  pattern remains the standard for any future broker subprocess that
  exceeds the bundle threshold.

- **The Phase 3→4 Strategy Critic backtest tool wiring** — RESOLVED.
  v0.4.0 reserved `["backtest_summary", "price_data", "fundamentals"]`
  in `strategy_critic.json`; v0.5.0 lights all three up:
  `backtest_summary` ships in foundation, `price_data` + `fundamentals`
  registered by Teammate K via `register_v0_5_0_tools()` in
  `services/agent_tools.py`. Agent runtime extended to dispatch
  multi-round `tool_use` blocks (up to 6 rounds).

- **Mega-sprint architectural rationale documented** — v0.5.0 CHANGELOG
  - the two handoff docs capture why Phase 4 + Phase 5 shipped under one
    tag (tight coupling, single product story, 60-day paper-soak as the
    live-execution gate).

## Phase-5.1 / 6.0 follow-ups (cosmetic / forward-looking)

### 1. ~~Populated screenshots of Teammate S's safety UI surfaces~~ — mostly moot (D81)

**CLOSED for KillSwitchToolbar / OrderConfirmationDialog / AuditLogViewer /
BrokerConnectPanel — removed with feature (D81, `a122dbf6`, 23 Sep 2026).**
None of those four components exist in the tree at `f4444790` (confirmed via
`git ls-tree`). The original ask also named "DisclaimerFlow three surfaces";
`src/modules/safety/DisclaimerFlow.tsx` is still live (first-launch terms,
tracked separately as decision 3.2 in `DECISIONS_FOR_OPERATOR.md`) — a
populated-state capture of DisclaimerFlow specifically, if still wanted,
would be a fresh ask, not a continuation of this stale item.

Teammate S's worktree terminated on a "monthly usage limit" error before
pushing its branch. UI components + stores landed via worktree sharing
(integrated through K's merge commit); the dedicated `test_safety_end_to_end.py`
audit suite + `docs/SAFETY_ARCHITECTURE.md` were lead-completed
post-merge. Non-blocking for v0.5.0 per CLAUDE.md visual-
verification protocol — composed and per-teammate shots from K/N/I/X +
audit-suite captures cover the load-bearing surfaces.

### 2. Tradesa V2 full plugin

BLUEPRINT §7 Phase 5 lists Tradesa V2 (all six plugin capabilities;
9-12 observability panels; real-time WebSocket; settings drift
detection; LLM cost tracking; Tradesa-specific agents + nodes). The
operator brief de-scoped Tradesa V2 from v0.5.0 in favour of broker
breadth. Foundation contracts (kill switch + audit log + `executeCommand`
control plane) are in place; v0.5.1 / v0.6.0 Tradesa V2 becomes plug-in
work, not contract work.

### 3. ~~Live-mode end-to-end verification~~

**CLOSED — removed with feature (D81, `a122dbf6`, 23 Sep 2026).** By
design, v0.5.0 shipped paper-mode end-to-end only, with a 60-day paper-soak
window as the live-execution gate; trading (paper mode, live orders, the
broker layer entirely) was removed from the product permanently before that
gate was exercised. There is no order path, paper account or broker
connection left to verify.

### 4. Playwright real-event suite for node-editor canvas interactions

chrome-devtools MCP cannot synthesize `isTrusted` events for canvas
drag-drop / edge-connect (v0.3.0 carry-forward). Teammate N's mocked-
fetch Load-path screenshots cover the equivalent visual surface for
v0.5.0; a Playwright real-event suite would close the regression-test
gap end-to-end. v0.5.1+ polish.

### 5. Claude Desktop external-MCP-client live screenshot

v0.4.0 carry-forward — Teammate B captured a session log proving the
Vysted MCP server end-to-end via Vysted's own `McpClient` over
Streamable-HTTP (same wire Claude Code uses). A polish-tier real
screenshot of Claude Desktop consuming Vysted's MCP server through the
`mcp-remote` bridge documented in `docs/MCP_INTEGRATION.md` is still
not load-bearing; carries to v0.5.1+.

### 6. Drawing-tool on-canvas screenshots

v0.3.0 carry-forward — `lightweight-charts` rejects synthesized mouse
events (`isTrusted` check). Same Playwright real-event suite (§4 above)
would close this. Drawings have full unit-test canvas-call coverage; UX
shape is captured in toolbar + drawing-inspector populated screenshots.

### 7. ~~OANDA `oandapyV20` SDK maintenance audit~~

**CLOSED — removed with feature (D81, `a122dbf6`, 23 Sep 2026).** OANDA was
one of the deleted broker adapters; `oandapyV20` is no longer a dependency
anywhere at `f4444790` (confirmed: no match in any `requirements*.txt`).
Nothing left to audit.

### 8. Workflow engine `resume-from` mode

The `WorkflowRunRequest.mode = "resume-from"` schema field exists; the
engine ships full-run only in v0.5.0. The run cache + per-node outputs
are already captured, so adding the resume path is small (~50 LoC) and
would land in v0.5.1+.

## Coordination lessons captured in CLAUDE.md

The Agent-tool `isolation: "worktree"` parameter does NOT fully isolate
writes for every agent — some agents wrote tracked files in the lead's
main worktree during execution. Going-forward rule (now in
CLAUDE.md): lead audits via `origin/<branch>` only; main-worktree
contamination is always discarded via `git restore HEAD -- <file>` +
proper fetch + merge from origin.

The S agent terminated on a usage-limit error mid-execution. Going-forward
rule for high-value teammates: agent dispatch should monitor usage-limit
proximity and push intermediate commits more frequently to minimise loss
surface (CLAUDE.md captures this for the next mega-sprint).
<!-- critic-footer -->
## Critic findings applied

1. n/a — targets CURRENT_STATE.draft.md, see its footer
2. n/a — targets CURRENT_STATE.draft.md, see its footer
3. applied
4. applied
5. applied
6. n/a — targets CURRENT_STATE.draft.md, see its footer
7. n/a — targets CURRENT_STATE.draft.md, see its footer
8. n/a — targets CURRENT_STATE.draft.md, see its footer
9. n/a — targets CURRENT_STATE.draft.md, see its footer
10. n/a — targets CURRENT_STATE.draft.md, see its footer
11. n/a — targets CURRENT_STATE.draft.md, see its footer
