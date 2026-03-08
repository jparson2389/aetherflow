"""Provider-agnostic OAuth interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class OAuthProvider(Protocol):
    """Minimal OAuth provider contract."""

    def is_enabled(self) -> bool:
        """Return whether the provider is enabled."""


@dataclass(frozen=True, slots=True)
class MockOAuthProvider:
    """Disabled OAuth provider used as a safe fallback."""

    enabled: bool = False

    def is_enabled(self) -> bool:
        """Return whether the provider is enabled."""
        return self.enabled
