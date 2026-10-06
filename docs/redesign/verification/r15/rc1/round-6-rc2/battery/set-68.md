# Battery set-68: lows-P1/research-depth-iter-deep (candidate ace7dd76, shard rc1-battery-3)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-RESEARCH-005 | design entry; AST scan of services/research for private-name cross-module imports | 106 cross-module imports scanned, private-name leaks [] (iter/verify now import public names only). Pinned: test_research_module_boundary.py | holds |
| R15-CODE-RESEARCH-006 | design entry; introspect depth/iter/deep_research for the duplicated constant | no _MIN_HEAVY_ANGLES / _MIN_ANGLES copy in either module; both use depth.PANEL_MIN_ANGLES / is_panel. Pinned: test_panel_threshold_single_source | holds |
| R15-RESEARCH-035 | in-process _Report.render() with 14048-char body over a 6000 cap | 5977 chars; every Facts established line kept whole, Planned next kept, Dead ends text dropped first | holds |

COVERAGE: 3/3 ids raw; no raw: none
