from __future__ import annotations

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom pytest options."""
    parser.addoption(
        '--count',
        action='store',
        default='1',
        help='Number of bundle installs to simulate.',
    )


@pytest.fixture(scope='session')
def bundle_install_count(pytestconfig: pytest.Config) -> int:
    """Return the bundle install count from CLI."""
    raw = pytestconfig.getoption('--count')
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 1
    return max(1, value)
