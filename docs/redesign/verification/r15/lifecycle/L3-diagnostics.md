# L3-diagnostics: could a user hand a maintainer a redacted diagnostics bundle today?

Worker: claude-opus-5-5[1m] (life-S2B, item `l3-diagnostics`). Status: COMPLETE (2026-09-23).
Attempt 2 (12:10-12:25 IST) re-verified the file and added §9 (the one artefact a user can copy
today). It adds no new raw finding.

**Short answer: no.** No diagnostics or support-bundle mechanism exists, and a shipped build
keeps no log of any kind. The nearest things are 14 loopback status endpoints, which are
secret-free and informative but not collected or exposed anywhere a user can reach, and the
raw data dir, which carries no secrets in a release build but does carry all of the user's
personal financial content, with no redaction path.

Method: a code-grep across `src/`, `sidecar/`, `src-tauri/`; a read-only search of the
operator's disk and the macOS unified log for any Vysted log; and an induced canary test on
my OWN sidecar (port 52227; data dir `$ISO/seat-l3-diagnostics/data`, a `sqlite .backup` +
`cp` of `$ISO/data`; sleep pid 50258, worker 50259, recorded in
`$ISO/pids-life-l3-diagnostics.json`). I fixed and instrumented nothing. Evidence dir:
`$ISO/seat-l3-diagnostics/evidence/`: `canary-drive.txt`, `sidecar-log-during-canary.txt`,
`status-endpoints.txt`, `unified-log-19sep.txt`.

## 1. Does a diagnostics / support-bundle mechanism exist?

`grep -rniE "diagnostic|support.?bundle|bug.?report|export.*log|log.*export|collect.*logs"`
over `src sidecar src-tauri/src` (excluding tests and .venv) returns 23 files. None of them is
a diagnostics mechanism:

| Hit | What it actually is |
|---|---|
| `sidecar/routers/safety.py:55-72` `GET /safety/audit-log/export.csv`, `src/modules/safety/AuditLogViewer.tsx:74` | the §6.5 **order** audit-log CSV (0 rows; trading is out of scope). Not a diagnostics export |
| `sidecar/services/data_cache.py:92` `db_path()` "for diagnostics", `run_manager.py:417` "for diagnostics" | internal helpers with no route and no caller outside tests |
| everything else | `export interface/function/const` false positives |

`src-tauri/Cargo.toml:25` has `tauri = { version = "2", features = [] }`: no `tauri-plugin-log`
and no `devtools` feature. The only diagnostic surface in the UI is the version string in
Settings → About (`SettingsPanel.tsx:1875-1880`, `v{HOST_VERSION}`). There is no "copy
diagnostics" button, no "report a bug" link, and no error boundary. **Nothing exists.** That
absence is the finding.

## 2. Where does diagnostic output go today? (measured)

| Producer | Mechanism | Destination in a shipped app |
|---|---|---|
| Rust core | `println!`/`eprintln!` (lib.rs:120-267, keychain.rs:234/281, kill_switch.rs:60-76, openbb_mcp.rs:83-178, sec_edgar_mcp.rs:83-…) | the app process's stdout/stderr. No file, no `os_log` |
| Python sidecar | uvicorn access/error loggers (`main.py:142`, `log_level="info"`). Service `logger.warning(...)` falls through Python's `lastResort` handler, because nothing calls `basicConfig`/`dictConfig`/a `FileHandler` anywhere in `sidecar/` | child stdout/stderr, re-printed by Rust as `[sidecar] …` (lib.rs:225-238). No timestamps, no level prefix on service lines |
| openbb-mcp / sec-edgar-mcp | same drain (openbb_mcp.rs:125-136) | same |
| React UI | 9 `console.warn` sites (e.g. `workspace.ts:524` "session restore failed") | the WKWebView console, which a release build cannot open (no `devtools` feature) |

Is anything persisted? No:

- `find ~/Library/Logs "~/Library/Application Support/com.vysted.terminal" ~/.vysted-terminal -iname "*log*"`
  finds only `audit_log.db` (the order audit table). There is no `~/Library/Logs/*vysted*`
  and no crash report in `DiagnosticReports`.
- macOS unified log, `log show --start "2026-09-19 06:28" --end "…06:36" --predicate 'process CONTAINS[c] "vysted"'`
  over the 0.8.0 boot on 19 Sep (the Rust core wrote `mcp-endpoint.json` at 06:31:43, so it
  certainly ran and printed): **38 lines, all Apple framework noise** (SkyLight,
  launchservices), and **0** lines of the app's own output (`[sidecar]`, `[vysted]`,
  `uvicorn`, "MCP endpoint discovery"). File: `unified-log-19sep.txt`.

So a user who hits a problem has **nothing** to send. The only way to see any log is to
relaunch the app binary from a terminal and reproduce the problem, which is the "extra
instrumentation" the question rules out. Even then the service lines carry no timestamp.

## 3. If a user DID capture the logs (dev/terminal run), what leaks? Induced canary test

