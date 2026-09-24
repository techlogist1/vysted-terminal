"""Unattended workflow runs (R15-AGENT-023, D-B7-7).

One asyncio loop, started and stopped in the app lifespan, fires saved
workflows on their schedules (``workflow_store`` ``schedules`` table) while the
app is open. Two triggers:

- ``interval``: due ``every_minutes`` after the last fire (or creation).
- ``announcement``: polls the exchange feed
  (``corporate_disclosures.get_announcements_cached``, cached upstream) and
  fires once per new announcement whose headline contains the phrase; the
  announcement is the run's input.

A fire runs the saved spec through :func:`workflow_engine.run_workflow` (the
path ``POST /workflow/run`` uses), never overlaps the schedule's own previous
fire, and records the outcome on the schedule row.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from models.workflow import AnnouncementTrigger, IntervalTrigger, WorkflowSchedule
from services import corporate_disclosures, workflow_engine, workflow_store
from services.errors import ProviderError

logger = logging.getLogger(__name__)

#: Loop period. Interval triggers are >= 5 min; the announcement feed is
#: cached for 15 min upstream, so a 60 s tick costs nothing extra.
TICK_SECONDS = 60.0

_ANNOUNCEMENT_POLL_LIMIT = 20

_loop_task: asyncio.Task[None] | None = None
#: schedule id -> its in-flight fire.
_fires: dict[str, asyncio.Task[None]] = {}


def start() -> None:
    """Start the loop (idempotent)."""
    global _loop_task
    if _loop_task is None or _loop_task.done():
        _loop_task = asyncio.create_task(_loop())


async def stop() -> None:
    """Cancel the loop and every in-flight fire, and wait for them."""
    global _loop_task
    tasks = [t for t in (_loop_task, *_fires.values()) if t is not None]
    _loop_task = None
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    _fires.clear()


async def _loop() -> None:
    while True:
        try:
            await tick(time.time())
        except Exception:  # noqa: BLE001 — one bad tick must not stop the scheduler
            logger.exception("workflow_scheduler: tick failed")
        await asyncio.sleep(TICK_SECONDS)


async def tick(now: float) -> list[asyncio.Task[None]]:
    """Start a fire for every enabled schedule that is due at ``now`` (epoch s).

    Returns the fires started (tests await them).
    """
    started: list[asyncio.Task[None]] = []
    for schedule in workflow_store.list_schedules():
        if not schedule.enabled or schedule.id in _fires:
            continue
        trigger = schedule.trigger
        if isinstance(trigger, IntervalTrigger):
            last = schedule.last_fired_at or schedule.created_at
            if now * 1000 - last < trigger.every_minutes * 60_000:
                continue
            inputs: dict[str, Any] = {}
            seen: str | None = None
        else:
            item = await _next_announcement(schedule, trigger)
            if item is None:
                continue
            inputs = {"value": item, "announcement": item}
            seen = item["ts"]
        workflow_store.mark_schedule_fired(schedule.id, int(now * 1000), seen)
        task = asyncio.create_task(_fire(schedule, inputs))
        _fires[schedule.id] = task
        task.add_done_callback(lambda _t, sid=schedule.id: _fires.pop(sid, None))
        started.append(task)
    return started


async def _next_announcement(
    schedule: WorkflowSchedule, trigger: AnnouncementTrigger
) -> dict[str, Any] | None:
    """The oldest matching announcement newer than the last one fired on (or
    than the schedule's creation), or ``None``."""
    try:
        feed = await corporate_disclosures.get_announcements_cached(
            trigger.symbol, limit=_ANNOUNCEMENT_POLL_LIMIT
        )
    except ProviderError as exc:
        workflow_store.record_schedule_outcome(schedule.id, "error", f"feed unavailable: {exc}")
        return None
    watermark = (
        datetime.fromisoformat(schedule.last_seen).timestamp()
        if schedule.last_seen
        else schedule.created_at / 1000
    )
    phrase = trigger.phrase.casefold()
    # ponytail: a timestamp watermark; two matching items filed in the same
    # second fire once. Track seen keys if that ever matters.
    fresh = [
        a
        for a in feed.announcements
        if a.ts is not None and a.ts.timestamp() > watermark and phrase in a.headline.casefold()
    ]
    if not fresh:
        return None
    return min(fresh, key=lambda a: a.ts.timestamp()).model_dump(mode="json")


async def _fire(schedule: WorkflowSchedule, inputs: dict[str, Any]) -> None:
    try:
        spec = workflow_store.get_workflow(schedule.workflow_id)
        if spec is None:
            workflow_store.record_schedule_outcome(schedule.id, "error", "workflow not found")
            return
        result = await workflow_engine.run_workflow(spec, inputs=inputs)
        workflow_store.record_schedule_outcome(schedule.id, result.status, result.error)
    except asyncio.CancelledError:
        workflow_store.record_schedule_outcome(schedule.id, "error", "cancelled at shutdown")
        raise
    except Exception as exc:  # noqa: BLE001 — record, never crash the loop
        logger.exception("workflow_scheduler: schedule %s failed", schedule.id)
        workflow_store.record_schedule_outcome(schedule.id, "error", str(exc))
