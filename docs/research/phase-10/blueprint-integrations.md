# Phase 10 Blueprint — Integrations / Brokers Hub + Real Kite Connect Read-Only Flow

Date: 2026-05-29
Author: Integrations/Brokers hub architect (headless)
Status: implementation-ready. The lead builds directly from this.

Scope of this track:
1. A user-facing **Integrations hub** (Settings section + dockview panel) with a
   declarative registry — informed by the Fincept `ConnectorRegistry` + OpenBB
   `Provider.instructions`/credentials-hub study.
2. The **real Kite Connect read-only flow** for a Tauri desktop app: api_key +
   api_secret entry → loopback OAuth login → daily `request_token → access_token`
   exchange (checksum in Rust) → keychain storage → daily re-auth UX → live
   positions/holdings/P&L in a panel + fed to the copilot.
3. A **shared integration contract** so **Dhan + Angel One** slot in identically
   (read-only). Reuse Phase-5 broker code where present.

Hard constraints honoured throughout:
- **§6.5 LOCKED files are NOT touched**: `sidecar/services/broker_base.py`,
  `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`,
  `types/plugin.ts`, `tests/test_safety_end_to_end.py`. Verified the public ABC
  surface in `broker_base.py:223-394` — `propose_order`/`confirm_and_place` are
  untouched; we only ADD read-only plumbing and OAuth that produces the
  `access_token` the existing `KiteAdapter._connect` already expects
  (`kite.py:69-102`).
- **Order execution stays OUT.** Every new route in this track is a `GET`, or a
  `POST` that only mints/stores a token or persists a connection — never an
  order. No new call site of `_place_confirmed`.
- The plugin contract (`types/plugin.ts`) is **read but never edited** (Tier-4).
  The hub's richer metadata is host-resolved, mirroring the existing
  `PLUGIN_COMPANIONS` host-side-glue precedent (`plugin-bootstrap.ts:81-83`).

---

## 0. Ground truth verified against source (the gaps we are closing)

| # | Claim | Cited source | Implication |
|---|-------|--------------|-------------|
| G1 | Kite `_connect` consumes a pre-resolved `access_token`; never does OAuth, never uses `api_secret` | `kite.py:69-102` (no `generate_session`/`login_url`/`request_token`); UI collects `api_secret` at `BrokerConnectPanel.tsx:53` but sidecar ignores it | Build real OAuth that mints the token. |
| G2 | Only one read route exists: `GET /brokers/{id}/account` → `AccountSummary` | `brokers.py:171-178`; `models/broker.py:109-121` | No `/positions`, `/holdings`, `/margins`. Add granular read routes. |
| G3 | Kite account_info uses `available.cash` for equity AND buyingPower; never calls `positions()` | `kite.py:190-202` (no `self._client.positions()`); F&O positions invisible | Fix equity = `net`; fetch positions. |
| G4 | No broker section in Settings; broker connect lives only in a dockview panel | `SettingsPanel.tsx:53-56` (Providers/Layouts/Modules/About only) | Add Integrations section + hub. |
| G5 | `store/brokers.ts` `disconnect()` POSTs `/brokers/{id}/disconnect` which does not exist | `brokers.ts:94-104` vs `brokers.py` (no disconnect route) | Add the route (latent 404). |
| G6 | Static-IP banner hardcodes `configuredIp={null}` and only mounts in live mode | `BrokerConnectPanel.tsx:252-254` | Fetch + pass configured IP; mount in paper too. |
| G7 | Broker plugins (`plugins/brokers/*`) are NOT bundled — their commands are dead | `plugin-bootstrap.ts:45-49` imports only example/openbb-mcp/tradesa-v2 | Hub talks to sidecar routes directly (the live surface), not the dead plugin layer. |
| G8 | No `tauri-plugin-oauth` / `tauri-plugin-deep-link` in deps | `Cargo.toml` deps list (shell/updater/global-shortcut/notification + keyring only) | Add a self-contained loopback listener in Rust (no new plugin crate needed — see §2.3). |
| G9 | No agent tool reads broker portfolio | grep of `sidecar/services/agent_tools/*.py` — zero `portfolio`/`positions`/`account` tool | Add a read-only `broker_portfolio` agent tool. |
| G10 | Sidecar CANNOT read keychain; renderer reads keychain → sends secret in request | `keychain.rs` (Rust-only commands); CLAUDE.md "renderer reads keychain → passes secret in request" | Keep this. `api_secret` is the one exception — it stays Rust-only (§2). |

Everything below is built to close G1-G9 without reopening any locked file.

---

## PART 1 — THE INTEGRATIONS HUB (UX + REGISTRY)

### 1.1 Concept: one declarative registry, two view modes, four categories

Adopt Fincept's `ConnectorConfig`/`FieldDef` shape (study-fincept §2,
`DataSourceTypes.h`) + OpenBB's per-provider `instructions`/`website`
credential-onboarding blob (study-openbb §1.4) as a **host-side TypeScript
registry**. It unifies what are today four disjoint surfaces:
- brokers (`BrokerConnectPanel.tsx`)
- AI providers (`SettingsPanel.tsx` ProvidersSection)
- MCP servers (no UI)
- data providers (none — baked into sidecar)

