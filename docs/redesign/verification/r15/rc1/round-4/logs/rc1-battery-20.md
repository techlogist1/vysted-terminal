# rc1-battery-20 — regression battery shard 20 (gate round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (verified via `git rev-parse HEAD`
in the scratch worktree at the start). Sets: batch-3/W2-agent-frontend-gate (set-6, 7
ids), batch-10/W5-chat-search-workflow (set-44, 7 ids), batch-12/W4-research-verdict-
parse-source-authority (set-59, 1 id). 15 ids total.

## Sidecar

Booted one sidecar for the whole shard: `sidecar/.venv/bin/python3 main.py --host
127.0.0.1 --port 52360 --data-dir <scratch>/rc1-round-4-data-rc1-battery-20` (fresh
copy of the seed data dir), detached via `nohup sh -c 'sleep 86400 | ...'`. Sleep pid
3468 (sh -c wrapper pid 3466, python worker pid 3469). `/health` confirmed ok before
any probe. Stopped at the end of the shard by killing sleep pid 3468 only.

## Method

Per the role instructions, vitest/pytest suites are off-limits to this shard (heavy
lane owns them) and there is no GUI. For the 15 ids:

- 6 ids have a live/backend-only mechanism reachable via curl or a direct Python call
  into the candidate's sidecar venv, with no vitest/GUI needed — re-ran those exactly:
  R15-RESEARCH-028 (GET /search/searxng/status), R15-AGENT-063 (news_tool._news +
  build_aliases/_tag_symbols fresh cases), R15-CODE-PLATFORM-017 (evaluate_code on
  the 6 original expressions), R15-CODE-RESEARCH-004 (grep for dead callers),
  R15-RESEARCH-002 (_parse_verdict on the 3 proven UNVERIFIED strings). All hold,
  byte-for-byte matching the batch cert's numbers/strings.
- 1 id (R15-AGENT-014) is half live (GET /custom-agents, checked) and half a frontend
  boot-loop call chain (bootstrapPlugins -> pluginHost.attach -> syncPluginAgents),
  confirmed present by source read but not independently executable without
  vitest/jsdom or the app running — ci_pinned on the committed test.
- The remaining 8 ids are pure frontend TS/React/Zustand/TipTap logic
  (proposed-changes autonomy gate, host-actions write_note/save_layout semantics,
  NotesPanel debounce/flush rewrite, CommandPalette chart-command routing, chat cost
  footer, slash-commands bare-ticker fast path, keybindings resolveChord) with no
  backend counterpart to curl. Verified each by reading the exact source lines the
  batch cert named and confirming the fixed mechanism is still there, then verdicted
  ci_pinned naming the committed vitest file/test that actually exercises it at
  runtime (never ran vitest myself).

No regressions found across either lane. No findings.

COVERAGE: 15/15 ids raw (7 set-6, 7 set-44, 1 set-59); no raw file missing.
