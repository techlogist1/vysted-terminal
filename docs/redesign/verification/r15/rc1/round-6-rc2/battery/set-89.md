# lows-P2/research-retrieval-relevance (set-89), shard rc1-battery-9, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-034 | in-process searxng_manager.setup() with write_settings raising OSError (test-module FakeDocker helpers) | state error, reason 'setup failed: [Errno 28] No space left on device', traceback logged, _log used | holds |
| R15-LIFECYCLE-035 | in-process: failed pull -> hand-started container -> refresh() | state ready, reason None, ready_base_url http://127.0.0.1:8888, last_error kept; running-but-unhealthy stays error | holds |

COVERAGE: 2/2 ids raw; no raw: none
