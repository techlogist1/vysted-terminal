# R15 CENSUS — Code critique: `brokers-adapters`

**Subsystem:** Broker Adapters (Read-Only Wrapper Layer) · 38 files · 7,766 LOC · 26 test files
**Method:** `aposd-critique` skill (loaded), two personas run sequentially in one context —
**assessment independence: degraded (no sub-agent isolation)**. Every verdict carries `file:line`.
**Snapshot persistence:** skipped deliberately (the run writes only the two census artifacts).

---

## Tactical Tornado verdict

**Risk: HIGH.** This subsystem reads as seven adapters written fast, in parallel, against a
well-designed ABC — and then a read-only layer, a granular-reads layer and a UI bolted on top
without anyone re-reading the layer below. The ABC itself (`broker_base.py`) is genuinely good
work. Almost everything above and beside it drifted.

The most damning pattern is not any single bug but **the same fact spelled three different ways
in three files, with only one spelling correct**:

- the connect request body: correct in `plugins/brokers/kite/index.ts:174-177`, wrong in
  `src/store/brokers.ts:80-87` (COD-2 — the Connect button 422s for every broker);
- the Angel One credential names: `pin`/`totp_secret` in
  `BrokerConnectPanel.tsx:48-53`, `password`/`totp` in `angelone.py:59-67` (COD-3);
- the static-IP configured value: fetched properly in `plugins/brokers/kite/index.ts:226-230`,
  hardcoded `null` in `BrokerConnectPanel.tsx:270` (COD-11);
- optionality: `error?: string` in `types/broker.ts:211` vs `error: str | None` in
  `models/broker.py:134` → a permanent red `err:` on every row (COD-10).

Four instances of the same failure mode. The tornado signature is that **each copy has a test
that passes** — `src/store/brokers.test.ts:108-114` stubs `fetch` and never inspects the body it
sent, `kite-static-ip-banner.test.tsx` passes a real IP the panel never passes, and every broker
plugin's test pins `supportsControlPlane` to the value the plugin happens to have rather than the
value the safety doc claims. The tests lock in the drift instead of catching it.

Patterns the Strategic Thinker pass did not surface on its own, which the red-flag scan found:

- `ccxt_exec.py:245,340,384` — blocking network calls on the event loop while all six siblings
  use `asyncio.to_thread` (COD-6);
- `routers/brokers.py:249-251` — the router assigning `adapter._client` by name, already wrong
  for IB (COD-12);
- `_translate_kite_margins` (`kite.py:476-485`) — `sum()` over a dict whose keys overlap (COD-1),
  the one finding here that shows a user a false number about their own money.

---

## Design principles score

