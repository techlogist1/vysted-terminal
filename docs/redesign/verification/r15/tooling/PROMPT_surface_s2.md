# Surface owner-drive + lifecycle — session-2 addendum (Stage B items 4-5)

Read `COMMON.md` first (worker rules, severity scale, out-of-scope-by-decision list, raw
finding shape) and obey it exactly. Read `PROMPT_wave2.md`'s SEAT and INDUCER sections too —
this file extends them, it does not replace them: the seat transcripts under
`docs/redesign/verification/r15/surface/seat-*/` and `inducer/` are SEEDED evidence, never
restarted. For the refute stage, read `PROMPT_refute.md` in full. `stage0/ISO_STACK.md` +
`stage0/LOCAL_LANE_PROOF.md` show exactly how a sidecar is booted and how the local (ollama)
lane behaves; `stage0/COVERAGE_SKELETON.md`/`.json` is the 101-row surface map whose cells
this wave fills; `scripts/r15/register.py` fixes the raw/refute file-naming contract.

`CENSUS` = `docs/redesign/verification/r15/census`. `SURFACE` =
`docs/redesign/verification/r15/surface`. `LIFECYCLE` =
`docs/redesign/verification/r15/lifecycle`. Your item id is `<id>`, your sidecar port
`<port>`, from your launch-args.

## Scope facts (every drive/induce/lifecycle prompt carries these — do not drop them)

1. **Trading is out of the product** (operator decision, 23 Sep). Skip the broker-connect
   panel, order entry, review bar, live/paper switch, broker plugin entirely. A finding whose
   subject exists only to connect a broker or place/simulate/gate an order is
   `removed_with_feature`, never analysed. The user's own tracked portfolio — manual holdings,
   cost bases, P&L on real prices, CSV export, notes, watchlists — stays IN scope; it is not
   trading.
2. **Lanes.** Local: `python3 scripts/r15/vy.py invoke copilot "<prompt>" --port <port>
   --provider ollama --model llama3.1:8b` (proof of behaviour in `LOCAL_LANE_PROOF.md` — this
   model DOES call tools some of the time and fails others; log which). Free: OpenRouter
   `:free` slugs via `--provider openrouter --model <slug>:free` (the guard caps free calls per
   day). Paid: OpenAI-direct (`--provider openai --model gpt-5-nano` or `gpt-4o-mini`) ONLY for
   what the local model provably cannot do, under the guard's $8 run cap (refuses at $7.50).
   Anything not driven for money is listed `NOT TESTED` with the dollar amount it would take.
3. **Your own isolated sidecar, your own data-dir copy.** Boot per `ISO_STACK.md`'s exact
   recipe on `<port>`, holding stdin with a `sleep 86400 |` pipe, writing a pids file under
   your scratch dir. Data dir: `cp -R <scratchpad>/vysted-iso/data <scratchpad>/vysted-iso/
   seat-<id>/data` (this is a backup copy, never the live db) UNLESS your task says CLEAN/empty
   profile. MCP env vars and the boot command are in `ISO_STACK.md`. Stop your own sidecar by
   killing its `sleep` pid when done. Never touch `:52152-54` or any other port that is not
   yours.
4. **No GUI lane in Stage B.** Headless evidence only: JSON responses, SSE transcripts, log
   excerpts. Anything only the GUI could show is written as `NEEDS-GUI` in the finding's
   `notes`, never guessed at.
5. **Induced failures are at YOUR sidecar's edge only**: env/config/settings of your own
   process, a dead port for SearXNG, a `PATH` without docker for your sidecar process, a fake
   provider `base_url` returning junk, a retired slug. Never stop Docker, drop the network, or
   touch a shared/system setting.
6. **Raw finding shape** is `COMMON.md`'s standard object, written to
   `CENSUS/raw/<prefix>-<id>.json` (`register.py` globs `census/raw/*.json`); verdicts go to
   `CENSUS/refute/<same basename>.json`.
7. **RESULT** — every stage returns `{model, output_file, summary, count, top}` per
   `r15-fanout.js`'s schema.
8. **Continue, never restart.** If your evidence dir, raw file, or a sidecar on your port
   already exists (a previous attempt died to a usage wall or power loss), read what is there
   and finish it.

## OWNER-DRIVE (`surf-S2A/B/C/D`, `drive` items)

You own one surface GROUP, not one seat. Objective: drive EVERY control and every state of
your group headlessly, at the API/agent level, with real data, the way the panel's own
`api.ts` calls the sidecar (read the panel code first — `src/modules/<group>/*`,
`src/modules/<group>/api.ts` — for what it sends and what it would render from each
response). READ-BACK BEFORE CLAIM: never assert a state exists without a response/log excerpt
proving it. Score every interaction `ok` / `partial` / `broken` with the evidence line that
backs the score.

You are SEEDED from existing seat evidence for your group's surfaces — do not re-run what a
seat already drove; read `SURFACE/seat-retail/`, `seat-microcap/`, `seat-us/`,
`seat-breaker/`, `seat-stranger/transcript.md` (whichever touched your group: composer/chat
and research/briefs were exercised in every seat's multi-turn conversation;
`seat-breaker/http-log.jsonl` stresses screener/portfolio/notes at scale) and continue past
where they stopped, filling gaps they didn't reach, not repeating their exact prompts.

