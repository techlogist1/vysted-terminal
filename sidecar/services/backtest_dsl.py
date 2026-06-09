"""Declarative custom-strategy signal DSL — R7 hackability Pillar 2.

A user/agent supplies a JSON definition::

    {"entry": "sma(20) > sma(50)", "exit": "rsi(14) > 70", "position_size": 100}

The sidecar parses each rule with the restricted recursive-descent grammar
below and evaluates it bar-by-bar inside the backtest engine. There is NO
``eval``/``exec``/``ast``-of-Python anywhere on this path — the tokenizer and
parser only ever accept the grammar's terminals, so an agent-authored string
can at worst fail to parse.

Grammar (EBNF) ::

    rule       = or_expr ;                       (* top level MUST be boolean *)
    or_expr    = and_expr { "or" and_expr } ;
    and_expr   = not_expr { "and" not_expr } ;
    not_expr   = "not" not_expr | comparison ;
    comparison = sum [ (">" | ">=" | "<" | "<=" | "==" | "!=") sum ] ;
    sum        = term { ("+" | "-") term } ;
    term       = factor { ("*" | "/") factor } ;
    factor     = "-" factor | primary ;
    primary    = NUMBER | FIELD | FUNC "(" INT ")" | "(" or_expr ")" ;

    FIELD = "open" | "high" | "low" | "close" | "volume" ;
    FUNC  = "sma" | "ema" | "rsi" | "highest" | "lowest" | "stdev" | "change" ;
    INT   = integer literal, 1..500 (indicator period) ;

Indicator semantics (per symbol, computed incrementally as the engine streams
bars — same single-pass model as the built-in strategies):

  - ``sma(n)``     simple moving average of the last n closes
  - ``ema(n)``     exponential MA, seeded with the SMA of the first n closes
  - ``rsi(n)``     Wilder RSI over n bar-to-bar close changes (0..100)
  - ``highest(n)`` max of the last n highs
  - ``lowest(n)``  min of the last n lows
  - ``stdev(n)``   population stdev of the last n closes
  - ``change(n)``  close minus the close n bars ago

Warm-up: every indicator yields ``None`` until its window fills; ``None``
propagates through every operator (including ``and``/``or``/``not``), so a
rule referencing ``sma(50)`` simply fires no signal for the first 49 bars.
Division by zero also yields ``None`` (no signal) rather than crashing a run.

The compiled rule reports the indicators it references and the warm-up bar
count so the frontend editor and the ``run_custom_backtest`` agent tool can
surface "uses sma(20), sma(50) — needs 50 bars" honestly.
"""

from __future__ import annotations

import re
import statistics
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from services.backtest_engine import (
    BacktestOrderIntent,
    BacktestStrategy,
    Bar,
    SimPortfolio,
)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class DslError(ValueError):
    """A parse/validation error with the 0-based character position."""

    def __init__(self, message: str, position: int | None = None) -> None:
        super().__init__(message)
        self.position = position


# ---------------------------------------------------------------------------
# Grammar surface
# ---------------------------------------------------------------------------

FIELDS: frozenset[str] = frozenset({"open", "high", "low", "close", "volume"})
FUNCTIONS: frozenset[str] = frozenset({"sma", "ema", "rsi", "highest", "lowest", "stdev", "change"})
KEYWORDS: frozenset[str] = frozenset({"and", "or", "not"})

MIN_PERIOD = 1
MAX_PERIOD = 500

_CMP_OPS = frozenset({">", ">=", "<", "<=", "==", "!="})


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Num:
    value: float


@dataclass(frozen=True)
class FieldRef:
    name: str


@dataclass(frozen=True)
class IndicatorRef:
    name: str
    period: int


@dataclass(frozen=True)
class BinOp:
    op: str
    left: Node
    right: Node


@dataclass(frozen=True)
class Compare:
    op: str
    left: Node
    right: Node


@dataclass(frozen=True)
class BoolOp:
    op: str  # "and" | "or"
    values: tuple[Node, ...]


