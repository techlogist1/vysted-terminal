"""Shared error type for the data-provider layer.

Providers raise :class:`ProviderError` on any upstream failure; routers catch it
and translate it into a clean HTTP error response.
"""

from __future__ import annotations


class ProviderError(RuntimeError):
    """Raised when a data provider cannot satisfy a request."""
