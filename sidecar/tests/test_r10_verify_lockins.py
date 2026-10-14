"""R10-VERIFY lock-in tests — pin the two lead hand-fixes that lacked a dedicated
regression test (the other three are already pinned: FIX1 substring/fuzzy-bind in
``test_resolution_policy.py``; FIX3 updatePosition fabricated-success in
``src/store/portfolios.test.ts``; FIX4 totalValue-null in
``src/modules/chat/context-provider.test.ts``).

Written by the R10-VERIFY census run (read-only verification pass) to LOCK IN the
current correct behaviour. No product code is changed by this run.

  - D47 — the ``/resolve`` HTTP endpoint (the @TICKER mention picker) routes
    through ``resolution_policy.decide()`` like every other consumer. The pre-fix
    endpoint used the legacy ``Resolution.needs_disambiguation`` property and
    returned ``best=None / needs_disambiguation=False`` for a marquee family name
    ("Tata") — reading as *unresolved* while research correctly disambiguated.
    Lock-in: "Tata" through the live router must DISAMBIGUATE.

  - D49 — the ack ledger (host-action read-back) is guarded by a ``threading.Lock``.
    The sync FastAPI ack route runs in the threadpool while the runtime's
    end-of-stream divergence check reads the ledger from the event loop; the pre-fix
    unguarded ``_prune`` could iterate ``_LEDGER`` while a concurrent ack inserted,
    raising "dictionary changed size during iteration". Lock-in: high-contention
    record/get is corruption-free, and the unguarded iterate-while-insert pattern
    the lock prevents is shown to be a real CPython hazard.
"""

from __future__ import annotations

import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import _RegionMiddleware
from routers import resolve
from services import action_ledger

# --- D47: /resolve endpoint honours decide() (marquee disambiguation) --------


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(resolve.router)
    app.add_middleware(_RegionMiddleware)
    return TestClient(app)


def test_resolve_endpoint_disambiguates_marquee_family_via_decide(
    client: TestClient,
) -> None:
    # D47 regression: the mention endpoint used to bind best=None /
    # needs_disambiguation=False for "Tata" (legacy property). Routed through
    # decide(), a marquee family must return an honest chooser — never a silent
    # guess and never a false "unresolved".
    resp = client.get("/resolve", params={"q": "Tata", "region": "IN"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["needs_disambiguation"] is True, body
    assert body["resolved"] is None, "a disambiguated query must not bind one instrument"
    symbols = [c["symbol"] for c in body["candidates"]]
    assert len(symbols) >= 2, symbols
    # The curated marquee chooser leads with the canonical Tata entities.
    assert {"TCS", "TATASTEEL"} <= set(symbols), symbols
    assert all(c["region"] == "IN" for c in body["candidates"]), body


def test_resolve_endpoint_still_binds_a_strong_match(client: TestClient) -> None:
    # The same endpoint must still BIND a strong, unambiguous match — the D47 fix
    # widened disambiguation, it did not break ordinary resolution.
    resp = client.get("/resolve", params={"q": "GOLDBEES", "region": "IN"})
    body = resp.json()
    assert body["needs_disambiguation"] is False
    assert body["resolved"] is not None and body["resolved"]["symbol"] == "GOLDBEES"


# --- D49: ack ledger is lock-guarded (no dict-iteration race) -----------------


@pytest.fixture(autouse=True)
def _clean_ledger() -> None:
    action_ledger.reset_for_tests()
    yield
    action_ledger.reset_for_tests()


def test_action_ledger_is_lock_guarded() -> None:
    # Structural pin: the module exposes a real lock that record/get acquire.
    assert isinstance(action_ledger._LOCK, type(threading.Lock())), "_LOCK must be a real lock"


def test_action_ledger_high_contention_record_get_no_corruption() -> None:
    # D49 regression: pre-seed a large ledger so every record() call's internal
    # _prune iterates a big dict, then hammer record()/get() from many threads
    # while new inserts land. The pre-fix unguarded prune raced the inserts and
    # raised "dictionary changed size during iteration"; the lock serialises it.
    for i in range(4000):
        action_ledger.record(f"seed-{i}", "applied", {"symbol": "RELIANCE"})

    errors: list[BaseException] = []
    barrier = threading.Barrier(17)  # 16 workers + this thread

    def worker(wid: int) -> None:
        barrier.wait()
        try:
            for j in range(1500):
                action_ledger.record(f"w{wid}-{j}", "kept_previous", {"n": j})
                action_ledger.get(f"seed-{(wid * j) % 4000}")
        except BaseException as exc:  # noqa: BLE001 — capture ANY race fault
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(16)]
    for t in threads:
        t.start()
    barrier.wait()
    for t in threads:
        t.join()

    assert errors == [], f"ack ledger corrupted under contention: {errors[:3]}"
    # Reads after the storm still return coherent entries, never crash.
    entry = action_ledger.get("seed-0")
    assert entry is not None and entry["status"] == "applied", entry
    assert entry["brief"] == {"symbol": "RELIANCE"}, entry


def test_unguarded_iterate_while_insert_is_a_real_cpython_hazard() -> None:
    # Demonstrates the exact failure mode the D49 lock prevents: iterating a dict
    # (as _prune does over _LEDGER.items()) while it is mutated raises. This is
    # what made the cross-thread prune-vs-ack race a real bug, not a theoretical
    # one — and why every _LEDGER access now holds _LOCK.
    d = {i: (float(i), i) for i in range(64)}
    with pytest.raises(RuntimeError, match="changed size during iteration"):
        for cid, _payload in d.items():
            d[f"insert-{cid}"] = (0.0, 0)
