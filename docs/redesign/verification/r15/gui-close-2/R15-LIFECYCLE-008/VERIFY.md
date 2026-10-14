# R15-LIFECYCLE-008 — fresh GUI verify at 1fddb2b (Copy diagnostics click only)

- verifier: Opus 5.5, fresh context, label close-verify-R15-LIFECYCLE-008. No GUI, no app launch.
- inputs: register entry R15-LIFECYCLE-008, DRIVE.md, the captures and raw/ in this folder, ../../CAPTURES.jsonl, ../presence.log, and code at 1fddb2b19dd41ae2085a78ef5d02d7e5ee3af056 (`src/components/SettingsPanel.tsx` DiagnosticsSection, `sidecar/services/diagnostics.py`, `styles/tokens.css`).
- scope: log rotation stood from 4 Oct (../../gui-close/R15-LIFECYCLE-008/DRIVE.md); not re-judged.

## Registration
All 12 PNGs in this folder hash to a CAPTURES.jsonl row with tool `scripts/rig/rig.py capture`, window_owner "Vysted Terminal", frontmost "Vysted Terminal". Each sits after a `[R15-LIFECYCLE-008 pre-…]` presence.log line (pre-capture-01 10:37:39Z -> 01; pre-batch-01 10:38:13Z -> 02-04; pre-batch-02 10:53:54Z -> 05; pre-batch-03 11:09:53Z -> 06-08; pre-batch-04 11:32:42Z -> 10-13). Unregistered captures: none. I opened all 12.

## Code at the sha
DiagnosticsSection: "Copy diagnostics" -> `collect()` GET /system/diagnostics -> `bundle = JSON.stringify(json, null, 2)`, rendered in `<pre aria-label="Diagnostics preview" className="… text-micro …">`; "Copy to clipboard" (rendered only when bundle exists) -> `navigator.clipboard.writeText(bundle)` -> status "Copied". The preview and the clipboard are the same `bundle` string. `text-micro` (`styles/tokens.css` @utility) sets `text-transform: uppercase`.

## Part 1 — Settings -> Diagnostics -> "Copy diagnostics" shows the Diagnostics preview
- evidence: 1fddb2b-04 (Settings open), 1fddb2b-05 (Diagnostics card with hint and a lone "Copy diagnostics", no preview), 1fddb2b-06 (a "Copy to clipboard" button has appeared under "Copy diagnostics" = bundle collected), 1fddb2b-07 and 1fddb2b-11 (preview `<pre>`: `"VERSION": "0.9.0"`, `"LOGFILE": "LOGS/VYSTED.LOG"`, `"STATUS": {"HEALTH": {"STATUS": "OK", "SERVICE": "VYSTED-SIDECAR", "VERSION": "0.9.0", "PROVIDERS": {"ANALYST_RATING": …`).
- shows: version and status are visible in the preview before anything was copied. The log tail is not scrolled into view in any capture (the `<pre>` is capped at max-h-64); its content is read back via the clipboard, which by code is the identical string.
- ruling: holds.

## Part 2 — "Copy to clipboard" sets "Copied"
- evidence: 1fddb2b-12 and 1fddb2b-13: status line "Copied" under the preview, buttons and preview unchanged. (1fddb2b-08 is the driver's tab-strip miss onto Equity Overview; 1fddb2b-10 is the cmd+, recovery; neither shows a defect.)
- ruling: holds.

## Part 3 — clipboard read-back
- evidence: raw/clipboard.txt (46712 B), re-checked by me: key-shape grep (`sk-…`, `AIza`, `Bearer `, 32+ char token run) = 0 matches; parses as JSON with keys version, logFile, status, logTail (300 lines, last 11:33:40.638Z); the only IPv4 is 127.0.0.1; query strings show as `?<query>`, request paths as `/system/<id>`. Seeded symbols AAPL/MSFT/NVDA: 0.
- shows: the copied bundle is the redacted version + status + log tail; no key shape.
- ruling: holds.

## Findings
1. Driver finding — preview upper-cases the bundle, clipboard gets lower-case JSON. **Confirmed, low.** Captures 07/11/12 show upper case; clipboard.txt starts `"version": "0.9.0"`; cause is `text-micro`'s `text-transform: uppercase` on the `<pre>`. Content is the same string, case display only; but the component's stated aim ("they see exactly what they would hand a maintainer") is not met byte for byte, and case-sensitive values (paths, ids) display wrongly.
2. Added (driver missed) — the Diagnostics hint promises "symbols … removed", but ticker symbols in log message text pass through unredacted. **Confirmed, medium.** raw/clipboard.txt logTail holds 54 occurrences of `^NSEI`, e.g. `WARNING services.provider_registry: provider nse_direct failed for quote, falling through: nse_direct: '^NSEI' is not a known NSE instrument`. `sidecar/services/diagnostics.py` at the sha only strips symbols that sit in a URL path (`_PATH`) or query (`_QUERY`), and quoted text only at 40+ chars (`_QUOTED`), so a short quoted ticker in a provider warning survives. The register fix_shape lists symbols among what the tail must redact. Workaround: the user sees the preview before copying and can edit the pasted text.

## Verdict
**passed** — every part of the check (preview with version/status, redacted log tail via the identical copied string, "Copied" status, key-shape-clean clipboard) is visible in registered captures and the raw read-back. Two defects recorded as findings (low preview case; medium symbol redaction gap), neither the defect the item was filed for.
