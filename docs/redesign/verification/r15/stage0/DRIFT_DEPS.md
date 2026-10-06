# R15 Stage 0 — Dependency Drift Report (read-only)

Generated 2026-09-19 on branch `004-r4-experience-rebuild`. Read-only audit: no
installs, no builds, no process control. `pnpm outdated`/`pnpm audit` ran live;
Rust used crates.io + OSV.dev JSON APIs (no cargo-outdated/cargo-audit
installed, none installed by this audit); Python used the existing
`sidecar/.venv` (`pip list --outdated`, no pip-audit installed) + OSV.dev
batch queries against installed versions. No secret values were read, echoed,
or logged anywhere in this process.

---

## 1. JavaScript / pnpm

### 1.1 Outdated (`pnpm outdated --format json`, 45 packages behind; `wanted == current` for every one — package.json pins exact versions almost everywhere, so **every** bump below requires an explicit `package.json` edit, not just a lockfile refresh)

**Patch/minor, low risk — bump freely:**
`@tailwindcss/postcss` 4.3.0→4.3.3, `@tauri-apps/api` 2.11.0→2.11.1,
`@tauri-apps/cli` 2.11.1→2.11.4, `@tauri-apps/plugin-notification` 2.3.3→2.4.0,
`@tauri-apps/plugin-shell` 2.3.5→2.3.6, `@tauri-apps/plugin-updater` 2.10.1→2.11.0,
`@testing-library/dom` 10.4.1→10.4.2, `@testing-library/react` 16.3.2→16.3.3,
`@types/node` 25.7.0→26.6.2, `@types/react` 19.2.14→19.3.0, `@types/react-dom`
19.2.3→19.3.0, `@vitejs/plugin-react` 6.0.1→6.1.1, `@xyflow/react`
12.10.2→12.11.6, `lightweight-charts` 5.2.0→5.2.1, `lucide-react`
1.14.0→1.47.0 (semver-major-looking jump but lucide-react does not follow
strict semver for its 1.x icon releases — icon additions only), `postcss`
8.5.14→8.5.28 (**see 1.2 — security**), `prettier` 3.8.3→3.9.8,
`prettier-plugin-tailwindcss` 0.8.0→0.8.1, `react`/`react-dom` 19.2.6→19.3.0,
`tailwind-merge` 3.6.0→3.7.0, `tailwindcss` 4.3.0→4.3.3, `typescript-eslint`
8.61.0→8.70.0, `vite` 8.0.16→8.3.0, `zustand` 5.0.13→5.0.15,
`@fontsource/jetbrains-mono` 5.2.8→5.3.0, `radix-ui` 1.4.3→1.6.7.

