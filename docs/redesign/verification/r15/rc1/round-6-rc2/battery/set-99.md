# Set: lows-P3/fundamentals-profile (set-99.md) - rc1-battery-15 at ace7dd76

Raw: battery/raw/set-99/<id>.txt (in-process, candidate venv; live sidecar :52355 for GETs).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-022 | FieldMeta(status='unavaliable') | ValidationError (rejected); 'ok'/'unavailable' accepted | holds |
| R15-DATA-103 | row_to_pair with quote_change None | change None / change_percent None (was 0.0); currency from row's own 'INR' else USD fallback | holds |
| R15-DATA-102 | row_to_pair on a bare seed row | field_meta {} / derived per-field keys (was None); growth_basis None when growth NULL or unrecorded (was mrq_yoy); Fundamentals default growth_basis None | holds |
| R15-UI-094 | _build_messages + _parse_output; panel render grep | prompt asks TAKE/BUSINESS/STORYLINE/BULL/BEAR/RISKS; parser fills summary, business, storyline, bull_case, bear_case, risks; EquityOverviewPanel renders Storyline/Bull/Bear/Risks blocks | holds |
| R15-CODE-DATA-011 | grep + live ratings routes | no 'except ProviderError' left in routers/fundamentals.py; four /fundamentals/AAPL/ratings* routes HTTP 200 via routers/_cached.cached | holds |

COVERAGE: 5/5 ids raw; no raw: none
