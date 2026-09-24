"""Delegate-run executor — durable, budgeted, cancellable background agent tasks.

This is the engine behind US9 / FR-026/027/028 / SC-008. A *Delegate run* is an
autonomous background agent task:

- **Durable (FR-027).** :func:`launch_run` persists a run row, then spawns a
  DETACHED ``asyncio`` task that drives :func:`agent_runtime.invoke_agent`. The
  task is owned by a module-level registry, NOT by the launching request — once
  ``launch_run`` returns the run id, the HTTP connection may close and the task
  keeps running. Status / cost / checkpoint live in ``runs_store`` so the
  run-tray UI observes the run through ``GET /runs``.

- **Budgeted (FR-026 / SC-008).** Each round's usage is fed to a
  :class:`~services.budget_guard.BudgetGuard` via the ``on_round_usage``
  callback ``invoke_agent`` exposes. After every round the run's cost is written
  to ``runs_store``; if ``guard.breach()`` returns a reason the run is ABORTED —
  status ``error``, ``detail`` set to the stated reason, the messages-so-far
  checkpointed — and the stream is torn down. A breach aborts 100% of the time.

- **Cancellable + foreground-able.** :func:`cancel_run` cancels the task and
  marks the run ``cancelled``. ``GET /runs/{id}`` returns the transcript digest
  so the user can bring the background run into the foreground.

- **Human-in-the-loop (FR-028 — scoped).** A run can be PAUSED for a human
  question (:func:`pause_run`). :func:`answer_run` records the human's reply and
  RESUMES the run by re-entering the agent loop from the persisted checkpoint
  with the answer appended as a new user turn — a genuine human-in-the-loop
  handshake. :func:`resume_run` re-enters an aborted run from its checkpoint with
  fresh ceilings (budget-breach recovery). **Scope note:** the pause is an
  EXPLICIT signal (operator/host-driven), not an autonomous in-loop ``ask_user``
  tool call — wiring the agent loop to self-pause would require a new catalog
  capability + the §6.5/parity audits to cover it, which is deferred. The
  pause/answer/resume control plane is fully implemented and durable; only the
  autonomous self-pause trigger is out of scope here.

The BYOK ``api_key`` lives ONLY on the in-memory task closure — never persisted
to ``runs_store``, never logged. The guard governs SPEND only; no trading
path exists.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import config
from models.agent import AgentContextSnapshot
from models.llm import LLMMessage, LLMProviderId, LLMUsage
from models.run import DEFAULT_RUN_BUDGET, RunBudget, RunCost, RunStatus
from services import agent_runtime, runs_store
from services.agent_tools.schemas import HOST_ACTION_TOOLS
from services.budget_guard import BudgetGuard
from services.runs_store import RunNotFound, RunStateError

logger = logging.getLogger(__name__)

# run_id -> the detached asyncio.Task driving the agent loop.
_TASKS: dict[str, asyncio.Task[None]] = {}


class RunManagerError(RuntimeError):
    """Raised when a run cannot be launched (unknown agent).

    Run-control errors are the store's typed :class:`RunNotFound` (404) and
    :class:`RunStateError` (409).
    """


# ---------------------------------------------------------------------------
# Snapshot coercion
# ---------------------------------------------------------------------------


def _coerce_snapshot(raw: dict[str, Any] | None) -> AgentContextSnapshot | None:
    """Build an ``AgentContextSnapshot`` from the launch request's dict, leniently.

    The frontend sends a free-form context snapshot; we accept the structured
    shape and fall back to wrapping a bare mapping so a thin snapshot still
    reaches the agent loop rather than erroring the run.
    """
    if raw is None:
        return None
    try:
        return AgentContextSnapshot.model_validate(raw)
    except Exception:  # noqa: BLE001 — tolerate a loose snapshot shape
        return AgentContextSnapshot(by_source=raw if isinstance(raw, dict) else {})


# ---------------------------------------------------------------------------
# The detached run driver
# ---------------------------------------------------------------------------


async def _drive_run(
    *,
    run_id: str,
    agent_id: str,
    prompt: str,
    snapshot: AgentContextSnapshot | None,
    provider: LLMProviderId | None,
    model: str | None,
    api_key: str | None,
    budget: RunBudget,
    options: dict[str, Any],
    resume_messages: list[LLMMessage] | None = None,
) -> None:
    """Drive one agent invocation to completion under a BudgetGuard.

    The detached task body. Streams ``invoke_agent``; after every round records
    usage into a guard, persists cost, and aborts on the first breach. Captures
    a running transcript for the checkpoint so a resume has context. Every exit
    writes a terminal status to the store.
    """
    guard = BudgetGuard(
        max_tokens=budget.max_tokens,
        max_spend_usd=budget.max_spend_usd,
        max_wall_seconds=budget.max_wall_seconds,
        max_steps=budget.max_steps,
    )
    provider_str = str(provider or "")
    options = dict(options)
    # R10: a resumed run re-threads its persisted region INSIDE the detached
    # task (the resume HTTP request's middleware set a region for the WRONG
    # request scope). Popped here so an unknown kwarg never leaks into the
    # adapter call; ``research_depth`` stays in options — invoke_agent pops it
    # into the depth ContextVar floor itself.
    region = options.pop("region", None)
    if isinstance(region, str) and region:
        config.set_request_region(region)
    transcript: list[dict[str, Any]] = []
    if resume_messages:
        transcript.extend(m.model_dump() for m in resume_messages)
    transcript.append({"role": "user", "content": prompt})
    breach_reason: str | None = None
    delta_buffer: list[str] = []
    # The run's collectable output (R15-AGENT-013): the last brief it published
    # and the host actions it proposed, delivered once to the originating chat
    # thread on the terminal poll — never applied here.
    brief: dict[str, Any] | None = None
    host_actions: list[dict[str, Any]] = []

    def _output() -> dict[str, Any]:
        return {
            "answer": "".join(delta_buffer).strip() or None,
            "brief": brief,
            "host_actions": list(host_actions),
        }

    def _on_round_usage(usage: LLMUsage, used_model: str) -> None:
        # Fold the round's usage into the guard, then persist the running cost so
        # GET /runs reflects spend-so-far even before the run finishes.
        guard.record(usage, used_model, provider_str)
        runs_store.update_run(run_id, cost=RunCost.model_validate(guard.cost()))
        nonlocal breach_reason
        if breach_reason is None:
            breach_reason = guard.breach()

    try:
        # The round-boundary breach() check below covers tokens/spend/steps (which
        # only change at a round terminator) AND the common wall-clock case. But
        # wall-clock advances continuously DURING a round, and the LLM adapters
        # carry no per-stream timeout — so a single long round, or a stalled
        # provider stream that never reaches its terminator, could outlive
        # max_wall_seconds without the round-boundary check ever firing. This
        # asyncio.timeout makes the wall ceiling a HARD ceiling regardless of round
        # boundaries (SC-008). asyncio.timeout(None) is a documented no-op, so a
        # run with no wall budget is unaffected.
        async with asyncio.timeout(budget.max_wall_seconds):
            async for event in agent_runtime.invoke_agent(
                agent_id=agent_id,
                prompt=prompt,
                context_snapshot=snapshot,
                api_key=api_key,
                provider=provider,
                model=model,
                options=dict(options),
                mode="delegate",
                on_round_usage=_on_round_usage,
            ):
                # A round's terminator may have flagged a breach; stop before
                # anything of the next round lands in the output.
                if breach_reason is not None:
                    break
                kind = getattr(event, "kind", None)
                if kind == "delta":
                    delta_buffer.append(getattr(event, "text", ""))
                elif kind == "tool_use":
                    name = getattr(event, "name", "?")
                    transcript.append({"role": "assistant", "content": f"[tool_use {name}]"})
                    # A tool round ends the model's paragraph; the next round's
                    # text starts a new one instead of running on.
                    if delta_buffer and delta_buffer[-1] != "\n\n":
                        delta_buffer.append("\n\n")
                    if name == "publish_brief":
                        brief = dict(event.input)
                    elif name in HOST_ACTION_TOOLS:
                        host_actions.append(
                            {
                                "tool_call_id": event.tool_call_id,
                                "name": name,
                                "input": dict(event.input),
                            }
                        )
                elif kind == "error":
                    breach_reason = breach_reason or getattr(event, "message", "agent error")

        if delta_buffer:
            transcript.append({"role": "assistant", "content": "".join(delta_buffer)})

        if breach_reason is not None:
            # SC-008 — abort with the stated reason + a resumable checkpoint.
            runs_store.update_run(
                run_id,
                status="error",
                detail=breach_reason,
                checkpoint=list(transcript),
                output=_output(),
            )
            return

        runs_store.update_run(
            run_id,
            status="done",
            detail="completed",
            checkpoint=list(transcript),
            output=_output(),
        )
    except TimeoutError:
        # The wall-clock backstop fired (asyncio.timeout). It cancels mid-round, so
        # this is the ONLY path that enforces max_wall_seconds against a hung or
        # over-long round. Abort with the stated reason + a resumable checkpoint
        # (SC-008), exactly like a round-boundary breach.
        if delta_buffer:
            transcript.append({"role": "assistant", "content": "".join(delta_buffer)})
        elapsed = guard.wall_seconds()
        if budget.max_wall_seconds is not None and elapsed >= budget.max_wall_seconds:
            reason = guard.breach() or (
                f"wall-clock ceiling {budget.max_wall_seconds:g}s reached ({elapsed:.1f}s elapsed)"
            )
        else:
            # A TimeoutError that is NOT the wall backstop (e.g. a tool raised its
            # own timeout) — report it as a generic failure, never mislabeled as a
            # ceiling breach.
            reason = "run failed: operation timed out"
        runs_store.update_run(
            run_id, status="error", detail=reason, checkpoint=list(transcript), output=_output()
        )
    except asyncio.CancelledError:
        # cancel_run already wrote status="cancelled"; persist the partial
        # transcript and re-raise so the task finishes in its cancelled state.
        runs_store.update_run(run_id, checkpoint=list(transcript))
        raise
    except Exception as exc:  # noqa: BLE001 — any agent failure ends the run
        logger.exception("delegate run %s crashed: %s", run_id, exc)
        runs_store.update_run(
            run_id,
            status="error",
            detail=f"run failed: {exc}",
            checkpoint=list(transcript),
            output=_output(),
        )
    finally:
        _TASKS.pop(run_id, None)


def _with_floor(budget: RunBudget | None) -> RunBudget:
    """Fill every omitted ceiling from the server default (R15-AGENT-034)."""
    given = budget.model_dump(exclude_none=True) if budget else {}
    return DEFAULT_RUN_BUDGET.model_copy(update=given)


def _spawn(run_id: str, **kwargs: Any) -> asyncio.Task[None]:
    """Create and register the detached driver task for ``run_id``."""
    task = asyncio.create_task(_drive_run(run_id=run_id, **kwargs))
    _TASKS[run_id] = task
    return task


# ---------------------------------------------------------------------------
# Public control surface
# ---------------------------------------------------------------------------


def launch_run(
    *,
    agent_id: str,
    prompt: str,
    context_snapshot: dict[str, Any] | None = None,
    provider: LLMProviderId | None = None,
    model: str | None = None,
    api_key: str | None = None,
    budget: RunBudget | None = None,
    options: dict[str, Any] | None = None,
) -> str:
    """Create a durable run row and spawn its detached executor task.

    Returns the new run id immediately — the caller (the HTTP route) returns it
    in a 201 and the request closes while the task keeps running (FR-027).
    Raises :class:`RunManagerError` if the agent id is unknown.
    """
    spec = agent_runtime.get_agent(agent_id)
    if spec is None:
        raise RunManagerError(f"unknown agent: {agent_id!r}")

    run_budget = _with_floor(budget)
    run_id = uuid.uuid4().hex
    # R10: persist the NON-SECRET options a resume must re-thread — the
    # caller's research_depth plus the LAUNCH request's active region (the
    # store's allow-list filters; a key can never land in SQLite).
    persisted_options = {**dict(options or {}), "region": config.get_region()}
    runs_store.create_run(
        run_id=run_id,
        agent_id=agent_id,
        agent_name=spec.name,
        budget=run_budget,
        options=persisted_options,
    )
    _spawn(
        run_id,
        agent_id=agent_id,
        prompt=prompt,
        snapshot=_coerce_snapshot(context_snapshot),
        provider=provider,
        model=model,
        api_key=api_key,
        budget=run_budget,
        options=dict(options or {}),
    )
    return run_id


def cancel_run(run_id: str) -> None:
    """Mark a live run ``cancelled`` and cancel its task.

    Marks the store first (so the terminal state is durable even if the task
    is already gone), then cancels the in-flight task. A finished run is never
    rewritten: the store raises :class:`RunStateError`, an unknown id
    :class:`RunNotFound`.
    """
    runs_store.update_run(run_id, status="cancelled", detail="cancelled by user")
    task = _TASKS.get(run_id)
    if task is not None and not task.done():
        task.cancel()


def pause_run(run_id: str, question: str) -> None:
    """Pause a RUNNING run for a human-in-the-loop question (FR-028).

    Flips the run to ``paused`` with the question (the store refuses any other
    starting status), then cancels the in-flight task, which checkpoints the
    transcript on the way out. The human answers via :func:`answer_run`.
    """
    runs_store.update_run(
        run_id, status="paused", from_status=frozenset({"running"}), question=question
    )
    task = _TASKS.get(run_id)
    if task is not None and not task.done():
        task.cancel()


def answer_run(
    run_id: str,
    answer: str,
    *,
    api_key: str | None = None,
    budget: RunBudget | None = None,
) -> None:
    """Deliver a human reply to a paused run and resume it (FR-028).

    The answer is appended to the run's checkpoint as a new user turn, then the
    agent loop is re-entered from that checkpoint. Raises :class:`RunNotFound`
    for an unknown run and :class:`RunStateError` when it is not paused.
    """
    _resume(run_id, frozenset({"paused"}), answer=answer, api_key=api_key, budget=budget)


def resume_run(
    run_id: str,
    *,
    api_key: str | None = None,
    budget: RunBudget | None = None,
) -> None:
    """Re-enter an ``error`` or ``cancelled`` run from its checkpoint (FR-028).

    Budget-breach recovery: relaunch with fresh ceilings. Raises
    :class:`RunNotFound` for an unknown run and :class:`RunStateError` for any
    other status (a finished run is never re-executed), a still-live task or a
    missing checkpoint.
    """
    _resume(run_id, frozenset({"error", "cancelled"}), api_key=api_key, budget=budget)


def _resume(
    run_id: str,
    from_status: frozenset[RunStatus],
    *,
    answer: str | None = None,
    api_key: str | None,
    budget: RunBudget | None,
) -> None:
    """Move a run back to ``running`` from ``from_status`` and respawn its task."""
    run = runs_store.get_run(run_id)
    if run is None:
        raise RunNotFound(f"unknown run: {run_id!r}")
    existing = _TASKS.get(run_id)
    if existing is not None and not existing.done():
        raise RunStateError(f"run {run_id!r} is still running")

    checkpoint = runs_store.get_checkpoint(run_id)
    if answer is not None:
        checkpoint.append({"role": "user", "content": answer})
    prompt = ""
    history: list[LLMMessage] = []
    for msg in checkpoint:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if not isinstance(content, str) or not content:
            continue
        if role == "user" and not prompt:
            prompt = content
            continue
        if role in ("user", "assistant"):
            history.append(LLMMessage(role=role, content=content))
    if not prompt:
        raise RunStateError(f"run {run_id!r} has no checkpoint to resume from")

    resume_budget = _with_floor(budget or run.budget)
    # R10: re-merge the persisted non-secret options (research_depth, region)
    # so the depth ContextVar floor / locale re-thread into the resumed loop.
    options: dict[str, Any] = dict(runs_store.get_options(run_id))
    if history:
        options["history"] = [m.model_dump() for m in history]
    runs_store.update_run(
        run_id,
        status="running",
        from_status=from_status,
        detail="resumed",
        clear_question=True,
        checkpoint=checkpoint,
        cost=RunCost(),  # fresh ceilings → fresh running total
    )
    _spawn(
        run_id,
        agent_id=run.agent_id,
        prompt=prompt,
        snapshot=None,
        provider=None,
        model=None,
        api_key=api_key,
        budget=resume_budget,
        options=options,
        resume_messages=history,
    )


def active_run_ids() -> list[str]:
    """Return the ids of runs whose task is still in flight (for diagnostics)."""
    return [rid for rid, task in _TASKS.items() if not task.done()]


async def shutdown() -> None:
    """Cancel every in-flight run task — called on sidecar shutdown.

    Prevents detached PyInstaller-worker tasks from leaking past the lifespan.
    Each task is cancelled and awaited so its ``finally`` cleanup runs.
    """
    tasks = list(_TASKS.values())
    for task in tasks:
        if not task.done():
            task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001 — shutdown best-effort
            pass
    _TASKS.clear()


def reset_for_tests() -> None:
    """Cancel and drop every in-flight task (test isolation)."""
    for task in list(_TASKS.values()):
        if not task.done():
            task.cancel()
    _TASKS.clear()