@dataclass(frozen=True)
class NotOp:
    operand: Node


@dataclass(frozen=True)
class Neg:
    operand: Node


Node = Num | FieldRef | IndicatorRef | BinOp | Compare | BoolOp | NotOp | Neg


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Token:
    kind: str  # "num" | "ident" | "op"
    text: str
    position: int


_TOKEN_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)"
    r"|(?P<ident>[A-Za-z_][A-Za-z_0-9]*)"
    r"|(?P<op>>=|<=|==|!=|>|<|\+|-|\*|/|\(|\)|,)"
)


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        match = _TOKEN_RE.match(text, i)
        if match is None:
            raise DslError(f"unexpected character {ch!r}", position=i)
        kind = str(match.lastgroup)
        tokens.append(_Token(kind=kind, text=match.group(), position=i))
        i = match.end()
    return tokens


# ---------------------------------------------------------------------------
# Recursive-descent parser
# ---------------------------------------------------------------------------


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.tokens = _tokenize(text)
        self.index = 0

    # -- token helpers ------------------------------------------------------

    def _peek(self) -> _Token | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _next(self) -> _Token:
        token = self._peek()
        if token is None:
            raise DslError("unexpected end of expression", position=len(self.text))
        self.index += 1
        return token

    def _accept_op(self, *ops: str) -> _Token | None:
        token = self._peek()
        if token is not None and token.kind == "op" and token.text in ops:
            self.index += 1
            return token
        return None

    def _accept_keyword(self, word: str) -> _Token | None:
        token = self._peek()
        if token is not None and token.kind == "ident" and token.text == word:
            self.index += 1
            return token
        return None

    def _expect_op(self, op: str, context: str) -> _Token:
        token = self._peek()
        if token is None:
            raise DslError(f"expected {op!r} {context}", position=len(self.text))
        if token.kind != "op" or token.text != op:
            raise DslError(f"expected {op!r} {context}, found {token.text!r}", token.position)
        self.index += 1
        return token

    # -- grammar ------------------------------------------------------------

    def parse(self) -> Node:
        if not self.tokens:
            raise DslError("empty rule", position=0)
        node = self._or_expr()
        trailing = self._peek()
        if trailing is not None:
            raise DslError(f"unexpected {trailing.text!r}", trailing.position)
        return node

    def _or_expr(self) -> Node:
        values = [self._and_expr()]
        while self._accept_keyword("or") is not None:
            values.append(self._and_expr())
        return values[0] if len(values) == 1 else BoolOp(op="or", values=tuple(values))

    def _and_expr(self) -> Node:
        values = [self._not_expr()]
        while self._accept_keyword("and") is not None:
            values.append(self._not_expr())
        return values[0] if len(values) == 1 else BoolOp(op="and", values=tuple(values))

    def _not_expr(self) -> Node:
        if self._accept_keyword("not") is not None:
            return NotOp(operand=self._not_expr())
        return self._comparison()

    def _comparison(self) -> Node:
        left = self._sum()
        token = self._accept_op(*_CMP_OPS)
        if token is None:
            return left
        right = self._sum()
        # Chained comparisons (a < b < c) read ambiguously in a signal rule —
        # reject with a clear message rather than silently misparse.
        chained = self._peek()
        if chained is not None and chained.kind == "op" and chained.text in _CMP_OPS:
            raise DslError(
                "chained comparisons are not supported — combine with 'and'",
                chained.position,
            )
        return Compare(op=token.text, left=left, right=right)

    def _sum(self) -> Node:
        node = self._term()
        while True:
            token = self._accept_op("+", "-")
            if token is None:
                return node
            node = BinOp(op=token.text, left=node, right=self._term())

    def _term(self) -> Node:
        node = self._factor()
        while True:
            token = self._accept_op("*", "/")
            if token is None:
                return node
            node = BinOp(op=token.text, left=node, right=self._factor())

    def _factor(self) -> Node:
        if self._accept_op("-") is not None:
            return Neg(operand=self._factor())
        return self._primary()

    def _primary(self) -> Node:
        token = self._next()
        if token.kind == "num":
            return Num(value=float(token.text))
        if token.kind == "op" and token.text == "(":
            node = self._or_expr()
            self._expect_op(")", "to close the parenthesis")
            return node
        if token.kind == "ident":
            name = token.text.lower()
            if name in KEYWORDS:
                raise DslError(f"unexpected keyword {name!r}", token.position)
            if name in FIELDS:
                return FieldRef(name=name)
            if name in FUNCTIONS:
                return self._indicator_call(name, token)
            raise DslError(
                f"unknown identifier {token.text!r} — fields: {', '.join(sorted(FIELDS))}; "
                f"functions: {', '.join(sorted(FUNCTIONS))}",
                token.position,
            )
        raise DslError(f"unexpected {token.text!r}", token.position)

    def _indicator_call(self, name: str, name_token: _Token) -> IndicatorRef:
        self._expect_op("(", f"after {name!r}")
        arg = self._next()
        if arg.kind != "num" or "." in arg.text:
            raise DslError(
                f"{name}() takes one integer period, e.g. {name}(20)",
                arg.position if arg.kind != "op" or arg.text != ")" else name_token.position,
            )
        period = int(arg.text)
        if not (MIN_PERIOD <= period <= MAX_PERIOD):
            raise DslError(
                f"{name}() period must be {MIN_PERIOD}..{MAX_PERIOD}, got {period}",
                arg.position,
            )
        self._expect_op(")", f"to close {name}()")
        return IndicatorRef(name=name, period=period)


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompiledRule:
    """A parsed rule plus the indicator references it makes."""

    source: str
    root: Node
    indicators: frozenset[tuple[str, int]]
    required_bars: int


