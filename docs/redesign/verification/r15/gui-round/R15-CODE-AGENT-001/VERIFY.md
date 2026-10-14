# R15-CODE-AGENT-001 — fresh GUI verify at ace7dd7

Verifier: claude-opus-5-5 (gui-verify-R15-CODE-AGENT-001). No GUI driven. Inputs used: register entry,
this directory's DRIVE.md, captures, raw/ files, r15/CAPTURES.jsonl, gui-round/presence.log, and code at
ace7dd768c3b809b0e72b20b20cfc94eea2368bd.

**Verdict: still_needs_gui.** The macOS packaged app and `pnpm tauri:dev` both hold. The Windows packaged
app, which the note names, was not driven.

## Claim under test

- **Title:** the sidecar answered any browser Origin with `access-control-allow-origin: *`.
- **fix_shape:** an explicit allow-list, a 403 for an Origin that is present but not listed, and a
  TestClient pin.
- **Note's GUI check:** launch the packaged app (macOS **and Windows**) and `pnpm tauri:dev`. Every panel
  must load, and the sidecar log must show no 403 for the webview's origin.

## Code at the sha (`git show ace7dd7:sidecar/app.py`)

- `ALLOWED_ORIGINS` lists `tauri://localhost`, `http://tauri.localhost`, `https://tauri.localhost`,
  `http://localhost:5173` and `http://127.0.0.1:5173`.
- `CORSMiddleware` uses `allow_origins=list(ALLOWED_ORIGINS)`, so there is no wildcard.
- `_OriginGuardMiddleware` is added last, which makes it the outermost layer. It returns a 403
  `{"detail":"origin not allowed"}` for an unlisted Origin and closes a websocket with code 1008.

This matches the fix_shape.

## Capture registration

All 46 `ace7dd7-*.png` files are registered:

- Files: 01-04, 10-29 and 40-61.
- Each sha256 is in CAPTURES.jsonl with tool `scripts/rig/rig.py capture` and window_owner "Vysted Terminal"
  or "vysted-terminal".
- Presence lines come before each batch:
  - 23:55:38Z, before cap 01
  - 23:56:14Z, before caps 02-29
  - 00:17:24Z, before cap 40
  - 00:17:42Z, before caps 41-61

Unregistered captures: none.

## Per part

| Part | Evidence | What it shows | Ruling |
|---|---|---|---|
| P1 packaged macOS (origin `tauri://localhost`): app boots and connects | 01, 02, 03, 04 | Seeded layout with the ^NSEI chart and the SETFNIF50 brief, both live. The terms and welcome modals sit over live data. Portfolio·2 shows $4,506.65 and +$2,106.65. Header reads CONNECTED. | holds |
| P2 packaged macOS: every panel loads | 10-29 | News, watchlist (7 prices), equity overview, analyst ratings (AAPL), earnings calendar, SEC filings, macro, yield curve, screener (NIFTY 50 universe; brief shows ₹252.41), option chain/pricer/greeks and the rest. Each is populated or in a designed idle/keyless state. Header reads CONNECTED in every capture, and none shows a 403, CORS or forbidden error. In 15 (SEC filings) the panel is mid-load: the log has OPTIONS at 05:27:26 and GET 200 at 05:27:36.4, 2.7 s after the capture. 16 (macro) shows the FRED keyless notice, which is expected and not an origin failure. | holds |
| P3 packaged macOS: sidecar log, no 403 for the webview origin | raw/ace7dd7-403-grep.txt plus my own count | 65 OPTIONS preflights, all 200. The only 403 is GET /health at 05:31:14 IST (00:01:14Z). That is the driver's evil-Origin curl after the tour ended at 23:59:56Z, so it is the guard working. SIDECAR_TIMED_OUT 0. | holds |
| D1 `pnpm tauri:dev` (origin `http://localhost:5173`): app boots and connects | 40 | CONNECTED, with a populated layout. | holds |
| D2 dev: every panel loads | 41-61 | All CONNECTED, each populated or in a designed idle state. 47 (SEC) shows AAPL·40 filings. 48 (macro) shows the FRED keyless notice. No 403 or CORS error appears. | holds |
| D3 dev: sidecar log, no 403 for the webview origin | raw/ace7dd7-403-grep.txt plus my own count | 96 OPTIONS, all 200 (the driver wrote 95). Status counts: 738×200, 1×202, 2×409, 2×502 (FRED keyless), 32×503 (yfinance quotes after the tour). The single 403 is GET /health at 05:56:55 IST (00:26:55Z), the driver's guard probe after the tour. SIDECAR_TIMED_OUT 0. | holds |
| W packaged **Windows** (origin `http(s)://tauri.localhost`) | none | DRIVE.md marks it not_driven. No captures and no log exist. | **not driven** |

## Ruling

The title and fix_shape conclusion is visible for every macOS part. The webview origins `tauri://localhost`
and `http://localhost:5173` are never refused, and the guard does refuse a foreign Origin. The note
explicitly names the Windows packaged app, whose webview origin is a different allow-list entry
(`http://tauri.localhost` or `https://tauri.localhost`), and that part was not driven.

**Remaining check:** on the Windows packaged app, tour every panel and grep the sidecar log for 403. Expect
none for the `tauri.localhost` origin.
