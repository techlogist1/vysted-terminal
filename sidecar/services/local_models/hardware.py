"""Machine facts for the model picker: RAM, free disk, GPU (stdlib only).

Total RAM reuses :func:`services.hardware_fit.detect_device`; this adds the
moment-to-moment numbers (available RAM, free disk) and a GPU probe.
"""

from __future__ import annotations

import ctypes
import platform
import re
import shutil
import subprocess
from pathlib import Path

from models.local_models import GpuInfo, HardwareInfo
from services import hardware_fit

_GIB = 1024**3


def _available_ram_macos() -> int | None:
    try:
        out = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=2.0, check=False
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    page = re.search(r"page size of (\d+) bytes", out)
    if not page:
        return None
    pages = 0
    for key in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable"):
        m = re.search(rf"{key}:\s+(\d+)", out)
        if m:
            pages += int(m.group(1))
    return pages * int(page.group(1))


def _available_ram_linux() -> int | None:
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _available_ram_windows() -> int | None:
    try:
        stat = hardware_fit._MemoryStatusEx()
        stat.dwLength = ctypes.sizeof(hardware_fit._MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
            return None
        return int(stat.ullAvailPhys)
    except (OSError, AttributeError, ValueError):
        return None


def available_ram_bytes(total: int) -> int:
    system = platform.system()
    probe = {
        "Darwin": _available_ram_macos,
        "Linux": _available_ram_linux,
        "Windows": _available_ram_windows,
    }.get(system)
    value = probe() if probe else None
    return min(value, total) if value is not None else total // 2


def _nvidia_gpu() -> GpuInfo | None:
    """First NVIDIA GPU via nvidia-smi (wmic AdapterRAM caps at 4 GB, so not used)."""
    kwargs: dict = {}
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3.0,
            stdin=subprocess.DEVNULL,
            check=False,
            **kwargs,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    name, _, mib = out.stdout.strip().splitlines()[0].rpartition(",")
    try:
        return GpuInfo(name=name.strip(), vramBytes=int(mib.strip()) * 1024 * 1024)
    except ValueError:
        return None


def detect_gpu(device: hardware_fit.DeviceProfile) -> GpuInfo | None:
    if device.is_apple_silicon:
        return GpuInfo(name=device.chip, vramBytes=None, unifiedMemory=True)
    if platform.system() in ("Windows", "Linux"):
        return _nvidia_gpu()
    return None


def free_disk_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def tier_for(total_ram: int) -> str:
    # Half a GiB of slack per band: an "8 GB" Windows PC reports ~7.8 GiB
    # after firmware/iGPU reservations, and it is still an 8 GB machine.
    gib = total_ram / _GIB + 0.5
    if gib >= 32:
        return "32gb"
    if gib >= 16:
        return "16gb"
    if gib >= 8:
        return "8gb"
    return "under-8gb"


def hardware(models_dir: Path) -> HardwareInfo:
    device = hardware_fit.detect_device()
    total = device.ram_bytes
    return HardwareInfo(
        os=device.os_name,
        arch=device.arch,
        totalRamBytes=total,
        availableRamBytes=available_ram_bytes(total),
        gpu=detect_gpu(device),
        freeDiskBytes=free_disk_bytes(models_dir),
        modelsDir=str(models_dir),
    )