def _collect_indicators(node: Node, out: set[tuple[str, int]]) -> None:
    if isinstance(node, IndicatorRef):
        out.add((node.name, node.period))
    elif isinstance(node, BinOp | Compare):
        _collect_indicators(node.left, out)
        _collect_indicators(node.right, out)
    elif isinstance(node, BoolOp):
        for value in node.values:
            _collect_indicators(value, out)
    elif isinstance(node, NotOp | Neg):
        _collect_indicators(node.operand, out)


def _warmup_bars(name: str, period: int) -> int:
    # rsi/change need a previous close beyond the window itself.
    return period + 1 if name in ("rsi", "change") else period


def _is_boolean(node: Node) -> bool:
    return isinstance(node, Compare | BoolOp | NotOp)


def compile_rule(source: str) -> CompiledRule:
    """Parse one rule. Raises :class:`DslError` with a character position."""
    stripped = source.strip()
    if not stripped:
        raise DslError("empty rule", position=0)
    root = _Parser(source).parse()
    if not _is_boolean(root):
        raise DslError(
            "rule must be a comparison or boolean expression, e.g. sma(20) > sma(50)",
            position=0,
        )
    indicators: set[tuple[str, int]] = set()
    _collect_indicators(root, indicators)
    required = max((_warmup_bars(n, p) for n, p in indicators), default=1)
    return CompiledRule(
        source=stripped,
        root=root,
        indicators=frozenset(indicators),
        required_bars=required,
    )


# ---------------------------------------------------------------------------
# Incremental per-symbol indicator state
# ---------------------------------------------------------------------------


class _EmaState:
    """EMA seeded with the SMA of the first ``period`` closes."""

    def __init__(self, period: int) -> None:
        self.period = period
        self._k = 2.0 / (period + 1.0)
        self._seed_sum = 0.0
        self._count = 0
        self.value: float | None = None

    def update(self, close: float) -> None:
        if self.value is None:
            self._seed_sum += close
            self._count += 1
            if self._count == self.period:
                self.value = self._seed_sum / self.period
            return
        self.value = (close - self.value) * self._k + self.value


