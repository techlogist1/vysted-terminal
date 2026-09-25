# batch-10/W4-screener-routes-statedocs (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 8 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-061 | `GET /macro/NOT.A.REAL.WB.ID?provider=world-bank`, `?provider=ecb`, `GET /quotes/ZZQXNOTASYM`, `/macro/CPIAUCSL?provider=fred` (no key) | 502 "unexpected response" (wb + ecb, no raw upstream text), 404 "not_found" copy, 502 authored FRED-key-needed copy | holds |
| R15-DATA-087 | `GET /macro/CPIAUCSL` (no provider) | 422 "provider is required for a series id" | holds |
| R15-CROSS-PLATFORM-003 | `GET /system/hardware` on this M1 Pro | `ramGib: 16.0`, `estimated: false`, `chip: "Apple M1 Pro"` — exact match to cert | holds |
| R15-RESEARCH-025 | `POST /screener/formula/validate` x5 | `(pe>10)+1` and `(pe>10)*2+1` rejected at position 10 "a boolean expression can't be used in arithmetic"; `abs(pe>10)`/`max(pe>10,1)` rejected "needs a numeric argument, not a boolean expression"; `pe>10 and pb<3` ok, fields [pe_ratio, price_to_book] | holds |
| R15-DATA-095 | in-process probe: built a `fundamentals` table missing `seed_updated_at`/`eod_updated_at`/`provider` via `fundamentals_store`'s own `_ALL_COLUMNS` minus those 3, then called the real `_connect()` | all 3 columns present after `_connect()` (the general `_migrate` ALTERs every column in `_ALL_COLUMNS`, not a hand-picked subset) | holds |
| R15-DOCS-016 | `grep` `CURRENT_STATE.md` §0.x/§3.10 + in-process `catalog.CAPABILITY_CATALOG` count | doc states "19 host actions ... no order action exists, D81 — none auto-apply"; live catalog has exactly 19 `kind='host_action'` capabilities, no order-shaped id | holds |
| R15-DOCS-017 | `grep` `CURRENT_STATE.md:359-363` | "506 symbols, a static snapshot dated 2026-06-04 ... R15-LEAD-013 open" and "nested AND/OR via `CriterionGroup`" both present verbatim | holds |
| R15-DOCS-018 | `grep` `CURRENT_STATE.md:93-94,320` + `GET /data-sources` | doc: "resolves by standard model key + preference order (not the asset-class chain); every result carries its serving provider"; live `/data-sources` returns per-provider `keys`/`rank`/`asset_classes` rows matching that model | holds |

Excluded (not certified in batch-10): R15-LEAD-013 (reverted out of batch 10, register stays open).

Raw output: `battery/raw/set-41/*`.
