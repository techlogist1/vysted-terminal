"""OpenBB subprocess package — ships with its own venv + PyInstaller binary.

Kept as a separate Python module tree so its dependencies never collide with
the main Vysted sidecar's pins. See ``sidecar/openbb_subprocess/main.py`` for
the FastAPI service the main sidecar's `services.openbb_provider` proxies
through.
"""
