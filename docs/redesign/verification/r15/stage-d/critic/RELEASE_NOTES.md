<!-- CRITIC of RELEASE_NOTES.draft.md at f444479031d7d493b7955b9af041d18e7c7a40cc -->

# Critic: RELEASE_NOTES.draft.md

Read cold as (A) a user upgrading to 0.9.0 and (B) the next maintainer reading CHANGELOG.md.
Every claim checked against FACTS.md, the register (`docs/redesign/verification/vysted-r15-register.json`
at the sha, 626 entries), the eight batch VERDICTS.md files, DECISIONS.md, LICENSING.md, CHANGELOG.md
and the code at f4444790. 56 register ids behind the "What changed for you" and "Fixed" lines were
mapped and their batch verdict located; the ones that failed are below.

## Verdict: REVISE

Six of the findings (1, 2, 3, 4, 7, 8) present something the register lists open or needs_gui as
delivered, or state a limitation that is not a product fact; a user or maintainer acting on them
would be misled. The rest are one-line corrections.

## Findings

1. **wrong** — Known limitations, lines 132-134: "Six areas still need hands-on GUI verification
   (onboarding/setup flows and workspace-loading behavior)". The six `needs_gui` entries
   (register; FACTS.md:194) are R15-CODE-AGENT-001 (the sidecar answers any browser Origin,
   including the unauthenticated /mcp surface), R15-LIFECYCLE-001 (every launch freezes the main
   event loop for the MCP bind window, 25-90 s), R15-LIFECYCLE-008 (a shipped build persists no
   log), R15-UI-009 (Watchlist/Portfolio Export CSV is a dead control on macOS), R15-UI-022 (chart
   drawing anchors snap to the bar close) and R15-UI-025 (Notes Link button is a no-op in the
   desktop webview). None is onboarding, setup or workspace loading. Fix: "Six fixes still need
   hands-on verification in the desktop app: CSV export on macOS, the Notes Link button, chart
   drawing placement, the launch-time freeze while the MCP helpers bind, the persisted log file,
   and the sidecar's cross-origin policy."

