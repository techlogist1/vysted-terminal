<!-- SCAN at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave -->

# Licence consistency check — 4d893147

## Intended state (operator decision, DECISIONS_FOR_OPERATOR.md §1.4)

Core under **PolyForm Strict 1.0.0** (public, noncommercial-use) + a **commercial licence**
as the only other path. The plugin contract (`types/plugin.ts`, `types/plugin-runtime.ts`)
and the example plugin (`plugins/example/*`) are carved out under **Apache-2.0**. Every
commit **before** the relicensing commit (subject `chore(license): relicense core to
PolyForm Strict 1.0.0`, D83, landed as `0c63d46`) remains AGPL-3.0 — historical fact, not a
current claim. `LICENSE` text sha256 recorded by the operator decision:
`e2361f52ad5be22b937a6e983c824a534c5cffa454b6c34af2f8ce0c2cdf7c1a` — **verified**: `git show
4d893147:LICENSE | shasum -a 256` at this sha reproduces that exact hash (network fetch
against polyformproject.org skipped as redundant, matching the prior scan's precedent).

## Mismatch table

| file | line | exact text quoted | one-line fix | tier |
|---|---|---|---|---|
| CLAUDE.md | 57–58 | "1. **Locked** — `docs/BLUEPRINT.md` §2. Never reopen unilaterally. (Stack; AGPL-3.0 + commercial dual license; MCP server in v1.0.)" | Replace with the PolyForm Strict 1.0.0 wording already drafted in `docs/redesign/CLAUDE_MD_PROPOSAL.md:76` ("Stack; PolyForm Strict 1.0.0 + commercial license (relicensed 23 Sep 2026); MCP server...") | **Tier-1: operator** |

Still the only mismatch, still known and queued (not a fresh discovery): DECISIONS_FOR_OPERATOR.md
§3.4 states "apply the queued CLAUDE.md edits in docs/redesign/CLAUDE_MD_PROPOSAL.md when
convenient," and CLAUDE_MD_PROPOSAL.md:72–83 carries the exact before/after diff. CLAUDE.md is
itself a Tier-1 file per this wave's brief, so it is listed, not edited.

## Since f4444790 (previous scan sha)

Byte-identical on every licence-encoding file: `git diff f4444790..4d893147 --` over the full
checklist (`LICENSE`, `LICENSE-APACHE`, `LICENSING.md`, `COMMERCIAL_LICENSE.md`, `CLAUDE.md`,
`src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, `types/plugin.ts`, `types/plugin-runtime.ts`,
`CONTRIBUTING.md`, `.specify/memory/constitution.md`, `docs/redesign/CLAUDE_MD_PROPOSAL.md`,
`src/modules/safety/DisclaimerFlow.tsx`, `docs/PLUGIN_DEVELOPMENT.md`, `plugins/`, `README.md`,
`docs/redesign/AGENT_TOOLUSE_PLAN.md`, `src/lib/markdown-stream.ts`) returns empty. 411 commits
landed in this range (batches 12–24, LEAD-030/033/035/036 fix series, sidecar feature work); none
touch a licence-bearing file.

Four files in the checklist DID change in this range but not on their licence-relevant lines:
`package.json` (script + one new npm dep — `"license"` field at :4 untouched), `docs/BLUEPRINT.md`
(module-count/scope wording — §2 lines 8/58 untouched), `docs/README.md` (one table-row wording
tweak, no licence mention), `sidecar/app.py` (new router import, no licence string).
`sidecar/services/bse_provider.py` changed (new `_NOMINAL_RANGE_DAYS` dict, a removed dead URL
constant) but its licence docstring at lines 31–32 is untouched (confirmed same text, same lines).

`docs/redesign/DECISIONS_FOR_OPERATOR.md` grew by ~400 lines; its one sweep-caught licence
mention moved from line 200 → line 293 (new content inserted earlier in the doc shifted it) with
**identical wording** — not a new hit. The full sweep grep (below) returns the same 78 lines
across the same files as the prior scan, modulo that one line-number shift. **New, gone, changed:
none.**

## Consistent hits (compact)

- `LICENSE` — text verified byte-identical to the operator-recorded sha256 (see above).
- `LICENSE-APACHE` — present, standard Apache-2.0 text.
- `LICENSING.md` — PolyForm Strict grant, commercial-licence trigger list, Apache-2.0 plugin carve-out (lines 12, 25, 40–54) all match intended state.
- `COMMERCIAL_LICENSE.md:11,13,18,23,46,70` — PolyForm Strict + commercial path, Apache-2.0 carve-out reference, matches.
- `package.json:4` — `"license": "SEE LICENSE IN LICENSE"` (no SPDX id exists for PolyForm Strict; DECISIONS.md D83 records this as the deliberate choice) — consistent.
- `src-tauri/Cargo.toml:8` — `license-file = "../LICENSE"`, points at the PolyForm Strict text — consistent.
- `src-tauri/tauri.conf.json` — no `copyright`/licence field present at this sha; nothing to be inconsistent with.
- `plugins/{yfinance,openbb-mcp,vysted-lenses,vysted-news,example}/manifest.json` — none carry a `license` field (JSON can't carry a header comment; LICENSING.md:44–48 explicitly documents this for the example manifest) — consistent by design, not an omission.
- `types/plugin.ts:1`, `types/plugin-runtime.ts:1`, `plugins/example/index.ts:1`, `plugins/example/example.test.ts:1` — `SPDX-License-Identifier: Apache-2.0`. This is the complete set of *code* files carrying the SPDX header repo-wide — matches the Apache-2.0 carve-out exactly, no more, no less. (`git grep -lI "SPDX-License-Identifier"` also now hits four files under `docs/redesign/verification/r15/stage-d/` — `FACTS.json`, `FACTS.md`, `LICENCE_CHECK.md`, `README.draft.md` — but those are this wave's own prior scan *reports quoting the string as text*, not licence headers on code; excluded from the carve-out count.)
- sidecar metadata — no `pyproject.toml`/`setup.py`/`setup.cfg` exist under `sidecar/`; `sidecar/app.py` and package `__init__.py` files carry no licence string — nothing to check, consistent by absence.
- `sidecar/services/bse_provider.py:31–32` — docstring: "under the project's license (PolyForm Strict 1.0.0 + commercial; AGPL-3.0 on commits before the 23 Sep 2026 relicense)" — correctly current + correctly historical in the same sentence.
- `src/modules/safety/DisclaimerFlow.tsx:35` — "source-available under PolyForm Strict 1.0.0 (noncommercial use) or a commercial license — see LICENSING.md." — matches.
- `README.md:172,175–177` — License section: PolyForm Strict grant, commercial-licence trigger, Apache-2.0 carve-out — matches.
- `docs/BLUEPRINT.md:8,58,297,305,341–347,397` §2/§6.1 — fully updated to PolyForm Strict 1.0.0 + commercial, relicensed 23 Sep 2026 — matches (this is the file CLAUDE.md's stale line 57 points to as authoritative, sharpening the mismatch above).
- `CONTRIBUTING.md:88–98` — PolyForm Strict + commercial + Apache-2.0 carve-out, CLA language — matches.
- `.specify/memory/constitution.md:123` — "PolyForm Strict 1.0.0 +..." — matches.
- `docs/redesign/DECISIONS.md:143` (D83) and `docs/redesign/DECISIONS_FOR_OPERATOR.md:48–66,293` — both correctly narrate the relicense as an already-done, dated decision — consistent.
- `docs/redesign/CLAUDE_MD_PROPOSAL.md:72–83` — quotes the *old* AGPL-3.0 CLAUDE.md line (:72) alongside the *proposed* PolyForm Strict replacement (:76) as an explicit before/after diff — this is the fix already drafted for the mismatch above, not itself a mismatch.
- `docs/PLUGIN_DEVELOPMENT.md`, `docs/README.md` — no licence mentions at this sha; nothing to check.
- `.github/workflows/*.yml` — no licence mentions.

### Historical (correctly past tense, or pre-relicense point-in-time records)

- `LICENSING.md:28–33`, `COMMERCIAL_LICENSE.md:21`, `README.md:175` — "every commit before the relicensing commit stays/remains AGPL-3.0" — correct, deliberate historical carve-out.
- `docs/redesign/AGENT_TOOLUSE_PLAN.md:47,53,59,63–64,67,73,77,89,164,224,230,259` — a research/planning doc recording licensing analysis and an "Operator decisions locked (2026-06-09)" note, dated **before** the 23 Sep 2026 relicense (D83). It analyzes the pre-relicense AGPL-3.0 + commercial regime to justify reimplementing the BSE provider rather than importing GPL-3.0 code. DECISIONS.md D83 explicitly lists which files were swept for "current-fact" language (CLAUDE.md queued, CHANGELOG/docs/archive left untouched) and does not name this file — treated as a dated decision record, not a live current-state claim. Flagged as an open question below rather than a hard mismatch (unchanged from the prior scan).

### Third-party (a dependency's or reference project's own licence, not Vysted's)

- `docs/BLUEPRINT.md:677–678,681` — Fincept Terminal (AGPL-3.0 + commercial) and OpenBB (AGPL-3.0), cited as research references.
- `docs/redesign/REBUILD_R3_SPEC.md:478,636,644` — mathjs library, Apache-2.0.
- `docs/research/phase-10/study-fincept.md:272` — Fincept's own AGPL+commercial licensing.
- `src/lib/markdown-stream.ts:17` — attribution comment for logic ported from `vercel/streamdown` (Apache-2.0), describing that project's licence, not Vysted's.

## Open questions

- `docs/redesign/AGENT_TOOLUSE_PLAN.md` reads AGPL-3.0 as the live licence throughout (predates the 23 Sep relicense, not in D83's sweep scope). It sits under `docs/redesign/` (not `docs/archive/`), so a reader skimming only this file — without DECISIONS.md's dating context — could believe the project is still AGPL-3.0. Worth a one-line "superseded by the 23 Sep 2026 relicense, see LICENSING.md" note if the lead wants it addressed; not a hard mismatch here (dated decision record, not a current-state doc). Carried forward unresolved from the prior scan (no batch touched this file in the interim).
- No `LICENSE`/`COMMERCIAL_LICENSE.md`/`types/plugin.ts` edits were needed this pass either — the only actionable item across two scans at different shas is still the single CLAUDE.md line, already drafted in CLAUDE_MD_PROPOSAL.md and tracked as an open Tier-4 item (DECISIONS_FOR_OPERATOR.md §3.4).
