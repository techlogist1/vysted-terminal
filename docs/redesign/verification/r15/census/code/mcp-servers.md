# R15 CENSUS — code critique: `mcp-servers` (MCP Servers & Subprocess Infra)

**Subsystem:** `mcp-servers` — 1992 LOC across `sidecar/services/mcp_client.py`,
`sidecar/services/mcp_server.py`, `sidecar/services/openbb_mcp_provider.py`,
`sidecar/routers/mcp.py`, `types/mcp.ts`, `sidecar/openbb_mcp_subprocess/`,
`sidecar/sec_edgar_mcp_subprocess/`, `src-tauri/src/openbb_mcp.rs`,
`src-tauri/src/sec_edgar_mcp.rs`.

**Method:** `aposd-critique` skill loaded and followed. **Assessment independence:
degraded (sequential)** — this worker is already a subagent in the R15 fan-out; spawning two
more personas for a 2 kLOC subsystem is not worth the tokens, so Strategic-Thinker and
Tactical-Tornado passes ran sequentially in one head. Persistence to `.aposd/critique/`
**skipped** — R15 owns the output paths and a snapshot tree would pollute the repo.

**Live evidence** was taken against the ISOLATED R15 sidecar (`127.0.0.1:52152`, GET/POST
allowed per COMMON.md). Three bugs were additionally proven with throwaway snippets under
`/tmp/claude-501/` (not committed).

---

## Tactical Tornado verdict

**Medium-high.** The two Rust supervisors and the two subprocess entry points are
disciplined, well-commented, symmetric code — the part of this subsystem that had a
production incident (the Windows `subprocess.Popen` deadlock) got designed twice and shows
it. The Python half did not. `McpClient` is a **shallow module**: it re-exports the MCP
SDK's `list_tools`/`call_tool` almost unchanged and *narrows* the result (drops
`structuredContent`), so the real abstraction — "an env-var-discovered local MCP subprocess
you call and decode" — got re-implemented **twice**, verbatim, in `openbb_mcp_provider.py`
and `sec_filings_provider.py`. Every bug found below in one of them exists in the other.

Most damning single pattern: `mcp_client.py:158,182` catches `(TimeoutError, mcp.McpError,
OSError)` to honour the module docstring's promise that "any transport-level failure … drops
the cached session so the next call rebuilds it" — but **none of the exceptions the real
transports raise are in that tuple** (`anyio.ClosedResourceError`,
`anyio.BrokenResourceError`, `httpx.ReadError` are all plain `Exception` subclasses, verified
against the installed `anyio 4.13.0` / `httpx 0.28.1`). The one test that guards the promise
(`test_mcp_client.py:114`) raises `mcp.McpError` — the single class that *is* in the tuple.
Special-casing to satisfy a test, textbook.

Flags found: 13 (2 high, 8 medium, 3 low). Four are provable bugs, not smells.

---

## Design principles score

