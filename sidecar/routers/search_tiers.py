"""Managed-SearXNG router — the one-click "Unlimited (Local)" flow (R9 core).

R9 (Track A): the managed SearXNG instance IS tier_a's retrieval engine — these
routes are core, not an optional tier. Exposes the
:mod:`services.searxng_manager` state machine to the UI's guided setup:

  ``GET  /search/searxng/status``    the live state (re-derived from docker on
                                     every poll unless a setup is in flight) —
                                     ``not_installed_docker`` /
                                     ``docker_present_not_setup`` / ``pulling`` /
                                     ``starting`` / ``ready`` / ``error`` (+reason).
  ``POST /search/searxng/setup``     kick off pull → configure → run → health as
                                     a background task; returns immediately, the
                                     UI follows progress via the status poll.
  ``POST /search/searxng/teardown``  stop + remove the managed container.

Keyless and credential-free: everything here talks only to the local docker
daemon and ``127.0.0.1`` — nothing leaves the machine.
"""

from __future__ import annotations

from fastapi import APIRouter

from services import searxng_manager

router = APIRouter(prefix="/search/searxng", tags=["search"])


@router.get("/status")
async def searxng_status() -> dict[str, object]:
    """The managed-SearXNG state machine's current status (the guided-flow contract)."""
    return await searxng_manager.manager.refresh()


@router.post("/setup")
async def searxng_setup() -> dict[str, object]:
    """Start (or join) the one-click setup; poll ``/status`` for progress."""
    return searxng_manager.manager.begin_setup()


@router.post("/teardown")
async def searxng_teardown() -> dict[str, object]:
    """Stop and remove the managed container; returns the post-teardown status."""
    return await searxng_manager.manager.teardown()
