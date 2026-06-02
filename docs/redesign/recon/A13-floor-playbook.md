# Recon — A13:floor-playbook

I have everything. The kill-switch model is `sidecar/services/kill_switch.py` (not `models/`), and the task brief's Tier-1 list omits `sidecar/models/broker.py` but CLAUDE.md/the brief name it — I'll reconcile. Now producing the blueprint.

---

# Floor-Enforcement Playbook — post-track audit (lead runbook)

## (1) Findings — what exists today, file:line precise

**§6.5 audit suite** — `sidecar/tests/test_safety_end_to_end.py`. Docstring says "8-point" but there are **9 test functions** (audit_8 splits into `_8` + `_8b`). Enumerated:

| #   | Function (line)                                        | What it greps/asserts                                                                                                                                                                                                                                                                                      |
| --- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `test_audit_1_paper_mode_default` (118)                | Every adapter constructs `mode=="paper"`; `subprocess grep -rE '_mode\s*[:=]\s*[\'"]live[\'"]'` over `sidecar/services/brokers` + `broker_base.py` → **must be empty** (153).                                                                                                                              |
| 2   | `test_audit_2_no_bypass_path_to_place_confirmed` (162) | `inspect.getsource(BrokerAdapter)` contains `async def _place_confirmed` + `await self._place_confirmed(`; `grep -rE '_place_confirmed\s*\(' sidecar/` → only allowed call sites (tests/, def, `await self._place_confirmed(`, comments) (177-196).                                                        |
| 3   | `test_audit_3_position_limit_enforcement` (213)        | `propose_order` at 2× `_limits.max_order_value_account_currency` raises `BrokerError match="exceeds limit"` for all 7 adapters.                                                                                                                                                                            |
| 4   | `test_audit_4_append_only_at_db_level` (246)           | UPDATE/DELETE on `audit_orders` raise `sqlite3.IntegrityError` with literal `"audit log is append-only: UPDATE/DELETE not permitted"` (271,277).                                                                                                                                                           |
| 5   | `test_audit_5_kill_switch_under_2s` (289)              | 12 subscribers; `bus.fire(...)` → `result.max_ack_ms < 2000.0` (321).                                                                                                                                                                                                                                      |
| 6   | `test_audit_6_ai_order_gate` (345)                     | No `place_order/submit_order/execute_order` in `agent_tools.registered_tools()`; AI proposal `confirm_and_place(human_confirmed=False)` raises `match="declined"`; audit log has `order-declined`; `grep -rnE '(auto_approve\|autoApprove\|AUTO_APPROVE)\s*[:=]' sidecar/services/` → **empty** (398-418). |
| 7   | `test_audit_7_read_only_mode_raises` (428)             | `set_read_only(True)` then `propose_order` raises `match="read-only"` for all 6 adapters.                                                                                                                                                                                                                  |
| 8   | `test_audit_8_disclaimer_session_flow` (454)           | Session-scoped first-live-order ack: not on cold start, set after `record_session_ack`, `disclaimer-ack` in audit tail.                                                                                                                                                                                    |
| 8b  | `test_audit_8b_static_ip_detection` (486)              | `static_ip_status` returns `.matches` on match/mismatch.                                                                                                                                                                                                                                                   |

**Tier-1 LOCKED files** (verified on disk): all exist EXCEPT the brief's `sidecar/models/kill_switch.py` — the kill-switch lives at **`sidecar/services/kill_switch.py`** (no `models/kill_switch.py`). The brief's list also names `sidecar/models/broker.py` (exists). Use the corrected list in §2.

**Build/PATH facts:** target triple `aarch64-apple-darwin`; binaries present in `src-tauri/binaries/`. `pnpm sidecar:build` = `node scripts/ensure-sidecar.mjs --force` (main only). PyInstaller flags single-sourced in `scripts/ensure-sidecar.mjs`: `--hidden-import` (110-119), `--copy-metadata` list `[fastmcp,mcp,anyio,httpx,starlette,uvicorn]` (128), `--add-data` array `[agents, services/screener_universes, services/resolver_masters, config]` (180-187). **`ci-local` calls bare `python`** (`python -m pip…`, `python -m ruff…`, `cd sidecar && … pytest`) — and **bare `python` is NOT on the bg-shell PATH** (only `/opt/homebrew/bin/python3`). The venv (`sidecar/.venv/bin`) must be prepended to PATH or `ci-local` dies at the first `python -m pip`. Sidecar pytest needs **cwd=`sidecar/`** (`sidecar/conftest.py`).