I sent 9 requests to my sidecar carrying canary secrets through every key path the frontend
uses, plus private content, then grepped the whole sidecar log (`canary-drive.txt`,
`sidecar-log-during-canary.txt`):

| # | Request (canary) | App behaviour | Canary in log? |
|---|---|---|---|
| 1 | `GET /news` + `X-Vysted-Newsapi-Key: CANARY-NEWSAPI-…` | NewsAPI 401 → RSS fallback. Log: `news: NewsAPI source failed after retries: Client error '401 Unauthorized' for url 'https://newsapi.org/v2/everything?q=stock+market+OR+finance&…'` (key rides a header, `news_provider.py:233`, so it is not in the URL) | no |
| 2 | `POST /llm/keys/validate` openai `sk-CANARY-…-222` | `{"ok":false}` | no |
| 3 | same + `base_url` at a dead port | log `provider openai validation transport error: Connection error.` | no |
| 4 | `POST /agents/copilot/invoke` openai key `…-444` + a prompt with holdings | 401 error frame. The SSE `detail` repeats OpenAI's own masked key `sk-CANAR***********-444` back to the UI; the log has only the access line | no (neither key nor prompt) |
| 5 | `GET /quotes/RELIANCE.NS` + `X-Vysted-Openrouter-Key` | 200 | no |
| 6 | `GET /fundamentals/…/narrative` + `X-LLM-Key` | 200, honest "No API key" reason | no |
| 7 | `GET /resolve?q=QUERY-CANARY-L3 my secret watchlist` | 200 | **yes**: the uvicorn access line logs the full query string |
| 8 | `POST /portfolio/positions` with note `NOTE-CANARY…` | 201 | no (bodies are never logged) |
| 9 | `POST /llm/chat` (my request put the key in a header; this route takes it in the body, `models/llm.py:256`, so the result is a harness artefact) | error frame | no |

Result: **0 of 7 key canaries** (#1-6, #9) reached the log. The key hygiene of the log stream holds.
What does reach it: every URL query string, which is the user's search terms (`/resolve?q=`,
`/resolve/autocomplete`, `/sec/filings/search?q=`, `/macro/search?q=`, `/news?…`), every
symbol requested, and on any 500 a full traceback (`routers/agents.py:106` `logger.exception`
on a crashed invoke).

## 4. The nearest thing to a bundle, part 1: the loopback status endpoints

14 GETs exist and together they would make a decent support snapshot
(`status-endpoints.txt`). I scanned them for identifying data (`grep -c "lokavya|/Users/|hostname|MacBook"`): **0 hits**.

| Endpoint | Content | Leak |
|---|---|---|
| `/health` | version, per-data-kind provider routing | none |
| `/system/hardware`, `/system/local-model-recommendation` | chip (M1 Pro), RAM, core counts, macOS version, local Ollama model list + fit verdicts | hardware fingerprint only |
| `/system/ollama/status`, `/llm/providers` | local models, provider registry | none |
| `/system/provider-health` | Yahoo circuit state (`open:true`, `opens_total 3`, `throttles_total 114`) | none; the most useful single support signal |
| `/search/status`, `/search/searxng/status` | search tier, engine cool-downs, Docker/SearXNG state | none |
| `/mcp/status`, `/openbb-mcp/status`, `/sec/status` | MCP readiness, last tool-call error | none |
| `/safety/kill-switch/status`, `/safety/disclaimer-status` | booleans | none |
| `/safety/static-ip-status` | **the user's public IP**, fetched from an external detector | yes. It is Kite/broker-only, so removed_with_feature |

None of these is reachable from the UI as a bundle. The sidecar port is random per launch
and published only in `<data-dir>/mcp-endpoint.json` (lib.rs:166-192). A user would have to
find that file, read the port, and `curl` 14 URLs.

## 5. The nearest thing to a bundle, part 2: zipping the data dir

This is the only artefact a non-technical user could plausibly send. Measured on both copies
(the ISO copy and the 19-Sep 0.8.0 copy under `seat-l4-upgrade`), counting matches of seven
secret-shaped patterns (`sk-…`, `sk-or-v1-…`, `sk-ant-…`, `AIza…`, `gsk_…`, `xai-…`,
`"api_key|secret|password|token": "…"`) and excluding `dev-keystore.json`:

- **Secrets: 0 real.** The 0.8.0 copy had 4 `sk-` hits, all false positives inside URL slugs
  (`…-ri|sk-ass…`). The printout was masked; no value was shown. In a release build secrets
  live only in the OS keychain (`keychain.rs:6-23`, `USE_DEV_KEYSTORE = cfg!(debug_assertions)`
  at `:45`). In a **dev** build `dev-keystore.json` (0600, plaintext) sits in the same dir, so a
  dev/tester zip would carry every key. The dev keystore itself is out of scope by decision,
  so this is recorded as a fact only.
