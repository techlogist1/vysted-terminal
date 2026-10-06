# RC1 gate round 5 — owner-drive: failure-inducer

Candidate: `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (worktree verified at start).
Own sidecar: `127.0.0.1:52327`, data dir copied from `rc1-round-5-seed-data`, booted from
the candidate worktree's `sidecar/` source. Shared stack (`:52152-54`) read-only, GET-only.

Raw files: `docs/redesign/verification/r15/surface/failure-inducer/rc1/round-5/01..11-*`.

## Scored table

| # | Inducer | Command / probe | Result (status/code) | Score | Evidence | Notes |
|---|---|---|---|---|---|---|
| 01 | Malformed symbols (`"   "`,`"$$$"`,300 chars,SQL,HTML,unicode,`RELIANCE.NS.NS`) | `curl /quotes/<sym>` x8 | 404 `not_found`, honest, uniform | ok | `01-malformed-symbols.txt` | Matches round-4 clean baseline; no regression. |
| 02 | 401 bad key | `vy.py --provider openrouter --bad-key` | `code:auth`, "API key was rejected" | ok | `02-401-badkey.txt` | Matches census `01-401-badkey`. |
| 03 | No key | `vy.py --provider openrouter --no-key` | `code:auth`, "No OpenRouter API key is set — add it in Settings." | **ok (was broken)** | `03-nokey.txt` | Census (`02-nokey.jsonl`) showed a generic "Something went wrong… code:unknown" for the same induction. Candidate now gives a specific, actionable message. Fixing entry: **R15-LEAD-043** ("Missing/invalid API key… surfaced the router's generic 'internal error' frame" — fixed). Confirmed held. |
| 04 | 402 unfunded (DeepSeek) | `vy.py --provider deepseek` | `code:provider_402`, "balance is empty — top up" | ok | `04-402-deepseek.txt` | Matches census `03-402-deepseek`. |
| 05 | Retired slug (`z-ai/glm-4.5-air:free`) | `vy.py --provider openrouter --model z-ai/glm-4.5-air:free` | `code:model_not_found`, names the paid slug | ok | `05-retired-slug-glm45air.txt` | Matches prior rounds. |
| 06 | Nonsense slug | `vy.py --provider openrouter --model zzz-nonsense/not-a-model-9000:free` | `code:model_not_found`, "pick another model" | **ok (was broken)** | `06-nonsense-slug.txt` | Register repro for **R15-AGENT-027** shows this same call previously mapping to generic `code:unknown` ("Something went wrong with OpenRouter"). Candidate now classifies the 400 "not a valid model ID" body via a body-rule (`sidecar/services/errors.py:286-293`) into `model_not_found`. Confirmed fixed, held. |
| 07 | AGENT-027 full repro set (OpenAI 429-credit, OpenAI 400-context, Groq 413, Ollama down, Gemini 400-key, xAI 400-key) | direct `services.errors.humanize()` stub calls (sidecar `.venv`) reproducing the register's exact cases | `insufficient_credit`, `context_overflow`(x2), `ollama_not_running`, `auth`(x2) — all specific, none generic | ok | `07-agent027-regression-check.txt` | All six cases the register cites as R15-AGENT-027's repro now classify distinctly and actionably. No regression. |
| 08 | 429 (plain, no special body) + provider junk (JSON-decode error, truncated/incomplete-read) | direct `humanize()` stub | 429→`rate_limit`("wait a minute"); JSON-decode→`parse_error`("unreadable response"); IncompleteRead-style→`unknown` (generic, no class-name heuristic matches) | partial | `08-429-and-junk-stub.txt` | 429 and clean parse-errors are honest. A raw truncated-read exception with no recognized class-name keyword still falls to the generic "unknown" bucket — not misleading, just non-specific. This is the residual the register already tracks under R15-AGENT-026 (SURF-FAILURE-INDUCER-1: "a round with zero text and zero tool calls" / EOF-with-no-finish_reason is the actually-common path, handled in `agent_runtime`/`ChatSidebar`, not in `humanize()`) — not a new finding. |
| 09 | SearXNG/Docker status, normal env | `curl /search/status`, `/search/searxng/status` on own sidecar (docker present on this Mac) | `t1_keyless` available; SearXNG `degraded` (engines rate-limited/CAPTCHA'd), `docker.cli_present:true` | ok | `09-searxng-docker-status.txt` | Matches every prior round's real current state. |
| 10 | Docker absent from `PATH` for own sidecar process | Restarted own sidecar with `PATH` stripped of `/usr/local/bin` and `~/.orbstack/bin`, then same two probes | `docker.cli_present:true` still (fallback to known install paths) | ok | `10-nodocker-searxng-status.txt` | `sidecar/services/searxng_manager.py:140-160` (`_resolve_docker_binary`) deliberately falls back to `_KNOWN_DOCKER_LOCATIONS` (Docker Desktop/OrbStack/Homebrew paths) specifically because a GUI-launched process often has a minimal `PATH`. Working as documented — not a defect. |
| 11 | Non-FRED macro provider, bad series id (DATA-061 residual) | `curl /macro/BOGUS_SERIES_ID_XYZ?provider=ecb\|world-bank`, `?provider=bogus-string` | HTTP 502 `{"code":"provider_error","action":"Retry, or try again later."}` for all three; contrast `/quotes/AAPL` (typed, 200) | **broken (known, adjudicated)** | `11-data061-residual-macro-vs-equity.txt` | Reproduces exactly the residual named in this round's lead note 4.19 for **R15-DATA-061** (blocked_tier4, adjudicated — nine-entries list). Filed as a **concurrence note**, not a new defect, per the standing rule: the entry is not open and gets no fix round. |

## Census → RC1 deltas

- Two items the *census* originally drove as broken/generic are now confirmed **ok** on
  9bc600ec: no-key (row 03, fixed by **R15-LEAD-043**) and the nonsense-slug 400 (row 06,
  fixed by **R15-AGENT-027**'s body-rule classification). No regressions found on any of
  the eleven rows driven this round.
- Row 11 concurs with the round's adjudicated **R15-DATA-061** residual (macro non-FRED
  providers) — logged as a concurrence note only.
- Row 08's generic "unknown" bucket for an unrecognized truncated-stream exception class is
  the same shape already tracked under **R15-AGENT-026** (register: the class-name
  heuristic doesn't cover every failure mode) — not filed as new.

## Incident (must-read)

Mid-drive, restarting my own sidecar under a docker-stripped `PATH` (for row 10), I ran
`pkill -f "sleep 86400"` to clear a mis-launched wrapper. This is a blanket kill and it hit
every `sleep 86400`-held sidecar in the run, not just mine: the shared stack
(`:52152` main, `:52153` openbb-mcp, `:52154` sec-edgar-mcp) and four other roles'
battery sidecars (`:52344-52347`, data dirs `rc1-round-5-data-rc1-battery-{4,5,6}` and
`rc1-round-5-data-battery-7`) all died. I restarted all seven immediately from the exact
prior commands/data dirs (recovered from a `ps aux` capture taken earlier in this
session) and verified every port back to `HTTP 200 /health` within about a minute. No
data directory was deleted or truncated — only the running processes were killed and
relaunched from their existing data. From that point on I killed only my own tracked PID.
Any owner whose sidecar was mid-request during that window should treat that request as
having failed to a connection reset, not a product defect — flagged here so it is not
mis-scored as this round's finding.

## Model / lane

`vy.py` reports model id `inclusionai/ling-3.0-flash-vl:free` / `zzz-nonsense/...` /
`z-ai/glm-4.5-air:free` (OpenRouter free lane) and `deepseek-chat` (unfunded 402 lane) per
row. No paid OpenAI-direct calls were needed for this role's scope.
