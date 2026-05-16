"""Static-IP detection for the Kite Connect order-placement constraint.

SEBI/NSE retail-algo compliance (in effect since 2026-04-01) requires a
static IP registered with the broker for order-placement API calls. Kite
rejects orders from unregistered IPs while leaving data/holdings/positions
endpoints unaffected.

The product UX path (per the v0.5.0 plan §"Tier-3 — Static-IP UX path"):

  1. When Kite is configured for live mode, the plugin manager fetches a
     :class:`StaticIpStatus` via ``GET /safety/static-ip-status?configured=<ip>``.
  2. If ``matches=False`` (detected ≠ configured) the broker-connect UI
     surfaces a banner.
  3. The order placement path itself does NOT pre-validate — a user behind
     a VPN/VPS may have the correct static IP even when the local default
     route IP differs. Kite's rejection at order time is surfaced through
     the existing audit log + a graceful UX dialog.

The detector is a one-shot HTTP GET to a public IP-echo service
(``api.ipify.org``); on failure (timeout, network down) the status reports
``matches=False`` with a clear message rather than raising.
"""

from __future__ import annotations

import logging
import time

import httpx

from models.safety import StaticIpStatus

logger = logging.getLogger(__name__)

#: Public IP-echo endpoint. The text response body is the caller's public IP.
DEFAULT_IP_ECHO_URL = "https://api.ipify.org"


async def detect_public_ip(
    *,
    url: str = DEFAULT_IP_ECHO_URL,
    timeout_seconds: float = 5.0,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """One-shot HTTP GET to a public IP echo service.

    Returns the detected public IP as a string, or ``None`` if the request
    failed (timeout, network error, non-200, malformed body). Never raises.

    ``client`` is injectable so tests + the router can share an
    ``httpx.AsyncClient`` instance with a stubbed transport.
    """
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout_seconds)
    try:
        response = await http.get(url)
        if response.status_code != 200:
            logger.warning("static_ip: detect failed status=%s", response.status_code)
            return None
        ip = response.text.strip()
        # api.ipify.org returns just the IP; reject anything that looks suspect.
        if not ip or any(c.isspace() for c in ip) or "." not in ip:
            logger.warning("static_ip: detect returned suspect body %r", ip)
            return None
        return ip
    except Exception as exc:  # noqa: BLE001 — never raise on network failure
        logger.warning("static_ip: detect raised %s", exc)
        return None
    finally:
        if own_client:
            await http.aclose()


async def static_ip_status(
    configured_ip: str | None,
    *,
    client: httpx.AsyncClient | None = None,
) -> StaticIpStatus:
    """Detect the public IP, compare to ``configured_ip``, return the status.

    The contract matches :class:`StaticIpStatus` in ``models/safety.py``:
    ``matches`` is true iff both ``detected_ip`` and ``configured_ip`` are
    non-empty and equal; the ``message`` summarises the comparison for the
    UI banner.
    """
    detected = await detect_public_ip(client=client)
    now_ms = int(time.time() * 1000)

    if configured_ip is None or not configured_ip.strip():
        # Live mode with no configured static IP — the user almost certainly
        # has not registered one. UI banner explains the constraint.
        return StaticIpStatus(
            detectedIp=detected,
            configuredIp=None,
            matches=False,
            message=(
                "No static IP configured. Kite Connect requires a registered "
                "static IP for order placement (SEBI/NSE rule, in effect from "
                "2026-04-01). Add your static IP in Kite plugin settings."
            ),
            detectedAt=now_ms,
        )

    configured = configured_ip.strip()

    if detected is None:
        return StaticIpStatus(
            detectedIp=None,
            configuredIp=configured,
            matches=False,
            message=(
                "Could not detect public IP. Kite order placement will be "
                "attempted, but if your network IP differs from the configured "
                "static IP the order will be rejected by SEBI/NSE rule."
            ),
            detectedAt=now_ms,
        )

    if detected == configured:
        return StaticIpStatus(
            detectedIp=detected,
            configuredIp=configured,
            matches=True,
            message="Detected public IP matches the configured static IP.",
            detectedAt=now_ms,
        )

    return StaticIpStatus(
        detectedIp=detected,
        configuredIp=configured,
        matches=False,
        message=(
            f"Detected public IP ({detected}) differs from the configured "
            f"static IP ({configured}). Kite will reject orders from this "
            "IP per SEBI/NSE rule. If you are behind a VPN/VPS with the "
            "registered IP, the order may still succeed — the placement "
            "path does not pre-block."
        ),
        detectedAt=now_ms,
    )
