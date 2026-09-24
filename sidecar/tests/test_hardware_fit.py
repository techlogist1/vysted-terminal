"""Hardware fit-scorer tests (Track D).

``score`` is pure given a :class:`DeviceProfile`, so every case uses a fixed
profile — no dependency on the host the tests run on. The load-bearing cases:
the 16 GB M1 forces a local 30B-A3B MoE → remote, while a 64 GB box auto-promotes
it to local with NO code change (FINDINGS §2.5 / §4.2).
"""

from __future__ import annotations

import ctypes
from dataclasses import replace

import pytest

from services import hardware_fit
from services.hardware_fit import (
    VERDICT_GREEN,
    VERDICT_MARGINAL,
    VERDICT_RED,
    DeviceProfile,
    ModelCandidate,
    can_run_locally,
    detect_device,
    score,
)

_GIB = 1024**3


@pytest.fixture(autouse=True)
def _reset_device_cache() -> None:
    """``detect_device`` caches module-globally; isolate this file's
    ``force=True`` probes from every other test that calls it un-forced."""
    hardware_fit._cached_device = None
    yield
    hardware_fit._cached_device = None


def _m1_16gb() -> DeviceProfile:
    ram = 16 * _GIB
    return DeviceProfile(
        ram_bytes=ram,
        gpu_budget_bytes=int(ram * 0.66),  # ~10.6 GiB Metal budget
        total_cores=8,
        perf_cores=6,
        is_apple_silicon=True,
        arch="arm64",
        chip="Apple M1 Pro",
        os_name="macOS",
        os_version="26.3",
    )


def _m_64gb() -> DeviceProfile:
    ram = 64 * _GIB
    return DeviceProfile(
        ram_bytes=ram,
        gpu_budget_bytes=int(ram * 0.75),  # 48 GiB
        total_cores=12,
        perf_cores=8,
        is_apple_silicon=True,
        arch="arm64",
        chip="Apple M3 Max",
        os_name="macOS",
        os_version="26.3",
    )


# Real candidates (GGUF on-disk sizes from FINDINGS §2.4).
def _qwen7b() -> ModelCandidate:
    return ModelCandidate(name="qwen2.5:7b", file_size_bytes=4_683_087_332, quant="q4_k_m")


def _moe_30b_a3b_iq3() -> ModelCandidate:
    # 30B-A3B MoE; IQ3_S ≈ 13.3 GB on disk; all experts resident.
    return ModelCandidate(
        name="30b-a3b-moe",
        file_size_bytes=int(13.3 * 1e9),
        total_params_b=30.5,
        active_params_b=3.3,
        quant="iq3_s",
    )


def test_qwen7b_runs_locally_on_16gb_at_capped_context() -> None:
    dev = _m1_16gb()
    # A 7B at a modest context fits the M1 comfortably.
    capped = replace(_qwen7b(), desired_ctx=8192)
    v = score(capped, dev)
    assert v.verdict in (VERDICT_GREEN, VERDICT_MARGINAL)
    assert can_run_locally(capped, dev)


def test_local_30b_moe_is_red_on_16gb_forcing_remote() -> None:
    dev = _m1_16gb()
    v = score(_moe_30b_a3b_iq3(), dev)
    assert v.verdict == VERDICT_RED
    assert can_run_locally(_moe_30b_a3b_iq3(), dev) is False
    # MoE footprint is sized against TOTAL params, annotated as throughput.
    assert "moe" in v.signals
    assert "30.5B" in v.throughput_note


def test_30b_moe_auto_promotes_to_local_on_64gb() -> None:
    dev = _m_64gb()
    v = score(_moe_30b_a3b_iq3(), dev)
    # Same candidate, same code — the bigger box earns the local path.
    assert v.verdict in (VERDICT_GREEN, VERDICT_MARGINAL)
    assert can_run_locally(_moe_30b_a3b_iq3(), dev) is True


def test_ctx_max_is_reported_and_below_4096_is_red() -> None:
    dev = _m1_16gb()
    # A model whose weights nearly fill the budget can't hold a usable context.
    huge = ModelCandidate(name="huge", file_size_bytes=int(10.0 * _GIB), total_params_b=20)
    v = score(huge, dev)
    assert v.verdict == VERDICT_RED
    assert v.ctx_max < 4096 or "over-budget" in v.signals


def test_file_size_is_authoritative_over_param_estimate() -> None:
    dev = _m_64gb()
    # Given a real file size, the estimate path is ignored.
    explicit = score(ModelCandidate(name="x", file_size_bytes=5 * _GIB), dev)
    assert explicit.weights_bytes == 5 * _GIB


def test_estimate_path_uses_quant_table() -> None:
    dev = _m_64gb()
    # 7B at Q4_K_M ≈ 7 * 0.6 = 4.2 GB.
    est = score(ModelCandidate(name="x", total_params_b=7, quant="q4_k_m"), dev)
    assert 3.8e9 < est.weights_bytes < 4.6e9


def test_detect_device_returns_a_sane_profile_on_this_host() -> None:
    dev = detect_device(force=True)
    assert dev.ram_bytes > 1 * _GIB
    assert 0 < dev.gpu_budget_bytes <= dev.ram_bytes
    assert dev.total_cores >= 1
    d = dev.to_dict()
    assert d["ramGib"] > 0 and d["gpuBudgetGib"] > 0
    assert d["estimated"] is False


def test_detect_windows_uses_real_ram_via_ctypes(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-CROSS-PLATFORM-003: Windows RAM comes from GlobalMemoryStatusEx
    (kernel32, via ctypes — no new dependency), not the generic 8 GiB guess."""
    monkeypatch.setattr(hardware_fit.platform, "system", lambda: "Windows")

    class _FakeKernel32:
        @staticmethod
        def GlobalMemoryStatusEx(ptr: object) -> int:
            struct = ctypes.cast(ptr, ctypes.POINTER(hardware_fit._MemoryStatusEx)).contents
            struct.ullTotalPhys = 32 * _GIB
            return 1

    class _FakeWindll:
        kernel32 = _FakeKernel32()

    monkeypatch.setattr(ctypes, "windll", _FakeWindll(), raising=False)
    dev = detect_device(force=True)
    assert dev.os_name == "Windows"
    assert dev.ram_bytes == 32 * _GIB
    assert dev.estimated is False


def test_detect_windows_falls_back_when_the_api_call_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Class pin, not written against: GlobalMemoryStatusEx unreachable (no
    ``ctypes.windll``, e.g. a non-Windows host or an odd sandbox) degrades to
    the generic guess, flagged ``estimated``, rather than crashing detection."""
    monkeypatch.setattr(hardware_fit.platform, "system", lambda: "Windows")
    monkeypatch.delattr(ctypes, "windll", raising=False)
    dev = detect_device(force=True)
    assert dev.ram_bytes == 8 * _GIB
    assert dev.estimated is True


def test_detect_unknown_os_is_estimated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hardware_fit.platform, "system", lambda: "SomeOtherOS")
    dev = detect_device(force=True)
    assert dev.ram_bytes == 8 * _GIB
    assert dev.estimated is True
