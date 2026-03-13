"""Keyboard and mouse ingestion model."""


class KeyboardMouseInputPlugin:
    """Minimal keyboard/mouse plugin descriptor."""

    device_family = 'keyboard-mouse'
    _supported_signatures = ('keyboard', 'mouse', 'trackpad')

    def supports_device(self, signature: str) -> bool:
        """Return whether a device signature matches keyboard/mouse inputs.

        Args:
            signature: Device identifier string.

        Returns:
            True when the signature matches known keyboard/mouse tokens.

        """
        normalized = signature.lower()
        return any(token in normalized for token in self._supported_signatures)