| # | Principle | Verdict | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | at-risk | `openbb_mcp_provider.py:387-395` — a ~100× unit bug was fixed with a `/100.0` + a 7-line comment rather than a typed unit at the contract | The unit convention lives in prose; the next provider repeats the bug |
| 2 | Deep modules | **violate** | `mcp_client.py:153-206` — `list_tools`/`call_tool` are a 1:1 re-export of `session.list_tools`/`call_tool` with a dict rename; interface ≈ implementation | Both consumers must own endpoint discovery, decoding and health state themselves |
| 3 | Information hiding | at-risk | `mcp_client.py:206` returns only `{isError, content}`; `mcp.types.CallToolResult` also carries `structuredContent` and `meta` | `sec_filings_provider.py:151-153`'s structured-content fallback is unreachable dead code |
| 4 | Information leakage | **violate** | `openbb_mcp_provider.py:122-252` vs `sec_filings_provider.py:95-170` — `_resolve_endpoint`/`is_available`/`status`/`_get_client`/`_decode_tool_result`/`_call_tool`/`_last_*` duplicated | Change amplification: every fix below lands twice or silently diverges |
| 5 | General-purpose modules are deeper | **violate** | `openbb_mcp_provider.py:260-262` `_normalize_symbol` applies a US class-share fix (`.`→`-`) to every symbol | `RELIANCE.NS` → `RELIANCE-NS`; special-general mixture on the product's primary market |
| 6 | Different layer, different abstraction | pass | `mcp_server.py:146-155` projects catalog capabilities into `FunctionTool`s dispatching to the same `agent_tools` handler — a genuine adapter, zero logic duplication | — |
| 7 | Pull complexity downward | **violate** | `mcp_server.py:94` returns a client bound to `http://127.0.0.1:0` "so an early failure produces a useful error", then `:178-180,:311-313,:362-364` swallow that error into `[]` | The complexity was pushed *up* to three call sites that each dispose of it differently |
| 8 | Better together or apart | at-risk | `routers/mcp.py:44-53` is a 1-line pass-through to `openbb_mcp_provider.status()`; a symmetric `/sec/status` lives in another router | Two half-modules where one "local MCP subprocess" module belongs |
| 9 | Define errors out of existence | **violate** | `mcp_client.py:158,182` except-tuple misses `anyio.*`/`httpx.*`; `mcp_client.py:228-231` `get_client` returns a cached client ignoring a changed `endpoint` | A broken session is cached forever; the documented self-healing never fires |
| 10 | Design it twice | pass | `openbb_mcp.rs:1-26` + `sec_edgar_mcp.rs:1-26` — `Popen` → Tauri `shell().sidecar()` is a considered second design with the first one's failure recorded | — |
| 11 | Comments describe non-obvious | at-risk | `mcp_client.py:78-81` explains a generation counter that the code does not structurally enforce (see P1 below) | The comment asserts an invariant the reader cannot verify from the structure |
| 12 | Comments first | pass | `mcp_server.py:377-390` documents *why* the streamable-http app must be one cached instance (lifespan vs mount) — knowledge no reader would recover | — |
| 13 | Choosing names | pass | `register_unavailable`, `wait_for_port_with_retries`, `_exit_when_parent_closes_stdin` all say exactly what they do | — |
| 14 | Modifying existing code | at-risk | `types/mcp.ts:8,104` still says protocol `2025-11-25`; `mcp_server.py:58` says `2025-06-18`; the live server negotiates `2025-11-25` | Three copies of one fact, already two-way drifted |
| 15 | Consistency | **violate** | `mcp_server.py` ships three different error policies across 8 hand-written tools: swallow-to-empty (`:178,:311,:362`), let-it-escape (`:244,:252,:334`), return-error-dict (`:120-122`) | The next tool author has no rule to follow; an MCP client sees three failure shapes |
| 16 | Code should be obvious | at-risk | `openbb_mcp_provider.py:532` `row.get("value") or row.get(series_id)` reads as a fallback, silently discards a legitimate `0.0` | Proven below: a 0.00 policy-rate observation is reported as missing |
| 17 | Design for the future | pass | `mcp_client.py:96-107` keeps the stdio transport alive for filesystem-installed plugins without paying for it elsewhere | — |
| 18 | Performance as design | at-risk | `openbb_mcp_provider` is declared rank-10 with **no** `region` scope (`provider_registry.py:128-142`) while every other IN-capable provider is region-scoped | Every Indian fundamentals request pays a guaranteed-failing MCP round-trip before falling back |

**Summary: 6 pass, 6 at risk, 6 violate (6/18 pass).**

---

## What's working

1. **Catalog projection is a genuinely deep adapter.** `mcp_server.py:146-155` builds every
   data/analysis MCP tool from `catalog.mcp_capabilities()` and dispatches to the *same*
   `agent_tools` handler the internal copilot calls. Adding a capability costs one catalog
   entry and appears on both surfaces. This is the single best piece of design in the
   subsystem and it is test-locked (`test_mcp_catalog_parity.py`). Live: 36 tools on
   `GET /mcp/status`.
