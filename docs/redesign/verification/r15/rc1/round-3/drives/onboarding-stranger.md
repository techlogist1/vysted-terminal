# drive:onboarding-stranger — gate round 3

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `127.0.0.1:52326` on a clean data
dir; MCP env pointed at the shared read-only `openbb-mcp:52153` / `sec-edgar-mcp:52154`, never
restarted. Full detail + evidence citations: `SURFACE/onboarding-stranger/rc1/round-3/RC1-R3-ONBOARDING-STRANGER.md`.

## Scored table

| # | Item | Census | RC1 R3 |
|---|---|---|---|
| 1 | First-launch TOS content | broken | ok |
| 2 | Fake OpenRouter key validates as ok | broken | ok |
| 3 | Key trailing-space handling (K08) | broken-ish | ok |
| 4 | Welcome-screen keyless "web research" claim | broken | ok |
| 5 | "Nothing leaves this machine" privacy claims | broken | ok |
| 6 | Banner shown after local-model setup | broken | ok |
| 7 | Zomato→Eternal resolve/autocomplete | broken | ok |
| 8 | `/quotes/ZOMATO.NS` error shape | broken (502, leaked internals) | ok (clean 404-shaped) |
| 9 | "eternal" resolve | ok | ok |
| 10 | Promote key over keyless default (UI-049) | n/a (found post-census) | ok, pinned test |
| 11 | Default watchlist/chart vs IN region | wrong | wrong (unchanged, R15-UI-076 open/low by design) |
| 12 | Keyless first-panel data | ok | ok |
| 13 | Keychain-denied dead end (T5, R15-UI-044) | broken | NOT TESTED (blocked_tier4, adjudicated) |
| 14 | Ollama daemon-down / not-pulled states | NOT TESTED | NOT TESTED (shared daemon, unchanged constraint) |

## Census → RC1 deltas

Fixing register ids confirmed live/code-verified with no regression: R15-UI-008, R15-UI-052,
R15-UI-019, R15-DATA-018, R15-UI-057, R15-UI-049. R15-UI-041 (`not_a_defect`) confirmed current —
the TOS body is in fact honest now. R15-UI-076 (open, low) confirmed unchanged, correctly out of
gate scope. No new defects. No regressions.