We do NOT touch `types/plugin.ts`. The registry is a new host module
(`src/lib/integrations/registry.ts`), exactly the way `PLUGIN_COMPANIONS`
(`plugin-bootstrap.ts:81`) adds host-side metadata that the locked contract
can't carry.

**Two view modes** (Fincept's `Gallery`/`Connections`, study-fincept §2):
- **Gallery** — "what can I connect", browse by category chip. Every registry
  entry renders as a connect card with icon, description, `instructions`
  markdown, and a `website` link.
- **Connections** — "what I've connected", status badge + Test + Disconnect.

### 1.2 The registry type (new file)

`src/lib/integrations/types.ts`:

```ts
export type IntegrationCategory = "broker" | "data" | "ai-provider" | "mcp";

export type IntegrationFieldType = "text" | "password" | "url" | "number" | "select";

export interface IntegrationFieldDef {
  key: string;                 // keychain field name, e.g. "api_key"
  label: string;
  type: IntegrationFieldType;  // drives input masking — fixes the heuristic in BrokerConnectPanel.tsx:401
  placeholder?: string;
  required: boolean;
  help?: string;               // inline per-field hint
  options?: { value: string; label: string }[]; // for "select"
}

/** Auth flow strategy. "loopback-oauth" is Kite; "static-token" is Dhan/Angel/Alpaca. */
export type IntegrationAuthFlow = "static-token" | "loopback-oauth" | "interactive-session";

export interface IntegrationSpec {
  id: string;                  // matches BrokerId for brokers, e.g. "kite"
  category: IntegrationCategory;
  label: string;
  icon: string;                // Lucide name
  blurb: string;               // one-line gallery subtitle
  description: string;         // full connect-card body
  website?: string;            // "get your key here" link
  instructions?: string;       // markdown, OpenBB-style how-to
  authFlow: IntegrationAuthFlow;
  fields: IntegrationFieldDef[];
  readOnly: true;              // Phase-10 hub is read-only-by-design; execution toggles live in the broker panel
  /** Daily-expiry warning copy for tokens that die at a fixed boundary (Kite). */
  dailyExpiry?: { boundaryLabel: string; note: string };
  /** Which sidecar id namespace this maps to. brokers → BrokerId. */
  testEndpoint?: string;       // e.g. "/brokers/kite/account" — used by the Test button
}
```

### 1.3 The registry entries (new file)

`src/lib/integrations/registry.ts` — the single declarative table. Brokers reuse
the field shapes already in `BrokerConnectPanel.tsx:40-86` but enriched with
`type`/`required`/`help`/`instructions`. Initial entries:

- **kite** (authFlow `loopback-oauth`): fields `api_key` (text, required),
  `api_secret` (password, required), `static_ip` (text, optional, help: "SEBI
  rule — order placement only; data/positions work from any IP"). NOTE:
  `access_token` is **removed from the form** — it's now minted by the OAuth
  flow, not pasted. `dailyExpiry: { boundaryLabel: "6:00 AM IST", note: "Kite
  resets your session daily — reconnect each trading morning." }`. `instructions`
  is the markdown from study-kite §A.2 (register an app at the Kite developer
  console, set redirect URL to `http://127.0.0.1:43117/kite/callback`).
- **dhan** (authFlow `static-token`): `client_id` (text), `access_token`
  (password). Mirrors `dhan.py:_connect:80-85`.
- **angelone** (authFlow `interactive-session`): `api_key`, `client_code`,
  `password` (password), `totp` (text, help: "current 6-digit code; enter
  immediately before connecting"). Mirrors `angelone.py:_connect:59-67`. NOTE:
  the existing UI field is `totp_secret` (`BrokerConnectPanel.tsx:49`) but the
  adapter expects a live `totp` code (`angelone.py:62`). **This is a real
  mismatch — the form sends a secret, the adapter wants the current code.** The
  registry fixes it to `totp`.

This registry is consumed by BOTH the new Settings section AND the existing
`BrokerConnectPanel` (which we refactor to read from it, killing the duplicated
`BROKER_CREDENTIAL_FIELDS` const at `BrokerConnectPanel.tsx:40`).

### 1.4 Hub UX surfaces

**A. Settings "Integrations" section** — add to `SettingsPanel.tsx`. Today it's
a flat 4-section page (`SettingsPanel.tsx:53-56`). Per study-fincept §4 the page
is about to cross the scroll-page threshold; but to keep blast radius minimal
this phase ADDS one section (`<IntegrationsSection />`) between Providers and
Layouts, NOT a left-rail rewrite (defer that to a later phase — Tier-3, noted).
The section renders a compact list grouped by category, each row a status pill +
"Connect"/"Manage" button that opens the connect card dialog. This is the
discoverable entry point onboarding points to (closes G4).

**B. Integrations dockview panel** — a new module
`src/modules/integrations/` with one panel `integrations-hub` giving the full
Gallery/Connections two-view experience. The existing `broker-connect` module
stays (it owns the execution-mode toggles — paper/live/read-only — which are NOT
part of the read-only hub). The hub LINKS to it: "manage execution mode →"
deep-links to the broker-connect panel.

**C. Connect card dialog** (`src/modules/integrations/ConnectCard.tsx`) — renders
`IntegrationSpec.fields` dynamically (one component, every integration), shows
`instructions` markdown + `website` link, masks `password` fields by `type` (not
the `field.key.includes("token")` heuristic at `BrokerConnectPanel.tsx:401`).
For `authFlow: "loopback-oauth"` it renders a **"Connect with Zerodha" button**
instead of an access_token field (see §2.4). For `static-token`/
`interactive-session` it renders the field list + a Connect button that writes
keychain then POSTs `/brokers/{id}/connect` (reusing `store/brokers.ts:connect`).

### 1.5 Connection status + the Test button

Per study-fincept §2 (`ConnectionTester`) and study-openbb §3.4 (provenance
envelope). Add a **Test** affordance: for brokers it calls the integration's
`testEndpoint` (`GET /brokers/{id}/account`) and shows "verified — N positions"
or the typed error. This is the difference between "I think my key works" and
"verified." No new sidecar route needed for brokers — `/account` already exists
(`brokers.py:171`).

### 1.6 Files for Part 1

Create:
- `src/lib/integrations/types.ts`
- `src/lib/integrations/registry.ts`
- `src/modules/integrations/index.ts` (VystedModule + panelComponents)
- `src/modules/integrations/IntegrationsHubPanel.tsx` (Gallery/Connections)
- `src/modules/integrations/ConnectCard.tsx`
- `src/modules/integrations/IntegrationStatusPill.tsx`

Modify:
- `src/components/SettingsPanel.tsx` — add `<IntegrationsSection />`.
- `src/modules/index.ts` — register `integrationsModule` (alongside
  `brokerConnectModule` at line 67).
- `src/modules/broker-connect/BrokerConnectPanel.tsx` — replace the local
  `BROKER_CREDENTIAL_FIELDS` (line 40) with a read from
  `src/lib/integrations/registry.ts`; mask by `field.type` not the substring
  heuristic; fix G6 (banner: read configured IP, mount in paper too).

---

## PART 2 — REAL KITE CONNECT (read-only)

### 2.1 The auth model and the secret-handling decision

Per study-kite §A.1/A.6 and the official docs: for desktop apps the
`api_secret` must NEVER reach the webview JS bundle, and the SHA-256 checksum
must run server-side. Vysted's keychain rule (CLAUDE.md, `keychain.rs`) says only
Tauri Rust can read the keychain. So:

**Decision: `api_secret` is Rust-only. The checksum and the `/session/token`
exchange both run in Rust. Only the resolved `access_token` crosses to the
sidecar — which is exactly what `KiteAdapter._connect` already expects
(`kite.py:76-77`).** This keeps the secret out of both the JS bundle AND the
sidecar process, and reuses the existing adapter contract verbatim (no
`_connect` change).

Rationale vs alternatives:
- Letting the sidecar do the exchange would require shipping `api_secret` to the
  Python process — avoidable, so avoid it (study-kite §A.6 step 4).
- The checksum is `SHA-256(api_key + request_token + api_secret)` hex digest
  (study-kite §A.3) — trivial in Rust with the `sha2` crate.

### 2.2 The redirect strategy: loopback localhost (chosen) vs alternatives

Per study-kite §A.6 (RFC 8252 §7.3) the three options are loopback localhost,
custom URL scheme, and manual paste. **Choose loopback localhost**, with manual
paste as an explicit fallback.

Justification (adversarial, from the study + verified env):
- **Loopback (chosen):** Rust spins a one-shot HTTP listener on a **pinned** port,
  opens the system browser to Kite's login URL, captures `request_token` from the
  redirect. System browser → real 2FA + password managers work. Kite's console
  requires an exact redirect URL match (study-kite §A.6 Option 1 con), so we
  **pin** `http://127.0.0.1:43117/kite/callback` (a high, unlikely-to-collide
  port the user registers once in the Kite developer console). Zero copy-paste.
- **Custom scheme (rejected):** RFC 8252 warns custom schemes are interceptable
  by other apps; Kite doesn't implement PKCE to mitigate; and Kite-console
  support for custom-scheme redirects is uncertain (study-kite §A.6 Option 2).
- **Manual paste (fallback only):** ugly and error-prone, but works with any
  redirect config and no platform plumbing. Keep it behind a "trouble
  connecting?" link for users whose corporate firewall blocks the loopback bind
  or who can't register the pinned port (study-kite §A.6 Option 3 / step 6).

We do NOT add `tauri-plugin-oauth` (G8) — a self-contained `std::net::TcpListener`
one-shot loopback in Rust is ~40 lines, has zero new crate-supply-chain surface,
and matches the existing in-house `pick_free_port`/`wait_for_port` style in
`lib.rs:23-51`. Adding a plugin crate for one flow is over-engineering.

### 2.3 New Rust module: `src-tauri/src/kite_auth.rs`

Self-contained. Three Tauri commands + a one-shot loopback listener. Add to the
`mod` list (`lib.rs:1-4`) and the `invoke_handler!` (`lib.rs:127-135`). Add `sha2`
+ `reqwest` (blocking, rustls) + a tiny `urlencoding`/manual query parse to
`Cargo.toml` deps; or reuse `tauri_plugin_shell`'s opener for the browser open
(`opener` is already transitively available via Tauri 2 — confirm at build; else
use the `open` crate). Pinned redirect port constant: `const KITE_REDIRECT_PORT:
u16 = 43117;`.

```rust
//! Kite Connect OAuth — desktop loopback flow. api_secret never leaves Rust.

#[tauri::command]
pub async fn kite_begin_login() -> Result<KiteLoginResult, String> {
    // 1. Read api_key + api_secret from keychain (broker:kite:api_key / :api_secret).
    //    Use the same keyring::Entry(SERVICE="vysted-terminal", account) as keychain.rs.
    // 2. Bind a one-shot TcpListener on 127.0.0.1:43117 (KITE_REDIRECT_PORT).
    //    On bind failure -> Err("loopback_unavailable") so the FE shows manual-paste fallback.
    // 3. Open system browser to:
    //      https://kite.zerodha.com/connect/login?v=3&api_key=<api_key>
    // 4. Block (on a worker thread, bounded ~180s) for ONE GET request; parse
    //    request_token from the query string; serve a "you can close this tab" HTML.
    // 5. checksum = sha256_hex(api_key + request_token + api_secret).
    // 6. POST (form-encoded) https://api.kite.trade/session/token with
    //      api_key, request_token, checksum  (header X-Kite-Version: 3)
    //    -> parse data.access_token, data.user_id, data.login_time.
    // 7. Store broker:kite:access_token + broker:kite:_meta:login_time (epoch ms, IST-aware)
    //    in keychain via the same keyring path.
    // 8. Return { userId, loginTimeMs } to the FE (NEVER the access_token or secret).
}

/// Manual-paste fallback: FE collected request_token via the system browser.
#[tauri::command]
pub async fn kite_exchange_request_token(request_token: String) -> Result<KiteLoginResult, String> {
    // Same as steps 5-8 above, skipping the listener. api_secret stays in Rust.
}

/// Launch-time + on-demand staleness check (study-kite §A.4).
#[tauri::command]
pub async fn kite_session_status() -> Result<KiteSessionStatus, String> {
    // Read broker:kite:access_token + :_meta:login_time.
    // stale = login_time is before the most recent 06:00 IST boundary, OR token absent.
    // Return { connected: bool, stale: bool, userId: Option<String>, loginTimeMs: Option<i64> }.
    // This lets the FE render "tap to reconnect" without a network round-trip.
}
```

`KiteLoginResult { user_id: String, login_time_ms: i64 }`,
`KiteSessionStatus { connected: bool, stale: bool, user_id: Option<String>,
login_time_ms: Option<i64> }` — `#[derive(serde::Serialize)]`.

The 6:00 AM IST boundary math: compute "most recent 06:00 Asia/Kolkata instant
≤ now"; if `login_time_ms < that`, the token is stale. IST is UTC+5:30 with no
DST, so this is pure arithmetic (no tz crate needed): `boundary_utc =
floor_to_06_00_minus_0530(now)`.

### 2.4 Frontend Kite OAuth wiring

New `src/lib/integrations/kite-auth.ts` — thin `invoke()` bindings:
```ts
export const kiteBeginLogin = () => invoke<KiteLoginResult>("kite_begin_login");
export const kiteExchangeRequestToken = (requestToken: string) =>
  invoke<KiteLoginResult>("kite_exchange_request_token", { requestToken });
export const kiteSessionStatus = () => invoke<KiteSessionStatus>("kite_session_status");
```

New `src/store/kite-session.ts` (Zustand) — holds `{ connected, stale, userId,
loginTimeMs }`, refreshed on app mount + after any 403/TokenException from a Kite
read route (§2.6). The ConnectCard for Kite (§1.4-C) renders:
1. api_key + api_secret fields (written to keychain via `setSecret` using
   `KEYCHAIN_NAMESPACES.broker("kite", "api_key"|"api_secret")` —
   `keychain.ts:46`).
2. **"Connect with Zerodha"** → `kiteBeginLogin()` → on success calls
   `store/brokers.ts:connect("kite", {})` with EMPTY credentials body. The sidecar
   `_connect` then needs the resolved api_key + access_token — see §2.5 for how
   the sidecar gets them (renderer reads keychain, passes in the connect body,
   per the CLAUDE.md "renderer reads keychain → passes secret in request"
   pattern). So actually: FE reads `api_key` + the freshly-minted `access_token`
   from keychain via `getSecret`, and passes BOTH in the connect body.
   `api_secret` is NOT passed (sidecar doesn't need it).
3. A "trouble connecting?" link → manual-paste fallback: opens the login URL,
   user pastes the redirected URL, FE extracts `request_token`, calls
   `kiteExchangeRequestToken`.

Daily re-auth UX (study-kite §A.4): the Kite row in BOTH the hub and
`BrokerConnectPanel` shows a **"Session expired — reconnect"** chip when
`kiteSessionStatus().stale`. Reconnect = re-run `kiteBeginLogin()` only (api_key
+ api_secret already in keychain). One tap, system browser, done. The panel
greys-but-keeps the last-known account identity (`userId`) so the UI doesn't go
blank.

### 2.5 Sidecar Kite adapter changes (NOT locked)

`kite.py` is NOT a §6.5 locked file. Changes (closing G3 + study-kite §A.5
account-read bugs):

**A. Fix equity/buying-power (`kite.py:190-202`).** Currently equity = cash =
buyingPower = `available.cash`. Per study-kite §A.5: use `equity.net` for
buyingPower, keep `available.cash` for the cash line:
```python
equity_block = (margins or {}).get("equity") or {}
available = equity_block.get("available") or {}
net = float(equity_block.get("net") or 0.0)
cash = float(available.get("cash") or 0.0)
return AccountSummary(
    broker="kite", accountId=self._account_id, currency="INR",
    equity=net, cash=cash, buyingPower=net,
    positions=_translate_kite_positions_and_holdings(positions, holdings),
    capturedAt=int(time.time() * 1000),
)
```

**B. Fetch positions, not just holdings (`kite.py:184-185`).** Add
`positions = await asyncio.to_thread(self._client.positions)` and merge the
`net` array (study-kite §A.5 — F&O/intraday positions are invisible today). New
helper `_translate_kite_positions_and_holdings`: holdings → long-term equity;
positions["net"] → intraday/F&O, mapping `pnl`/`last_price`/`average_price`/
`quantity` into `BrokerPosition` (the model at `models/broker.py:97-106`).

**C. Catch `TokenException` → typed "session expired" (study-kite §A.4/§A.8).**
Wrap the margins/positions/holdings calls; on
`kiteconnect.exceptions.TokenException` (HTTP 403) raise
`BrokerError("kite: session expired — reconnect (daily token expiry)")` with a
recognisable prefix the route maps to a 419-style payload (§2.6). The existing
generic `except Exception` (`kite.py:186-187`) stays as the fallback.

These are pure adapter-internal changes; `_connect`'s signature is unchanged
(still `api_key` + `access_token`), so the OAuth flow in Rust + the existing
connect body path (§2.4) feed it exactly what it already expects.

### 2.6 New granular read-only routes (closing G2)

`brokers.py` is NOT locked. Add THREE `GET` routes mirroring Kite's REST surface
(study-kite §A.5) — these are read-only by construction (no `_place_confirmed`,
no audit mutation; `account_info` path is already audit-free at
`broker_base.py:215-217`):

```python
@router.get("/{broker_id}/positions")   # net + day arrays for Kite; holdings-as-positions for Dhan/Angel
async def get_broker_positions(broker_id: BrokerId) -> AccountSummary: ...

@router.get("/{broker_id}/holdings")     # long-term holdings only
async def get_broker_holdings(broker_id: BrokerId) -> AccountSummary: ...

@router.get("/{broker_id}/margins")      # funds/buying-power only (no positions)
async def get_broker_margins(broker_id: BrokerId) -> AccountSummary: ...
```

To keep these read-only-by-construction AND avoid widening the LOCKED ABC, add
THREE optional read hooks to the adapter base via **duck-typing in the router**
(not new abstract methods — that would touch `broker_base.py`). The router checks
`hasattr(adapter, "positions_info")` and falls back to `account_info()` when the
adapter doesn't implement the granular split:
```python
adapter = _get_adapter(broker_id)
fn = getattr(adapter, "positions_info", None)
return await (fn() if callable(fn) else adapter.account_info())
```
Then implement `positions_info`/`holdings_info`/`margins_info` as NEW
(non-abstract, non-overriding) public methods ONLY on `KiteAdapter` (and later
Dhan/Angel). Because they don't exist on the locked ABC, adding them is a
subclass-only change. They are reads; they never call `_place_confirmed`.

Also add the **session-expired translation** in these routes + `/account`:
catch `BrokerError` whose message starts with `kite: session expired` and return
`HTTPException(status_code=419, detail="kite-session-expired")` so the FE
`kite-session` store flips `stale=true` and shows the reconnect chip instead of a
red error (study-kite §A.4 #1).

**Fix G5 (disconnect route).** Add `POST /brokers/{id}/disconnect` that flips
`adapter._connected = False` and clears the cached client (Kite/Dhan/Angel:
`self._client = None`). This is a state reset, not an order — safe, non-locked.
The FE `store/brokers.ts:disconnect` (line 94) already calls it.

### 2.7 Read-only positions/P&L panel + copilot feed

**A. Panel.** The new Integrations hub's Connections view already shows account
state via the Test/refresh path. Additionally surface a **dedicated read-only
P&L panel** by reusing the existing portfolio module pattern — but to avoid
scope creep, the cleanest move is: the `integrations-hub` panel's "Connections"
tab, when a broker is connected, renders an inline `BrokerAccountView`
(positions table + equity/cash/buyingPower header + per-position unrealized P&L)
driven by `GET /brokers/{id}/positions`. New component
`src/modules/integrations/BrokerAccountView.tsx`, polling every ~5s (well within
Kite's 10 req/s limit — study-kite §A.8) and pausing when stale.

This view also **publishes to the panel-context bus** (`store/panel-context.ts`,
`publish({ source: "broker-account", ... })`) so the copilot's context preamble
(`agent_runtime.py:133-150` `_build_context_preamble`) sees the live portfolio —
matching the existing publisher pattern (portfolio is a documented publisher,
`panel-context.ts:16`).

**B. Copilot tool (closing G9).** Add a read-only agent tool
`broker_portfolio` so an agent can pull the REAL portfolio on demand (not just
the preamble snapshot). New file
`sidecar/services/agent_tools/broker_portfolio.py`, registered via the existing
`register_v0_5_0_tools` pattern (`agent_tools/price_data.py` is the template;
`__init__.py:106-117`). Handler:
```python
async def _broker_portfolio(args: dict) -> dict:
    broker = args.get("broker", "kite")
    from services.brokers import registry as brokers_registry
    try:
        adapter = brokers_registry.get(broker)
    except KeyError:
        return {"ok": False, "error": f"broker {broker!r} not connected"}
    try:
        summary = await adapter.account_info()   # READ ONLY — no order path
    except BrokerError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "account": summary.model_dump(by_alias=True)}
```
Register it in `__init__.py`'s `register_v0_5_0_tools` (and in
`reset_for_tests` re-registration list per the CLAUDE.md gotcha about
import-time tools). Add `"broker_portfolio"` to the relevant agents' `tools`
allow-list (e.g. `portfolio_advisor.json`) so it's exposed only where intended
(`AgentSpec.tools` allow-list, `agent_runtime` `is_registered` gate). This is a
READ tool — it can NEVER place an order; per study-openbb §4.3 + the LOCKED
two-step, action tools that touch a broker must emit a `propose_order` proposal,
never call `_place_confirmed`. This tool calls neither — it's pure `account_info`.

Now the copilot can answer "is my Zerodha portfolio overexposed to one sector?"
over the user's REAL holdings.

### 2.8 Static-IP banner fixes (closing G6)

In `BrokerConnectPanel.tsx`: (1) fetch `GET /brokers/kite/static-ip`
(`brokers.py:293`) and pass the real `configuredIp` to `<KiteStaticIpBanner>`
instead of `null` (line 254); (2) mount the banner regardless of mode (drop the
`state.mode === "live"` guard at line 252) per `BROKER_INTEGRATIONS.md:62-65`;
(3) the banner copy must say **"read-only panels keep working on any IP — only
order placement needs the registered static IP"** (study-kite §A.7 refinement),
so users don't think their whole Kite connection is broken on an IP mismatch.

### 2.9 Files for Part 2

Create:
- `src-tauri/src/kite_auth.rs`
- `src/lib/integrations/kite-auth.ts`
- `src/store/kite-session.ts`
- `src/modules/integrations/BrokerAccountView.tsx`
- `sidecar/services/agent_tools/broker_portfolio.py`
- `sidecar/tests/test_brokers_readonly_routes.py` (new read routes + 419 mapping;
  asserts no non-GET added route mutates state — mirrors the v0.6.5 read-only
  router audit pattern in CLAUDE.md)
- `sidecar/tests/test_kite_account_readonly.py` (equity=net, positions merged,
  TokenException → session-expired BrokerError)

Modify:
- `src-tauri/src/lib.rs` — `mod kite_auth;` + 3 commands in `invoke_handler!`.
- `src-tauri/Cargo.toml` — add `sha2`, `reqwest` (rustls, blocking) or reuse an
  existing HTTP client; add browser-open dep if `opener` isn't transitively
  available.
- `sidecar/services/brokers/kite.py` — equity/positions/TokenException (§2.5);
  add `positions_info`/`holdings_info`/`margins_info` public read methods.
- `sidecar/routers/brokers.py` — 3 GET read routes + disconnect + 419 mapping.
- `sidecar/services/agent_tools/__init__.py` — register `broker_portfolio`.
- `sidecar/agents/portfolio_advisor.json` — add `broker_portfolio` to `tools`.
- `src/modules/broker-connect/BrokerConnectPanel.tsx` — G6 banner fixes + Kite
  ConnectCard uses OAuth not access_token paste.

---

## PART 3 — THE SHARED CONTRACT FOR DHAN + ANGEL (read-only, identical slot-in)

### 3.1 The contract is already 90% there — formalize it

The §6.5 ABC (`broker_base.py:461-480`) already gives every broker the same four
abstract methods, and Dhan/Angel/Kite already implement `_account_info`
(`dhan.py:104`, `angelone.py:87`, `kite.py:170`). The read-only hub needs only:

1. **Registry entry** in `src/lib/integrations/registry.ts` (§1.3) — Dhan + Angel
   already enumerated there with their real credential fields.
2. **`authFlow` per broker**: Dhan = `static-token` (long-lived console token,
   `dhan.py:73-85`); Angel = `interactive-session` (api_key + client_code +
   password + live TOTP → `generateSession`, `angelone.py:51-85`); Kite =
   `loopback-oauth`. The ConnectCard branches on `authFlow` (§1.4-C) — Dhan/Angel
   take the static field-list path (write keychain → POST `/connect`), Kite takes
   the OAuth-button path. **No per-broker bespoke UI** — the field list +
   authFlow drive everything.
3. **Granular read methods** (§2.6): implement `positions_info`/`holdings_info`/
   `margins_info` on `DhanAdapter` + `AngelOneAdapter` too, splitting their
   existing `_account_info` SDK calls (`dhan.py:126-127` `get_holdings`/
   `get_fund_limits`; `angelone.py:102-103` `rmsLimit`/`holding`). Until then the
   router's `hasattr` fallback (§2.6) serves `account_info()` for all three —
   so Dhan/Angel work in the hub on day one even before the granular split lands.

### 3.2 The credential/keychain/header flow (uniform across all three)

This is the load-bearing reuse story. The flow is IDENTICAL for Dhan/Angel/Kite
static fields, and Kite's OAuth is the only special case:

```
Static-token / interactive-session (Dhan, Angel):
  ConnectCard collects fields
    → setSecret(KEYCHAIN_NAMESPACES.broker(id, field), value)   [keychain.ts:46, Rust-only store]
    → store/brokers.ts:connect(id, fieldsAsBody)                [brokers.ts:78-92, BODY not header]
    → POST /brokers/{id}/connect  { credentials: {...} }        [brokers.py:153-168]
    → adapter._connect(credentials)                              [dhan/angelone _connect]

Loopback-OAuth (Kite):
  ConnectCard collects api_key + api_secret
    → setSecret(broker:kite:api_key / :api_secret)               [api_secret stays for Rust ONLY]
    → "Connect with Zerodha" → invoke("kite_begin_login")        [Rust: loopback + checksum + exchange]
        → Rust mints access_token, stores broker:kite:access_token  [keychain]
    → FE getSecret(broker:kite:api_key) + getSecret(broker:kite:access_token)
    → store/brokers.ts:connect("kite", { api_key, access_token }) [reuses the SAME connect path]
    → adapter._connect({api_key, access_token})                  [kite.py:69-102, UNCHANGED]
```

Note the **connect body vs header** distinction (CLAUDE.md): broker connect uses
the request BODY (`brokers.ts:84-86`, `BrokerConnectRequest.credentials`,
`models/broker.py:138-149`), NOT headers. The header pattern is specific to the
Tradesa V2 read-only wrapper; broker execution-adapters use the body. Keep it.
Transport is loopback-only (sidecar binds 127.0.0.1); secrets are never logged
or echoed (the v0.6.5 `test_response_never_echoes_credentials` audit pattern
should extend to the new connect/read routes).

### 3.3 Daily-token handling per broker

- **Kite**: daily 6 AM IST expiry, NO silent refresh (study-kite §A.4). Handled
  by §2.3 `kite_session_status` (launch-time staleness) + §2.6 419 mapping +
  §2.4 reconnect chip. This is the ONLY broker with a daily interactive re-auth.
- **Dhan**: `access_token` is a long-lived console-issued bearer
  (`dhan.py:77-78`) — no daily dance. Re-auth only when the user rotates it in
  the Dhan console. The hub surfaces a generic "connection failed — re-enter
  token" on 401, no special staleness clock.
- **Angel One**: `generateSession` mints a session from a LIVE TOTP
  (`angelone.py:76`); the session token has its own (multi-hour) lifetime and a
  `refreshToken` (`angelone.py:84`). For the read-only hub, treat an Angel auth
  failure like Dhan's: prompt re-connect (which re-collects a fresh TOTP). A
  silent `refreshToken` flow is a later-phase enhancement (noted Tier-3, not
  built — keeps execution out and scope tight).

So the registry's `dailyExpiry` field is set ONLY for Kite; Dhan/Angel leave it
undefined and the UI shows no daily clock for them. One declarative field, three
correct behaviours.

### 3.4 Files for Part 3

Modify (no new files — pure reuse + registry entries):
- `src/lib/integrations/registry.ts` — Dhan + Angel entries (done in §1.3).
- `sidecar/services/brokers/dhan.py` — add `positions_info`/`holdings_info`/
  `margins_info` (split existing `_account_info` SDK calls).
- `sidecar/services/brokers/angelone.py` — same split.
- `sidecar/tests/test_brokers_readonly_routes.py` — parametrize over
  dhan/angelone/kite to prove identical slot-in.

(Dhan + Angel need NO Rust changes — only Kite has the OAuth special case.)

---

## 4. What is explicitly OUT of scope (guardrails)

- **No order execution.** Zero new `_place_confirmed` call sites. Every new route
  is GET or a token/connection POST. The `propose_order → confirm_and_place`
  two-step (`broker_base.py:223-394`) is reused as-is for the existing manual
  order-entry panel; this track adds nothing to it.
- **No §6.5 file edits.** Verified the locked set is untouched: the new read
  routes use duck-typed `hasattr` rather than new ABC abstract methods; the new
  `broker_portfolio` agent tool calls `account_info()` (read) not the order path;
  the kill-switch/audit/disclaimer files are not referenced by new code beyond
  the existing adapter inheritance.
- **No `types/plugin.ts` change.** The integration registry is host-side TS,
  mirroring `PLUGIN_COMPANIONS`.
- **No Kite as a market-data feed.** Per study-kite §A.7 (Zerodha's "execution
  platform only" stance) Kite is used for the user's OWN account state only; live
  quotes/candles keep flowing from Vysted's existing data layer (yfinance/OpenBB).
- **No Settings left-rail rewrite** (Tier-3, deferred): add one section now;
  full IA restructure when sections exceed ~8.
- **No silent Angel `refreshToken` flow** (Tier-3, deferred).

## 5. Build order (for the lead)

1. **Sidecar reads first** (no UI dependency): kite.py equity/positions/
   TokenException fix; granular `*_info` methods on kite/dhan/angel; 3 GET routes
   + disconnect + 419 mapping; `broker_portfolio` tool + agent allow-list. Tests:
   `test_kite_account_readonly.py`, `test_brokers_readonly_routes.py`. Run
   `pnpm ci-local` (ruff/pytest gate per CLAUDE.md).
2. **Rust OAuth**: `kite_auth.rs` + 3 commands + Cargo deps. `cargo clippy -D
   warnings` + `cargo test`.
3. **Frontend registry + hub**: `integrations/` lib + module + Settings section +
   ConnectCard + BrokerAccountView + kite-session store. Refactor
   `BrokerConnectPanel` to the registry; fix G6 banner.
4. **Wire-through verification**: connect Kite via loopback (lead runs the GUI —
   I'm headless), confirm positions/P&L render populated (per the visual protocol:
   AAPL-anchor analogue → use a real INR holding), confirm the copilot answers a
   portfolio question over the live account, confirm the daily-stale chip after a
   simulated stale `login_time`.

## 6. File:line index used to author this blueprint

- Kite adapter: `sidecar/services/brokers/kite.py` (connect :69-102, account
  :170-202 equity bug :190-202, place :208, holdings translate :298)
- Brokers router: `sidecar/routers/brokers.py` (account read :171, connect :153,
  kite static-ip :293/:302, no disconnect route)
- Broker models: `sidecar/models/broker.py` (BrokerId :24-35, AccountSummary
  :109-121, BrokerPosition :97-106, BrokerConnectRequest :138-149)
- LOCKED ABC (read-only): `sidecar/services/broker_base.py` (abstract surface
  :461-480, propose :223, confirm :310, account_info audit-free :215-217)
- Dhan adapter: `sidecar/services/brokers/dhan.py` (connect :73-98, account
  :104-146)
- Angel adapter: `sidecar/services/brokers/angelone.py` (connect/generateSession
  :51-85, account :87-118, TOTP-code-not-secret :62)
- Registry/bootstrap: `sidecar/services/brokers/registry.py:97-112`;
  `sidecar/app.py:186-191`
- Keychain (Rust): `src-tauri/src/keychain.rs` (service name :16, set/get :18-42)
- Tauri lifecycle + free-port/wait helpers + command registration:
  `src-tauri/src/lib.rs` (mod list :1-4, free-port :23-29, wait :42-56,
  invoke_handler :127-135, setup :136)
- Rust subprocess-spawn reference pattern: `src-tauri/src/openbb_mcp.rs`
- Cargo deps (no oauth/deep-link/sha2 yet): `src-tauri/Cargo.toml`
- Keychain (frontend): `src/lib/keychain.ts` (broker namespace :46, set/get
  :50-58)
- Brokers store: `src/store/brokers.ts` (connect body :78-92, missing-route
  disconnect :94-104)
- Broker panel: `src/modules/broker-connect/BrokerConnectPanel.tsx` (fields :40,
  api_secret :53, totp_secret mismatch :49, banner null/live-only :252-254,
  mask heuristic :401)
- Broker module: `src/modules/broker-connect/index.ts`; `src/modules/index.ts:67`
- Settings: `src/components/SettingsPanel.tsx` (sections :53-57, ProvidersSection
  :68)
- Plugin bootstrap + host-side glue precedent: `src/lib/plugin-bootstrap.ts`
  (BUNDLED_PLUGINS :45-49, PLUGIN_COMPANIONS :81-83, HOST_VERSION :39)
- Plugin contract (read-only): `types/plugin.ts` (PluginCapabilities,
  DataSource, AgentSpec, PluginConfig.secrets)
- Panel-context bus: `src/store/panel-context.ts` (publish :41, portfolio
  publisher noted :16)
- Copilot context preamble: `sidecar/services/agent_runtime.py:133-150`,
  compose :158-164, context arg :231-259
- Agent tool template + registration: `sidecar/services/agent_tools/price_data.py`;
  `sidecar/services/agent_tools/__init__.py:106-141`
- Safety static-ip route: `sidecar/routers/safety.py:186-193`
- Dead broker plugins (not bundled): `plugins/brokers/kite/index.ts:48-60`
