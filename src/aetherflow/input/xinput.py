"""XInput provider model."""


class XInputPlugin:
    """Minimal XInput plugin descriptor."""

    device_family = 'xinput'
    _supported_signatures = ('xinput', 'xbox')

    def supports_device(self, signature: str) -> bool:
        """Return whether a device signature matches XInput.

        Args:
            signature: Device identifier string.

        Returns:
            True when the signature matches known XInput tokens.

        """
        normalized = signature.lower()
        return any(token in normalized for token in self._supported_signatures)
