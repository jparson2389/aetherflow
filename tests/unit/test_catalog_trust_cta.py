"""Unit tests for purchase_cta_for_trust_reason."""

import pytest

from aetherflow.plugins.catalog import purchase_cta_for_trust_reason


@pytest.mark.parametrize(
    ('reason', 'expected'),
    [
        ('untrusted-publisher', 'Publisher certificate is not trusted'),
        ('tampered', 'Plugin signature mismatch detected'),
        ('hash-mismatch', 'Plugin signature mismatch detected'),
        ('revoked', 'Publisher certificate revoked'),
        ('expired', 'Plugin signature expired'),
        ('unsigned', 'Signed publisher certificate required'),
        ('missing-artifact-path', 'Signed publisher certificate required'),
        ('invalid-artifact-path', 'Signed publisher certificate required'),
        ('unknown-reason', 'Plugin trust verification failed'),
        (None, 'Plugin trust verification failed'),
    ],
)
def test_purchase_cta_for_trust_reason(reason: str | None, expected: str) -> None:
    assert purchase_cta_for_trust_reason(reason) == expected
