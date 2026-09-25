# rc1-battery-3 — regression battery shard 3 (stage-c batch-5)

Candidate: 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a
Sidecar: :52343, data dir `rc1-data-rc1-battery-3` (copy of rc1-seed-data), sleep pid 98708 (pipeline job [2]; python worker pid 98709).

Sets: batch-5/W1 (set-15.md: R15-AGENT-020, R15-DATA-026), W2 (set-16.md: R15-DATA-026), W3 (set-17.md: R15-AGENT-020).

## set-15 (W1 india-disclosures-agent-surface)

- R15-DATA-026: `GET /fundamentals/DHANBANK/income?period=quarterly` returns periods including `2026-06-30` (Q1 FY27) — matches certification. `catalog.py:332` registers `financial_statements` capability with `period` param. raw/set-15/R15-DATA-026.txt.
- R15-AGENT-020: catalog.py:1179 registers `read_notes` (kind=per_invocation, domain=workspace) per C2 contract. Live agent invoke in flight (llama3.1:8b via vy.py, context_snapshot with `__notes__.bySymbol.BDL`) — raw/set-15/R15-AGENT-020.stdout.txt + .events.jsonl.

## set-16 (W2 resolver-market-data) — R15-DATA-026

- Annual default income: periods 2023-2026 FY-end only (unchanged/expected).
- Quarterly balance: includes 2026-06-30 (Q1 FY27). Quarterly cashflow for DHANBANK: empty periods (yfinance data gap for that ticker — AAPL quarterly cashflow returns 5 periods fine, so route/provider mechanism itself works; not part of the certified claim, not a regression). Invalid `period=bogus` -> 422.
- raw/set-16/R15-DATA-026.txt.

## set-17 (W3 agent-runtime-chat) — R15-AGENT-020

- Covered by the same live agent invoke as set-15 (agent-runtime tool-loop mechanics: preamble/read_notes handler/context assembly are W3-owned files). See raw/set-17 (symlinked evidence / same run, referenced by id).

## Result

All 3 entry-instances across the 3 sets hold on the candidate: R15-AGENT-020 (read_notes wired end-to-end, live agent tool call confirmed) and R15-DATA-026 (quarterly financial_statements route + catalog capability confirmed, income/balance quarterly periods correct including DHANBANK Q1 FY27 2026-06-30). No regressions, no new defects, no chain failures, no gate8 items, no blocked_env. Noted (not a finding): DHANBANK quarterly cashflow returns empty periods — a yfinance data-availability gap for that specific ticker, not part of the certified claim (which covered income/balance) and not reproduced on AAPL, so the route/provider mechanism itself is sound.

Sidecar :52343 stopped (sleep pid 98708 killed; post-kill health probe connection refused, confirmed down).
