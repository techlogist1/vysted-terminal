# Set lows-P1/frontend-stores (set-62)

Candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd. Raw: battery/raw/set-62/<id>.txt

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-087 | re-read src/store/agent-mode.ts docblock, types/agent-modes.ts, src/store/keybindings.ts, specs FR-003/SC-029 | store docblock now "two-mode intent + autonomy-axis model ... switchable by keyboard (⌥1–⌥2)", keybindings carry only alt+1 and alt+2, FR-003 (spec.md:259/834) and SC-029 say two modes; only historical "collapsed from the four modes" mentions remain (adjacent: spec.md:47 and :1291 still say "four-mode spine"); store test src/store/agent-mode.test.ts exists (not run) | holds |

COVERAGE: 1/1 ids raw; no raw: none