| # | Principle | Verdict | Evidence (`file:line`) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | **violate** | Four independent re-spellings of one contract: `src/store/brokers.ts:85` vs `plugins/brokers/kite/index.ts:176`; `BrokerConnectPanel.tsx:48-53` vs `angelone.py:59-67`; `BrokerConnectPanel.tsx:270` vs `plugins/brokers/kite/index.ts:226`; `types/broker.ts:211` vs `models/broker.py:134` | Every UI entry point into the subsystem is dead or misleading; working copies exist one file over |
| 2 | Deep modules | **pass** | `broker_base.py:223-394` — `propose_order` + `confirm_and_place` hide kill-switch, read-only, limits, audit and SDK translation behind a two-call interface; seven adapters implement four private methods (`:461-480`) | Real depth; adding a broker is ~250 lines and inherits the whole safety envelope |
| 3 | Information hiding | **violate** | `routers/brokers.py:249-251` `adapter._client = None; adapter._connected = False` — the route hardcodes adapter internals, and IB stores its socket in `_ib` (`ib.py:101`) | Disconnect silently no-ops for IB: zombie TWS sessions, clientId still claimed (COD-12) |
| 4 | Information leakage (duplicated truth) | **violate** | `types/broker.ts` and `types/broker-reads.ts` are hand-maintained mirrors of `models/broker.py` / `models/broker_reads.py`; the `error?:` vs `str \| None` drift at `types/broker.ts:211` is the first one to bite (`BrokerConnectPanel.tsx:266`) | Permanent false error badge on every broker row (COD-10) |
| 5 | General vs special purpose | **at-risk** | `routers/brokers.py:192-203` `_read_granular` duck-types `getattr(adapter, "positions_info")`; only `kite.py:241-280` defines them | Six of seven brokers render "no granular read" though `alpaca.py:134`, `ib.py:170`, `oanda.py:136`, `ccxt_exec.py:255` all fetch real positions (COD-5) |
| 6 | Different layer, different abstraction | **violate** | `AccountSummary` (`models/broker.py:109-121`) has no provenance; `BrokerReadProvenance` (`models/broker_reads.py:30-47`) does. The doc at `broker_reads.py:13-15` promises "every result" carries it | The one model that carries money is the one without the label; paper mode serves ₹10,00,000 as real (COD-4) |
| 7 | Pull complexity downward | **at-risk** | `broker_base.py:262-273` pushes market-order sizing to "the broker is expected to reject grossly-oversized market orders too" | The §6.5 #3 limit is a no-op for market orders — a local guarantee converted into a remote hope (COD-7) |
| 8 | Define errors out of existence | **violate** | `models/broker.py:105` `market_value: float` is required, so `ccxt_exec.py:268` and `ib.py:203` must write `0.0` for "unknown" | A 1-BTC account reads as zero equity, every position as worthless (COD-14). `float \| None` would define the case away |
| 9 | Exception aggregation | **violate** | `routers/brokers.py:205-212` catches only `BrokerError`; `alpaca.py:133-134` and `ib.py:169-170` raise raw SDK errors. The sibling `connect_broker` (`:179-180`) does have the `except Exception → 502` arm | Expired token → unhandled 500 → browser reports "CORS policy" (the trap CLAUDE.md documents) (COD-13) |
| 10 | Consistency | **violate** | `asyncio.to_thread` in `alpaca.py:117,133`, `kite.py:192-194`, `dhan.py:126`, `angelone.py:102`, `oanda.py:108` — absent in `ccxt_exec.py:245,340,384` | One slow exchange call freezes the whole sidecar event loop, against the ≤2 s kill-switch latency claim at `alpaca.py:42-43` (COD-6) |
| 11 | Pass-through variables | **violate** | `currency` defaults to `"INR"` at `routers/brokers.py:76` and `"USD"` at `broker_base.py:233`; compared unconverted against `10_000.0` (`broker_base.py:269`); lands in `Stock(..., proposal.currency)` at `ib.py:229` | Same nominal limit means ₹10k or $10k depending on entry point; IB gets an INR-denominated US contract (COD-8) |
| 12 | Comments say what code cannot | **at-risk** | `broker_reads.py:13-15`, `types/broker.ts:6-30` and `broker_base.py:20-33` assert invariants; `kite.py:465-469` describes a margins model the code then gets wrong | The comments describe the intended system, not the built one — a reader who trusts them is misled (COD-1, COD-4, COD-15) |
| 13 | Naming | **at-risk** | The public order method is `confirm_and_place` (`broker_base.py:310`) — a prefix audit for `place_/submit_/execute_` passes it | The guard's shape is satisfiable without the guarantee holding (COD-15) |
| 14 | Obviousness | **at-risk** | `kite.py:476-485` `sum(block.values())` over overlapping keys; `ib.py:188-189` `if ... == "AccountType": pass` (dead branch); `BrokerConnectPanel.tsx:290,293` "Connecting…" state that `broker_base.py:125` never emits | Each reads as intentional and is not; reviewers skim past them |
| 15 | Temporal decomposition | **pass** | `broker_base.py` is organised by responsibility (state / mode / lifecycle / orders / kill-switch), not call order | Adding the granular reads (`kite.py:241-280`) needed no reshuffle of the ABC |
| 16 | Pass-through methods | **pass** | `account_info` (`broker_base.py:215-217`) is a one-liner but is the documented no-audit-row seam; everything else wraps real policy | Acceptable; the wrapper is where the audit/gate decision lives |
| 17 | Better together / better apart | **pass** | One `CcxtExecutionAdapter` parametrised by exchange (`ccxt_exec.py:107-146`) instead of four near-identical classes; `_synthetic_paper_result` shared by dhan/angelone/kite (`dhan.py:220`) | Correct merge — the four ccxt brokers differ only in a capability bit and a quote currency |
| 18 | Design it twice | **at-risk** | Granular reads were designed once, for Kite, and bolted on via `getattr` rather than through the ABC (`routers/brokers.py:198`) | The second design (a default `positions_info` on the ABC) would have given all seven brokers the feature for ~10 lines (COD-5) |

