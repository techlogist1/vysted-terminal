# Refutation audit round 4 — datapack — R15-DATA-008 (key rc1-datapack:1)

Auditor: Opus, follow-up group `datapack`. Written 07:11 IST.
HEAD: 06a8535c. `git diff --name-only 01015033 HEAD | grep -v '^docs/' | grep -v '^CHANGELOG.md$'`
printed nothing, so the code tree equals the post-fix-round merge 01015033.
Own sidecar: `sleep 86400 | sidecar/.venv/bin/python3 main.py --host 127.0.0.1 --port 52440 --data-dir <scratch>/data`
(env `VYSTED_DATA_DIR=<scratch>/data`, `VYSTED_OPENBB_MCP_PORT=0`, `VYSTED_SEC_EDGAR_MCP_PORT=0`).
Scratch: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-datapack/`.

## Verdict: regression_confirmed (critical). failure_count 1.

On SIFY, the name in the claim, every in-app consumer labels the INR figure as INR. The
verifier's rejection is right about SIFY. The entry's own symptom still reproduces at HEAD on
**INFY.NS**: INR-scale `revenue_ttm`/`net_income_ttm` are presented as **USD**, about 91x too
large, on every consumer (Equity Overview panel, research brief card, the model's fundamentals
tool result, the research tool's model view and the company-narrative facts). The cause is the
DATA-008 fix's own `financial_currency` label. A later commit, the NSE exchange-filed overlay
(59de8327, R15-DATA-014/027/076/LEAD-004), replaces Yahoo's USD sizes with INR filed sums but
leaves `financial_currency: "USD"` in place. The DATA-008 fix (f284b89f) is an ancestor of the
overlay commit, and both are in HEAD.

## (a) SIFY at HEAD: the claim's repro

`curl -s http://127.0.0.1:52440/fundamentals/SIFY` (HTTP 200):

```
currency: USD   financial_currency: INR
revenue_ttm: 46506049536.0   net_income_ttm: -912369984.0   market_cap: 967002176.0
field_meta.revenue_ttm   = {status: ok, provider: yfinance, reason: null, label: null}
field_meta.net_income_ttm = {status: ok, provider: yfinance, reason: null, label: null}
price_to_sales: null  field_meta.price_to_sales = {status: withheld, reason: "Yahoo's price/sales ... divides or states a USD listing value against INR statements; ... withheld"}
```

The claim's raw fields reproduce exactly. The payload also carries `financial_currency: "INR"`.
The contract names that field as the currency of the statement sizes:
`sidecar/models/fundamentals.py:66-69,82-87` and `types/data.ts:143-148`. The fix_shape allowed
two options: FX-convert, or "carry a separate financial_currency on the model and format with it".
The second one was implemented. Whether that is honest therefore depends on the consumers.

## (b) Every consumer of revenue_ttm / net_income_ttm

The list comes from `grep -rn "revenue_ttm\|net_income_ttm" sidecar src types plugins`, excluding
tests.

| Consumer | Code | SIFY at HEAD | INFY.NS at HEAD |
|---|---|---|---|
| Equity Overview panel | `src/modules/equity-overview/EquityOverviewPanel.tsx:832-833` (`statementCurrency = financial_currency ?? instrumentCurrency`), `:854` (statement sizes use it), `metrics.ts:76-89` (`statementSize: true`) | ₹ (vitest `EquityOverviewPanel.test.tsx:592-606` pins ₹14.0B for the SIFY shape; passes) | **"$1.85T" revenue, "$303B" net income** (`formatCompactMoney(v, financial_currency)` on the live payload) |
| Research brief metric card | `src/modules/research/brief-blocks.tsx:334-337` (`formatInstrumentMoney(revenue_ttm, fund.financial_currency ?? currency)`) | **"₹46.5B"** (deriveMetrics on the live SIFY snapshot) | **"$1.85T"** (deriveMetrics on the live INFY.NS snapshot) |
| Model: fundamentals / compare / statements tool | `sidecar/services/agent_runtime.py:1088-1091` → `agent_tools/research.py:492-540` `fundamentals_content` (statement sizes `display_value(..., financial_currency or currency)`) | **revenue_ttm "₹4,651 cr", net_income_ttm "₹-91.24 cr"**, market_cap "USD 967.00M", plus the ads_ratio (6 shares/ADS, 20-F) | **revenue_ttm "USD 1.85T", net_income_ttm "USD 302.88B"**, market_cap "₹405,115 cr" |
| Model: research tool view | `agent_tools/research.py:402-461` `model_view` (same statement-currency rule) | "₹4,651 cr" / "₹-91.24 cr" | "USD 1.85T" / "USD 302.88B" |
| Company narrative facts | `sidecar/services/company_narrative.py:301,319-321` (`reporting = financial_currency or currency`) | "Revenue (TTM): 46.51B INR" | **"Revenue (TTM): 1.85T USD", "Net income (TTM): 302.88B USD"** |
| MCP surface (external clients) | `services/mcp_server.py:142` returns the raw handler dict (no `fundamentals_content`) | raw float + `financial_currency: INR` sibling (same shape as REST) | raw 1.8458e12 + `financial_currency: USD` |
| Derivations | `yfinance_provider.py:769-795` (ROE = NI/equity, same basis; EPS derivation gated on `financial_currency is None`) | not presentation | not presentation |