**Major version behind — needs a real look before bumping (not a security
issue by itself):**
- `@tiptap/core` + 8 co-versioned `@tiptap/*` packages 3.25.0→3.31.3 — **also
  carries the security items in 1.2**, bump together (all 9 packages must move
  in lockstep, they're one release train).
- `dockview` 6.2.2→8.3.1 (two majors) — panel-layout engine
  (`src/components/PanelHost.tsx` per CLAUDE.md); a major bump here is
  Tier-3/4 territory (touches the dockview API surface the whole panel system
  rides on), not a drive-by version bump.
- `framer-motion` 12.38.0→13.4.0.
- `eslint` 9.39.4→10.11.0, `jsdom` 29.1.1→30.1.0, `@vitest/coverage-v8` +
  `vitest` 4.1.6→5.0.1, `typescript` 6.0.3→7.0.2, `@testing-library/jest-dom`
  6.9.1→7.0.1 — all dev/test tooling, safe to defer past a release gate.

### 1.2 `pnpm audit --json` — 715 resolved deps, **0 critical / 28 high / 33 moderate / 6 low**

Every unique advisory, deduped by module, with dependency-chain root and
runtime-vs-dev classification (verified via `pnpm why <module>` — chains
below are the actual resolved paths, not guesses):

| Module | Sev | Chain root | Runtime or dev-only | Notes |
|---|---|---|---|---|
| `@tiptap/core` | **HIGH** | direct (`dependencies`) | **RUNTIME** | Quadratic ReDoS in block/inline Markdown attribute parsing. Installed 3.25.0 is inside the vulnerable range (`>=3.7.0 <3.30.5`). |
| `@tiptap/core` | MODERATE | direct (`dependencies`) | **RUNTIME** | `mergeAttributes()` turns an own `__proto__` key into inherited executable DOM attributes (XSS-adjacent). Vulnerable range `>=2.0.0-alpha.0 <3.30.4`; installed 3.25.0 is in range. |
| `dompurify@3.4.8` | LOW/MODERATE | `jspdf@4.2.1` (direct `dependencies`) → used by `src/lib/export-artifact.ts` | **RUNTIME** (PDF export path) | `CUSTOM_ELEMENT_HANDLING` bypasses `afterSanitizeElements` for allowed custom elements. Vulnerable `<=3.4.11`, fixed `>=3.4.12`. Low severity, but on the export/HTML-to-PDF surface. |
| `undici@7.25.0` | HIGH/MODERATE/LOW | `jsdom` (devDependency) → `vitest`/`@vitest/coverage-v8` | **DEV-ONLY** (test runner only; `jsdom`/`vitest` are devDependencies, never in the static-export bundle) | TLS cert-validation bypass via dropped `requestTls` on SOCKS5 `ProxyAgent` (CVE-2026-9697). No production reach. |
| `brace-expansion`, `js-yaml` | HIGH/MODERATE | `eslint`, `typescript-eslint` (devDependencies) | **DEV-ONLY** | Lint tooling only. |
| `hono`, `fast-uri`, `ip-address`, `@hono/node-server`, `qs`, `body-parser` | HIGH/MODERATE/LOW | `tauri-plugin-mcp` (devDependency, git-pinned) → `@modelcontextprotocol/sdk` | **DEV-ONLY, and further gated out of release binaries** — confirmed at `src-tauri/Cargo.toml:16-27`: `dev-tools` is a non-default Cargo feature (`dev-tools = ["dep:tauri-plugin-mcp"]`), only enabled by `tauri dev --features dev-tools`; `tauri build` never enables it, so the Rust side of this plugin is compiled out of release entirely (comment at Cargo.toml:17-19 states this explicitly). JS side: `tauri-plugin-mcp` only appears in `src/app/page.tsx` and `src/lib/dev-mcp-bridge.ts`, both dev-tooling. |
| `nanoid` | HIGH | `postcss` (devDependency) | **DEV-ONLY** | Non-secure generator can loop indefinitely on negative size — build tooling only. |
| `postcss@8.5.14` | MODERATE | direct devDependency + `vite>postcss` | **DEV-ONLY** | Incomplete fix of a prior sourceMappingURL advisory (reads arbitrary `.map` files when `from` is unset) — build-time only, fixed by the 1.2 patch bump above (8.5.23+). |
| `browserslist`, `baseline-browser-mapping` | HIGH/MODERATE | `eslint-plugin-react-hooks` (devDependency) → `@babel/core` | **DEV-ONLY** | Lint tooling transitive. |
| `vitest`, `@vitest/mocker` | MODERATE | direct devDependency | **DEV-ONLY** | Test runner only. |

**Net runtime security exposure from `pnpm audit`: exactly 3 items** —
2 `@tiptap/core` advisories (1 high, 1 moderate) and 1 `dompurify` advisory
(low). All three already have upstream fixes available at or below the
"latest" versions `pnpm outdated` already reports (tiptap 3.31.3 satisfies
both fix floors of 3.30.4/3.30.5; dompurify's fix ships transitively once
`jspdf` is bumped — `jspdf` itself is not in the `pnpm outdated` list, meaning
`jspdf@4.2.1`'s own dependency range on dompurify needs checking at bump time,
not just a jspdf version bump). Everything else flagged by the audit is
dev/build tooling with no path into the shipped static-export bundle or the
release Tauri binary.

---

## 2. Rust / cargo (`src-tauri/`)

`cargo-outdated` and `cargo-audit` are **not installed**; per instructions
none were installed. Used crates.io's public JSON API for latest versions and
OSV.dev's public API (covers RustSec + GitHub Security Advisories for
`crates.io` ecosystem) for known vulnerabilities — no `cargo build`/`test`/
`clippy` was run.

