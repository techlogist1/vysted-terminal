"""R15-CROSS-PLATFORM-012: --cache-dir must split regenerable caches from
``get_data_dir()`` (roaming user state) when the Tauri core supplies one, and
fall back to ``get_data_dir()`` when it does not (dev runs, older callers).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import config


def test_cache_dir_uses_env_var_when_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_target = tmp_path / "local-cache"
    monkeypatch.setenv(config.CACHE_DIR_ENV, str(cache_target))
    resolved = config.get_cache_dir()
    assert resolved == cache_target
    assert resolved.is_dir()


def test_cache_dir_falls_back_to_data_dir_when_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(config.CACHE_DIR_ENV, raising=False)
    data_target = tmp_path / "roaming-data"
    monkeypatch.setenv(config.DATA_DIR_ENV, str(data_target))
    resolved = config.get_cache_dir()
    assert resolved == data_target


def test_cache_dir_and_data_dir_diverge_when_both_set(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data_target = tmp_path / "roaming-data"
    cache_target = tmp_path / "local-cache"
    monkeypatch.setenv(config.DATA_DIR_ENV, str(data_target))
    monkeypatch.setenv(config.CACHE_DIR_ENV, str(cache_target))
    assert config.get_data_dir() == data_target
    assert config.get_cache_dir() == cache_target
    assert config.get_cache_dir() != config.get_data_dir()
