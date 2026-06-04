"""Hardware fit-scorer — llmfit-style device capability gating (Track D).

The app stays keyless-by-default and only enables a heavy LOCAL path (a local
deep-research model, a large local LLM) where the device actually earns it;
elsewhere it degrades gracefully to the keyless-remote path. This module is the
gate function: it detects the device once, then scores any candidate model to a
``green`` / ``marginal`` / ``red`` verdict (FINDINGS §2.5).

Design notes (Apple Silicon is the primary target, the M1 travel rig this ships
on first):

- **Unified RAM is the hard ceiling** — there is no separate VRAM. Metal caps
  GPU-addressable memory at ``recommendedMaxWorkingSetSize`` ≈ 66% of RAM below
  36 GB (75% at/above 64 GB). That budget — not total RAM — is what a model on
  the GPU must fit under.
- **Weight footprint ≈ GGUF file size** (the authoritative input); fall back to
  ``params × bytes_per_param[quant]`` when the file size is unknown.
- **KV cache is the second, context-driven cost** — sized per token × context.
- **MoE pays RAM for TOTAL params, compute for ACTIVE params** — a 30B-A3B model
  loads all 30B of weights; "A3B" is a throughput signal, never a memory one.
  The scorer sizes against total params and annotates active params as speed.

``detect_device`` shells out (sysctl / /proc) and is cached; ``score`` is pure
(inject a :class:`DeviceProfile`) so it is unit-testable on any host.
"""

from __future__ import annotations

import platform
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any

_GIB = 1024**3
#: OS + WebKit/Tauri shell + Python sidecar floor that must stay resident.
_RESERVE_BYTES = 4 * _GIB

#: Resident bytes-per-parameter by quantization (rule of thumb: Q4_K_M ≈ 0.6 ×
#: params_B GB ≈ 28–32% of FP16). Used only when the GGUF file size is unknown.
_BYTES_PER_PARAM: dict[str, float] = {
    "f32": 4.0,
    "f16": 2.0,
    "fp16": 2.0,
    "bf16": 2.0,
    "q8_0": 1.06,
    "q6_k": 0.82,
    "q5_k_m": 0.70,
    "q5_k_s": 0.68,
    "q5_0": 0.69,
    "q4_k_m": 0.60,
    "q4_k_s": 0.58,
    "q4_0": 0.56,
    "iq4_xs": 0.55,
    "q3_k_m": 0.43,
    "iq3_s": 0.43,
    "q3_k_s": 0.41,
    "q2_k": 0.36,
}
_DEFAULT_BYTES_PER_PARAM = 0.60  # assume a Q4_K_M-class quant when unstated

VERDICT_GREEN = "green"
VERDICT_MARGINAL = "marginal"
VERDICT_RED = "red"


# ---------------------------------------------------------------------------
# Device profile
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DeviceProfile:
    """The detected machine, normalised for scoring. ``gpu_budget_bytes`` is the
    memory a model on the accelerator may actually use (Metal working-set on
    Apple Silicon; a CPU-inference heuristic otherwise)."""

    ram_bytes: int
    gpu_budget_bytes: int
    total_cores: int
    perf_cores: int
    is_apple_silicon: bool
    arch: str
    chip: str
    os_name: str
    os_version: str
    reserve_bytes: int = _RESERVE_BYTES

    def to_dict(self) -> dict[str, Any]:
        return {
            "ramBytes": self.ram_bytes,
            "ramGib": round(self.ram_bytes / _GIB, 1),
            "gpuBudgetBytes": self.gpu_budget_bytes,
            "gpuBudgetGib": round(self.gpu_budget_bytes / _GIB, 1),
            "totalCores": self.total_cores,
            "perfCores": self.perf_cores,
            "isAppleSilicon": self.is_apple_silicon,
            "arch": self.arch,
            "chip": self.chip,
            "osName": self.os_name,
            "osVersion": self.os_version,
            "reserveBytes": self.reserve_bytes,
        }


