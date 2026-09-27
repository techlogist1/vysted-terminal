# batch-17/W1-one-writer-set (set-65.md)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Shard rc1-battery-3. Raw output:
`battery/raw/set-65/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-031 | In-process: `LeakHold({"price_data"}).feed(ch)` fed the register's exact leaked shape (`'{"name": "price_data"}The ADR-to-ordinary-share ratio is 1:1.'`) one character at a time — the worst-case granularity for a splice bug | Nothing is shown to the user before the marker resolves (`streamed == ''`); the whole fragment + trailing prose sits in `held()` until end-of-stream rescue, so no `{"name": "price_data...`-glued-to-prose fragment ever reaches the stream. Source: `tool_call_rescue.py` `LeakHold` (holds a chunk whole while `_PARTIAL_JSON`/`_PARTIAL_CALL` may still complete — commit ede02247, comment names R15-LEAD-031); both `ollama.py` and `openai.py` iterate `hold.feed(event.text)` | holds |

COVERAGE: 1/1 ids raw.