For comparison, the INFY ADR under region US is correct:
`curl -H 'X-Vysted-Region: US' /fundamentals/INFY` returns `currency USD, financial_currency None,
revenue_ttm 20298999808.0` (provider yfinance).

WIT is also correct. It returns `currency USD, financial_currency INR, revenue_ttm 9.4968e11`
(INR books), and consumers label it INR.

### Live model turn (SIFY, llama3.1:8b, under the ollama lock 07:09-07:10 IST)

`vy.py invoke copilot ... --port 52440` refused: "non-GET calls are only allowed against R15
isolated sidecars (ports 52100-52399)". I did not bypass that guard. Instead I sent the same
request body vy builds (copilot, ollama llama3.1:8b, mode agent, region IN, tier_a) in-process
to the HEAD app via FastAPI TestClient, using the scratch data dir and touching no running
sidecar. Script: `<scratch>/llm_inproc.py`. Events: `<scratch>/llm_sify_events.jsonl`.

- Tool: `financial_statements {symbol: SIFY, statement: income, period: annual}`. The
  model-facing content, re-derived in-process (`<scratch>/sify_fs.py`), has `currency: INR` and
  ads_ratio present. Lines render as INR, e.g. "Reconciled Cost Of Revenue 2026-03-31: ₹2,684 cr".
- Answer: "The trailing revenue for SIFY in dollars is not directly available from the provided
  data. However, we can see that the revenue figures are given in Indian Rupees (INR). To convert
  these to US Dollars (USD), we would need additional exchange rate information. ..." The model
  labels the figure INR and does not state an INR-scale figure in dollars.

### Frontend runs

- `node_modules/.bin/vitest run src/modules/equity-overview/EquityOverviewPanel.test.tsx
  src/modules/research/brief-blocks.test.ts` → 2 files, 62 tests passed.
- Scratch vitest (config and tests under `<scratch>/fe/`, importing the HEAD sources):
  deriveMetrics on the live snapshot.
  - SIFY → `{"Revenue":"₹46.5B","Market cap":"$967M"}`
  - INFY.NS → `{"brief":{"Revenue":"$1.85T","Market cap":"₹4.05T"},"panel":{"Revenue (TTM)":"$1.85T","Net income (TTM)":"$303B","Market cap":"₹4.05T"}}`

## The INFY.NS path

`GET /fundamentals/INFY` defaults to region IN and resolves to INFY.NS:

```
currency: INR   financial_currency: USD   revenue_ttm: 1845820000000.0   net_income_ttm: 302880000000.0
field_meta.revenue_ttm = {status: ok, provider: nse, as_of: 2026-06-30,
  reason: "exchange-filed (NSE) figure served; the provider's 20,298,999,808 disagrees with it — not served",
  label: "consolidated, sum of 4 filed quarters to 2026-06-30"}
field_meta.net_income_ttm = {status: ok, provider: nse, reason: "... the provider's 3,323,000,064 disagrees ..."}
eps 74.13 (nse, INR per share)
```

1. `yfinance_provider._financial_currency` (`sidecar/services/yfinance_provider.py:476-488`,
   used at `:977`) sets `financial_currency = "USD"` for INFY.NS, because Yahoo's
   financialCurrency is USD and the trading currency is INR. That is correct for Yahoo's own
   sizes: 20.30B / 3.32B USD.
2. `correctness_gate.overlay_filed_periods` (`sidecar/services/correctness_gate.py:673-739`,
   `_FILED_SIZES` at `:661`, loop at `:715-725`) replaces `revenue_ttm`/`net_income_ttm`/`eps`
   with NSE-filed sums. `exchange_financials.py:74` says "Sizes in INR". The overlay does not touch
   `financial_currency`, which stays "USD". Its "disagrees" test (`_relative_divergence` at
   `:722-724`) compares 20.3B USD with 1.8458T INR without regard to currency, so the ~91x FX
   ratio is what drives the substitution and the reason text.
3. Every consumer in (b) then formats the INR sums in `financial_currency` (USD). The result is
   Infosys revenue shown as $1.85T against a true ~$20.3B, and net income as $303B against
   ~$3.3B. This is the entry's symptom: INR amounts served under a USD label, about 91x (entry:
   ~94x). It appears for the user (panel, brief) and for the model (fundamentals and research
   tools, narrative facts).

