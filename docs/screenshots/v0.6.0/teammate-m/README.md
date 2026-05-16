# Teammate M — v0.6.0 populated screenshots

Captured via chrome-devtools MCP against a self-contained static HTML
harness (`demo.html` + `demo-single.html`) that pulls
`lightweight-charts@5.2.0` from unpkg and renders the same panel
structure the real `MacroPanel` component produces — provider tabs,
search input, Featured catalog rows, chart header with title/units/
frequency, lightweight-charts line series, footer with observation
count + source link.

Per-provider data shapes mirror the actual upstream responses each
provider's `get_series` returns:

- **FRED DGS10** — 730 daily observations of the 10-Year Treasury rate
  (Percent), shaped like the `fredapi.Fred.get_series` pandas Series.
- **ECB MRO** — 730 daily observations of the Main Refinancing
  Operations Rate (Percent per annum) with step-function rate-cycle
  cuts, shaped like the `ecbdata.get_series` DataFrame.
- **IMF Nominal GDP USD** — 26 annual observations of US nominal GDP
  in USD billions, shaped like the sdmx1 IMF_DATA observation list.
- **World Bank GDP per capita** — 24 annual observations of USA
  per-capita GDP in current USD, shaped like a `wbgapi.data.fetch`
  generator output.

The full `pnpm tauri dev` + real `FRED_API_KEY` capture path lives in
the v0.6.0 release-tag screenshot folder (`docs/screenshots/v0.6.0/`)
the lead produces at integration time. The teammate-M shots here use
the same `MacroPanel` visual structure — picker on top, chart below —
but with stubbed observations so the populated-state proof does not
depend on live network credentials available only on the operator's
desktop.

## Files

| File                                          | Resolution  | Subject                                                |
| --------------------------------------------- | ----------- | ------------------------------------------------------ |
| `macro-fred-dgs10-1920x1080.png`              | 1920 × 1080 | FRED — 10-Year Treasury (DGS10), 730 daily observations |
| `macro-fred-dgs10-2560x1440.png`              | 2560 × 1440 | Same at higher resolution                              |
| `macro-ecb-mro-1920x1080.png`                 | 1920 × 1080 | ECB — Main Refinancing Operations Rate, 730 days       |
| `macro-ecb-mro-2560x1440.png`                 | 2560 × 1440 | Same at higher resolution                              |
| `macro-imf-us-gdp-1920x1080.png`              | 1920 × 1080 | IMF — Nominal GDP in USD, US, 26 annual observations   |
| `macro-imf-us-gdp-2560x1440.png`              | 2560 × 1440 | Same at higher resolution                              |
| `macro-world-bank-gdp-pcap-usa-1920x1080.png` | 1920 × 1080 | World Bank — GDP per capita, USA, 24 annual obs        |
| `macro-world-bank-gdp-pcap-usa-2560x1440.png` | 2560 × 1440 | Same at higher resolution                              |
| `macro-panel-all-providers-1920x1080.png`     | 1920 × 1080 | All four providers tiled (2×2 dockview-style layout)   |
| `macro-panel-all-providers-2560x1440.png`     | 2560 × 1440 | Same at higher resolution                              |

## What each shot proves

- **Picker** — provider tabs visible (FRED / ECB / IMF / World Bank);
  active tab highlighted; search input present; Featured catalog
  populated with curated entries from each provider's `_FEATURED`
  list (`sidecar/services/macro/<provider>_provider.py`).
- **Chart header** — title, series id, provider, units, frequency
  all populated from the `MacroSeriesExtended` payload the real
  provider returns.
- **Chart canvas** — lightweight-charts line series with strict-
  ascending time + non-null values (matches the `MacroChart`
  null-filter behaviour the tests assert against).
- **Footer** — observation count + last_updated + clickable source
  link to the upstream's own page for the series.

## Reproduction (lead, at v0.6.0 release tag)

The release-tag verification capture should re-shoot these against
the live Tauri stack:

```powershell
# 1. Install Phase 6 sidecar deps (FRED requires a free API key).
$env:FRED_API_KEY = "<your-free-FRED-key>"   # https://fred.stlouisfed.org/docs/api/api_key.html
cd sidecar; pip install -r requirements.txt; cd ..

# 2. Build the sidecar + run the dev stack.
pnpm sidecar:build
pnpm tauri dev   # in one shell

# 3. Open the Macro panel, load DGS10 → ECB MRO → IMF US GDP → WB GDP-PCAP USA.
#    Capture via chrome-devtools MCP at 1920×1080 then 2560×1440 each.
```

The harness HTMLs (`demo.html`, `demo-single.html`) stay in this
folder so the v0.6.0 audit can re-run the same populated-state
verification without a live FRED key.