class _RsiState:
    """Wilder RSI over ``period`` bar-to-bar close changes."""

    def __init__(self, period: int) -> None:
        self.period = period
        self._prev_close: float | None = None
        self._count = 0
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self.value: float | None = None

    def update(self, close: float) -> None:
        prev = self._prev_close
        self._prev_close = close
        if prev is None:
            return
        gain = max(close - prev, 0.0)
        loss = max(prev - close, 0.0)
        self._count += 1
        if self._count < self.period:
            self._avg_gain += gain
            self._avg_loss += loss
            return
        if self._count == self.period:
            self._avg_gain = (self._avg_gain + gain) / self.period
            self._avg_loss = (self._avg_loss + loss) / self.period
        else:
            self._avg_gain = (self._avg_gain * (self.period - 1) + gain) / self.period
            self._avg_loss = (self._avg_loss * (self.period - 1) + loss) / self.period
        if self._avg_loss == 0.0:
            self.value = 100.0
        else:
            rs = self._avg_gain / self._avg_loss
            self.value = 100.0 - (100.0 / (1.0 + rs))


class SymbolState:
    """Rolling buffers + incremental indicator state for one symbol."""

    def __init__(self, indicators: frozenset[tuple[str, int]]) -> None:
        max_period = max((p for _, p in indicators), default=1)
        # change(n) needs the close n bars back — keep one extra slot.
        self._closes: deque[float] = deque(maxlen=max_period + 1)
        self._highs: deque[float] = deque(maxlen=max_period)
        self._lows: deque[float] = deque(maxlen=max_period)
        self._emas = {p: _EmaState(p) for n, p in indicators if n == "ema"}
        self._rsis = {p: _RsiState(p) for n, p in indicators if n == "rsi"}

    def update(self, bar: Bar) -> None:
        self._closes.append(bar.close)
        self._highs.append(bar.high)
        self._lows.append(bar.low)
        for ema in self._emas.values():
            ema.update(bar.close)
        for rsi in self._rsis.values():
            rsi.update(bar.close)

    def indicator(self, name: str, period: int) -> float | None:
        """Current value, or ``None`` while the window is still warming up."""
        if name == "ema":
            return self._emas[period].value
        if name == "rsi":
            return self._rsis[period].value
        if name == "change":
            if len(self._closes) < period + 1:
                return None
            return self._closes[-1] - self._closes[-1 - period]
        if len(self._closes) < period:
            return None
        if name == "sma":
            return statistics.fmean(list(self._closes)[-period:])
        if name == "stdev":
            return statistics.pstdev(list(self._closes)[-period:])
        if name == "highest":
            return max(list(self._highs)[-period:])
        if name == "lowest":
            return min(list(self._lows)[-period:])
        raise DslError(f"unknown indicator {name!r}")  # pragma: no cover — parser gates


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _eval(node: Node, bar: Bar, state: SymbolState) -> float | bool | None:
    if isinstance(node, Num):
        return node.value
    if isinstance(node, FieldRef):
        return float(getattr(bar, node.name))
    if isinstance(node, IndicatorRef):
        return state.indicator(node.name, node.period)
    if isinstance(node, Neg):
        value = _eval(node.operand, bar, state)
        return None if value is None else -float(value)
    if isinstance(node, BinOp):
        left = _eval(node.left, bar, state)
        right = _eval(node.right, bar, state)
        if left is None or right is None:
            return None
        lf, rf = float(left), float(right)
        if node.op == "+":
            return lf + rf
        if node.op == "-":
            return lf - rf
        if node.op == "*":
            return lf * rf
        # Division by zero → no signal this bar, never a crashed run.
        return None if rf == 0.0 else lf / rf
    if isinstance(node, Compare):
        left = _eval(node.left, bar, state)
        right = _eval(node.right, bar, state)
        if left is None or right is None:
            return None
        lf, rf = float(left), float(right)
        if node.op == ">":
            return lf > rf
        if node.op == ">=":
            return lf >= rf
        if node.op == "<":
            return lf < rf
        if node.op == "<=":
            return lf <= rf
        if node.op == "==":
            return lf == rf
        return lf != rf
    if isinstance(node, NotOp):
        value = _eval(node.operand, bar, state)
        return None if value is None else not bool(value)
    # BoolOp — conservative warm-up: any None operand suppresses the signal.
    results = [_eval(value, bar, state) for value in node.values]
    if any(result is None for result in results):
        return None
    truths = [bool(result) for result in results]
    return all(truths) if node.op == "and" else any(truths)


