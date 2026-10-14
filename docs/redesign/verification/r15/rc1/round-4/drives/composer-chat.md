# Owner-drive: composer-chat — gate round 4

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar :52320 (own
data-dir copy). Reads-only checks went via the shared :52152 read path where
applicable; every write (chat invoke, ack) went to :52320 only.

Full round-4 raw evidence: `docs/redesign/verification/r15/surface/composer-chat/rc1/round-4/`.

## Scored table (deltas from census only — rows not retested carry the
census verdict unchanged; full 24-row COVERAGE.json is in this dir)

| # | Row / check | Census verdict | RC1-R4 verdict | Evidence (raw file) |
|---|---|---|---|---|
| 1 | `composer-send-stop-button` (mid-stream Stop cancels upstream work) | broken | **ok** (regression risk cleared) | `03-stop-midstream.jsonl`, `.meta.txt`, `.postkill-tail.log` |
| 2 | `chat-message-notices` (divergence/kept_previous/failed chip) | broken | **ok** | code read `agent_runtime.py:1416`, `message-notices.ts:68`; live in `05-hostaction-watchlist-add.jsonl`, `07-hostaction-screen-arrange.jsonl` |
| 3 | No-key error humanization (R15-LEAD-043, OpenAI) | n/a (new probe) | **ok** | `02-err-nokey-openai.jsonl`, `.stdout.txt` |
| 4 | Intent gate / R15-AGENT-019 (fresh delete/edit phrasings incl. the round-3 verifier's exact failing case) | n/a | **ok**, all 7 phrasings retain write tools | `04-agent-019-intent-probe.txt` |
| 5 | Schema coercion / R15-AGENT-093 (nested numeric-string args) | n/a | **ok** by code read (recursive `_coerce`, every depth) | code read `agent_runtime.py:908-940` |
| 6 | Tool-call-id uniqueness / R15-AGENT-046 (ollama) | n/a | **ok**, real UUID-based ids, not empty/`leaked-0` | `05-hostaction-watchlist-add.jsonl` |
| 7 | Host action: `add_to_watchlist` via chat, staged not auto-applied, ack round-trip | partial (census) | **ok** end-to-end (propose → stage → ack) | `05-hostaction-watchlist-add.jsonl`, `06-hostaction-ack.txt` |
| 8 | Host action: `write_screener_filters` + `arrange_layout` compound turn | partial | **ok** dispatch/stage/notice mechanics; model's own filter semantics are imperfect (see log, out of scope) | `07-hostaction-screen-arrange.jsonl` |

All other composer/chat-agent rows (`composer-mount`, `composer-depth-control`,
`composer-model-control`, `composer-slash-picker`, `chat-agents-rail`,
`chat-empty-state`, `chat-suggestion-chips`, `chat-budget-config`,
`agent-autonomy-ask-auto`, `agent-persona-picker`, `agent-command-bus`,
`agent-runs-store`, `chat-markdown-render`, etc.) were not re-driven this
round — no evidence of regression surfaced while driving the above (which
exercises the same composer/streaming/tool-call/notice machinery they
depend on), so they carry the census verdict unchanged in `COVERAGE.json`.

## Census → RC1 deltas

- **Regression risk cleared, not found**: `R15-AGENT-002` (stop-cancel),
  `R15-AGENT-031`/`R15-UI-054` (divergence notice matching), `R15-AGENT-019`
  (intent-gate write-stripping), `R15-AGENT-093` (nested schema coercion),
  `R15-AGENT-046` (tool-call-id uniqueness) all hold at this candidate. None
  of the round-3 verifier's composer/chat-scoped refutations reproduce here.
- **New**: `R15-LEAD-043` (no-key humanizer) probed fresh this round and
  holds (`code: "auth"`, humanized message, not the generic internal-error
  frame).
- **No new defects.** `findings/rc1-drive-composer-chat.json` is `[]`.

## Notes

- One own-mistake incident (killed a wrong PID while simulating a client
  abort — see `logs/rc1-drive-composer-chat.md`); no evidence was lost, the
  correct measurement was retaken with an exact-PID kill.
- Out-of-scope observation for the screener owner: local-model tool-arg
  quality on `write_screener_filters` (see log). Not filed as a
  composer-chat finding.
