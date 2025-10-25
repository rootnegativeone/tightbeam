"""
Assertions that web-served Python assets stay in sync with their source modules.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_demo_payloads_synced_with_web_bundle() -> None:
    """Ensure the Pyodide bundle ships the same demo payload generator as core."""
    root = _project_root()
    source = root / "common" / "shared" / "demo_payloads.py"
    web_public = (
        root / "web" / "public" / "python" / "common" / "shared" / "demo_payloads.py"
    )
    web_dist = (
        root / "web" / "dist" / "python" / "common" / "shared" / "demo_payloads.py"
    )

    source_text = source.read_text(encoding="utf-8")
    assert web_public.read_text(encoding="utf-8") == source_text
    if web_dist.exists():
        assert web_dist.read_text(encoding="utf-8") == source_text
    else:
        pytest.skip("web/dist assets not generated in this checkout")
