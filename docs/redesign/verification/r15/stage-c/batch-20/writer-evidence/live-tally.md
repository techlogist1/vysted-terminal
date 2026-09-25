# batch-20 W1 live bar — llama3.1:8b via ollama, autonomy ask, sidecar from this tree on :52350

Transcripts: `<tag>.jsonl` (events, no tool payloads) + `<tag>.txt` (client log). Runner: `b20w_live.py`
(pass 1 = `all` on 6870c19a+ffd988a9; `pass2` on the sidecar restarted after a8070bba + c430fca8).
Offline: `b20w_probe.py` 18/18, `b17v/b18v/b19v_probe*.out` PASS except the two batch-19 false-premise
"q?" controls (`t-err-user-figures-list`, `t-err-user-position-summary`, which `b20w_probe.py` re-pins
with user figures in the prompt). `b20w_replay.py` replays a live jsonl through `invoke_agent` with the
live round layout.

| tag | calls / results | verdict |
|---|---|---|
| v-sify-ttm | financial_statements ok | no figure stated; honest "no data" |
| f-sify-q | financial_statements ok x2 | no figure stated; the model opened a ```python fence it never closed (model's own text, no note involved) |
| f-wipro-fund | fundamentals errored | negative report only, kept |
| f-infy-tcs-t2 (pass 1) | price_data errored | LEAK: history trailer seeded price_data ok, this turn's call errored, "INFY.NS: ₹1,042.30 / TCS.NS: ₹3,444.15" streamed -> fixed a8070bba |
| f-infy-tcs-t2-p2 | price_data errored | REPLACED: "The price_data tool returned no data for this in this turn." |
| f-err-table | price_data errored, ok, ok | real table, SBIN 983.0 / AXISBANK 1222.4 from the ok calls, kept |
| f-err-fenced (pass 1) | price_data errored, ok | ESCAPE: figure-less fenced dump streamed in the same round as the pending native call, before its errored result -> fixed c430fca8 (offline replay of this jsonl now yields the note) |
| f-err-fenced-p2 | (see live-pass2.out; in flight at write time) | rerun on the fixed sidecar |
| t-msft-price | price_data ok | $513.99 stated; sidecar /quotes/MSFT read 514.81 minutes later (live market), consistent |
| t-rel-list | price_data errored | list replaced by the note; extra blank lines after it (cosmetic) |
| t-user-sale | portfolio_add_position staged | user figures ₹3,100 x 5 = ₹15,500 kept (grounded by the prompt + derivation) |
| t-tcs-fund | fundamentals ok | ₹753,286 cr matches /fundamentals/TCS.NS market_cap 7.53e12; the model's "7,532.86 lakh cr" is a 1000x unit slip on a real figure (arithmetic, not a fabricated tool figure; out of the guard's remit) |

Stray "} " before the pass-1 f-err-fenced dump: the model's own content after Ollama's NATIVE tool call
(`services/llm/ollama.py` emits `message.tool_calls` mid-stream); LeakHold only holds from a
`{"name":` / `ident(` marker and the rescue only fires at end of stream with no native call, so it is not
a rescue leftover. `tool_call_rescue.py` untouched.