**Summary: 4 pass, 7 at risk, 7 violate — 4/18 pass.**

---

## Overall impression

`broker_base.py` is the best file in this subsystem and one of the better files in the repo: a
genuinely deep module where the entire §6.5 envelope — kill-switch subscription forced in
`__init__:103`, paper default at `:94`, audit rows on every state transition, the
`human_confirmed` gate at `:325` — is structural rather than conventional. Seven adapters ride it
and none of them can accidentally skip it.

Everything the redesign added *around* that core is where the rot is. The granular-read layer, the
provenance label, the OAuth session route and the read-only story were each built correctly in
one place and then not wired, not mirrored, or not enforced. The result is a subsystem where the
foundation is sound and **the user cannot reach it**: the Connect button 422s, Angel One's
credentials are misnamed, Kite's real login exchange has no caller, and the one broker that does
have granular reads shows a 2.4x-inflated margin figure.

Single biggest opportunity: stop hand-mirroring contracts. Four of the fifteen findings are one
failure mode — a wire contract written twice and drifting. `types/broker.ts` and
`types/broker-reads.ts` are mirrors maintained by a CLAUDE.md rule; the request bodies are
mirrors maintained by nothing at all.

---

## What's working

1. **The safety envelope is architectural, not conventional.** `broker_base.py:100-103`
   subscribes to the kill-switch bus in the constructor, so an adapter *cannot exist* unsubscribed;
   `:325-340` makes a declined proposal an audited event rather than a silent return; `:342-350`
   re-checks both gates in the propose→confirm window. That last re-check is the kind of detail
   that only shows up when someone thought about the failure, not just the happy path.

2. **The ccxt merge and the per-broker split are both the right call.** One
   `CcxtExecutionAdapter` parametrised at `ccxt_exec.py:128-141` covers four exchanges that differ
   only in a futures bit and a quote currency, while Kite/Dhan/Angel One stay separate because
   their session models genuinely differ. `dhan.py:215-217` even writes down *why* the shared
   helpers stayed local. That is a deliberate together/apart decision, made twice.

3. **The 419 session-expiry mapping.** `kite.py:498-504` types the daily token expiry distinctly
   and `routers/brokers.py:184-189` turns it into a 419 so the UI can show "reconnect" instead of a
   generic red error. Small, cheap, and exactly the kind of thing that separates a terminal from a
   demo — it is a shame it is the only adapter that gets it (COD-13).

---

## Priority issues

### [P0] Kite margins double-counts — the terminal states a false number about the user's money

- **Principle**: obviousness / comments that mis-describe the code
- **Symptom**: unknown unknowns — nothing in the UI hints the figure is derived
- **Evidence**: `sidecar/services/brokers/kite.py:476-485`, rendered at
  `src/modules/broker-connect/BrokerReadsSection.tsx:295`
- **Proof (run from `sidecar/`)**: `_translate_kite_margins` on the documented Kite payload returns
  `available=590588.25, used=287439.10`; the true values are `245431.60` and `145706.55`.
- **Why it matters**: Kite's `available` map holds several *views* of one balance (`cash`,
  `opening_balance`, `live_balance`) and `utilised.debits` is itself the sum of its siblings.
  `sum(values())` therefore double- and triple-counts. The user sees ~2.4x their real buying power
  behind a green `LIVE · kite` badge. This is the single finding that would, on its own, lose the
  data-trust argument the product is built on.
- **Fix**: read named fields — `available = available.live_balance or available.cash`,
  `used = utilised.debits`, `net = net` — and drop the segment row when
  `net ≉ available - used`. Pin the documented payload in `test_kite_granular_reads.py`.

### [P0] Every UI path into the subsystem is dead

- **Principle**: strategic over tactical / information leakage (duplicated truth)
- **Symptom**: change amplification — one contract, four hand-written copies
- **Evidence**: `src/store/brokers.ts:80-87` (no `broker` → 422, verified against
  `models/broker.py:138-149`); `BrokerConnectPanel.tsx:48-53` vs `angelone.py:59-67`;
  `routers/brokers.py:415-434` (Kite OAuth exchange, zero non-test callers);
  `BrokerConnectPanel.tsx:270` (`configuredIp={null}`)