### 2.1 Key crates (brief's named list) vs. crates.io latest stable

| Crate | Locked (`Cargo.lock`) | Latest stable | Gap | OSV hit on locked version? |
|---|---|---|---|---|
| `tauri` | 2.11.1 | 2.11.5 | patch | none |
| `tauri-build` | 2.6.1 | 2.6.3 | patch | none |
| `tauri-plugin-shell` | 2.3.5 | 2.3.6 | patch | none |
| `tauri-plugin-updater` | 2.10.1 | 2.11.0 | minor | none |
| `tauri-plugin-global-shortcut` | 2.3.1 | 2.3.2 | patch | none |
| `tauri-plugin-notification` | 2.3.3 | 2.4.0 | minor | none |
| `keyring` | 3.6.3 | **4.2.0** | **major** | none |
| `tokio` | 1.52.3 | 1.53.1 | patch | none |
| `reqwest` | 0.13.3 (transitive, via `tauri-plugin-updater`) | 0.13.5 | patch | none |
| `serde` | 1.0.228 | 1.0.229 | patch | none |
| `serde_json` | 1.0.149 | 1.0.151 | patch | none |

No CVEs found against any of these at their locked versions. The one real
flag is **`keyring` 3.6.3 → 4.2.0 (major)**: CLAUDE.md's own Gotchas record
that keyring v3 already needed explicit backend-feature flags
(`apple-native`, `windows-native`, `sync-secret-service`, `crypto-rust` —
`src-tauri/Cargo.toml:34`) and that `set_password` silently no-ops without
them. A major bump to v4 is exactly the kind of change that could rename or
restructure those backend features and silently degrade to a no-op secret
store on one platform without a build error. **Do not bump this without
reading keyring 4.x's migration notes and re-testing `keychain_set/get` on
all three OSes** — this is BYOK-secret-critical code.

### 2.2 Full-lockfile OSV sweep (643 crates.io-sourced packages, batch-queried;
not requested by the brief's fallback path but cheap and caught real hits the
"key crates" list would have missed)

17 hits across 12 unique crates, all **transitive**:

