"""Screener formula expression layer — R7 hackability Pillar 3.

A screener request may carry a free-text boolean ``formula`` that the SIDECAR
evaluates per universe member alongside the criteria, e.g.::

    pe < 15 and roe > 0.2
    market_cap / volume > 1e6
    max(roe, roa) > 0.15 and abs(change_percent_1d) < 2

This module is the ONE authoritative grammar. ``src/lib/screener-expr.ts`` is
the hand-mirrored TypeScript twin that powers the editor's instant caret-position
validation + field autocomplete — change BOTH in the same commit (the frontend
test suite carries the shared parity vectors). There is NO ``eval``/``exec``
anywhere on this path: the tokenizer and recursive-descent parser only accept
the grammar's terminals, so an agent-authored string can at worst fail to parse
with a positioned :class:`FormulaError`.

Grammar (EBNF) ::

    formula    = or_expr ;                       (* top level MUST be boolean *)
    or_expr    = and_expr { "or" and_expr } ;
    and_expr   = not_expr { "and" not_expr } ;
    not_expr   = "not" not_expr | comparison ;
    comparison = sum [ (">" | ">=" | "<" | "<=" | "==" | "!=") sum ] ;
    sum        = term { ("+" | "-") term } ;
    term       = factor { ("*" | "/") factor } ;
    factor     = "-" factor | primary ;
    primary    = NUMBER | FIELD | FUNC "(" or_expr { "," or_expr } ")"
               | "(" or_expr ")" ;

    FIELD  = any ScreenerNumericField (snake_case) or a documented alias
             (pe, marketCap, pb, …) — matched case-insensitively ;
    FUNC   = "abs" (exactly 1 arg) | "min" | "max" (2..8 args) ;
    NUMBER = float literal incl. scientific notation (1e9) ; must be finite ;

``pct_change`` is deliberately NOT a function: screener rows are point-in-time
snapshots with no per-row history to difference over. The change data the rows
DO carry is exposed as the ``change_percent_1d`` and ``fifty_two_week_change``
fields instead — honest, not fabricated.

Hostile-input caps mirror :mod:`services.backtest_dsl`: ``MAX_TOKENS`` bounds
token floods and ``MAX_NESTING_DEPTH`` bounds paren/``not``/unary-minus bombs,
so both stay positioned :class:`FormulaError`\\ s, never a ``RecursionError``
escaping the validation surface.

Evaluation semantics (per universe member, over ``(Fundamentals, Quote|None)``):

  - A referenced field that resolves to ``None`` marks the row MISSING that
    field — the screener skips the row and itemizes it in the skip ledger as
    ``missing_field:<field>`` (SC-034 — never a silent criterion-fail). Every
    operand is evaluated (no short-circuit), matching the criteria path's
    enrichment gate: a row missing ANY referenced field is skipped even when an
    ``or`` branch would have matched.
  - Division by zero yields ``None`` → the row simply does NOT match (it stays
    in the evaluated count; the value is unknowable, not absent).
  - The verdict is ``True`` only when the whole expression evaluates ``True``
    with no missing field.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, get_args

from models.screener import ScreenerNumericField

if TYPE_CHECKING:
    from models.fundamentals import Fundamentals
    from models.market import Quote

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class FormulaError(ValueError):
    """A parse/validation error with the 0-based character position."""

    def __init__(self, message: str, position: int | None = None) -> None:
        super().__init__(message)
        self.position = position


# ---------------------------------------------------------------------------
# Grammar surface
# ---------------------------------------------------------------------------

#: Canonical numeric fields — derived from the request model's Literal so the
#: grammar can never drift from what a criterion may target.
NUMERIC_FIELDS: tuple[str, ...] = get_args(ScreenerNumericField)

#: Friendly aliases (lowercased) → canonical field. The set matches the old
#: client-side scope so existing user formulas keep parsing, and the TS twin
#: carries the identical table.
FIELD_ALIASES: dict[str, str] = {
    "pe": "pe_ratio",
    "marketcap": "market_cap",
    "forwardpe": "forward_pe",
    "pegratio": "peg_ratio",
    "pricetobook": "price_to_book",
    "pb": "price_to_book",
    "pricetosales": "price_to_sales",
    "ps": "price_to_sales",
    "dividendyield": "dividend_yield",
    "debttoequity": "debt_to_equity",
    "de": "debt_to_equity",
    "changepercent1d": "change_percent_1d",
}

#: Lowercased identifier → canonical field (snake_case names are already
#: lowercase; camelCase aliases collapse onto the same table).
_FIELD_LOOKUP: dict[str, str] = {f: f for f in NUMERIC_FIELDS} | FIELD_ALIASES

KEYWORDS: frozenset[str] = frozenset({"and", "or", "not"})
FUNCTIONS: frozenset[str] = frozenset({"abs", "min", "max"})

#: min()/max() variadic arity bounds; abs() is exactly 1.
MIN_VARIADIC_ARGS = 2
MAX_VARIADIC_ARGS = 8

# Hostility caps — bound both parser recursion (nesting) and AST spine depth.
MAX_TOKENS = 256
MAX_NESTING_DEPTH = 32

_CMP_OPS = frozenset({">", ">=", "<", "<=", "==", "!="})


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Num:
    value: float


@dataclass(frozen=True)
class FieldRef:
    name: str  # canonical snake_case


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple[Node, ...]


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


Node = Num | FieldRef | Call | BinOp | Compare | BoolOp | NotOp | Neg


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Token:
    kind: str  # "num" | "ident" | "op"
    text: str
    position: int


_TOKEN_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
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
            raise FormulaError(f"unexpected character {ch!r}", position=i)
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
        self._depth = 0
        if len(self.tokens) > MAX_TOKENS:
            raise FormulaError(
                f"formula too long — max {MAX_TOKENS} tokens, got {len(self.tokens)}",
                position=self.tokens[MAX_TOKENS].position,
            )

    # -- token helpers ------------------------------------------------------

    def _peek(self) -> _Token | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _next(self) -> _Token:
        token = self._peek()
        if token is None:
            raise FormulaError("unexpected end of formula", position=len(self.text))
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
        if token is not None and token.kind == "ident" and token.text.lower() == word:
            self.index += 1
            return token
        return None

    def _expect_op(self, op: str, context: str) -> _Token:
        token = self._peek()
        if token is None:
            raise FormulaError(f"expected {op!r} {context}", position=len(self.text))
        if token.kind != "op" or token.text != op:
            raise FormulaError(f"expected {op!r} {context}, found {token.text!r}", token.position)
        self.index += 1
        return token

    def _enter_nesting(self, position: int) -> None:
        # One shared depth budget for every recursive production — parens,
        # function calls, `not` chains, and unary-minus chains all consume it.
        self._depth += 1
        if self._depth > MAX_NESTING_DEPTH:
            raise FormulaError(
                f"formula too deeply nested — max depth {MAX_NESTING_DEPTH}",
                position,
            )

    # -- grammar ------------------------------------------------------------

    def parse(self) -> Node:
        if not self.tokens:
            raise FormulaError("empty formula", position=0)
        node = self._or_expr()
        trailing = self._peek()
        if trailing is not None:
            raise FormulaError(f"unexpected {trailing.text!r}", trailing.position)
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
        token = self._accept_keyword("not")
        if token is not None:
            self._enter_nesting(token.position)
            operand = self._not_expr()
            self._depth -= 1
            return NotOp(operand=operand)
        return self._comparison()

    def _comparison(self) -> Node:
        left = self._sum()
        token = self._accept_op(*_CMP_OPS)
        if token is None:
            return left
        right = self._sum()
        # Chained comparisons (a < b < c) read ambiguously in a filter —
        # reject with a clear message rather than silently misparse.
        chained = self._peek()
        if chained is not None and chained.kind == "op" and chained.text in _CMP_OPS:
            raise FormulaError(
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
        token = self._accept_op("-")
        if token is not None:
            self._enter_nesting(token.position)
            operand = self._factor()
            self._depth -= 1
            return Neg(operand=operand)
        return self._primary()

    def _primary(self) -> Node:
        token = self._next()
        if token.kind == "num":
            value = float(token.text)
            if math.isnan(value) or math.isinf(value):
                raise FormulaError("number literal too large", token.position)
            return Num(value=value)
        if token.kind == "op" and token.text == "(":
            self._enter_nesting(token.position)
            node = self._or_expr()
            self._depth -= 1
            self._expect_op(")", "to close the parenthesis")
            return node
        if token.kind == "ident":
            name = token.text.lower()
            if name in KEYWORDS:
                raise FormulaError(f"unexpected keyword {name!r}", token.position)
            if name in FUNCTIONS:
                return self._call(name, token)
            field = _FIELD_LOOKUP.get(name)
            if field is not None:
                return FieldRef(name=field)
            raise FormulaError(
                f"unknown field {token.text!r} — fields: "
                f"{', '.join(NUMERIC_FIELDS)}; functions: {', '.join(sorted(FUNCTIONS))}",
                token.position,
            )
        raise FormulaError(f"unexpected {token.text!r}", token.position)

    def _call(self, name: str, name_token: _Token) -> Call:
        open_paren = self._expect_op("(", f"after {name!r}")
        self._enter_nesting(open_paren.position)
        args = [self._or_expr()]
        while self._accept_op(",") is not None:
            args.append(self._or_expr())
            if len(args) > MAX_VARIADIC_ARGS:
                raise FormulaError(
                    f"{name}() takes at most {MAX_VARIADIC_ARGS} arguments",
                    name_token.position,
                )
        self._expect_op(")", f"to close {name}()")
        self._depth -= 1
        if name == "abs" and len(args) != 1:
            raise FormulaError(
                f"abs() takes exactly 1 argument, got {len(args)}", name_token.position
            )
        if name in ("min", "max") and len(args) < MIN_VARIADIC_ARGS:
            raise FormulaError(
                f"{name}() takes at least {MIN_VARIADIC_ARGS} arguments, e.g. {name}(roe, roa)",
                name_token.position,
            )
        return Call(name=name, args=tuple(args))


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompiledFormula:
    """A parsed formula plus the canonical fields it references."""

    source: str
    root: Node
    fields: frozenset[str]


def _collect_fields(node: Node, out: set[str]) -> None:
    if isinstance(node, FieldRef):
        out.add(node.name)
    elif isinstance(node, BinOp | Compare):
        _collect_fields(node.left, out)
        _collect_fields(node.right, out)
    elif isinstance(node, BoolOp | Call):
        for value in node.values if isinstance(node, BoolOp) else node.args:
            _collect_fields(value, out)
    elif isinstance(node, NotOp | Neg):
        _collect_fields(node.operand, out)


def _is_boolean(node: Node) -> bool:
    return isinstance(node, Compare | BoolOp | NotOp)


def compile_formula(source: str) -> CompiledFormula:
    """Parse one formula. Raises :class:`FormulaError` with a character position."""
    stripped = source.strip()
    if not stripped:
        raise FormulaError("empty formula", position=0)
    fields: set[str] = set()
    try:
        root = _Parser(source).parse()
        if not _is_boolean(root):
            raise FormulaError(
                "formula must be a comparison or boolean expression, e.g. pe_ratio < 15",
                position=0,
            )
        _collect_fields(root, fields)
    except RecursionError:
        # Belt-and-suspenders: the MAX_TOKENS/MAX_NESTING_DEPTH caps make this
        # unreachable, but a parse must NEVER leak a non-FormulaError upward.
        raise FormulaError("formula too deeply nested", position=0) from None
    return CompiledFormula(source=stripped, root=root, fields=frozenset(fields))


def validate_formula(source: str) -> dict[str, Any]:
    """Inline-validation surface — ``{ok, error, position, fields}``. Never raises."""
    try:
        compiled = compile_formula(source)
    except FormulaError as exc:
        return {"ok": False, "error": str(exc), "position": exc.position, "fields": []}
    return {"ok": True, "error": None, "position": None, "fields": sorted(compiled.fields)}


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _field_value(fundamentals: Fundamentals, quote: Quote | None, field: str) -> float | None:
    """Resolve a canonical field over a fundamentals+quote pair.

    Mirrors ``services.screener._numeric_field_value`` (kept separate to avoid
    a service-module import cycle): the price/change%/volume trio derives from
    the latest quote; everything else is a ``Fundamentals`` attribute.
    """
    if field == "price":
        return quote.price if quote is not None else None
    if field == "change_percent_1d":
        return quote.change_percent if quote is not None else None
    if field == "volume":
        return quote.volume if quote is not None else None
    value = getattr(fundamentals, field, None)
    return float(value) if isinstance(value, int | float) else None


class _Evaluator:
    """One row's evaluation pass — tracks the first missing field it hits."""

    def __init__(self, fundamentals: Fundamentals, quote: Quote | None) -> None:
        self.fundamentals = fundamentals
        self.quote = quote
        self.missing: str | None = None

    def eval(self, node: Node) -> float | bool | None:
        if isinstance(node, Num):
            return node.value
        if isinstance(node, FieldRef):
            value = _field_value(self.fundamentals, self.quote, node.name)
            if value is None and self.missing is None:
                self.missing = node.name
            return value
        if isinstance(node, Call):
            args = [self.eval(arg) for arg in node.args]
            if any(arg is None for arg in args):
                return None
            floats = [float(a) for a in args]  # type: ignore[arg-type]
            if node.name == "abs":
                return abs(floats[0])
            return min(floats) if node.name == "min" else max(floats)
        if isinstance(node, Neg):
            value = self.eval(node.operand)
            return None if value is None else -float(value)
        if isinstance(node, BinOp):
            left = self.eval(node.left)
            right = self.eval(node.right)
            if left is None or right is None:
                return None
            lf, rf = float(left), float(right)
            if node.op == "+":
                return lf + rf
            if node.op == "-":
                return lf - rf
            if node.op == "*":
                return lf * rf
            # Division by zero → unknowable, not a crash and not a skip.
            return None if rf == 0.0 else lf / rf
        if isinstance(node, Compare):
            left = self.eval(node.left)
            right = self.eval(node.right)
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
            value = self.eval(node.operand)
            return None if value is None else not bool(value)
        # BoolOp — every operand is evaluated (no short-circuit) so a missing
        # field is detected deterministically regardless of branch order.
        results = [self.eval(value) for value in node.values]
        if any(result is None for result in results):
            return None
        truths = [bool(result) for result in results]
        return all(truths) if node.op == "and" else any(truths)


def evaluate_formula(
    compiled: CompiledFormula,
    fundamentals: Fundamentals,
    quote: Quote | None,
) -> tuple[bool, str | None]:
    """Evaluate one row. Returns ``(matched, missing_field)``.

    ``missing_field`` is the first referenced field the row could not supply —
    the caller skips the row and itemizes ``missing_field:<f>`` (SC-034). When
    it is ``None`` the row was fully evaluable and ``matched`` is the verdict
    (a div-by-zero ``None`` result counts as "did not match").
    """
    evaluator = _Evaluator(fundamentals, quote)
    result = evaluator.eval(compiled.root)
    if evaluator.missing is not None:
        return False, evaluator.missing
    return result is True, None


__all__ = [
    "FIELD_ALIASES",
    "FUNCTIONS",
    "MAX_NESTING_DEPTH",
    "MAX_TOKENS",
    "NUMERIC_FIELDS",
    "CompiledFormula",
    "FormulaError",
    "compile_formula",
    "evaluate_formula",
    "validate_formula",
]
