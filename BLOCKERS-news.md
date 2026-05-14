# Blocker — `test_app.py::test_stub_router_mounted[news-teammate-c]`

## Context

`sidecar/tests/test_app.py` is parametrized to assert that each Phase 1.B stub
router still returns the `_status` stub payload:

```python
("news", "teammate-c"),
...
body = client.get(f"/{router}/_status").json()
assert body == {"status": "stub", "router": router, "owner": owner}
```

My deliverable explicitly required **replacing** the `/news/_status` stub with
the real `GET /news` endpoint (see the Teammate C brief: "Fill
`sidecar/routers/news.py` (replace the `_status` stub)"). With the stub removed,
`GET /news/_status` now 404s and this parametrized case fails.

## What I tried

- Confirmed the failure is _only_ this one stale assertion — the full suite is
  otherwise green: `pytest sidecar` = 39 passed, 1 failed; deselecting this case
  → 39 passed, 1 deselected.
- My own `test_news.py` (17 tests) covers the real `/news` endpoint and the
  sentiment scorer and all pass.

## Why I did not fix it myself

`sidecar/tests/test_app.py` is **outside my allowed-edit set** (the brief
constrains Teammate C to `sidecar/tests/test_news.py` only, plus the news
router/services). Editing it would cross the worktree's file-ownership boundary.

## What is needed

`test_app.py` must be updated as Phase 1.B teammates replace their stubs —
Teammates A (`/indicators`), B (`/portfolio`), and D (`/workspace`) will hit the
identical failure for their parametrized rows. The integration/merge owner
should either:

1. Drop the `news` row (and each teammate's row, as they land) from the
   `test_stub_router_mounted` parametrize list, or
2. Replace it with a real smoke assertion against the now-live endpoint.

This is expected churn from the 1.A → 1.B transition, not a defect in the news
feature. Everything in my deliverable is complete and green; only this
cross-owned test file is stale.
