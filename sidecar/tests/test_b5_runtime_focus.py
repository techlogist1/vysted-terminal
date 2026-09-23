"""Batch 5 (W3): the preamble names the panel the user actually focused.

R15-AGENT-051: ``_render_terminal_preamble`` always rendered ``charts[0]`` as
"Focused chart", so with two charts open (or a non-chart panel focused) the
model was told the wrong subject for "this".
"""

from __future__ import annotations

from services.agent_runtime import _render_terminal_preamble


def _chart(panel_id: str, symbol: str) -> dict[str, object]:
    return {"panelId": panel_id, "symbol": symbol, "timeframe": "1d", "indicators": []}


def test_the_focused_second_chart_is_the_one_rendered() -> None:
    preamble = _render_terminal_preamble(
        {
            "focusedPanel": "chart-2",
            "focusedSymbol": "BDL.NS",
            "charts": [_chart("chart", "SPY"), _chart("chart-2", "BDL.NS")],
        }
    )
    assert "Focused chart: BDL.NS (1d, no indicators)." in preamble
    assert "SPY" not in preamble


def test_a_focused_non_chart_panel_is_named_not_the_chart() -> None:
    preamble = _render_terminal_preamble(
        {
            "focusedPanel": "equity-overview",
            "focusedSymbol": "INFY",
            "charts": [_chart("chart", "SPY")],
        }
    )
    assert "Focused chart" not in preamble
    assert "Chart: SPY (1d, no indicators)." in preamble
    assert "Focused panel: equity-overview." in preamble
    assert "they mean INFY" in preamble