- **Why it matters**: the Connect button cannot connect *any* broker; Angel One would still fail
  after that is fixed; Kite's genuine login flow — the thing CLAUDE.md calls the v1 flow — is
  unreachable, so the whole daily-token story has no recovery path; and the SEBI static-IP banner
  is permanently stuck in its alarm state. Four separate one-line drifts, every one of which has a
  correct sibling implementation elsewhere in the repo.
- **Fix**: COD-2/3/9/11 individually (each is a 1–10 line change). Structurally: assert the posted
  body against the Pydantic shape in `src/store/brokers.test.ts`, and generate the credential field
  list from the adapters rather than hand-maintaining `BROKER_CREDENTIAL_FIELDS`.

### [P1] The documented read-only guarantee does not exist

- **Principle**: naming / comments asserting invariants the structure does not hold
- **Symptom**: unknown unknowns — a reviewer who trusts the doc stops looking
- **Evidence**: `grep -rn getmembers --include=*.py .` → zero hits repo-wide; six of seven plugins
  declare `supportsControlPlane: true` (`plugins/brokers/kite/index.ts:53` et al) and their tests
  pin it there (`kite.test.ts:33`); `test_brokers_readonly_routes.py:61-69` audits methods only on
  paths ending `/positions|/holdings|/margins`, so `POST /brokers/{id}/orders`
  (`routers/brokers.py:255`) is never seen; the public order method is named `confirm_and_place`
  (`broker_base.py:310`), which a `place_/submit_/execute_` prefix audit would pass.
- **Why it matters**: CLAUDE.md and this subsystem's own responsibility statement both describe a
  three-layer read-only enforcement that was never written. The guard's *shape* is satisfiable
  without the guarantee holding — that is worse than no guard, because it stops the next reviewer.
- **Fix**: **Tier-4 — surface to the operator, do not decide.** Either flip the six plugins to
  `supportsControlPlane: false`, drop the `place-order` branches, and widen the route audit to
  "the brokers router has no non-GET route"; or correct the docs so they stop asserting a guard
  that does not exist.

### [P1] ccxt blocks the event loop; four adapters leak raw SDK errors as 500s

- **Principle**: consistency / exception aggregation
- **Symptom**: cognitive load — the reader must check each of seven adapters to know the rule
- **Evidence**: `ccxt_exec.py:245,340,384` (no `to_thread`, against six siblings that have it and
  the ≤2 s kill-switch claim at `alpaca.py:42-43`); `routers/brokers.py:205-212` catches only
  `BrokerError` while `alpaca.py:129-156` and `ib.py:163-218` raise SDK-native exceptions and the
  sibling `connect_broker:179-180` has the broad arm.
- **Why it matters**: one hung Binance call freezes research, agents and the kill switch; an
  expired Alpaca token reaches the user as a bogus CORS error. Both are *inconsistencies*, not
  missing features — the correct pattern is already in the file next door.
- **Fix**: wrap the three ccxt calls in `asyncio.to_thread`; add `except Exception → 502` to the
  read routes; wrap the alpaca/ib SDK calls in `BrokerError`.

### [P2] The provenance label is on the models that do not carry money

- **Principle**: different layer, different abstraction / define errors out of existence
- **Symptom**: unknown unknowns
- **Evidence**: `models/broker_reads.py:13-15` promises every read is labelled;
  `models/broker.py:109-121` `AccountSummary` has no label; `kite.py:178-189`, `dhan.py:112-122`,
  `angelone.py:89-99` return a hardcoded ₹10,00,000 / ₹5,00,000 in paper mode; `models/broker.py:105`
  forces `market_value: float`, so `ccxt_exec.py:268` and `ib.py:203` write `0.0` for "unknown".
- **Why it matters**: the one shape the panel, the plugin `account` command and any agent tool
  actually read is the one without the guarantee, and a required `float` makes "I don't know"
  unspellable — so it is spelled `0`. Both are the same mistake: the model cannot represent the
  honest answer, so it emits a confident wrong one.
