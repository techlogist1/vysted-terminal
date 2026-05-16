# Teammate M — Tier-3 decisions + non-blocking findings

## T3-M-1 — `fred-mcp-server` is a Node.js package, FRED moved to in-process `fredapi`

**Status:** decision made, code follows the new path. NOT a Tier-4 escalation.

**Discovery:** the v0.6.0 Phase-6 plan assumed `fred-mcp-server` was a Python
package on PyPI installable into the existing `sidecar/openbb_mcp_subprocess`-
shaped PyInstaller setup. PyPI search at dispatch time (2026-05-16) found no
such package. The `stefanoamorelli/fred-mcp-server` project that the plan
referenced is a **Node.js / TypeScript** MCP server — installable via
`npx @smithery/cli install @stefanoamorelli/fred-mcp-server` or via Docker,
not via `pip install`.

**Decision (Tier-3, spec-ambiguous → DNA-derivable):** drop the FRED subprocess
+ Tauri-Rust-spawn portion of the slice and consume FRED in-process via the
mature `fredapi==0.5.2` Python SDK, matching the in-process pattern the
plan already uses for ECB / IMF / World Bank.

**Reasoning (decision authority Tier-3 derivation from project DNA):**

1. **Plugin contract not touched** — no Tier-4 surface affected. The macro
   provider router still exposes the four-provider dispatch the foundation
   types contract describes.
2. **Bundle size + quality posture** — v0.6.0's posture explicitly removes the
   bundle-size constraint, but adding a Node.js runtime to the Tauri build
   purely to host one MCP server crosses a much larger language-runtime
   boundary than the plan intended. Phase 7 (signing + distribution) would
   absorb a 30+ MB Node runtime as an externalBin that we presently do not
   ship; that is a noticeable distribution-cost regression and a new
   language-runtime liability with no architectural payoff (the four
   in-process providers cover the same surface).
3. **`fredapi` is mature** — `fredapi==0.5.2` (Dec 2024) is the canonical
   Python FRED client. Pure Python, depends on requests + pandas (already in
   the main sidecar), no native deps. The PyInstaller `--onefile` graph is
   unaffected.
4. **Architectural symmetry** — FRED, ECB, IMF, World Bank now all use the
   "official Python SDK in-process" pattern, instead of mixing MCP-subprocess
   for FRED with in-process for the other three. Symmetry simplifies the
   provider router and removes one Tauri-side spawn supervisor.

**Code-level consequences:**

- Drop: `sidecar/fred_mcp_subprocess/` (would have been an empty PyInstaller
  wrapper around a Node package — wrong).
- Drop: `src-tauri/src/fred_mcp.rs` + `src-tauri/src/lib.rs` `fred_mcp::spawn`
  + `tauri.conf.json` `binaries/vysted-fred-mcp-sidecar` entry +
  `package.json` `fred-mcp-sidecar:build` script.
- Keep: `sidecar/services/macro/fred_provider.py`, now using
  `fredapi.Fred(api_key=...)` directly instead of an `mcp_client` wrapper.
- Add: `fredapi==0.5.2` to `sidecar/requirements.txt` (replaces the
  `fred-mcp-server` line that did not resolve).

**FRED API key handling:** the user must supply `FRED_API_KEY` via
environment variable (or via the future plugin-manager settings panel
v0.6.x). When the key is missing the provider raises `ProviderError`
which the router translates to 502, matching every other BYOK upstream.

## T3-M-2 — Search + catalog discovery scope for in-process providers

**Status:** decision made.

`ecbdata` 0.1.1 + `sdmx1` 2.26.0 + `wbgapi` 1.0.14 each expose richer
discovery surfaces than the contract's `MacroSearchResult` / `MacroCatalog`
need; for v0.6.0 each provider's `search()` does a name-substring match
against its native catalog endpoint (best-effort) and `catalog()` returns
a hand-curated featured list (10–25 entries per provider) plus the live
catalog when the SDK exposes one cheaply. This keeps the panel-side picker
useful at v0.6.0 without overcommitting to richer discovery (e.g. ECB
keyfamily browsing) that the BLUEPRINT does not call for until v1.0.x.

## T3-M-3 — Macro cache TTL set to 6 hours (per plan)

**Status:** decision made, per the plan's stated TTL.

The `data_cache.py` ttl_seconds value is 21600s (6h) for all four macro
providers. World Bank data updates annually; ECB MRO weekly; IMF GDP
quarterly; FRED varies but most series are daily-or-slower. 6h satisfies
all four; users can manually `invalidate("macro:")` via a follow-up
admin endpoint (out of scope for this slice).

## Non-blocking carry-forwards (lead picks up at integration)

- `wbgapi.data.fetch(indicator, country)` returns a pandas DataFrame; the
  provider serialises by-time observations from the DataFrame.
- `sdmx1` is heavier than the others (lxml dep) — bundle size impact
  expected to be modest (~5 MB to main sidecar).
- World Bank country code defaults to `USA`; series_id format
  `WB:NY.GDP.PCAP.CD:USA` overrides per spec.