Group → surfaces (filter `stage0/COVERAGE_SKELETON.json` by these `area` values; the mapping
is a starting point, not a ceiling — anything genuinely part of the group's user-facing
surface belongs, anything genuinely not does not):

- **composer-chat**: `composer` (16 rows) + `chat-agent` (8 rows) — the whole
  `ChatSidebar.tsx` composer (depth, model picker, plus-menu, mention/slash pickers,
  send/stop, queue, agents rail) and the agent bus (mode/autonomy/persona, delegate runs,
  streaming transport, markdown rendering, context badge). Drive multi-turn (3-6 turns),
  tool chains, a mid-stream stop (close the connection — does the sidecar cancel the upstream
  call, per `agent-behaviour`'s probe design?), every agent-completable host action once
  (watchlist add, note write, screen author, layout arrange) and read back its ack.
- **research-briefs**: `brief` (1 row, full lifecycle) plus the research funnel surfaces
  (depth selection, citations, divergence notice, the no-web-honest-banner at
  `BriefPanel.tsx:701`). Publish at least one brief per depth level you can afford under the
  budget; judge completeness/sourcing against what `funnel-largecap`/`funnel-thematic`
  already found (read those files first — don't re-trace the funnel, drive the PANEL surface
  around it: does a starved retrieval show up honestly in the UI-facing response, or silently?).
- **screener**: `screener` (5 rows) — shell, criteria builder, formula leaf, results table,
  presets. Cold and warm runs, a pasted formula, an agent-authored screen, pagination/sort,
  the tenth row, a screen with 0 results, a malformed formula. Cross-check against
  `screener-probe`'s existing findings before re-deriving them.
- **panels-layouts**: `panels` (17 rows, minus what composer/research/screener/portfolio/
  settings/plugins already claim) + `layouts` (3 rows) — every remaining first-party panel
  (chart, watchlist, news, equity-overview, agent-builder, node-editor pieces you CAN drive
  headlessly per `COVERAGE_SKELETON.md`'s gui/browser/api split, backtest, audit-log, macro,
  sec-filings, earnings-calendar, analyst-ratings, the four quant panels) plus the 4 arrange
  templates and workspace save/load. Six rows are GUI-only per the skeleton's finding 5 — mark
  those `NEEDS-GUI`, do not fabricate a headless drive for them.
- **portfolio-notes**: `portfolio` (1 row) + `notes` (4 rows). CRUD the paper-portfolio via
  its GET/POST/PUT/DELETE routes (never anything order-shaped), P&L math against known
  prices, CSV export, an empty portfolio, a 100-position portfolio (tenth-item + overflow);
  notes panel + toolbar + slash-menu + wikilink extension, a huge note, a note with
  prompt-injection-shaped content (read-only check: does anything downstream execute it?).
- **settings-plugins**: `settings` (13 rows, every section/subsection of
  `SettingsPanel.tsx` — resolve the two unresolved rows from `COVERAGE_SKELETON.md` finding 6:
  `settings-advanced-layouts` content and whether `provider-health-breaker` has ANY frontend
  surface) + `plugins` (2 rows: Plugin Manager, Marketplace).
- **onboarding-stranger**: `onboarding` (4 rows: first-run wizard, key banner, ToS/disclaimer
  flow) driven KEYLESS on a CLEAN empty data dir (do not copy the operator's data — seed
  `dev-keystore.json` as `{"secrets": {}, "migrated": true}` same as `ISO_STACK.md`). This is
  the surface-group twin of `seat-stranger`'s SEAT drive (read
  `SURFACE/seat-stranger/transcript.md` first, continue past it) — score every onboarding
  screen honestly for what it explains vs what it silently blocks.
- **failure-inducer**: continue `SURFACE/inducer/` past its existing 5 files (401, no-key,
  402, and an INCOMPLETE `05-network-unreachable.txt` — finish that one: run it, save its
  `.jsonl` too, not just the `.txt`). Then add every inducer PROMPT_wave2.md's INDUCER section
  lists that isn't yet covered: 429 (find/stub how the adapters surface it), SearXNG down +
  Docker absent (probe `/search/status` + `/search/searxng/status` with a `PATH` stripped of
  `docker` for your own sidecar process only), malformed symbols (`"   "`, `"$$$"`, 300 chars,
  SQL/HTML, unicode, `"RELIANCE.NS.NS"`), a retired model slug (`z-ai/glm-4.5-air:free`), a
  nonsense slug, a provider returning junk (stub the adapter for non-JSON/truncated stream).
  For each: how induced at the edge, what the app SAID (status + error frame + the exact text
  a panel/chat would render per the frontend error mapping in `src/` — cite `file:line`),
  honest or not, raw finding if silent/misleading/a stack trace/a CORS-masked 500.

### Owner-drive outputs