- **Personal financial content: all of it.** `workspaces/__autosave__.vysted-workspace` holds
  the tracked portfolio holdings, watchlist, notes (`general`, `bySymbol`), the last research
  brief (query + markdown + sources) and the research-space chat archive.
  `delegate_runs.db` holds run checkpoints (3.6 KB of transcript for 2 runs). `portfolio.db`
  holds positions with free-text notes. `exports/` holds research PDFs (38 MB on the operator's
  disk, per L5). `fundamentals_cache.db`/`data_cache.db` are 8 MB of regenerable market data,
  useless to a maintainer.

So "send us your data dir" is a privacy leak of exactly the data a BYOK/local-first user was
promised stays local (README.md:5 "no telemetry: data and secrets stay on your machine"). No
tool exists to redact it.

## 6. Crash capture

There is **no error boundary anywhere in the React tree**. `src/main.tsx:17` calls
`createRoot(…).render(<StrictMode><Page/></StrictMode>)` with no
`onUncaughtError`/`onCaughtError` options. `src/app/` holds only `page.tsx` + `globals.css`,
and `grep -rn "componentDidCatch|ErrorBoundary" src` returns 0 non-test hits. dockview renders
every panel through `createPortal` into the same root
(`node_modules/.pnpm/dockview@6.2.2_react@19.2.6/.../main.cjs.js`, 3 `createPortal` sites). By
React's documented default ("if your application throws an error during rendering, React will
remove its UI from the screen", https://react.dev/reference/react/Component), one panel's
render throw blanks the whole cockpit. The stack goes to a console the release build cannot
open. NEEDS-GUI to demonstrate visually; the mechanism is established from code and docs.

BLUEPRINT §4 Infrastructure (`docs/BLUEPRINT.md:315`) promised "Opt-in anonymous telemetry
(basic crash + usage)". The README now promises the opposite ("no telemetry"), and nothing
local replaced the crash signal.

## 7. Root cause read-back (recorded, not fixed)

- Diagnostics were never designed. Output is a side effect of `println!` and uvicorn defaults.
  No component owns "what does a maintainer need", so there is no log file, no rotation, no
  timestamps, no redaction list and no collection point.
- The local-first posture removed telemetry, which was right for privacy, but did not replace
  it with a **user-controlled** local equivalent (a log file under the data dir plus an
  explicit "Copy diagnostics" button that bundles the status endpoints and a redacted log
  tail). The ingredients are already secret-clean: 0/7 key canaries leaked, and the 14 status
  endpoints carry no secrets or usernames. So the bundle is mostly assembly work. The
  redaction list it needs: URL query strings, symbols, prompt/brief/note/run text, and the
  public IP.

## 8. Raw findings written

`census/raw/life-l3-diagnostics.json`: 2 findings (LIFE-L3-DIAGNOSTICS-1 high,
LIFE-L3-DIAGNOSTICS-2 medium).

Sidecar stopped: `kill 50258` (its sleep pid) at the end of the stage.

## 9. Continuation (attempt 2): the one diagnostic a user CAN copy today

§1 is right that no bundle exists. In practice, what a user pastes into a bug report is the
chat's error row. It shows the humanised message, the action, and a **"Details"** disclosure
that renders `frame.detail` verbatim in a selectable `<pre>`
(`src/modules/chat/ChatSidebar.tsx:1458-1472`). That `detail` is the raw provider exception
text, passed through with no redaction: `raw = detail or str(exc)` in
`sidecar/services/errors.py:123`, carried as `detail=raw` in every branch (`:155-258`), and
documented at `:82` as "the raw provider text — UI shows behind a toggle". Two observed
payloads:

| Source | What the Details text carries |
|---|---|
| OpenAI 401 (canary #4, `canary-drive.txt`) | OpenAI's own masked echo of the key, `sk-CANAR***********-444`: the first 8 and last 3 characters |
| OpenRouter 404 (`lifecycle/L2-rot/20-retired-slug.jsonl`, 1 hit) | the OpenRouter **account `user_id`** (`'user_id': 'user_…'`), verbatim |

Neither is a usable secret. The key fragment is the provider's own mask, and a user id is an
account identifier. But both are identifying, and they sit in exactly the text a user is most
likely to paste into a public GitHub issue. That changes the redaction list for the smallest
honest bundle in §7: add **upstream error bodies (`detail`): strip `user_id`/`account`/`org`
fields and key-shaped fragments**. The list is now: URL query strings, symbols,
prompt/brief/note/run text, the public IP, and upstream error bodies. This is a bundle design
input, so it is folded into LIFE-L3-DIAGNOSTICS-1 rather than filed separately. On its own it
would not change a decision.

Attempt-2 note: `$ISO/seat-l3-diagnostics/data/` was re-copied from `$ISO/data` before the
earlier evidence was found. Attempt 1's canary portfolio row is therefore gone from that dir;
the evidence files under `seat-l3-diagnostics/evidence/` are untouched. No L3 sidecar was
started in attempt 2 (`:52227` was already down: `pids-life-l3-diagnostics.json`, sleep 50258,
is no longer running).