2. **The Rust supervisors are the right shape.** `openbb_mcp.rs:79-180` /
   `sec_edgar_mcp.rs:79-177` pick the port immediately before spawn, drain stdout/stderr
   *before* the bind probe, degrade to `port=0` on every failure path, and never panic. The
   failure-mode log lines name the historical finding id and the fallback behaviour — a
   maintainer debugging a cold boot gets told what to do.
3. **The stdin-EOF watchdog is deliberate, not copy-paste.** Both
   `*_mcp_subprocess/main.py:29-51` use `os.read` rather than `sys.stdin.buffer.read` with a
   comment naming the exact deadlock that forced it. That is a comment saying what the code
   cannot.

---

## Priority issues

### [P0] The MCP surface accepts any cross-origin caller — the spec-mandated Origin check is absent

- **Principle:** 9 (Define errors out of existence) / 3 (Information hiding)
- **Complexity symptom:** Unknown unknowns
- **Evidence:** `sidecar/app.py:301-307` installs `CORSMiddleware(allow_origins=["*"],
  allow_methods=["*"], allow_headers=["*"])`; `sidecar/app.py:345` mounts the FastMCP
  Streamable-HTTP app at `/mcp`; nothing in `mcp_server.py` or `routers/mcp.py` reads the
  `Origin` header (`grep -n "Origin" sidecar/app.py sidecar/services/mcp_server.py
  sidecar/routers/mcp.py` → no hits). Live against `127.0.0.1:52152`:
  `OPTIONS /mcp/` with `Origin: https://evil.example` → `200` + `access-control-allow-origin: *`;
  the follow-up `POST /mcp/ initialize` with the same Origin → `200`,
  `access-control-allow-origin: *`, full capability handshake.
- **Why it matters:** the MCP spec requires local Streamable-HTTP servers to validate
  `Origin` precisely because browser-side mitigations are inconsistent. Behind that one
  unauthenticated path sit all 36 tools: workspaces, portfolio, broker reads, `run_workflow`,
  `save_workflow`, and `invoke_agent` (which spends the user's BYOK LLM budget). The only
  real barriers are the random per-launch port and Chrome's Private-Network-Access preflight
  — neither is a design decision this repo made, and Safari/older Chrome do not apply PNA.
- **Fix:** one Starlette middleware on the `/mcp` mount rejecting requests whose `Origin` is
  present and not `tauri://localhost` / `http://localhost:*`. Do not widen scope — the rest
  of the REST API shares the CORS policy, but `/mcp` is the single path that bundles the
  whole tool surface.
- **Honest caveat for the refute stage:** reachability from a *browser* depends on PNA and
  mixed-content behaviour; reachability from any other local process is unconditional.

### [P0] `McpClient`'s reconnect-on-error cannot fire for the exceptions the real transports raise

- **Principle:** 9 (Define errors out of existence) / 1 (Strategic over tactical)
- **Complexity symptom:** Unknown unknowns
- **Evidence:** `mcp_client.py:15-19` promises "any transport-level failure (the underlying
  anyio streams close, the JSON-RPC request times out, the server returns an `mcp.McpError`)
  drops the cached session". `mcp_client.py:158` and `:182` catch
  `(TimeoutError, mcp.McpError, OSError)`. Verified against the installed venv:
  `anyio.ClosedResourceError`, `anyio.BrokenResourceError`, `anyio.EndOfStream`,
  `httpx.ConnectError`, `httpx.ReadError`, `httpx.RemoteProtocolError` are **all** direct
  `Exception` subclasses, none an `OSError`. Runtime proof — a session raising each of the
  three leaves `client._session is None → False`, i.e. the dead session stays cached:
  ```
  ClosedResourceError      session dropped? False
  BrokenResourceError      session dropped? False
  ReadError                session dropped? False
  ```
