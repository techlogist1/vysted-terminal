# rc1-battery-23 — regression battery shard 23 (round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar `127.0.0.1:52363`, data dir
`rc1-round-5-data-rc1-battery-23` (copy of the ISO seed, kept for the round). Sets:
batch-8/W1-sidecar-lifecycle-transport (set-29), batch-8/W5-agent-runtime-research (set-33),
batch-28/W2-sonnet (set-75). 15 fixed/certified entries re-checked, 0 regressions.

## Method per set

- **set-29** (7 frontend/Rust lifecycle-transport entries): live curl against my sidecar for the
  two backend-shaped entries (CODE-PLATFORM-011, UI-012), source-code confirmation for the
  transport-catch entry (UI-014), and — where the original certification only had a since-deleted
  scratch vitest/Rust test — a **targeted** re-run of the single relevant committed test file
  (never the full 136-file vitest run or the full cargo suite): `cargo test --lib <name> --
  --nocapture` for LIFECYCLE-010's two Rust pins, and `vitest run <one file>` for LIFECYCLE-011
  (`src/store/app.test.ts`), RESEARCH-032 (`src/components/SettingsPanel.test.tsx`), and
  LIFECYCLE-023 (`src/components/PanelHost.test.tsx`). All passed; verdict `ci_pinned` where the
  entry rests on a named committed test, `holds` where a live curl/source check was possible.
- **set-33** (6 sidecar/agent-runtime entries): in-process Python against the candidate's
  `sidecar/.venv`, importing `agent_runtime`, `model_registry`, `llm`, `budget_guard` and
  `deep_research` directly. Registry edits for CODE-AGENT-007 were done as an in-memory
  monkeypatch of `model_registry._PROVIDERS_BY_ID` (restored after) — the read-only candidate
  worktree's files on disk were never touched. LIFECYCLE-014/CODE-AGENT-016 used a scratch copy
  of the real `sidecar/agents/` dir with an added bad file and an openrouter-provider file,
  through `agent_runtime._discover_specs()` (also has a `agents_dir` param for exactly this).
  All 6 hold.
- **set-75** (2 data/research entries): DATA-113 via live `GET /earnings/<SYM>/estimates`
  against my sidecar for the batch-28 fresh-case symbol set (WIT/PDD/NVO/TSM/AAPL/BIDU/INFY.NS/
  BABA); RESEARCH-027 via one live agent research call (`llama3.1:8b`, under the Ollama lock)
  plus a source read of the two timeout constants in `fast.py`. Both hold.

## Notes / near-misses (not findings, recorded for the collator)

- **BABA earnings probe, first attempt:** hitting `/earnings/BABA/estimates` with no region
  header resolved to the IN-listed "Baba Arts Limited" (BSE `BABA.BO`), an unrelated small-cap,
  returning all-null estimates — a probe artifact of my sidecar's default region, not a product
  regression. Retried with `X-Vysted-Region: US`, which resolved to Alibaba and reproduced
  batch-28's certified CNY figure exactly.
- **RESEARCH-027 total vy.py time (81.5s) vs the research tool's own wall time (8.54s):** the
  register/FR-070 target is the research tool's own latency, which the tool's `started_at`/
  `finished_at` execution-record timestamps isolate from the surrounding llama3.1:8b agent-loop
  overhead (heartbeats while the local model decides to call the tool and writes its final
  reply). Used the isolated 8.54s figure for the verdict, noted both numbers in the raw file.
- Cargo/vitest commands used `--exact`/a single test-file target throughout — never the full
  `cargo test` or the full `vitest run` (136 files) — per the battery role's ban on running the
  full suites (the heavy lane owns those).

## Coverage

15/15 ids have a raw file from this run (7 in set-29, 6 in set-33, 2 in set-75). No id was
skipped, timed out, or blocked. 0 findings (0 regressions, 0 new defects, 0 chain, 0 gate8,
0 environment).

Sidecar stopped at the end of the run (`127.0.0.1:52363`, own process only).
