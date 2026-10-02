"""Contract tests for the fundamentals Pydantic models (mirror of ``types/data.ts``)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.fundamentals import FieldMeta


def test_field_meta_status_rejects_unknown() -> None:
    """R15-CODE-DATA-022: ``FieldMeta.status`` is the same closed union as the TS
    mirror, so a misspelt status fails at the producer instead of rendering no
    chip in the panel."""
    for status in ("ok", "flagged", "withheld", "unavailable"):
        assert FieldMeta(status=status).status == status
    with pytest.raises(ValidationError):
        FieldMeta(status="unavaliable")