- **Why it matters:** when the openbb-mcp or sec-edgar-mcp child dies or its stream breaks
  mid-life (the *expected* failure for a PyInstaller `--onefile` child), the cached
  `McpClient` never rebuilds. Every subsequent `/fundamentals`, `/sec/*`, `/macro` call fails
  identically until the whole app restarts. The self-healing the module exists to provide is
  structurally unreachable.
- **Fix:** catch `Exception` (re-raise `asyncio.CancelledError`) in both handlers — the
  handler only drops a cache entry, so over-catching is strictly safer than under-catching.
  Then change `test_mcp_client.py:114` to parametrise over `anyio.ClosedResourceError` and
  `httpx.ReadError` as well as `mcp.McpError`.

### [P1] Three incompatible error policies across the eight hand-written MCP tools; three of them turn a broken router into an empty list

- **Principle:** 15 (Consistency) / 7 (Pull complexity downward)
- **Complexity symptom:** Cognitive load + unknown unknowns
- **Evidence:** swallow-to-empty — `mcp_server.py:178-180` (`list_agents` → `{"agents": []}`),
  `:311-313` (`list_workflows` → `{"workflows": []}`), `:362-364` (`list_runs` → `{"runs": []}`);
  let-it-escape — `:244-246` (`list_workspaces`), `:252-254` (`get_workspace`), `:331-336`
  (`save_workflow`) all call `raise_for_status()` bare; return-error-dict —
  `:116-122` (`_make_catalog_tool` → `{"ok": False, "error": …}`). The swallow branch is
  reachable from `_internal_client`'s own fallback at `:94` (`base_url="http://127.0.0.1:0"`),
  whose comment claims it "exists so an early failure produces a useful error".
- **Why it matters:** this is the product's external face. An LLM in Claude Desktop asking
  Vysted "what agents do you have?" while the agents router is unreachable is told
  *"none"* — a confident wrong answer, indistinguishable from a build with no agents. The
  agent-native promise is exactly what this silently degrades. Meanwhile a missing workspace
  id throws a raw `httpx` error out of a sibling tool.
- **Fix:** one policy for the file — return `{"<key>": [], "error": "<reason>"}` on failure
  so the LLM can tell "empty" from "broken", and wrap the three bare `raise_for_status()`
  sites in the same shape. Delete the `127.0.0.1:0` fallback at `:94` and raise instead; it
  cannot produce a useful error while three of its four consumers eat it.

### [P1] `lastToolCallOk` reports **green after a failed tool call** (proven), in two providers

- **Principle:** 16 (Obviousness) / 4 (Information leakage)
- **Complexity symptom:** Change amplification
- **Evidence:** `openbb_mcp_provider.py:239-252` — the `except` only wraps
  `client.call_tool` (`:244-248`). `_decode_tool_result` (`:249`) raises `ProviderError` on
  `isError`, on non-JSON text, and on "no text content" — every one of those paths exits
  before `_last_tool_call_ok = True` at `:250` **and before any `= False`**, leaving the
  previous value in place. Identical shape at `sec_filings_provider.py:158-171`. Proven:
  ```
  A: after OK  -> {... 'lastToolCallOk': True, 'lastError': None}
  A: tool raised: openbb-mcp tool 'equity_price_quote' reported error: [...]
  A: after isError -> {... 'lastToolCallOk': True, 'lastError': None}
  ```
- **Why it matters:** `GET /openbb-mcp/status` (`routers/mcp.py:44-53`) and `GET /sec/status`
  feed the plugin-manager chip. An MCP server that is up but returning tool errors on every
  call is painted healthy, and `lastError` stays `null`, so the operator has no thread to
  pull. This is a data-trust surface on a product whose moat is data trust.
- **Fix:** move the decode inside the `try` (`raw = …; decoded = _decode_tool_result(...)`)
  so the single `except` owns both failure classes — then do it **once** in a shared helper
  rather than twice (see P2).

