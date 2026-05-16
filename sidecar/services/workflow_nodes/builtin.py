"""Ten built-in workflow node implementations.

Each handler has the signature ``async def(inputs, config) -> outputs``
required by :data:`services.workflow_engine.NodeHandler`. Handlers are
deliberately small and dependency-light — they shim into the existing
sidecar services (``provider_registry``, ``indicators``, ``agent_runtime``)
rather than re-implementing logic. Inputs that come from upstream node
outputs are dicts shaped by Pydantic ``model_dump`` (the foundation engine
hands them through verbatim); config is the static node-level config
from the saved workflow spec.

Error handling philosophy: a handler raises a :class:`ValueError` with a
human-readable message for configuration mistakes. The foundation engine
catches handler exceptions and surfaces them as ``node-error`` events,
so a raised ``ValueError`` produces the right per-node observability
without coupling this module to the engine's error type. Provider errors
propagate verbatim — the workflow run records them on the node and
marks downstream nodes failed.

The agent-invoke handler is intentionally tolerant of "no provider key
configured" — workflows must run end-to-end in CI where no real LLM
keys exist, so the handler degrades to a sentinel content string rather
than failing the run.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from models.agent import AgentContextSnapshot
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMErrorEvent
from services import agent_runtime, indicators, provider_registry

logger = logging.getLogger(__name__)

#: Hard cap on ``flow.sleep`` — keeps a malformed workflow from hanging the
#: sidecar for hours. 300s matches the plan brief.
_SLEEP_MAX_SECONDS = 300.0

#: Truthy strings that ``logic.branch`` recognises when routing a string-valued
#: condition. Anything else is treated by Python's normal truthiness.
_TRUTHY_STRINGS = frozenset({"true", "yes", "1", "on"})


# ---------------------------------------------------------------------------
# data.fetch_quote
# ---------------------------------------------------------------------------


async def fetch_quote(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Fetch the latest quote for one symbol via the provider registry.

    Resolution order: ``inputs["symbol"]`` overrides ``config["symbol"]``.
    Either may be set; both missing is a configuration error.
    """
    symbol = inputs.get("symbol") or config.get("symbol")
    if not symbol:
        raise ValueError("data.fetch_quote: missing 'symbol' (provide via input or config)")
    asset_class = config.get("asset_class", "equity")
    # provider_registry.get_quote is sync; run it in a thread so the engine's
    # event loop is not blocked by HTTP I/O on the underlying yfinance/ccxt call.
    quote = await asyncio.to_thread(provider_registry.get_quote, str(symbol), asset_class)
    return {"quote": quote.model_dump(mode="json")}


# ---------------------------------------------------------------------------
# data.fetch_history
# ---------------------------------------------------------------------------


