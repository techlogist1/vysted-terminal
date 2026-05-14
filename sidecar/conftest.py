"""Pytest configuration — ensures the sidecar package root is importable."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
