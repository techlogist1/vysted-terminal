"""FastAPI routers for the Vysted Terminal sidecar.

Phase 1.A ships the data-layer routers (health, quotes, history, crypto,
fundamentals, macro). The indicators / portfolio / news / workspace routers are
stubs the Phase 1.B teammates fill in — each is already mounted by
:func:`app.create_app`, so a teammate only edits their own file.
"""
