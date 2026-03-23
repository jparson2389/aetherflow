"""Tests for the main() Qt event loop integration."""

from __future__ import annotations


def test_main_returns_zero_in_headless_mode(monkeypatch) -> None:
    """main() must return 0 and skip Qt startup when AETHERFLOW_HEADLESS=1."""
    monkeypatch.setenv('AETHERFLOW_HEADLESS', '1')

    from aetherflow.main import main

    result = main()

    assert result == 0
