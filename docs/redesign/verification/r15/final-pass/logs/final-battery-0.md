# final-battery-0 working log (claude-opus-5-5, effort high, lane battery:0)

- Candidate d38b5d1a (read-only worktree final-cand). Shard ids: battery/shard-0.ids (149). rc2 reference: rc1/round-6-rc2/battery.
- Booted one sidecar on :52860 from final-cand (pids in battery/shard-0.pids.json); reused for every live probe.
- Probes generated per id into scratchpad fb0/p/<id>.sh; runner writes battery/raw/<id>.txt (header, command, output, EXIT). Batches: aa/ab/ac, 009 (TO 420), 023, llm, llm2, llm3; LLM probes held /tmp/vysted-r15-ollama.lock (released by trap).
- Environment: Yahoo 429 window after the india-all screener probe; Yahoo-dependent ids re-run after cooldown, all hold. BSE outside-world call denied (DATA-015 judged on internal flags).
- Probe-side corrections (no product change): DATA-040 camelCase body, LEAD-015 dict values, DATA-032 estimate_analyst_count, DATA-056 split_basis, UI-092 signature, UI-077 sample_count, LIFECYCLE-022 fresh tmp dir, AGENT-057 snake_case + default_provider, AGENT-084 catalog.internal_tool_ids, AGENT-023 localhost webhook (127.0.0.1 rejected by the allow-list, unchanged) + manual schedule cleanup, AGENT-013 rc2-style prompt, CODE-FRONTEND-008 dropped an unsupported vitest flag; vy.py scratch copy allows :52860.
- Verdicts: holds 114, regressed 0, ci_pinned 34, needs_gui 1 (R15-UI-009, GUI-certified only), blocked_env 0. findings/battery-0.json stays [].
- Sat 03 Oct 17:26 IST: sidecar stopped (kill sleep pid 89801 only; worker 89802 exited; :52860 refuses). Ollama lock absent.

COVERAGE: 149/149 ids raw; no raw: none
