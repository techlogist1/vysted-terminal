"""Batch-7 research-funnel pins: a source domain is a bare host; provenance is separate."""

from __future__ import annotations

from services.research.sonar import PROVENANCE_NOTE, _extract_sources


def test_a_sonar_sec_citation_keeps_a_bare_host_and_moves_provenance() -> None:
    """R15-UI-038: provenance rides `provider`; `domain` is the host alone."""
    body = {"choices": [{"message": {"content": "x"}}], "citations": ["https://www.sec.gov/a"]}
    (source,) = _extract_sources(body)
    assert source.domain == "sec.gov"
    assert source.provider == PROVENANCE_NOTE