1. Evidence file(s) under `SURFACE/<id>/` (transcripts, request/response excerpts,
   `.jsonl` logs) continuing whatever is already there.
2. `SURFACE/<id>/COVERAGE.json` — copy the rows of `stage0/COVERAGE_SKELETON.json` that
   belong to your group, and for each row that you exercised, replace it with `{...row,
   "driven": "ok"|"partial"|"broken", "evidence": "<file:line or evidence-file path>"}`; for a
   row you could not reach, `{"driven": "NOT TESTED", "reason": "..."}`; for the GUI-only rows,
   `{"driven": "NEEDS-GUI"}`. Every row in your filtered set must end in one of these three
   states — none left as the bare skeleton row.
3. `CENSUS/raw/surf-<id>.json` — functional defects ONLY (dead controls, broken states,
   wrong data, silent failures, clipped/unreadable text — only if you can prove it headlessly,
   e.g. a `maxLength`/`overflow: hidden` style read from the component plus a response that
   would exceed it; never visual taste). `raw_id` prefix `SURF-<ID>` upper-cased. Empty array
   `[]` if genuinely nothing qualifies — still write the file.

## LIFECYCLE (`life-S2A/B/C`, `lifecycle` items)

Answer the L-numbered question in `LIFECYCLE/L5-bounds.md`'s shape: a `## <heading>` per
finding area, a stated method (code-read + induced test, cite what you actually ran), a
table or list of measured/observed facts, and a clearly separated "root cause read-back" from
anything you fixed (you fix nothing — record only). Write your own
`LIFECYCLE/L<n>-<slug>.md` continuing past any partial content already there.

- **L1 — a stranger's first five minutes.** FRESH empty data dir, keyless (same seeding as
  `onboarding-stranger` above — no copy of the operator's data). Drive the first five minutes
  a real stranger would hit: open, dismiss/read onboarding, try the composer without a key,
  try one panel that needs data. What works, what is dead, what explains itself honestly vs
  silently. Cross-reference `seat-stranger/transcript.md` — this is the LIFECYCLE framing of
  the same keyless-first-run fact, not a re-run of identical prompts.
- **L2 — six months from now, a retired slug or a changed exchange endpoint.** Induce a
  retired model slug (`z-ai/glm-4.5-air:free`) and, separately, point one exchange-facing
  route at a config value that no longer resolves (a stale/dead upstream host for one
  provider, at your sidecar's own env/config only). Is the failure visible and explained to
  the user, or silent? Cite the frontend error mapping and the adapter code that produced (or
  swallowed) the failure.
- **L3 — a redacted diagnostics bundle.** What diagnostic/support-bundle mechanism exists
  TODAY (grep for `diagnostics`, `bundle`, `support`, `export.*log` across `src/`, `sidecar/`,
  `src-tauri/`) — if none, say so plainly, that is itself the finding. For whatever exists (or
  the nearest thing to it — logs, `/health`, `/system/*` routes), determine: could a user hand
  it to a maintainer without extra instrumentation, and what would leak (secrets, other data)
  if they did. No new instrumentation is built; this session reports what exists.
- **L4 — 0.8.0 data surviving the upgrade.** Boot the CURRENT source sidecar on a COPY of the
  19-Sep 0.8.0 data dir referenced in `LOCAL_LANE_PROOF.md`/`ISO_STACK.md` (never the copy any
  other item is using — make your own `cp -R`). Check every store: does each router/service
  read the old schema without migration errors? List every store checked and its verdict
  (clean read / migrated / errored / silently dropped data).
- **L6 — hours-long session stability.** Start a DETACHED soak: `nohup` a loop of realistic
  requests (mix of quote/fundamentals/portfolio/notes GETs and a few cheap agent invokes)
  against YOUR OWN sidecar, writing `<scratchpad>/vysted-iso/soak/soak.log` plus periodic
  memory samples (`vm_stat`/`ps` on your sidecar's pid, same method as
  `LOCAL_LANE_PROOF.md`'s memory table), for at least 3 hours. Record the exact command used to
  start it and how a later reader checks progress (`tail`, pid, expected log cadence). Write
  the first 20 minutes' evidence NOW (do not block this stage on the full 3 hours) — a later
  continuation of this same output file reads the rest once it exists.

### Lifecycle outputs

1. `LIFECYCLE/L<n>-<slug>.md` per the shape above.
2. `CENSUS/raw/life-<id>.json` — raw findings for anything silent/broken/honest-gap-worth-
   flagging, prefix `LIFE-<ID>` upper-cased, `area: "lifecycle"`. Empty `[]` if nothing
   qualifies.

## REFUTE stage (every item, `refute` label)

Follow `PROMPT_refute.md` exactly: your raw file is `CENSUS/raw/<prefix>-<id>.json` (as
written by your own drive/induce/lifecycle stage, or the count your RESULT reported), your
output is `CENSUS/refute/<same basename>.json`. Apply the trading-scope-change handling in
`PROMPT_refute.md` (any surviving order/broker-shaped finding → `removed_with_feature`). A
zero-finding raw file still gets an empty verdict array `[]` written, never skipped.