- **Fix**: add `synthetic` + `mode` to `AccountSummary` (or make paper mode raise like
  `alpaca.py:130-131` already does), and make `market_value` `float | None` rendered as `—`.

---

## Persona walkthrough

**Tactical Tornado.** If the Tornado wrote this, the next feature lands exactly where the last four
did: a new read gets its own `getattr` duck-type in `routers/brokers.py:192-203`, its own hand-typed
mirror in `types/`, and its own fetch in the store — and the existing four drifted copies stay
drifted, because nothing fails when they do. The specific accelerant is
`BROKER_CREDENTIAL_FIELDS` (`BrokerConnectPanel.tsx:43-89`): a hand-maintained
`Record<BrokerId, Field[]>` sitting 300 lines and one language away from the seven `_connect`
methods that define the real contract. Every new broker adds one more pair to drift.

**Strategic Thinker.** The redesign would put the wire contract in one place and derive the rest.
Concretely, three moves: (a) give `BrokerAdapter` a `REQUIRED_CREDENTIALS: ClassVar[tuple[str,...]]`
and a `GET /brokers/{id}/credential-fields` route so the dialog is generated, killing COD-3 and its
successors; (b) add a default `positions_info` on the ABC that projects `_account_info().positions`
with correct provenance, so all seven brokers get a labelled granular read and `_read_granular`'s
`getattr` becomes a plain method call (COD-5); (c) add `disconnect()` to the ABC so
`routers/brokers.py:249-251` stops assigning private attributes by name (COD-12). None of the three
touches the §6.5 surface, and each removes a whole category rather than one instance.

---

## Minor observations

- `ib.py:188-189` — `if str(getattr(row, "tag", "")) == "AccountType": pass` is a dead branch, and
  the `Currency` tag it loops for is not an IB `accountSummary` tag, so `currency` is always `"USD"`.
- `routers/brokers.py:124` — `_pending_proposals` is an unbounded process-lifetime dict; a propose
  that is never confirmed or declined leaks its entry forever.
- `static_ip_detector.py:36` — a local-first app makes an unconditional, uncached GET to
  `api.ipify.org` every 30 s while Kite is live (`kite-static-ip-banner.tsx:63,127`), with no opt-out.
- `kite.py:498-504` — `_raise_kite_read_error` always raises but is annotated `-> None`; callers at
  `:196,248,263,276` then read a possibly-unbound name. Correct at runtime, invisible to the checker.
  `NoReturn` would make it honest.
- `broker_base.py:433-455` — `_on_kill_switch` sets `_read_only = True` and never restores it; there
  is no documented path back, so a fired-then-reset kill switch leaves every adapter read-only
  until the sidecar restarts.
- `src/lib/plugin-bootstrap.ts:143-152` — control-plane commands are invoked as
  `executeCommand(id, undefined)`, so `set-static-ip` from the palette posts `{staticIp: null}` and
  `connect` posts empty credentials. The plugin command seam is structurally argument-less.

---

## Questions to consider

- `types/broker.ts` and `types/broker-reads.ts` are hand-maintained mirrors guarded by a CLAUDE.md
  rule. Four of these fifteen findings are mirror drift. What would it cost to generate them from
  the Pydantic models at build time and delete the rule?
- If `market_value` and `equity` could say "unknown", how many of the zero-and-fabricated-number
  findings (COD-4, COD-14) disappear without any new code?
- Is the broker layer read-only for this release or not? Six plugins, seven route handlers and one
  CLAUDE.md paragraph currently give three different answers (COD-15).

---

## Run notes

- Target: `brokers-adapters` per `CODE_PARTITION.json`. All 38 owning files opened; core files
  (`broker_base.py`, `routers/brokers.py`, all seven adapters, both model files, both stores, all
  four panel files, `kite` plugin) read in full.
- Assessment independence: **degraded (sequential, no sub-agent isolation)**.
- Two claims settled by execution rather than reading: the Kite margins double-count and the 422 on
  the connect body (both reproduced with `sidecar/.venv/bin/python`, commands in the raw findings).
- No process was started or stopped; no GUI interaction; the operator's live app was not touched.
- `.aposd/critique/` snapshot not written — this run emits only the two census artifacts.
- 15 raw findings: 1 critical, 7 high, 7 medium → `census/raw/code-brokers-adapters.json`.