Timeline: f284b89f (23 Sep, "carry financialCurrency ... (R15-DATA-008)") is an ancestor of
59de8327 (24 Sep, "serve exchange-filed results as the India witness ..."), which is also in the
pre-fix candidate 1006c6da. Before f284b89f, the same INR overlay would have been formatted in
`currency` (INR), which is correct. No gate test covers `financial_currency`:
`grep -l financial_currency sidecar/tests/test_correctness_gate*.py` finds 0 files.

## Root cause

`sidecar/services/correctness_gate.py:715-725` (`overlay_filed_periods`) serves INR
exchange-filed `revenue_ttm`/`net_income_ttm` over Yahoo's sizes without resetting
`Fundamentals.financial_currency`, which `sidecar/services/yfinance_provider.py:476-488,977` set
from Yahoo's financialCurrency (USD for INFY.NS). All consumers trust that field as the
statement-size currency. A second symptom of the same root cause: the "disagrees" reason at
`:722-724` compares the two figures across currencies.

## Fix shape

Fix it once, in `overlay_filed_periods`. That is the only place that knows the served sizes
switched basis, and every consumer (panel, brief, model views, narrative, MCP) routes through the
`financial_currency` field it would correct. When the overlay serves any filed size, the
statement currency for the served sizes becomes the filing currency (INR for NSE/BSE):

- Set `financial_currency` to `None` when the trading `currency` is INR, else to `"INR"`.
- Any Yahoo statement size the overlay did NOT replace and that was stated in the old
  `financial_currency` (`free_cash_flow` on INFY.NS: 3.17B, Yahoo USD) must be withheld with a
  typed reason, the same way `_withhold_mixed_basis_ratios` does it. Otherwise it flips to a
  wrong INR label.
- Before the 30% divergence test, compare the provider figure only when it is on the same
  currency basis. When the bases differ, state the basis difference instead of "disagrees".

Do not FX-convert. The code base has no stated-rate source, and D-B2-3 already chose withhold
over convert. Labelling at every consumer is the wrong layer: six consumers and a field that lies
would all need patching.

## Acceptance test

`sidecar/tests/test_correctness_gate.py`: build a `Fundamentals(symbol="INFY.NS",
currency="INR", financial_currency="USD", revenue_ttm=20_299_000_000.0,
net_income_ttm=3_323_000_000.0, free_cash_flow=3_165_625_088.0)` and run `overlay_filed_periods`
with a `FiledPeriods` of four INR quarters summing to 1_845_820_000_000. Assert:

- `out.financial_currency in (None, "INR")`
- `out.revenue_ttm == 1_845_820_000_000`
- `out.free_cash_flow is None` with `field_meta["free_cash_flow"].status == "withheld"`
- the revenue reason does not contain "disagrees"

Also add a `fundamentals_content` assertion that the model view shows revenue_ttm as
"₹184,582 cr" (`display_value` INR), not "USD 1.85T".

Live re-proof: `curl -s http://127.0.0.1:<port>/fundamentals/INFY | python3 -c "import json,sys;
d=json.load(sys.stdin); assert d['financial_currency'] in (None,'INR'), d['financial_currency'];
print(d['currency'], d['financial_currency'], d['revenue_ttm'])"`. Also re-run the scratch probes
`<scratch>/infy_consumers.py` (expect "₹…cr" for revenue_ttm in both model views and "INR" in the
narrative fact) and `<scratch>/fe/live-infy.test.ts` (expect the brief "Revenue" to start with
"₹"). SIFY must stay unchanged: `/fundamentals/SIFY` keeps `financial_currency: INR` and the
brief shows "₹46.5B".

## Residual observation (not counted)

The MCP surface (`services/mcp_server.py:142`) returns the raw handler dict, so an external MCP
client gets unscaled floats with only the sibling `financial_currency` field. The in-app model
path formats them through `fundamentals_content`. The `fundamentals` catalog description
(`agent_tools/catalog.py:318-321`) does not say that statement sizes are in `financial_currency`.
This is the same shape the REST contract serves, and the root-cause fix above corrects the field
the MCP client would read.

## Scratch artifacts

`fund_SIFY.json`, `fund_INFY.json`, `fund_INFY_US.json`, `fund_WIT.json`, `sify_consumers.py/.log`,
`sify_structured.py/.json/.log`, `sify_narrative.py`, `infy_consumers.py/.log`,
`infy_structured.json`, `fe/live-sify.test.ts`, `fe/cards.json`, `fe/live-infy.test.ts`,
`fe/infy_cards.json`, `llm_inproc.py`, `llm_turn2.log`, `llm_sify_events.jsonl`, `sify_fs.py`,
`vitest.log`. All are under the scratch path above.
