"""Phase 6 QuantLib-backed pricing services.

In-process pricing — see ``docs/superpowers/plans/2026-05-16-phase-6-macro-research-quantlib.md``
section "Architectural decisions" for the Tier-3 rationale (quality posture
removes the bundle-size constraint; in-process gives hot-path math
performance without an MCP roundtrip per pricing call and a simpler lifecycle).

The submodules expose narrow function APIs over Pydantic models from
:mod:`models.quant`. None of the QuantLib types leak out of this
package — every public function takes a Pydantic request and returns a
Pydantic response so the wire stays framework-neutral.

Submodules
----------
``options``        — Black-Scholes analytic + Cox-Ross-Rubinstein binomial +
                     Monte Carlo European pricing.
``greeks``         — Standalone analytic Greeks dashboard helper.
``bonds``          — Fixed-rate bond clean/dirty/accrued/duration/convexity.
``yield_curve``    — Depo + swap bootstrap of a piecewise-linear zero curve.
``monte_carlo``    — Path-dependent MC: Asian arithmetic-average + barrier.
"""

from __future__ import annotations
