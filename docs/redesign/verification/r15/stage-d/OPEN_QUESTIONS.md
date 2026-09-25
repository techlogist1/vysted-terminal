<!-- DRAFT at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave; refresh before rc2 -->

# Open questions for the operator — Stage D, sha `4d893147def983623de681effd1bfbae2e7441c5`

Only items only the operator can answer. Everything the lead can answer stays in
`STAGE_D_INDEX.md`'s per-file "open questions" column instead.

## 1. Open Tier-4 decisions (`docs/redesign/DECISIONS_FOR_OPERATOR.md` §4.9-4.12, per `FACTS.md`)

- **4.9 R15-LEAD-030** — status `blocked_tier4`; a fresh verifier concurred in batch-23
  (`docs/redesign/verification/r15/stage-c/batch-23/LEAD-030-CONCURRENCE.md`). Smallest
  unblock: the operator's acceptance of this status is already recorded as binding for
  this release per the lead's refresh-rules note — no further action needed unless the
  operator wants to reopen it.
- **4.10 R15-LEAD-035** — status `open` at this sha; the batch-23 disposition verifier
  REFUSED `blocked_tier4` this round (over-match fix routed to batch-24; the under-match
  residual is pending batch-24's own concurrence). Smallest unblock: confirm at the tag
  whether `docs/redesign/verification/r15/stage-c/batch-24/LEAD-035-CONCURRENCE.md` landed
  and whether its wording should be adopted verbatim (it had not landed as of this sha).
- **4.11 R15-LEAD-037** — status `blocked_tier4`; fresh verifier concurred on corrected
  wording. Same acceptance basis as 4.9.
- **4.12 R15-LEAD-038** — status `blocked_tier4`; fresh verifier concurred. Same acceptance
  basis as 4.9.

Smallest unblock for all four as a set: the operator's Tier-4 sign-off already covers
4.9-4.12 (relayed in this run's refresh rules); the only live gap is confirming
R15-LEAD-035's batch-24 concurrence text once that file exists, at the tag.

Filed as: already covered: §4.9–4.12 (`docs/redesign/DECISIONS_FOR_OPERATOR.md`). 4.10 is settled by
batch-24's verifier concurrence at the close-out; no operator action unless that verifier refuses.

## 2. Copyleft / bundled licences flagged by `DEPS_LICENCES.md`

Facts only, no legal conclusion — the operator decides what each implies for the
PolyForm Strict 1.0.0 + commercial dual-license model.

| Package | Scope | Linkage | Licence |
|---|---|---|---|
| `openbb-core`, `openbb-economy`, `openbb-equity`, `openbb-fmp`, `openbb-fred`, `openbb-mcp-server`, `openbb-news`, `openbb-yfinance` | bundled (`python/openbb_mcp`, Requires-Dist closure from `sidecar/openbb_mcp_subprocess/requirements.txt`) | frozen into the `vysted-openbb-mcp-sidecar` PyInstaller `--onefile` binary | AGPL-3.0-only |
| `sec-edgar-mcp` 1.0.8 | bundled (`python/sec_edgar_mcp`) | frozen into the `vysted-sec-edgar-mcp-sidecar` PyInstaller binary | AGPL-3.0 |
| `Unidecode` 1.4.0 | bundled (`python/sec_edgar_mcp`) | frozen into the sec-edgar-mcp binary | GPL (OSI classifier: GPLv2+) |
| `frozendict` 2.4.7 | bundled (`python/sidecar` + `python/openbb_mcp`) | same package frozen into both the main sidecar and openbb-mcp binaries | LGPL v3 |
| `r-efi` 5.3.0 and 6.0.0 | bundled per cargo resolve graph | reachable only via `getrandom`'s `cfg(all(target_os="uefi", getrandom_backend="efi_rng"))` edge — this app never builds for UEFI, so the edge is inert in any shipped artifact | MIT OR Apache-2.0 OR LGPL-2.1-or-later (OR-licensed choice, not solely LGPL) |

Also flagged (empty licence metadata, not a copyleft finding but adjacent to the same
question): `caio` 0.9.25, `peewee` 4.0.6, `fredapi` 0.5.2, `httpxthrottlecache` 0.3.5 —
bundled, installed metadata `License` field empty, PyPI JSON `info.license` /
`info.license_expression` / classifiers all null/empty as of a live re-check on
2026-09-26 (unchanged from the prior scan).

Filed as: AGPL/GPL rows → §5.1; `frozendict` → §5.2; `r-efi` and the empty-metadata packages → §5.3
(each resolved from its shipped licence file: `caio`/`fredapi` Apache-2.0, `peewee`/`httpxthrottlecache` MIT).

## 3. `LICENCE_CHECK.md` mismatches in Tier-1 files

- `CLAUDE.md:57-58` still reads: "1. **Locked** — `docs/BLUEPRINT.md` §2. Never reopen
  unilaterally. (Stack; AGPL-3.0 + commercial dual license; MCP server in v1.0.)" — stale
  pre-relicense wording. A fix is already drafted verbatim at
  `docs/redesign/CLAUDE_MD_PROPOSAL.md:76`. `CLAUDE.md` is Tier-1/locked and was not
  edited by this wave (out of lane). Open across two scans at different shas
  (f4444790 and this one, 4d893147) with no interim fix — the operator decides whether to
  promote it now or hold for a batched CLAUDE.md edit.

Filed as: §5.4 (also already covered: §3.4, §2.19). Fixed at `c1e9164c` on the unmerged
`worktree-agent-r15-version-0.9.0`, merging right after the `r15-rc1` tag.

## 4. Windows

Nothing verified this wave. `FACTS.md:71` confirms the three CI workflows run an
`[windows-latest, macos-latest, ubuntu-latest]` matrix on every push/PR to `main`, but
Stage D is a read-only, off-machine, no-GUI wave — no Windows build, smoke test, or manual
verification was run or is claimable at this sha.

Filed as: §5.5 (related: §2.8, §2.11, §2.17).

## 5. Secrets hits classed `real_or_unknown`

None. `SECRETS_SCAN.md`/`.json` at this sha report `real_or_unknown: 0` and
`pushed_real_or_unknown: 0` across tree-at-sha (115 files), full history (2090 commits /
10647 blobs), and the blob sweep (314). No location/rule to list.

Filed as: §5.6 (acknowledge only; re-run at the tag sha).

## 6. Draft open questions that need the operator's decision (not answerable by the lead)

- **RELEASE_RUNBOOK draft, §11** — whether the operator keeps any locally-built prior
  `.dmg`/`.app` on hand outside this repo, for a real rollback path.
  Filed as: §5.7.
- **OPERATOR_BRIEFING draft, §4** — whether the filing-watcher groundwork folder should
  move under the git-ignored `r15/local/` per the operator's own one-line call (referenced
  but not resolved at this sha).
  Filed as: §5.8 (the evidence folder and its two tooling files, both under `r15/local/` before the launch tag).
- **R15-LEAD-035 promotion** (also listed in §1 above) — whether to adopt batch-24's
  concurrence wording once it exists, before or at the tag.
  Filed as: already covered: §4.10. Decided by batch-24's verifier concurrence at the close-out;
  no operator action unless the verifier refuses.