async def fetch_history(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Fetch an OHLCV history series for one symbol.

    Config keys: ``symbol`` (required if no input), ``period`` (optional
    range hint, mapped to the registry's ``range_`` parameter),
    ``interval`` (timeframe, default ``"1d"``), ``asset_class`` (default
    ``"equity"``).
    """
    symbol = inputs.get("symbol") or config.get("symbol")
    if not symbol:
        raise ValueError("data.fetch_history: missing 'symbol' (provide via input or config)")
    timeframe = config.get("interval") or inputs.get("interval") or "1d"
    range_ = config.get("period") or inputs.get("period")
    asset_class = config.get("asset_class", "equity")
    series = await asyncio.to_thread(
        provider_registry.get_history, str(symbol), str(timeframe), range_, asset_class
    )
    return {"series": series.model_dump(mode="json")}


# ---------------------------------------------------------------------------
# compute.indicator
# ---------------------------------------------------------------------------


async def compute_indicator(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Compute one indicator from the 50-key registry against an OHLCV series.

    Inputs: ``series`` — the dict from an upstream ``data.fetch_history`` node.
    Config: ``indicator_id`` — the indicator key (e.g. ``"rsi"``, ``"macd"``).
    Optional ``params`` are reserved for future per-indicator knobs but are
    not consumed today (the indicator service uses defaults).
    """
    series_payload = inputs.get("series")
    if series_payload is None:
        raise ValueError("compute.indicator: missing 'series' input")
    indicator_id = config.get("indicator_id")
    if not indicator_id:
        raise ValueError("compute.indicator: missing 'indicator_id' in config")
    # Rehydrate the OHLCVSeries Pydantic model so the indicator service runs
    # on a typed value. ``series_payload`` may be a model dump (camelCase or
    # snake_case) or a live model — handle both for test ergonomics.
    if hasattr(series_payload, "model_dump"):
        series_obj = series_payload  # already a Pydantic model
    else:
        from models.market import OHLCVSeries

        series_obj = OHLCVSeries.model_validate(series_payload)
    response = await asyncio.to_thread(indicators.compute, series_obj, [str(indicator_id)])
    return {"result": response.model_dump(mode="json")}


# ---------------------------------------------------------------------------
# ai.agent_invoke
# ---------------------------------------------------------------------------


def _render_template(template: str, context: dict[str, Any]) -> str:
    """Best-effort ``str.format``-style template rendering.

    Missing keys fall back to ``""`` so a half-wired workflow does not
    crash on a typo — the agent sees an empty slot instead.
    """
    try:
        return template.format(**context)
    except (KeyError, IndexError):
        # Replace the missing field with empty string; render whatever else
        # is well-formed.
        class _Defaulting(dict):
            def __missing__(self, key: str) -> str:  # noqa: D401, ANN101
                return ""

        try:
            return template.format_map(_Defaulting(context))
        except Exception:  # noqa: BLE001
            return template


async def agent_invoke(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Invoke a first-party agent and aggregate its streamed reply.

    Config: ``agent_id`` (required), ``prompt_template`` (required —
    a ``str.format``-style template rendered with ``inputs`` as the
    context dict, so ``{context}`` interpolates ``inputs["context"]``).
    Optional ``provider`` / ``model`` overrides ride through to the
    agent runtime; ``api_key`` is read from the env (``VYSTED_<PROV>_API_KEY``)
    in production. In a CI / no-key environment the agent runtime returns
    an LLMErrorEvent — this handler still completes by returning a
    sentinel ``"(no provider key configured)"`` string rather than failing
    the workflow.
    """
    agent_id = config.get("agent_id")
    if not agent_id:
        raise ValueError("ai.agent_invoke: missing 'agent_id' in config")
    template = config.get("prompt_template") or "{context}"
    # Render the prompt with the inputs dict as the format context.
    prompt = _render_template(str(template), inputs)
    api_key = config.get("api_key") or inputs.get("api_key")
    provider = config.get("provider")
    model = config.get("model")
    context_snapshot: AgentContextSnapshot | None = None
    if "context_snapshot" in inputs and isinstance(inputs["context_snapshot"], dict):
        try:
            context_snapshot = AgentContextSnapshot.model_validate(inputs["context_snapshot"])
        except Exception:  # noqa: BLE001 — best-effort context wiring
            context_snapshot = None

    text_chunks: list[str] = []
    error_message: str | None = None
    try:
        async for event in agent_runtime.invoke_agent(
            agent_id=str(agent_id),
            prompt=prompt,
            context_snapshot=context_snapshot,
            api_key=api_key,
            provider=provider,
            model=model,
        ):
            if isinstance(event, LLMDeltaEvent):
                text_chunks.append(event.text)
            elif isinstance(event, LLMErrorEvent):
                error_message = event.message
            elif isinstance(event, LLMDoneEvent):
                continue
    except Exception as exc:  # noqa: BLE001 — degrade gracefully on transport errors
        error_message = str(exc)

    content = "".join(text_chunks)
    if not content:
        # No-key / CI path: return a deterministic sentinel so the run
        # completes without surfacing an error. The intent is "this ran but
        # the LLM call was a no-op" — useful in tests and offline demos.
        if error_message:
            content = "(no provider key configured)"
    return {"content": content, "agent_id": str(agent_id), "error": error_message}


# ---------------------------------------------------------------------------
# logic.branch
# ---------------------------------------------------------------------------


def _is_truthy(value: Any) -> bool:
    """Return Python truthiness with a small string-aware override."""
    if isinstance(value, str):
        return value.strip().lower() in _TRUTHY_STRINGS or bool(value.strip())
    return bool(value)


async def logic_branch(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Route the input ``value`` down one of two output paths.

    Inputs: ``value`` (the payload to route), ``threshold`` (optional
    numeric threshold; when set, the value is compared with ``> threshold``).
    Config: ``condition_field`` is reserved for future deep-pathing and is
    currently informational only. ``mode`` may be ``"truthy"`` (default)
    or ``"gt"`` (greater-than threshold).

    Outputs: ``true_path`` carries the value on a positive condition and is
    ``None`` otherwise; ``false_path`` is the inverse. Downstream nodes wire
    to whichever port they want to consume.
    """
    value = inputs.get("value")
    mode = config.get("mode", "truthy")
    if mode == "gt":
        threshold = inputs.get("threshold", config.get("threshold", 0))
        try:
            condition = float(value) > float(threshold)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "logic.branch: 'gt' mode requires numeric value/threshold; "
                f"got {value!r}/{threshold!r}"
            ) from exc
    else:
        condition = _is_truthy(value)
    if condition:
        return {"true_path": value, "false_path": None}
    return {"true_path": None, "false_path": value}


# ---------------------------------------------------------------------------
# logic.compare
# ---------------------------------------------------------------------------


_COMPARE_OPS: dict[str, Any] = {
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
}


async def logic_compare(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Numeric comparator — emits a boolean.

    Config: ``op`` ∈ ``{lt, gt, eq, lte, gte, neq}``. Inputs: ``a``, ``b``.
    Equality / inequality work on any comparable type; other ops coerce to
    ``float`` so a quote price (str) and a literal number compare cleanly.
    """
    op = config.get("op", "eq")
    fn = _COMPARE_OPS.get(op)
    if fn is None:
        raise ValueError(
            f"logic.compare: unknown op {op!r}; expected one of {sorted(_COMPARE_OPS)}"
        )
    a = inputs.get("a")
    b = inputs.get("b")
    if op in ("eq", "neq"):
        return {"result": bool(fn(a, b))}
    try:
        return {"result": bool(fn(float(a), float(b)))}  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"logic.compare: op {op!r} requires numeric a/b; got {a!r}/{b!r}") from exc


# ---------------------------------------------------------------------------
# action.log
# ---------------------------------------------------------------------------


_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


async def action_log(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Write a workflow log entry at the configured level.

    Config: ``level`` (default ``"info"``), ``message_template`` (default
    ``"{value}"``). The template is ``str.format``-rendered against the
    inputs dict, so ``{symbol}`` resolves to ``inputs["symbol"]``.
    """
    level_name = str(config.get("level", "info")).lower()
    level = _LOG_LEVELS.get(level_name, logging.INFO)
    template = str(config.get("message_template", "{value}"))
    message = _render_template(template, inputs)
    logger.log(level, "workflow.action.log: %s", message)
    return {"logged": True, "level": level_name, "message": message}


# ---------------------------------------------------------------------------
# action.notify_desktop
# ---------------------------------------------------------------------------


async def action_notify_desktop(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Emit a desktop-notification intent.

    The sidecar does not call Tauri directly — instead it logs the intent
    and emits a structured payload the frontend's :mod:`useWorkflowStore`
    can dispatch via ``@tauri-apps/api/notification`` when it sees the
    node's output stream past. For v0.5.0 foundation, the handler simply
    records the intent.
    """
    title = _render_template(str(config.get("title", "Workflow")), inputs)
    message = _render_template(str(config.get("message_template", "{value}")), inputs)
    logger.info("workflow.action.notify_desktop: %s — %s", title, message)
    return {
        "notified": True,
        "title": title,
        "message": message,
        # The frontend store narrows on ``intent == "desktop-notification"``
        # to know which output to forward into the Tauri notification API.
        "intent": "desktop-notification",
    }


# ---------------------------------------------------------------------------
# transform.json_path
# ---------------------------------------------------------------------------


def _walk_path(payload: Any, path: str) -> Any:
    """Walk a dotted path through a nested dict / list.

    Numeric segments index into lists; non-numeric segments index into dicts.
    Returns ``None`` on any miss rather than raising — workflows often
    tentatively probe optional fields.
    """
    if not path:
        return payload
    cursor: Any = payload
    for raw in path.split("."):
        if cursor is None:
            return None
        segment = raw.strip()
        if not segment:
            continue
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        elif isinstance(cursor, list):
            try:
                cursor = cursor[int(segment)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cursor


async def transform_json_path(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Extract a value from a dict/list payload by dotted path.

    Config: ``path`` (required). Inputs: ``value`` (the payload to walk).
    Missing fields return ``None`` — the absence of a value is itself a
    valid output that downstream ``logic.branch`` / ``logic.compare`` nodes
    can act on.
    """
    path = config.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("transform.json_path: 'path' (non-empty string) is required in config")
    payload = inputs.get("value")
    return {"extracted": _walk_path(payload, path)}


# ---------------------------------------------------------------------------
# flow.sleep
# ---------------------------------------------------------------------------


async def flow_sleep(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Sleep for ``seconds`` (clamped to ``[0, 300]``).

    Passes the upstream inputs through unchanged on the ``value`` port so
    a sleep can sit in the middle of a chain without breaking the wire.
    """
    raw = config.get("seconds", 0)
    try:
        seconds = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"flow.sleep: 'seconds' must be numeric; got {raw!r}") from exc
    clamped = max(0.0, min(_SLEEP_MAX_SECONDS, seconds))
    if clamped > 0:
        await asyncio.sleep(clamped)
    return {"value": inputs.get("value"), "slept": clamped}