### [P2] The "local MCP subprocess provider" abstraction is duplicated verbatim; `McpClient` is too shallow to hold it

- **Principle:** 2 (Deep modules) / 4 (Information leakage)
- **Complexity symptom:** Change amplification
- **Evidence:** `openbb_mcp_provider.py:122-252` and `sec_filings_provider.py:95-170` are
  the same seven members with two strings changed: `_resolve_endpoint` (env var → `http://
  host:port/mcp`), `is_available`, `status`, `_get_client`, `_decode_tool_result`,
  `_call_tool`, and the `_last_tool_call_ok`/`_last_error` pair. `mcp_client.py:153-206`
  offers none of it — it hands back the SDK's two verbs and a narrowed dict.
- **Why it matters:** P1 (stale `lastToolCallOk`) and the `structuredContent` drop below
  both exist twice. So will the next one. A third bundled MCP child (the `fred_mcp` the Rust
  comments already anticipate at `sec_edgar_mcp.rs:18`) makes it three.
- **Fix:** promote the duplicated half into `mcp_client` as a
  `LocalMcpSubprocess(server_id, port_env, host_env)` owning endpoint discovery, `status()`,
  the health flags and `call_tool_json()`. Both providers keep only their field mapping.
  Roughly −120 LOC and one place to fix P1.

---

## Secondary findings (still decision-changing)

### `/mcp/status` reports a protocol version the server does not speak — proven, three-way drift

`mcp_server.py:58` hardcodes `_PROTOCOL_VERSION = "2025-06-18"` with the comment "MCP
revision FastMCP 3.x speaks"; `routers/mcp.py:40` serves it; `types/mcp.ts:8` and `:104`
document `2025-11-25`. Live against `127.0.0.1:52152`:

```
GET  /mcp/status                      -> {"ready":true,"toolCount":36,"protocolVersion":"2025-06-18"}
POST /mcp/ initialize (2025-11-25)    -> {"result":{"protocolVersion":"2025-11-25",...}}
```

The installed SDK's `mcp.types.LATEST_PROTOCOL_VERSION` is `2025-11-25`. So the status
endpoint — the one surface that exists *so a client need not speak JSON-RPC* — is the only
place that reports the wrong answer, and it drifts again on every SDK bump.
**Fix:** `return mcp.types.LATEST_PROTOCOL_VERSION` and delete the constant + the TS prose.

### `McpClient.call_tool` drops `structuredContent`, making a documented fallback dead code

`mcp_client.py:189-206` builds `{"isError", "content"}` only. `mcp.types.CallToolResult`
carries `['meta', 'content', 'structuredContent', 'isError']`.
`sec_filings_provider.py:151-153` then does `structured = result.get("structuredContent")`
with the comment "Fallback: structured content (FastMCP 3.x with output_schema)" — that
branch can never execute. Proven: a result whose only payload is
`structuredContent={"x":1}` comes back as `{'isError': False, 'content': []}`, so the
provider raises "returned no content" instead of using the structured body.
`types/mcp.ts:74-79` mirrors the same omission. **Fix:** pass `structuredContent` through
(one key) and add it to `McpToolCallResult`.

### A legitimate `0.0` macro observation is reported as missing — proven

`openbb_mcp_provider.py:532`: `value = _coerce_float(row.get("value") or row.get(series_id))`.
`0.0` is falsy, so the `or` falls through to a key that is normally absent → `None`.

```
input : [{"date":"2021-01-04","value":0.0},{"date":"2021-01-05","value":0.07}]
output: [('2021-01-04', None), ('2021-01-05', 0.07)]
```

A ZIRP-era policy rate, a zero spread, a zero net-flow print all disappear from the macro
panel as holes rather than zeros. **Fix:** `row["value"] if "value" in row else
row.get(series_id)`. The same `or`-as-fallback idiom is at `:305`, `:306`, `:321` and
`:532` — `volume or exchange_volume` turns a halted-session volume of 0 into `None` too.

