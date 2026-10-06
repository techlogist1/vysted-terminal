<!-- SCAN at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave -->

# Dependency licence scan — 4d893147

Read-only scan, no installs run. Full machine data: `DEPS_LICENCES.json`.
REFRESH of the prior scan at `f4444790` (see **Since f4444790** below).

## Method per ecosystem

- **pnpm** (frontend, static export): `pnpm licenses list --json --prod` for the
  bundled set, `pnpm licenses list --json` for the full set (prod + dev). `dev-only`
  = full set minus the prod set by name@version. `pnpm-lock.yaml` matches the sha
  (`git diff --quiet 4d893147 -- pnpm-lock.yaml`).
- **cargo** (src-tauri, compiled into the app binary): `cargo metadata --format-version 1
  --no-deps --manifest-path src-tauri/Cargo.toml` for the app's own licence fields, then
  `cargo metadata --format-version 1 --locked --offline` for the full resolve graph.
  Scope is computed by BFS from the root over `resolve.nodes[].deps[].dep_kinds`: a
  crate reachable via an all-normal-edge path is `bundled`; else reachable via a path
  needing a build edge is `build-only`; else via a dev edge is `dev-only`.
  `src-tauri/Cargo.lock` matches the sha. `cargo-license` is absent from PATH — cargo
  metadata's own `license`/`license_file` fields were used instead, per the role's
  fallback instruction.
- **Python** (three venvs, each frozen into its own PyInstaller `--onefile` binary per
  `FACTS.md`): for each, `scripts/r15/licence_scan.py <requirements.txt>` walks the
  `Requires-Dist` closure from the requirements roots (markers evaluated for this
  platform, extras followed) — those rows are `bundled`. `pip list --format json` gives
  the full installed set; anything outside the closure is `dev-only`. All three
  `requirements.txt` files match the sha. `pip-licenses` is absent from PATH.
  The PyInstaller bootloader itself (GPL, with the PyInstaller bootloader exception) is
  recorded as one `bundled` row per binary (`PyInstaller-bootloader` / `embedded`).

All five lockfile/requirements inputs (`pnpm-lock.yaml`, `src-tauri/Cargo.lock`,
`sidecar/requirements.txt`, `sidecar/openbb_mcp_subprocess/requirements.txt`,
`sidecar/sec_edgar_mcp_subprocess/requirements.txt`) match the sha
(`git diff --quiet 4d893147... -- <file>`, all clean) — no ecosystem carries the
"installed tree differs from the sha" caveat.

## Counts by ecosystem

| Ecosystem | Bundled packages | Dev-only / other packages |
|---|---:|---:|
| pnpm (frontend) | 205 | 459 |
| cargo (src-tauri) | 542 (+ 26 build-only) | 0 dev-only |
| python/sidecar | 125 (incl. bootloader row) | 55 |
| python/openbb_mcp | 106 (incl. bootloader row) | 6 |
| python/sec_edgar_mcp | 68 (incl. bootloader row) | 7 |

pnpm licence keys present in the bundled (prod) set: MIT, `Apache-2.0 OR MIT` /
`MIT OR Apache-2.0`, Apache-2.0, ISC, BSD-3-Clause, `(MPL-2.0 OR Apache-2.0)`,
`(MIT AND Zlib)`, 0BSD. None contain AGPL/GPL/LGPL/SSPL/EUPL/OSL/CC-BY-NC/Commons
Clause/BUSL and none are empty/unknown — pnpm has no flagged rows.

## Flagged (bundled copyleft first)