def evaluate_rule(rule: CompiledRule, bar: Bar, state: SymbolState) -> bool:
    """``True`` iff the rule fires on this bar (warm-up/None → ``False``)."""
    return _eval(rule.root, bar, state) is True


# ---------------------------------------------------------------------------
# Definition validation — shared by the router + agent tool + tests
# ---------------------------------------------------------------------------


def validate_definition(definition: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a ``{entry, exit, position_size?}`` definition.

    Returns ``{ok, errors: [{rule, message, position}], indicators,
    requiredBars}``. Never raises — this is the inline-validation surface.
    """
    errors: list[dict[str, Any]] = []
    compiled: dict[str, CompiledRule] = {}
    for rule_name in ("entry", "exit"):
        source = definition.get(rule_name)
        if not isinstance(source, str) or not source.strip():
            errors.append(
                {
                    "rule": rule_name,
                    "message": f"missing {rule_name} rule",
                    "position": None,
                }
            )
            continue
        try:
            compiled[rule_name] = compile_rule(source)
        except DslError as exc:
            errors.append({"rule": rule_name, "message": str(exc), "position": exc.position})

    size = definition.get("position_size", 100)
    if isinstance(size, bool) or not isinstance(size, int | float) or size <= 0:
        errors.append(
            {
                "rule": "position_size",
                "message": "position_size must be a positive number",
                "position": None,
            }
        )

    if errors:
        return {"ok": False, "errors": errors, "indicators": [], "requiredBars": 0}
    indicators = sorted(
        {f"{name}({period})" for rule in compiled.values() for name, period in rule.indicators}
    )
    required = max(rule.required_bars for rule in compiled.values())
    return {"ok": True, "errors": [], "indicators": indicators, "requiredBars": required}


# ---------------------------------------------------------------------------
# The engine-facing strategy class
# ---------------------------------------------------------------------------


class CustomDslStrategy(BacktestStrategy):
    """The ``custom`` strategy lane — entry/exit rules from ``params``.

    ``params = {"entry": str, "exit": str, "position_size": number}``.
    Parse errors raise :class:`DslError` from ``__init__``; the run route
    surfaces them as a ``run-error`` SSE frame with the parser's message.
    """

    NAME = "custom"

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        report = validate_definition(params)
        if not report["ok"]:
            first = report["errors"][0]
            suffix = f" (col {first['position'] + 1})" if first["position"] is not None else ""
            raise DslError(
                f"custom strategy {first['rule']} rule: {first['message']}{suffix}",
                first["position"],
            )
        self.entry = compile_rule(str(params["entry"]))
        self.exit = compile_rule(str(params["exit"]))
        self.position_size = float(params.get("position_size", 100))
        self._indicators = self.entry.indicators | self.exit.indicators
        self._states: dict[str, SymbolState] = {}

    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        state = self._states.setdefault(bar.symbol, SymbolState(self._indicators))
        state.update(bar)

        if portfolio.has_position(bar.symbol):
            if evaluate_rule(self.exit, bar, state):
                held = portfolio.positions[bar.symbol].quantity
                return [
                    BacktestOrderIntent(
                        symbol=bar.symbol,
                        quantity=-held,
                        reason=f"exit: {self.exit.source}",
                    )
                ]
            return []
        if evaluate_rule(self.entry, bar, state):
            return [
                BacktestOrderIntent(
                    symbol=bar.symbol,
                    quantity=self.position_size,
                    reason=f"entry: {self.entry.source}",
                )
            ]
        return []