## (2) Exact change plan — commands to run after every track (READ-ONLY; lead executes)

This is a runbook, not a file-edit plan. The lead runs these verbatim.

### A. §6.5 9/9 audit

```bash
cd /Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar && \
  .venv/bin/python -m pytest tests/test_safety_end_to_end.py -v
```

**Expected pass output (tail):** `9 passed` — every line `tests/test_safety_end_to_end.py::test_audit_{1,2,3,4,5,6,7,8_disclaimer_session_flow,8b_static_ip_detection} PASSED`. Any non-`9 passed` = floor breach; STOP, do not integrate the track.

### B. Tier-1 LOCKED files unchanged vs sprint base (HEAD `ae2a499`)

```bash
cd /Users/lokavyasingh/Documents/dev/vysted-terminal && \
git diff ae2a499 -- \
  types/plugin.ts types/safety.ts types/broker.ts \
  sidecar/models/safety.py sidecar/models/broker.py \
  sidecar/models/audit_log.py \
  sidecar/services/kill_switch.py sidecar/services/broker_base.py \
  src-tauri/src/kill_switch.rs sidecar/tests/test_safety_end_to_end.py \
  src-tauri/tauri.conf.json .github/workflows/
```

**Output MUST be empty.** (Base = `origin/002-jarvis-intelligence` HEAD `ae2a499`; use `git fetch origin && git diff origin/002-jarvis-intelligence -- …` if integrating remote teammate branches.) Note: the brief's `sidecar/models/kill_switch.py` does not exist — substituted with the real `sidecar/services/kill_switch.py`. The proposed-changes gate `src/store/proposed-changes.ts` is a safety-critical invariant; diff it too and eyeball that AUTO still gates non-UI mutations.

### C. Rebuild + smoke-test main sidecar (only when sidecar Python changed)

```bash
cd /Users/lokavyasingh/Documents/dev/vysted-terminal && \
  pnpm sidecar:build && \
  node scripts/smoke-test-sidecars.mjs
```

`smoke-test` requires the binary newer than source (freshness gate, smoke 449-478), so run **after** `sidecar:build`. Expected: `[smoke] all sidecars booted cleanly.` (probes `/health` + `/screener/universe?id=sp500`, MCP port-binds). Pre-flight fails if orphans alive → `pkill -9 -f 'vysted-.*sidecar'` first.

### D. Targeted pytest + vitest

```bash
# sidecar (cwd=sidecar is mandatory)
cd /Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar && \
  .venv/bin/python -m pytest tests/test_<touched>.py -q
# frontend
cd /Users/lokavyasingh/Documents/dev/vysted-terminal && pnpm test -- <path-or-pattern>
```

### E. PyInstaller `--onefile` metadata-gap checklist (apply ONLY if a track added a new pip/sidecar dep)

Edit `scripts/ensure-sidecar.mjs` (or the matching `ensure-{openbb,sec-edgar}-mcp-sidecar.mjs`):

1. **`--copy-metadata`** (line 128) — add the dep iff its `__init__` runs `importlib.metadata.version("<pkg>")` (e.g. anything FastMCP-like). Symptom if missed: smoke FAIL `PackageNotFoundError`.
2. **`--collect-data=<pkg>`** — add iff the dep loads pkgutil/resource data from inside its own package (precedent `edgar`). Symptom: `FileNotFoundError` at boot.
3. **`--add-data "<abs>${sep}<dest>"`** (array 180-187, sep 165) — add iff a non-package or in-package-JSON data dir is loaded via `Path(__file__).parent` / `importlib.resources`; dest must mirror the package hierarchy; SOURCE absolute (specpath is `build/`). Symptom: endpoint 502 / silently-empty.
   After any edit: `pnpm sidecar:build && node scripts/smoke-test-sidecars.mjs` (editing the ensure recipe auto-invalidates the binary via staleness `extraFiles`). Adding a _new_ sidecar also needs `tauri.conf.json externalBin` + `SCRIPTS` in `ensure-all-sidecars.mjs` — that touches a Tier-1 file → operator sign-off.