2. **wrong** — Fixed / Platform & sidecar, lines 108-109: "a rotating diagnostics log and a redacted
   Settings export were added". The rotating log is R15-LIFECYCLE-008, `needs_gui` (batch-5
   VERDICTS.md:216 "## needs_gui (2)"; register closure note: "Batch-5 (1574ed8) needs_gui.
   /system/diagnostics was verified live ... no planted c[rash]"). A "redacted Settings export"
   collides with R15-UI-058, open medium ("Settings Export carries only 3 preference fields ...
   Import reports 'Imported settings.' for any JSON"). The clause was lifted from the batch-5
   CHANGELOG scope note (CHANGELOG.md:162-163 "a rotating diagnostics log and a redacted Settings
   bundle"), which the draft's own VERIFY comment says not to trust. Fix: delete the clause; the
   persisted log belongs in Known limitations (finding 1).

3. **wrong** — What changed for you, lines 26-27: "CSV exports go through a proper writer instead
   of an ad hoc string join". The only CSV-path entry is R15-UI-009, `needs_gui` (batch-4
   VERDICTS.md:22; closure note "jsdom shows downloadCsv going through saveTextArtifact ... needs
   GUI"); CHANGELOG.md:220 "CSV saves through the Rust writer" is the uncertified batch-4 scope
   note. "ad hoc string join" has no source anywhere in the register or CHANGELOG. The certified
   CSV fix is R15-DATA-042 (batch-2 VERDICTS.md: "certified": the export no longer writes a
   cross-currency Weight % and carries a currency column). Fix: replace with "the portfolio CSV
   export now carries a currency column and no longer mixes currencies in Weight %".

4. **wrong** — Fixed / Market data, lines 74-75: "foreign-suffixed and renamed India tickers now
   resolve consistently across venues". R15-LEAD-022 is open high (FACTS.md:192): "_yahoo_symbol
   rewrites every non-Indian foreign exchange suffix with a dash (BHP.AX -> BHP-AX, 0700.HK ->
   0700-HK ...) so Yahoo answers 'possibly delisted'". The certified fixes are for
   exchange-suffixed Indian tickers (R15-DATA-029 ".NS/.BO are mangled to -NS/-BO", batch-4
   certified; R15-DATA-030 batch-2) and renames (R15-DATA-012, R15-DATA-018, R15-UI-039 batch-8).
   Fix: "exchange-suffixed (.NS/.BO) and renamed India tickers"; and in Known limitations name the
   open one plainly: "tickers on non-Indian foreign exchanges (BHP.AX, 0700.HK, 7203.T, VOD.L)
   still fail to resolve".

5. **wrong** — Fixed / Market data, lines 77-78: "India-specific exchange calendars ... were
   corrected". R15-DATA-073 is open medium: "The bundled trading-holiday tables end on 2026-12-25
   with no regenerator or expiry test, and already miss 2026 BSE non-session days, so freshness
   labels drift". What was certified is narrower: R15-LIFECYCLE-022 (a moved NSE bhavcopy archive
   path is no longer cached as a week of holidays, batch-8) and R15-UI-090 (quote freshness is
   stamped against the instrument's exchange, not the user's locale, batch-4 "certified (both
   halves)"). Fix: "quote freshness now follows the instrument's own exchange calendar, and a
   missing NSE archive day is no longer mistaken for a holiday".

6. **wrong** — Fixed / Platform & sidecar, lines 109-110: "the workspace cache is cleared
   automatically on a version change". The certified entry is R15-LEAD-003, subsystem
   `data/cache` ("Rows cached before a correctness fix keep being served for up to 24 h after the
   fix", batch-5 VERDICTS.md:183 under "## Certified (48)"): it is the data cache. The workspace
   side is R15-LIFECYCLE-024, open medium ("No persistent store records a schema version ... no
   top-level workspace blob version ... nothing backs up the data dir before a new build touches
   it"). Fix: "the data cache is cleared automatically on a version change".

7. **wrong** — Fixed / AI assistant, line 94: "research spend reaches you as a display value only,
   never as executable instructions". No register entry or CHANGELOG line says this. The only
   spend-display entry is R15-AGENT-082, open medium ("A foreground chat run's token count and
   spend are never shown anywhere: spend is hard-coded to $0"); CHANGELOG.md:15 lists it as
   "landed one leg short and stay[s] open" (the chat footer never parses `spend_usd`). Fix: delete
   the clause. The certified spend work is metering (R15-AGENT-012 / R15-RESEARCH-009, batch-3
   "certified"), already covered by "delegate ... runs get real lifecycle limits".

8. **wrong** — Known limitations, lines 139-140: "Your default AI provider may not answer out of the
   box if its account has no funded balance". This is DECISIONS_FOR_OPERATOR.md §2.1 (FACTS.md:212-
   214: the operator's own OpenRouter negative balance / DeepSeek $0), an environment note, not a
   product limitation; a user's provider account is their own. The real open default-lane defect
   is R15-AGENT-017, open high: "The shipped default chat model (DeepSeek V4 Flash via OpenRouter)
   returns content_filter with zero tool calls on ordinary portfolio-write asks, so the core
   host-action flow fails on the default". Fix: replace the bullet with "On the shipped default
   model (DeepSeek V4 Flash via OpenRouter) asking the assistant to edit your portfolio can come
   back as a content-filter refusal with no action taken; pick another model in Settings if you
   hit it."

9. **wrong** — Part B / Carried forward, line 209: "per this file's 'Versioning & process' gotcha".
   In CHANGELOG.md "this file" is CHANGELOG.md; the gotcha is CLAUDE.md:274-278 at the sha
   ("### Versioning & process ... Version lives in many sources"). Fix: "per CLAUDE.md's
   'Versioning & process' gotcha".

10. **wrong** (minor) — Known limitations, line 141: "Deep research quietly degrades to a keyless
    web scraper if Docker/OrbStack isn't running". The fallback is real (sidecar/services/
    searxng_manager.py:5-6 manages a `vysted-searxng` container "on the user's own docker runtime
    (Docker Desktop, OrbStack, or a bare engine)"; R15-RESEARCH-008 calls the keyless tier "the
    default for most users"), but it is not quiet: sidecar/config.py:233-263 stamps the brief with
    the "honest `backend=\"keyless-fallback\"` id ... never an error state". Fix: "falls back to
    the keyless search engines (the brief is labelled keyless-fallback)".

11. **missing** — Part B / Decisions, lines 191-197: the "D85–D92" rider list omits D91
    (DECISIONS.md:151: "India EOD-only provider error copy no longer suggests adding a BYOK
    broker"). Fix: add "; the India EOD-only data error no longer suggests connecting a broker".

12. **missing** — Part B, line 152 vs line 189-190: "626-entry" register next to D84's "887 raw
    findings → 603 entries" with no bridge. Both are true at their dates; the 23 added since D84
    are the R15-LEAD-* entries the lead found during Stage C (`grep -c '^R15-LEAD-'` on the
    register = 23; `stage-c/LEAD_FOUND.applied-batch-3.json` and `...-batch-6.json`). Fix: after
    "603 entries" add "(626 by this sha, after 23 lead-found R15-LEAD-* entries were admitted
    during Stage C)".

13. **missing** — Removed: trading, lines 51-57 (cleanup instructions). (a) `broker:_meta:first-
    launch-tos` is an orphaned keychain account that is not "for your former broker" (D92,
    DECISIONS.md:152; pre-removal src/lib/keychain.ts:113 at a122dbf6^1) and D85 replaced it with
    `app-meta:first-launch-terms`. (b) Linux is a target platform (build.yml matrix) but only
    Keychain Access and Credential Manager are named; the `keyring` build uses
    `sync-secret-service` on Linux (CLAUDE.md "keyring Rust crate v3"). (c) `~/.vysted-terminal`
    is the default only when the data-dir override is unset (a122dbf6^1 sidecar/config.py:547).
    Fix: "remove every keychain entry whose account starts with `broker:` (including
    `broker:_meta:first-launch-tos`) — Keychain Access on macOS, Credential Manager on Windows,
    your secret-service keyring (e.g. GNOME Keyring / Seahorse) on Linux".

14. **wrong** — Part A register/jargon check (the mandated check, not taste). No register id
    appears in part A prose (the two `<!-- VERIFY -->` comments name VERDICTS.md / FACTS.md /
    batch-9 and must be stripped before publishing). Jargon that a user cannot decode: line 29
    "fundamentals witnessing"; line 81 "checked against a witness source"; line 86 "misreads a
    leading verdict token"; line 88 "off-entity news", "deep/ultra research pass"; line 93 "a
    capped final round"; line 96-97 "delegate (unattended) runs ... checkpointing". Fix: line 29 →
    "fundamentals cross-checked against exchange filings"; line 81 → "cross-checked against the
    exchange filing before being shown"; line 86 → "no longer marks an unverified claim as
    agreed"; line 88 → "news about a different company no longer leaks into a research brief";
    line 93 → "when the assistant hits its tool-call limit it no longer leaves calls half-done";
    line 96-97 → "unattended (Delegate) runs now have spend and time limits, save progress, and
    can be resumed".

## Checked and correct

- Line 1 is exactly `<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->`.
- No key, token or keystore content anywhere in the draft.
- Every path the draft names exists at the sha (`git cat-file -e`): COMMERCIAL_LICENSE.md, LICENSE,
  LICENSE-APACHE, LICENSING.md, types/plugin.ts, types/plugin-runtime.ts, docs/redesign/DECISIONS.md,
  docs/redesign/DECISIONS_FOR_OPERATOR.md, scripts/r15/vy.py, package.json, src-tauri/Cargo.toml,
  src-tauri/tauri.conf.json, sidecar/app.py, src/lib/plugin-bootstrap.ts, src-tauri/Cargo.lock,
  stage-c/batch-{2..9}/VERDICTS.md. The four named as deleted (registry_v0_6_5.py,
  services/kill_switch.py, src-tauri/src/kill_switch.rs, models/audit_log.py) are absent at the sha
  and appear in `git show --diff-filter=D a122dbf6`; 17 `sidecar/tests/test_*.py` files were deleted
  there (18 files under sidecar/tests, the 18th being `gen_audit_trail.py`, a generator).
- No command appears in part A or part B; the version-bump instruction names the same six files as
  FACTS.md "versions" (all `0.8.0`, version_consistent true).
- Licence section matches LICENSING.md verbatim in substance (source-available; noncommercial grant;
  commercial licence for commercial use, modification, redistribution; pre-relicense commits stay
  AGPL-3.0; Apache-2.0 carve-out for types/plugin.ts, types/plugin-runtime.ts and the example
  plugin) and D83 (DECISIONS.md:143). LICENSE first heading is PolyForm Strict License 1.0.0.
- Removed section matches D81 (DECISIONS.md:141), the merged-removal row (DECISIONS.md:153: kill
  switch and append-only audit log deleted, 7 broker plugins, 17 test files) and D92 (no automatic
  purge; DECISIONS_FOR_OPERATOR §3.1). `~/.vysted-terminal/audit_log.db` matches the pre-removal
  default (a122dbf6^1 sidecar/config.py:547, sidecar/models/audit_log.py:12,54); `broker:<id>:<field>`
  matches pre-removal src/lib/keychain.ts:46. "What stays" matches D81's list.
- Part A "What changed for you" claims map to certified entries: autosave pipeline R15-LIFECYCLE-003
  and named-workspace rollback R15-CODE-FRONTEND-001 (batch-2 "certified"); unknown-panel restore
  R15-LIFECYCLE-002 (shipped with a122dbf6, certified per DECISIONS.md:153); research-space names
  R15-CODE-FRONTEND-004 (batch-2); AUTO scope R15-AGENT-080 / R15-CODE-FRONTEND-008 (batch-3, D-B3-1
  "panel, chart and watchlist" only) and typed step notices R15-AGENT-032/033; Cmd/Ctrl-K ticker →
  chart R15-UI-002 (batch-3; default `mod+k` at src/components/CommandPalette.tsx:20) and focused
  symbol R15-CODE-FRONTEND-015; sidecar errors R15-UI-014 and per-panel error boundary
  R15-LIFECYCLE-023 (batch-8); validation reasons R15-UI-013, reachability banner R15-UI-019, dead
  keyless default replaced R15-UI-049 (batch-8); drawings per symbol/timeframe R15-UI-020 (batch-7),
  locked drawing R15-UI-021 (batch-6), overlay stacking R15-UI-023 (batch-7); portfolio quote
  failure/staleness R15-UI-004 (batch-4) and R15-UI-036 (batch-7).
- Fixed lines otherwise map to certified entries: same-instrument rule R15-CODE-DATA-001 (batch-2);
  NaN prices R15-DATA-033 (batch-2) and fabricated candles R15-LIFECYCLE-004 (batch-4); stale quote
  as fresh R15-DATA-006 (batch-2); SME/Emerge R15-DATA-017 (batch-6 after batch-5 "half fixed");
  ownership/share-basis witnesses R15-DATA-004/005 (batch-3), EPS/P-E R15-DATA-013 (batch-2), revenue
  R15-DATA-014 (batch-7 after batch-2 "NOT certified"); pledge/deals/corporate actions/FII-DII
  R15-DATA-023/024/025/056 (batch-5 "Certified (48)" section); undated news R15-DATA-070 (batch-2);
  verdict parse R15-RESEARCH-002, citations R15-RESEARCH-003/029, other-company news R15-RESEARCH-001
  (batch-2); crashed explorer R15-RESEARCH-017 (batch-6) and blocked page visits R15-RESEARCH-019
  (batch-7); ticker+number (KSE-100 index regex) R15-RESEARCH-021 (batch-7); stream cancel
  R15-AGENT-002 and capped round R15-AGENT-003 (batch-3); dropped screener criteria R15-AGENT-043 and
  portfolio-edit R15-UI-034 (batch-7); plan-before-run R15-AGENT-039 (batch-7; Delegate-specific);
  delegate lifecycle R15-CODE-AGENT-010, R15-LIFECYCLE-012/013, R15-AGENT-035..038; watchlist/compare
  resolver R15-AGENT-044 (batch-7) and R15-AGENT-045 (batch-8 after batch-7 "not certified");
  corrupt workspace quarantine R15-DATA-090 and autosave failure surfaced R15-CODE-FRONTEND-019
  (batch-7); status both directions R15-LIFECYCLE-011 and spawn failure cause R15-LIFECYCLE-010
  (batch-8).
- Part B: batch merge hashes and counts match `git log --first-parent --merges r13-bedrock..f4444790`
  (the draft drops the word "live" from "certified live"; harmless). Base tag r13-bedrock, nine
  batches, all merge commits. Register counts, the three open highs and their subsystems, 16/16
  criticals fixed, 114 open mediums, 205 open lows, 6 needs_gui, 4 blocked_tier4 (§2.8-2.11) all
  match FACTS.md "register". D81-D90 and D92 summaries match DECISIONS.md:141-152 (D82's $8.00 cap
  with `PAID_USD_CAP = 7.50` in scripts/r15/vy.py; D84's 887 → 603). CI claim matches FACTS.md "ci"
  (push restricted to main, pull_request unrestricted, three-OS matrix, never run on 004 per §2.6/
  §2.11). Heading form "## v0.9.0 — ... (dates)" matches the existing v0.7.0/v0.6.5 sections.
- Known limitations on signing, no release pipeline / updater, Windows unverified: match
  DECISIONS_FOR_OPERATOR §2.8-2.11 (FACTS.md:233-244).
- Note for rc2, not a finding: batch-6's VERDICTS.md is a post-kill reconstruction whose first lines
  name `VERDICTS.json` as the authoritative verdict list; the part-B pointer to
  `batch-N/VERDICTS.md` still lands on the right file.