| Crate | Locked | Advisory | Sev | Pulled in by |
|---|---|---|---|---|
| `rustls` | 0.23.40 | RUSTSEC-2026-0285 — TLS 1.3 handshake messages accepted across encryption-level boundaries | CVSS 3.1 (network, low complexity) | `reqwest` + `tauri-plugin-updater` (confirmed: `hyper-rustls`, `tokio-rustls`, `rustls-platform-verifier` all list `rustls` as a dependency in `Cargo.lock`) — **this is on the auto-updater's HTTPS fetch path**, a real trust boundary. Fixed ≥0.23.45; locked is 0.23.40, i.e. already past the vulnerable floor's introduction (0.23.13) and short of the fix by a handful of patch releases. |
| `quick-xml` | 0.30.0 / 0.37.5 / 0.39.4 (3 resolved versions coexist) | RUSTSEC-2026-0194 (quadratic-time duplicate-attribute check), RUSTSEC-2026-0195 (unbounded namespace-decl allocation → memory-exhaustion DoS) | High (network DoS) | transitive (XML parsing dep tree — likely `zip`/font or plist tooling under Tauri's bundler chain); fixed ≥0.41.0. |
| `tar` | 0.4.45 | GHSA-3pv8-6f4r-ffg2 — PAX header desync | Moderate | transitive (bundler/archive chain). Fixed 0.4.46. |
| `glib` | 0.18.5 | RUSTSEC-2024-0429 / GHSA-wrw7-89jp-8q8g — unsound `VariantStrIter` iterator impls | Low-ish (CVSS4 VC:N) | transitive (GTK bindings, Linux Tauri webview backend). Fixed 0.20.0. |
| `rand` | 0.8.5 | GHSA-cq8v-f236-94qc / RUSTSEC-2026-0097 | Low | transitive, widespread. Fixed 0.8.6 (patch). |
| `serde_with` | 3.20.0 | GHSA-7gcf-g7xr-8hxj — `KeyValueMap` panic on empty sequence | Low (local DoS via panic) | transitive. Fixed 3.21.0. |
| `anyhow` | 1.0.102 | RUSTSEC-2026-0190 — unsoundness in `Error::downcast_mut()` | None rated | transitive. Fixed 1.0.103 (patch). |
| `memmap2` | 0.9.10 | RUSTSEC-2026-0186 — unchecked pointer offset | None rated | transitive. Fixed 0.9.11 (patch). |
| `event-listener` | 5.4.1 | RUSTSEC-2026-0221 — `!Send` crosses thread boundary | None rated | transitive. Fixed 5.4.2 (patch). |
| `proc-macro-error` | 1.0.4 | RUSTSEC-2024-0370 | Unmaintained (not a vuln) | transitive, build-time only. |
| `unic-char-property`/`unic-char-range`/`unic-common`/`unic-ucd-ident`/`unic-ucd-version` | 0.9.0 | RUSTSEC-2025-0081/0075/0080/0100/0098 | Unmaintained (not vulns) | transitive Unicode tables, no upstream fix exists (crate is dead). |

None of these are in the brief's "key crates" list, so a `cargo update` alone
(without touching `Cargo.toml` version pins) resolves most of the real ones
(`rand`, `anyhow`, `memmap2`, `event-listener` are all patch-level fixes
already compatible with current `^` requirements — `cargo update -p <crate>`
gets them for free). `rustls`, `tar`, `quick-xml`, `glib` need their
*parent* crates bumped first since they're pinned by range through
intermediate dependents — a full `cargo update` (not run here, per the "no
cargo commands" rule) would very likely pick these up too since none require
a manifest edit at the leaf.

---

## 3. Python / sidecar (`sidecar/.venv`, Python 3.13.13)

`pip-audit` is **not installed** in the venv; none was installed. Used
`pip list --outdated --format json` (179 packages installed, 104 outdated)
plus an OSV.dev batch query against all 179 *installed* versions (not just
the outdated ones — catches a vuln fixed by a version pip doesn't consider
"latest" for other reasons, though none turned up here).

### 3.1 Direct pins (`sidecar/requirements.txt` + `requirements-dev.txt`) vs PyPI latest

| Package | Pinned | Latest | Gap | Risk class |
|---|---|---|---|---|
| `yfinance` | 1.3.0 | 1.7.0 | 4 minors | **Breaks-against-today's-world candidate** — brief names it explicitly; Yahoo Finance changes its unofficial endpoints often enough that yfinance ships breaking fixes as patch/minor releases, not just features. |
| `jugaad-data` | 0.33.1 | 0.35.5 | — | **Live-scraper drift** — wraps the live NSE website (`sidecar/requirements.txt:108-116`, comment: "Verified live against NSE 2026-06-01"). PyPI shows jugaad-data's own latest release was 2026-08-25 — i.e. the upstream maintainer has already shipped 2+ releases past what this repo verified, almost certainly in response to NSE site changes. This is the single highest-velocity dependency in the whole tree (it exists *because* the site it wraps changes) and the repo's own comment says it was last checked 3+ months ago. |
| `curl_cffi` | 0.15.0 | 0.16.3 | — | Browser-TLS-impersonation library for the keyless T1 search tier + NSE anti-bot bypass (`requirements.txt:8-12` comment). Fingerprint databases go stale as target sites update bot detection — same class of risk as jugaad-data, one layer down. |
| `anthropic` | 0.100.0 | **1.7.0** | **major (0.x→1.x)** | Provider SDK powering `sidecar/services/llm/anthropic.py`. A 0→1 major on a first-party LLM SDK is exactly the kind of bump that renames client methods/response shapes; CLAUDE.md's own Gotchas record adapter-shape fragility on the sibling OpenAI adapter (gpt-5.x `reasoning_effort` 400-repair, `services/llm/` `tool_ids` popping) — same class of code, same risk. |
| `openai` | 2.36.0 | **3.16.2** | **major** | `sidecar/services/llm/openai.py`. CLAUDE.md documents two live 400-error workarounds against this exact SDK/API surface (native-search gating, `reasoning_effort` repair) — a major bump is likely to touch precisely those code paths. |
| `google-genai` | `>=1.0` (**unpinned floor**) | 2.24.0 | installed is 2.5.0 | **Reproducibility gap, not just drift**: the floor-only constraint means a fresh `pip install -r requirements.txt` today resolves to 2.24.0, not the 2.5.0 this venv was actually tested against — two machines building the same commit get different SDKs. Named explicitly in the brief's API-churn list. |
| `fastmcp` | 3.2.4 | **4.0.5** | **major** | Mounts the MCP server (`sidecar/services/mcp_server.py:134`, `FastMCP("vysted")`) that CLAUDE.md's Gotchas describe as catalog-projected (`mcp_capabilities()` → `FunctionTool(parameters=<schema>, fn=<handler>)`). A major fastmcp bump is core-architecture-adjacent for this repo specifically. Upgrading it also fixes the `mcp` SDK CVEs below (fastmcp 4.x pulls a newer `mcp`), but that means the fix path is coupled to a major-version review, not a quiet patch bump. |
| `groq` | 1.1.1 | 1.7.0 | minor-ish | Third BYOK provider SDK, same file family as above. |
| `ccxt` | 4.5.53 | 4.5.78 | 25 patch releases behind | ccxt ships near-daily releases tracking individual exchange API changes; this many releases behind on a crypto-exchange integration library means several exchange-side breakages have already shipped fixes upstream that this pin doesn't have. |
| `fastapi` | 0.136.1 | 0.141.1 | minor | Core sidecar framework, low risk at this range. |
| `uvicorn` | 0.46.0 | 0.53.0 | minor | ASGI server, low risk. |
| `dhanhq` | 2.1.0 | 2.2.0 | minor | Broker SDK (read-only wrapper path, §6.5). |
| `kiteconnect` | 5.2.0 | 5.2.2 | patch | Broker SDK — see 3.2, `autobahn` risk rides under this one. |
| `alpaca-py` | 0.42.0 | 0.44.0 | minor | Broker SDK. |
| `pypdf` | 6.13.1 | 6.19.0 | 6 minors | **See 3.2 — carries live advisories.** PDF text extraction for the research-visit path. |
| `numpy`, `pandas`, `beautifulsoup4`, `feedparser`, `sdmx1`, `QuantLib` | — | — | minor/patch | Low risk, routine bump candidates. |
| `jsonschema` | `>=4.0` (**unpinned floor**) | — | installed 4.26.0 | Same reproducibility issue as google-genai, lower blast radius (schema validation, not a provider API). |
| `httpx`, `ollama`, `vaderSentiment`, `ib_async`, `oandapyV20`, `wbgapi`, `ecbdata`, `fredapi`, `smartapi-python` | — | — | **already at PyPI latest** | See 3.3 for why "at latest" isn't the same as "healthy" for two of these. |
| `pyinstaller` (dev) | 6.20.0 | 6.22.3 | minor | Build tooling. |
| `ruff` (dev) | 0.15.12 | 0.16.8 | minor | Lint tooling — already gated by `ci-local`'s ruff step. |
| `pytest`, `pytest-asyncio` (dev) | 9.0.3 / 1.3.0 | 9.1.1 / 1.4.0 | patch | Test tooling. |

### 3.2 OSV.dev hits against *installed* versions (batch query, 179 packages → 16 hit) — runtime-vs-dev + reachability

| Package | Installed | Direct or transitive | Runtime reachability | Worst advisory |
|---|---|---|---|---|
| `mcp` | 1.27.1 | transitive, via `fastmcp` (`pip show mcp` → `Required-by: fastmcp`) | **RUNTIME, but loopback-only** — `sidecar/app.py:340-344` mounts FastMCP's Streamable-HTTP transport at `/mcp` on the same app that `sidecar/app.py:299` binds to `127.0.0.1` only. | 3× **HIGH**: cross-client task cancellation, HTTP transport skips principal auth, WebSocket transport has no Host/Origin validation. Real bugs, but exploitability requires code already running on the same machine — at that point the attacker already has broader access than this endpoint grants. Still worth fixing; fix requires the `fastmcp` major bump (3.1). |
| `cryptography` | 48.0.0 | transitive (`Required-by: Authlib, autobahn, ccxt, google-auth, joserfc, pyOpenSSL, service-identity`) | **RUNTIME** — sits under nearly every outbound-TLS and JWT path in the sidecar (broker SDKs, Google auth for `google-genai`, JWT via `joserfc`). | 3× **HIGH**: bundled-OpenSSL CVEs, a PKCS#7 Bleichenbacher oracle, exponential path-building DoS via duplicate self-signed intermediates. 2 majors behind (48→50). Given how central this crate is, it's the single highest-leverage Python bump on the list. |
| `aiohttp` | 3.13.5 | transitive | Runtime if any dependent uses aiohttp's client/server at runtime (needs a per-dependent check beyond this audit's scope) | 1× HIGH (heap read in C parser on malformed chunked response), rest moderate/low. 27 advisory IDs total but many are duplicate GHSA/PYSEC aliases for the same handful of distinct bugs. |
| `PyJWT` | 2.12.1 | transitive | Runtime if `PyJWKClient` is used anywhere (JWT verification path) | 1× **HIGH**: public-key JWK accepted as an HMAC secret, forging HS256 tokens when key families are mixed — classic JWT `alg` confusion. Worth a direct check of any JWT-verification call site before a public release even though this audit didn't locate one. |
| `starlette` | 1.0.0 | transitive, `Required-by: fastapi, mcp, sse-starlette` | **RUNTIME** — the ASGI layer under every sidecar route | 2× HIGH: `request.form()` limits silently ignored (DoS), `StaticFiles` SSRF/NTLM-credential-theft via UNC paths **on Windows** — this repo explicitly ships on Windows (CLAUDE.md: "Builds stay green on Windows, macOS, Linux"), so this one is not theoretical for this project. |
| `python-multipart` | 0.0.29 | transitive, `Required-by: mcp` (not fastapi in this tree) | **RUNTIME** — wired in via the same `/mcp` Streamable-HTTP transport as the `mcp` SDK findings above, not dead weight | 4 advisories, DoS-class (unbounded multipart parsing). |
| `autobahn` | 19.11.2 | transitive, `Required-by: kiteconnect` | **RUNTIME on the broker path** (§6.5-adjacent — read-only per CLAUDE.md's Kite Connect flow, but this library is Kite's websocket/WAMP layer) | 1 moderate open-redirect. Bigger issue: **latest release was 2019** — this is an abandoned dependency with no upstream fix path; whatever `kiteconnect` version range is pinning it, there is no newer autobahn to move to without kiteconnect itself dropping the dependency. |
| `soupsieve`, `joserfc`, `msgpack`, `pyasn1`, `h2`, `anyio`, `setuptools`, `pydantic-settings` | various | mostly transitive via `beautifulsoup4`/`fastmcp`/`google-auth` chains | Mixed | Lower-severity or narrow-precondition advisories (symlink traversal for `pydantic-settings`'s `NestedSecretsSettingsSource`, algorithm-confusion classes for `joserfc`). Full IDs preserved in the raw OSV dumps referenced in §5 if a deeper pass is wanted. |

### 3.3 "At PyPI latest" but not actually healthy

- **`vaderSentiment` 3.3.2`** — this **is** the latest version on PyPI, but PyPI's own metadata shows it was published **2020-05-22**. The package is abandoned upstream (no release in 6+ years); "not outdated" here just means there is nothing to update *to*, not that it's maintained.
- **`oandapyV20` 0.7.2`** — same shape: latest release was **2021-08-27**, a forex-broker SDK with no activity in 5 years.
- Neither shows a known CVE via OSV, but both are single-point-of-failure unmaintained dependencies on data/broker paths, worth a conscious "accept the risk" decision for a public release rather than silent staleness.

---

## 4. Top 10 drift risks for a public release, ranked

1. **`@tiptap/core` 3.25.0 (JS, runtime)** — 1 HIGH (ReDoS) + 1 MODERATE
   (prototype-style DOM-attribute injection) advisory, both already fixed
   upstream (bump the whole `@tiptap/*` family to ≥3.31.3). Concrete,
   low-effort, highest-confidence fix on this whole list — do this first.
2. **Python `cryptography` 48.0.0 (2 majors behind, transitive, runtime)** —
   3 HIGH advisories (bundled OpenSSL CVEs, Bleichenbacher oracle, DoS via
   cert chains) sitting under nearly every TLS/JWT/broker path in the
   sidecar. Highest-leverage single bump in the Python tree.
3. **`fastmcp` 3.2.4 → 4.0.5 (Python, major, runtime)** — architecture-adjacent
   (the MCP catalog-projection layer CLAUDE.md documents in detail) and the
   only real fix path for the 3× HIGH `mcp` SDK advisories. Needs a real
   regression pass on `mcp_capabilities()`/`FunctionTool` projection, not a
   drive-by bump — but blocking on it leaves 3 HIGH CVEs unpatched on a
   RUNTIME (if loopback-scoped) MCP transport.
4. **`anthropic` 0.100.0 → 1.7.0 and `openai` 2.36.0 → 3.16.2 (Python, both
   major, runtime)** — the two first-party LLM provider SDKs, both a major
   version behind, both sitting exactly where CLAUDE.md documents existing
   fragile provider-API workarounds. Highest "breaks against today's world"
   risk on the list precisely because provider SDKs change response/tool-call
   shapes across majors without warning.
5. **`google-genai` unpinned floor (`>=1.0`) — reproducibility gap, not just
   drift.** Two machines installing the same commit today get different SDK
   versions (2.5.0 tested vs. 2.24.0 resolved fresh). Pin it exactly before a
   public release ships instructions to `pip install -r requirements.txt`.
6. **`jugaad-data` 0.33.1 (Python, direct, runtime)** — wraps a live scraped
   website; upstream has shipped releases as recently as 2026-08-25 (this
   repo's own comment says it was last verified live 2026-06-01, 3+ months
   stale). Highest velocity of any dependency in the tree because it exists
   *to track* a moving target.
7. **`starlette` 1.0.0 (Python, transitive, runtime)** — 2 HIGH advisories,
   one of which (`StaticFiles` SSRF/NTLM-credential theft via UNC paths) is
   **Windows-specific**, and this repo explicitly ships on Windows.
8. **Rust `rustls` 0.23.40 (transitive, on the auto-updater's HTTPS path)** —
   RUSTSEC-2026-0285, TLS 1.3 handshake message boundary confusion. Sits
   directly under `tauri-plugin-updater` + `reqwest`; a `cargo update`
   (patch-range only, not run here) likely resolves it without a manifest
   edit.
9. **`keyring` 3.6.3 → 4.2.0 (Rust, major)** — no known CVE, but this exact
   crate has already bitten this repo once on a feature-flag rename
   (documented in CLAUDE.md's own Gotchas). A major bump needs a manual
   cross-platform `keychain_set/get` re-test before it's safe, not a
   version-number edit.
10. **`autobahn` 19.11.2 (Python, transitive via `kiteconnect`, broker path)**
    — abandoned since 2019, one moderate open-redirect advisory, no upstream
    fix path available short of `kiteconnect` itself dropping it. Paired with
    `oandapyV20` and `vaderSentiment` as three unmaintained upstream
    dependencies worth a conscious accept-the-risk sign-off before a public
    release rather than silent staleness.

**Not on the top 10, but should not be silently ignored:** `dompurify`
(low-severity, runtime, PDF export path), `pypdf` (6 minors behind with
several open advisories, runtime, research PDF-extraction path — deserves its
own look given how many distinct GHSA IDs it carries), `mcp`/`python-multipart`
HIGH advisories (real, but meaningfully mitigated by the confirmed
127.0.0.1-only bind at `sidecar/app.py:299`), `ccxt` (25 patch releases
behind — routine but worth clearing before a release), `PyJWT`'s HS256/JWK
algorithm-confusion HIGH advisory (only matters if `PyJWKClient` is actually
used somewhere in this tree — this audit did not locate the call site and
did not have budget to grep the full transitive-dependency call graph; verify
before dismissing).

---

## 5. Method notes / raw evidence

- `pnpm outdated --format json` and `pnpm audit --json` ran directly against
  the live `pnpm-lock.yaml`; raw output saved during this session (not
  committed) at the scratchpad paths `pnpm_outdated.json` / `pnpm_audit.json`.
- Rust: no `cargo outdated`/`cargo audit` binaries present (`cargo outdated`
  → "no such command"), none installed. Crate versions came from
  `src-tauri/Cargo.lock` (`grep -A2 'name = "<crate>"'`); latest-version
  numbers from `https://crates.io/api/v1/crates/<crate>` (`max_stable_version`
  field); vulnerability data from `https://api.osv.dev/v1/query` (single) and
  `/v1/querybatch` (full 643-package lockfile sweep, crates.io-sourced
  packages only — the two git deps, `tauri-plugin-mcp`, were excluded from
  the OSV sweep since OSV's crates.io ecosystem doesn't resolve git refs).
- Python: `sidecar/.venv/bin/pip list --outdated --format json` and
  `pip list --format json` (179 installed packages) against the existing venv
  — no `pip install` of anything, including pip-audit (confirmed absent via
  `pip show pip-audit` → not found). Vulnerability data from the same OSV.dev
  `/v1/query` + `/v1/querybatch` endpoints, ecosystem `PyPI`. Dependency-chain
  attribution (`Required-by:`) came from `pip show <pkg>` against the live
  venv. Package-recency checks (`vaderSentiment`, `oandapyV20`, `jugaad-data`,
  etc.) came from `https://pypi.org/pypi/<pkg>/json`.
- Code-reachability claims are anchored: `sidecar/app.py:299` (127.0.0.1-only
  bind), `sidecar/app.py:340-344` (FastMCP mount point), `sidecar/services/
mcp_server.py:134` (`FastMCP("vysted")`), `sidecar/services/llm/anthropic.py`
  + `openai.py` (provider SDK call sites, confirmed present, not opened
  line-by-line beyond confirming the import), `src-tauri/Cargo.toml:16-27`
  (`dev-tools` feature gate), `src/lib/export-artifact.ts` (jspdf/dompurify
  call site), `sidecar/requirements.txt:1-116` (all direct-pin line numbers).
  `grep -rln "UploadFile\|multipart" sidecar/routers/ sidecar/app.py` returned
  no hits — `python-multipart`'s reachability claim rests on `mcp`'s own
  dependency declaration (`Required-by: mcp`), not a direct FastAPI upload
  route in this codebase.
- No GUI interaction, no process start/stop/kill, no `pytest`/`cargo test`/
  `cargo clippy`/PyInstaller/production build was run. No secret values were
  printed, echoed, or logged — only provider/package *names* appear above.
  The live dev stack (pids ~97534-98007, sidecar on 127.0.0.1:52052) was not
  touched; this audit needed no read requests against it.