### `_normalize_symbol` mangles every Indian ticker, and openbb-mcp is the rank-10 provider for them

`openbb_mcp_provider.py:260-262` returns `symbol.replace(".", "-").upper()` for *every*
symbol — a fix for US class shares (`BRK.B` → `BRK-B`) applied globally. `RELIANCE.NS` →
`RELIANCE-NS`, which no upstream resolves. `provider_registry.py:128-142` declares
`openbb-mcp` at `rank=10` with **no** `region=` field, while `nse_direct` (15), `nse` (20)
and `bse` (25) are all `region=frozenset({"IN"})`. So every IN `fundamentals` /
`income_statement` / `balance_sheet` / `cash_flow` / `analyst_rating` request is offered to
openbb-mcp first, mangles the suffix, returns no rows, raises, and only then falls through to
yfinance (`provider_registry.py:405-410`). `test_openbb_mcp_provider.py:101-108` parametrises
only `BRK.B`, `BF.B`, `aapl`, `AAPL` — the India case is untested. Returned models also carry
the *mangled* symbol (`Fundamentals(symbol=normalized …)` at `:397`), so a `BRK.B` request
answers with `BRK-B`. **Fix:** preserve a trailing exchange suffix
(`.NS`/`.BO`/`.L`/…) and only rewrite an interior dot; add the `.NS` case to the parametrise
list.

### `_ensure_session` reads the session/generation pair outside the lock the comment relies on

`mcp_client.py:126-132` checks and returns `self._session` and `self._generation` outside
`self._lock`; `_open()` at `:121-123` assigns `_session` *before* incrementing `_generation`.
A caller can therefore capture `session=new, generation=old` (or the reverse) and later call
`close(expected_generation=…)` on a session a sibling already replaced — the exact
"concurrent-cold-call poisoning race" the counter was introduced to prevent per the comment
at `:78-81`. The `assert self._session is not None` at `:131` is the only guard and is
stripped under `python -O`. **Fix:** take the lock for the whole of `_ensure_session` and
return the pair from inside it; the lock is uncontended on the hot path.

### `invoke_agent` advertises `api_key` as an MCP tool parameter to every external client

`mcp_server.py:183-185`: `async def invoke_agent(agent_id: str, prompt: str, api_key: str |
None = None)`. FastMCP publishes that signature as the tool's input schema, so Claude
Desktop / Claude Code / any MCP client sees a tool asking the *model* to supply a BYOK
secret, and a filled value lands in that client's tool-call transcript and provider logs.
CLAUDE.md's BYOK rule is that the secret rides a header from the renderer and is never
persisted or echoed. **Fix:** drop the parameter; let the in-process call inherit the
sidecar's own key resolution, or read it from a request header at the `/mcp` mount.

### Two OS threads write the process environment concurrently

`lib.rs:470-485` spawns `openbb_mcp::spawn` and `sec_edgar_mcp::spawn` on two
`thread::spawn` handles "IN PARALLEL"; each then calls `std::env::set_var` twice
(`openbb_mcp.rs:95-96`, `sec_edgar_mcp.rs:95-96`) and `std::env::remove_var` twice on the
failure path (`openbb_mcp.rs:59-60`, `sec_edgar_mcp.rs:58-59`). POSIX `setenv`/`unsetenv` are
not thread-safe and Rust made `set_var` `unsafe` in edition 2024 for exactly this; the crate
is `edition = "2021"` (`src-tauri/Cargo.toml:6`) so the compiler says nothing. The joins at
`:484-485` order the *reads* correctly but not the concurrent writes. **Fix:** have each
thread return its `u16` and have the (single-threaded) setup body set both vars after the
joins — the joins are already there.

### Vysted-as-server never sets `isError`, while Vysted-as-client keys failure off it