### F. Full `pnpm ci-local` (release-gate; run with venv on PATH)

`ci-local` invokes bare `python`, absent from this shell. Prepend the venv:

```bash
cd /Users/lokavyasingh/Documents/dev/vysted-terminal && \
  PATH="$PWD/sidecar/.venv/bin:$PATH" pnpm ci-local
```

Run in background (>30s) with job tracking; never pipe through `head`/`tee`. Cheapest pre-push guard: `pnpm format:check`; before any Python commit: `sidecar/.venv/bin/ruff format <files> && sidecar/.venv/bin/ruff format --check sidecar && sidecar/.venv/bin/ruff check sidecar`.

## (3) Risks + safe fallback

- **`ci-local` aborts at `python -m pip`** (bare python missing). → Fallback: the `PATH=…sidecar/.venv/bin:$PATH` prefix in §F. If still broken, run stages individually (lint/typecheck/`cargo` clippy/`.venv/bin/ruff`/`pnpm test`/`cargo test`/`.venv/bin/python -m pytest` from `sidecar/`).
- **Diffing wrong base** (local `ae2a499` drifted from origin). → `git fetch origin && git diff origin/002-jarvis-intelligence -- <files>`; the origin SHA is authoritative for audit (CLAUDE.md worktree rule).
- **smoke FAIL "STALE binary"** (source newer than binary). → run `pnpm sidecar:build` first; never smoke a stale binary.
- **smoke pre-flight orphan abort.** → `pkill -9 -f 'vysted-.*sidecar'`, re-run.
- **Cold-boot timeout** (main 120s, MCP 90s). → re-run warm; if persistent, suspect a missing PyInstaller flag (§E), not the budget.
- **Tier-1 diff non-empty from teammate contamination** (Sonnet writes into lead worktree). → discard with `git restore --source ae2a499 -- <file>`; audit the teammate's work via `origin/<branch>` only.

## (4) Verification — prove the floor holds

1. **§6.5:** §A → expect `9 passed`. Capture the line count; `8 passed` or any FAIL = revert that track.
2. **Tier-1 immutable:** §B → `git diff …` prints **nothing** (exit 0, empty). If non-empty, `git restore --source ae2a499 -- <file>`, re-diff to empty.
3. **Binary runtime:** §C → `pnpm sidecar:build` then `node scripts/smoke-test-sidecars.mjs` → `all sidecars booted cleanly.` (proves `/health` + screener-universe + MCP binds).
4. **Targeted tests:** §D for touched modules; green before integrate.
5. **Release gate:** §F `PATH=…/.venv/bin:$PATH pnpm ci-local` green end-to-end (background, job-ID tracked) before any tag.

**In short:**

- The audit is **9 tests** (`9 passed`), not 8 — run `sidecar/.venv/bin/python -m pytest tests/test_safety_end_to_end.py -v` from `sidecar/`.
- Tier-1 diff base is `ae2a499`; brief's `sidecar/models/kill_switch.py` is wrong — the real locked file is `sidecar/services/kill_switch.py`. `git diff ae2a499 -- <files>` must be empty.
- `pnpm ci-local` needs `PATH="$PWD/sidecar/.venv/bin:$PATH"` — bare `python` is not on the bg-shell PATH.
- PyInstaller gap checklist (copy-metadata / collect-data / add-data) applies only on a new dep; all three single-sourced in `scripts/ensure-sidecar.mjs:128,180`.

Confidence: 9/10 — uncertain only whether your worktree's local `ae2a499` matches `origin` (fetch + diff against `origin/002-jarvis-intelligence` if any teammate branch was merged).