def _sysctl(name: str) -> str | None:
    try:
        out = subprocess.run(
            ["sysctl", "-n", name], capture_output=True, text=True, timeout=2.0, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    val = out.stdout.strip()
    return val or None


def _int_or(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _gpu_budget(ram_bytes: int, is_apple_silicon: bool) -> int:
    """Apple Metal exposes ~66% of RAM below 36 GB, ~75% at/above 64 GB. A
    non-Apple box (no detected dedicated VRAM here) is treated as CPU inference
    with a conservative 55% working budget."""
    if is_apple_silicon:
        frac = 0.75 if ram_bytes >= 64 * _GIB else 0.66
    else:
        frac = 0.55
    return int(ram_bytes * frac)


def _detect_macos() -> DeviceProfile:
    ram = _int_or(_sysctl("hw.memsize"), 8 * _GIB)
    arch = platform.machine()  # "arm64" | "x86_64"
    is_apple = arch == "arm64"
    chip = _sysctl("machdep.cpu.brand_string") or _sysctl("hw.model") or "Apple Silicon"
    total = _int_or(_sysctl("hw.ncpu"), 8)
    perf = _int_or(_sysctl("hw.perflevel0.physicalcpu"), 0) or total
    return DeviceProfile(
        ram_bytes=ram,
        gpu_budget_bytes=_gpu_budget(ram, is_apple),
        total_cores=total,
        perf_cores=perf,
        is_apple_silicon=is_apple,
        arch=arch,
        chip=chip,
        os_name="macOS",
        os_version=platform.mac_ver()[0] or platform.release(),
    )


def _detect_linux() -> DeviceProfile:
    ram = 8 * _GIB
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    kb = int(re.search(r"(\d+)", line).group(1))  # type: ignore[union-attr]
                    ram = kb * 1024
                    break
    except (OSError, AttributeError, ValueError):
        pass
    import os

    total = os.cpu_count() or 4
    return DeviceProfile(
        ram_bytes=ram,
        gpu_budget_bytes=_gpu_budget(ram, is_apple_silicon=False),
        total_cores=total,
        perf_cores=total,
        is_apple_silicon=False,
        arch=platform.machine(),
        chip=platform.processor() or "x86_64",
        os_name="Linux",
        os_version=platform.release(),
    )


def _detect_fallback() -> DeviceProfile:
    import os

    ram = 8 * _GIB
    total = os.cpu_count() or 4
    return DeviceProfile(
        ram_bytes=ram,
        gpu_budget_bytes=_gpu_budget(ram, is_apple_silicon=False),
        total_cores=total,
        perf_cores=total,
        is_apple_silicon=False,
        arch=platform.machine() or "unknown",
        chip=platform.processor() or "unknown",
        os_name=platform.system() or "unknown",
        os_version=platform.release(),
    )


_cached_device: DeviceProfile | None = None


def detect_device(*, force: bool = False) -> DeviceProfile:
    """Detect + cache the device profile (probe once at boot, reuse thereafter)."""
    global _cached_device
    if _cached_device is not None and not force:
        return _cached_device
    system = platform.system()
    try:
        if system == "Darwin":
            profile = _detect_macos()
        elif system == "Linux":
            profile = _detect_linux()
        else:
            profile = _detect_fallback()
    except Exception:  # noqa: BLE001 — detection must never crash the sidecar
        profile = _detect_fallback()
    _cached_device = profile
    return profile


# ---------------------------------------------------------------------------
# Candidate + scoring
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ModelCandidate:
    """A model to score. Supply ``file_size_bytes`` (GGUF on-disk) when known —
    it is authoritative; otherwise ``total_params_b`` + ``quant`` estimate it.
    ``active_params_b`` (MoE) annotates throughput only, never the footprint."""

    name: str
    file_size_bytes: int | None = None
    total_params_b: float | None = None
    active_params_b: float | None = None
    quant: str | None = None
    n_layers: int | None = None
    n_kv_heads: int | None = None
    head_dim: int | None = None
    desired_ctx: int = 32768


@dataclass(slots=True)
class FitVerdict:
    """A scored candidate. ``verdict`` gates enablement; ``ctx_max`` is the
    largest context that fits on the accelerator; ``reason`` is a human line."""

    name: str
    verdict: str
    gpu_fit_ratio: float
    ram_fit_ratio: float
    demand_bytes: int
    weights_bytes: int
    kv_bytes: int
    ctx_max: int
    reason: str
    throughput_note: str = ""
    signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "verdict": self.verdict,
            "gpuFitRatio": round(self.gpu_fit_ratio, 3),
            "ramFitRatio": round(self.ram_fit_ratio, 3),
            "demandBytes": self.demand_bytes,
            "demandGib": round(self.demand_bytes / _GIB, 1),
            "weightsBytes": self.weights_bytes,
            "kvBytes": self.kv_bytes,
            "ctxMax": self.ctx_max,
            "reason": self.reason,
            "throughputNote": self.throughput_note,
            "signals": self.signals,
        }


def _weight_bytes(candidate: ModelCandidate) -> int:
    if candidate.file_size_bytes and candidate.file_size_bytes > 0:
        return candidate.file_size_bytes
    params = candidate.total_params_b or 0.0
    quant = (candidate.quant or "").strip().lower()
    per = _BYTES_PER_PARAM.get(quant, _DEFAULT_BYTES_PER_PARAM)
    return int(params * per * 1e9)


def _kv_per_token(candidate: ModelCandidate) -> float:
    """Bytes of KV cache per token (Q8 KV ≈ ollama flash-attn default). Use the
    exact arch geometry when known; else a 7B-equivalent fallback (~0.25 MB/token
    at Q8 for a 7B-class attention).

    KV scales with the ATTENTION size, not the MoE total — a 30B-A3B has roughly
    a 3B-dense attention, so for an MoE candidate the dense-equivalent is its
    ACTIVE params (using total would overstate KV ~10×). For a dense model the
    dense-equivalent is its total params."""
    if candidate.n_layers and candidate.n_kv_heads and candidate.head_dim:
        return float(2 * candidate.n_layers * candidate.n_kv_heads * candidate.head_dim * 1)
    dense_equiv = candidate.active_params_b or candidate.total_params_b or 7.0
    return 250_000.0 * (dense_equiv / 7.0)


def score(candidate: ModelCandidate, device: DeviceProfile | None = None) -> FitVerdict:
    """Score a candidate against the device. Verdict bands (FINDINGS §2.5):

    - GREEN: gpu_fit ≤ 0.85 AND ram_fit ≤ 0.80 — full offload, headroom intact.
    - MARGINAL: gpu_fit ≤ 1.00 AND ram_fit ≤ 0.92 — fits but tight (downgrade ctx).
    - RED: otherwise — would swap/CPU-thrash/OOM. Do not enable the local path.

    A model whose ``ctx_max`` falls below 4096 is RED regardless of weight fit
    (it cannot hold a usable context).
    """
    dev = device or detect_device()
    weights = _weight_bytes(candidate)
    kv_per_tok = _kv_per_token(candidate)
    kv = int(kv_per_tok * candidate.desired_ctx)
    overhead = max(_GIB, int(0.10 * weights))
    demand = weights + kv + overhead

    gpu_budget = max(1, dev.gpu_budget_bytes)
    gpu_fit = demand / gpu_budget
    ram_fit = (demand + dev.reserve_bytes) / max(1, dev.ram_bytes)

    # Largest context that fits on the accelerator with the weights + overhead.
    ctx_max_raw = (0.85 * gpu_budget - weights - overhead) / kv_per_tok if kv_per_tok > 0 else 0
    ctx_max = max(0, int(ctx_max_raw // 2048) * 2048)

    signals: list[str] = []
    if ctx_max < 4096:
        verdict = VERDICT_RED
        reason = (
            f"can't hold a usable context (max ≈ {ctx_max} tokens) — weights alone "
            f"({weights / _GIB:.1f} GiB) crowd the {gpu_budget / _GIB:.1f} GiB budget."
        )
        signals.append("ctx<4096")
    elif gpu_fit <= 0.85 and ram_fit <= 0.80:
        verdict = VERDICT_GREEN
        reason = (
            f"fits with headroom ({demand / _GIB:.1f} GiB of {gpu_budget / _GIB:.1f} GiB "
            f"GPU budget) — enable locally."
        )
    elif gpu_fit <= 1.00 and ram_fit <= 0.92:
        verdict = VERDICT_MARGINAL
        reason = (
            f"fits but tight ({demand / _GIB:.1f} GiB vs {gpu_budget / _GIB:.1f} GiB) — "
            f"enable only with a shorter context (≤ {ctx_max} tokens) or smaller quant."
        )
        signals.append("tight")
    else:
        verdict = VERDICT_RED
        reason = (
            f"too large — needs {demand / _GIB:.1f} GiB but the GPU budget is "
            f"{gpu_budget / _GIB:.1f} GiB; would swap/CPU-thrash. Use the remote path."
        )
        signals.append("over-budget")

    throughput = ""
    if candidate.active_params_b and candidate.total_params_b:
        if candidate.active_params_b < candidate.total_params_b:
            throughput = (
                f"MoE: loads all {candidate.total_params_b:g}B params (RAM), runs at "
                f"~{candidate.active_params_b:g}B-dense speed."
            )
            signals.append("moe")

    return FitVerdict(
        name=candidate.name,
        verdict=verdict,
        gpu_fit_ratio=gpu_fit,
        ram_fit_ratio=ram_fit,
        demand_bytes=demand,
        weights_bytes=weights,
        kv_bytes=kv,
        ctx_max=ctx_max,
        reason=reason,
        throughput_note=throughput,
        signals=signals,
    )


def can_run_locally(candidate: ModelCandidate, device: DeviceProfile | None = None) -> bool:
    """Gate helper: True iff the device earns the local path (GREEN or MARGINAL).
    A RED candidate routes to the keyless-remote path (e.g. a 30B MoE the device
    can't fit)."""
    return score(candidate, device).verdict in (VERDICT_GREEN, VERDICT_MARGINAL)


__all__ = [
    "DeviceProfile",
    "FitVerdict",
    "ModelCandidate",
    "VERDICT_GREEN",
    "VERDICT_MARGINAL",
    "VERDICT_RED",
    "can_run_locally",
    "detect_device",
    "score",
]