`mcp_server.py:116-122` converts every handler failure into a *successful* tool result
containing `{"ok": False, "error": …}`; nothing in `_build_server` ever sets `isError`.
`openbb_mcp_provider.py:187-190` and `sec_filings_provider.py:131-134` both treat
`isError` as *the* failure signal. An MCP client that keys off the protocol flag (including
a future Vysted-to-Vysted federation) sees every Vysted failure as a success. **Fix:** raise
`ToolError` from `_make_catalog_tool` instead of returning a dict, or set `isError`.

---

## Minor observations

- `openbb_mcp_provider.py:139-144` caches `_AVAILABLE` for process life while
  `status()` at `:154` re-reads `_resolve_endpoint()` every call — two sources for one truth,
  and the cache is the one `provider_registry.py:131` consults.
- `openbb_mcp_provider.py:354-355` drops every malformed bar with a bare `continue`, so a
  fully-malformed payload yields an empty `OHLCVSeries` with `reason=None` — the field
  `models/market.py:58` added specifically so an empty chart can explain itself.
- `mcp_client.py:228-231` — `get_client` returns a cached client on `server_id` alone and
  silently ignores a different `transport`/`endpoint` argument.
- `types/mcp.ts:101` "Always `"/mcp"` in v0.4.0" is stale prose in a v0.6.x tree.
- `mcp_server.py:171,189` still reference "Teammate A" / "Teammate W" in shipped docstrings.
- `openbb_mcp_provider.py:387-395`'s `dividend_yield / 100.0` is a money-relevant unit
  convention held only by a comment; there is no test asserting the percent→fraction
  direction (`test_openbb_mcp_provider.py:199-244` does not cover it).

---

## Persona walkthrough

**Tactical Tornado.** Given "the sec-edgar child needs a provider too", the Tornado copies
`openbb_mcp_provider.py:122-252` into `sec_filings_provider.py:95-170`, changes two env-var
names, and ships — which is exactly what happened. Then, told "call_tool sometimes doesn't
reconnect", it adds `OSError` to the tuple at `mcp_client.py:158`, writes a test that raises
the one exception already caught (`test_mcp_client.py:114`), and marks it done. Then, told
"the status chip is wrong", it adds a `_last_error` string next to `_last_tool_call_ok`
in *both* providers rather than moving the decode inside the `try`.

**Strategic Thinker.** Redesigns `mcp_client` into the module its two callers actually need:
`LocalMcpSubprocess(server_id, port_env)` owning discovery, health, a single `Exception`
catch that drops a dead session, `call_tool_json()` returning the decoded body including
`structuredContent`, and a `status()` the routers serve directly. `openbb_mcp_provider` and
`sec_filings_provider` shrink to field mapping. `_PROTOCOL_VERSION` becomes
`mcp.types.LATEST_PROTOCOL_VERSION`. The eight hand-written tools in `mcp_server.py` get one
failure shape. Net: roughly −150 LOC, and P1/P2/the `structuredContent` drop stop being two
bugs each.

---

## Questions to consider

- If `mcp_client` returned the decoded JSON body instead of a narrowed content-block dict,
  would either provider still need a `_decode_tool_result` at all?
- `openbb-mcp` is declared with no `region` scope while every other non-US provider is
  scoped. Is that a decision, or a field nobody filled in?
- `/mcp` is the single richest unauthenticated surface in the app. What is the argument for
  it sharing the REST API's `allow_origins=["*"]` rather than owning its own Origin check?

---

## Run notes

Target: `mcp-servers` (13 files, 1992 LOC) — all core files read in full.
Ignore list: none (`.aposd/critique/ignore.md` absent).
Assessment independence: **degraded (sequential)** — deliberate, see header.
Snapshot persistence: **skipped** (R15 owns the output paths).
Live probes: isolated sidecar `127.0.0.1:52152` only, GET + POST, no process started or
stopped. Temp scripts under `/tmp/claude-501/` — not committed.