| Ecosystem | Package | Version | Licence | Scope / linkage | Note |
|---|---|---|---|---|---|
| python/openbb_mcp | openbb-core | 1.6.9 | AGPL-3.0-only | bundled — Python module frozen into the **openbb-mcp** PyInstaller binary | OSI classifier: GNU Affero General Public License v3 |
| python/openbb_mcp | openbb-economy | 1.6.1 | AGPL-3.0-only | bundled — frozen into the **openbb-mcp** binary | same classifier |
| python/openbb_mcp | openbb-equity | 1.6.1 | AGPL-3.0-only | bundled — frozen into the **openbb-mcp** binary | same classifier |
| python/openbb_mcp | openbb-fmp | 1.6.0 | AGPL-3.0-only | bundled — frozen into the **openbb-mcp** binary | same classifier |
| python/openbb_mcp | openbb-fred | 1.6.0 | AGPL-3.0-only | bundled — frozen into the **openbb-mcp** binary | same classifier |
| python/openbb_mcp | openbb-mcp-server | 1.4.0 | AGPL-3.0-only | bundled — frozen into the **openbb-mcp** binary | same classifier |
| python/openbb_mcp | openbb-news | 1.6.0 | AGPL-3.0-only | bundled — frozen into the **openbb-mcp** binary | same classifier |
| python/openbb_mcp | openbb-yfinance | 1.6.2 | AGPL-3.0-only | bundled — frozen into the **openbb-mcp** binary | same classifier |
| python/sec_edgar_mcp | sec-edgar-mcp | 1.0.8 | AGPL-3.0 | bundled — Python module frozen into the **sec-edgar-mcp** PyInstaller binary | OSI classifier: GNU Affero General Public License v3 |
| python/sec_edgar_mcp | Unidecode | 1.4.0 | GPL | bundled — frozen into the **sec-edgar-mcp** binary | OSI classifier: GNU General Public License v2 or later (GPLv2+) |
| python/sidecar | frozendict | 2.4.7 | LGPL v3 | bundled — frozen into the **main sidecar** binary | OSI classifier: GNU Lesser General Public License v3 (LGPLv3) |
| python/openbb_mcp | frozendict | 2.4.7 | LGPL v3 | bundled — same package also frozen into the **openbb-mcp** binary | same classifier |
| cargo | r-efi | 5.3.0 | `MIT OR Apache-2.0 OR LGPL-2.1-or-later` | bundled *only* under `cfg(all(target_os="uefi", getrandom_backend="efi_rng"))`, pulled in transitively via `getrandom`; this app builds macOS/Windows/Linux desktop targets only, so this edge is never active in a shipped artifact — would be a static Rust crate in `src-tauri` if it ever were | flagged because the licence string contains "LGPL"; it is an OR-licensed choice (MIT/Apache-2.0 selectable without LGPL obligations) and the edge is target-gated off |
| cargo | r-efi | 6.0.0 | `MIT OR Apache-2.0 OR LGPL-2.1-or-later` | same as above (second resolved version in the lockfile) | same note |
| python/sidecar | caio | 0.9.25 | (empty) | bundled — frozen into the **main sidecar** binary | installed metadata License field empty; PyPI JSON `info.license`/`info.license_expression` both null, no `License ::` classifiers (checked 2026-09-26) |
| python/openbb_mcp | caio | 0.9.25 | (empty) | bundled — same package also frozen into the **openbb-mcp** binary | same PyPI check |
| python/sidecar | fredapi | 0.5.2 | (empty) | bundled — frozen into the **main sidecar** binary | same PyPI check (empty at registry) |
| python/sidecar | peewee | 4.0.6 | (empty) | bundled — frozen into the **main sidecar** binary | same PyPI check (empty at registry) |
| python/openbb_mcp | peewee | 4.0.6 | (empty) | bundled — same package also frozen into the **openbb-mcp** binary | same PyPI check |
| python/sec_edgar_mcp | httpxthrottlecache | 0.3.5 | (empty) | bundled — frozen into the **sec-edgar-mcp** binary | same PyPI check (empty at registry) |

20 flagged rows total (9 unique AGPL/GPL/LGPL packages across venvs/versions, 2 r-efi
LGPL-string rows that are target-gated off, 5 unique empty-licence packages appearing
across venvs). These are the facts as scanned; no legal conclusion about compatibility
with the PolyForm Strict core is drawn here.

## Not scanned

- `cargo-license` and `pip-licenses`: absent from PATH (per `FACTS.md` tools section);
  fell back to `cargo metadata` and the repo's `scripts/r15/licence_scan.py`.
- Python dev-only rows (pip-list-full minus the closure) carry no licence text — the
  closure tool is the only lane that resolves licence metadata, and it only walks
  `Requires-Dist` from the requirements roots, so dev-only rows in `DEPS_LICENCES.json`
  are marked `licence: null` rather than a scanned licence.
- No GUI, no sidecar boot, no installs were run for this scan (lane restrictions).

## Since f4444790 (previous Stage D scan)

**Verdict: no real dependency or licence change.** Only `pnpm-lock.yaml` moved between
the two shas (`git diff f4444790..4d893147 -- pnpm-lock.yaml`: `+3/-0`), and that change
adds a direct-importer specifier for `@tiptap/extension-list` — a package already
resolved transitively at the previous sha with the identical version (`3.25.0`) and
licence (`MIT`). `src-tauri/Cargo.lock` and all three `requirements.txt` files are
byte-identical between the two shas (`git diff --quiet`, no output).

Per-ecosystem package-identity diff (name@version present/absent, or licence/scope
changed), cross-checked field-by-field against the previous `DEPS_LICENCES.json`:

| Ecosystem | Added | Removed | Changed |
|---|---:|---:|---:|
| pnpm | 0 | 0 | 0 |
| cargo | 0 | 0 | 0 |
| python/sidecar | 0 real (1 label artifact) | 0 real (1 label artifact) | 0 real (58 label artifacts) |
| python/openbb_mcp | 0 real (1 label artifact) | 0 real (1 label artifact) | 0 real (8 label artifacts) |
| python/sec_edgar_mcp | 0 real (1 label artifact) | 0 real (1 label artifact) | 0 real (8 label artifacts) |

The python "added/removed/changed" rows this run's raw JSON diff surfaces are every one
a naming-convention artifact of **this run's own output shape** versus the previous
run's, not a real package-set or licence change on disk:
- the bootloader row's key changed from `PyInstaller bootloader` / `n/a (embedded...)`
  (previous run) to `PyInstaller-bootloader` / `embedded` (this run) — same fact, same
  package, different label string;
- dev-only python rows carry `licence: null` this run vs. the previous run's explicit
  placeholder string `"(not scanned by closure tool; classifier lookup not run)"` — same
  underlying fact (no licence data was collected for dev-only rows either time);
- the 4 empty-licence bundled rows (`caio`, `peewee`, `httpxthrottlecache`) show
  `licence: ""` (previous) vs. `licence: null` (this run) — both mean "empty", re-curled
  against PyPI just now and still empty at the registry.

**Flagged table: identical, 20/20.** Once the ecosystem-label spelling is normalised
(`python/sidecar` vs. `python-sidecar`, etc.), `flagged_added` and `flagged_removed` are
both empty — the same 9 unique AGPL/GPL/LGPL packages, the same 2 target-gated r-efi
LGPL-string rows, and the same 5 unique empty-licence packages, at the same versions,
across the same three venvs.
