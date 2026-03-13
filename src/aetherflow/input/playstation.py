"""PlayStation input provider model."""


class PlayStationInputPlugin:
    """Minimal PlayStation plugin descriptor."""

    _modern_signatures = ('dualsense', 'dualshock4')
    _legacy_signatures = ('dualshock2', 'dualshock3', 'ps2')

    def __init__(self, *, legacy: bool) -> None:
        """Create a PlayStation plugin descriptor.

        Args:
            legacy: Whether the descriptor targets a legacy device family.

        """
        self._legacy = legacy
        self.device_family = 'playstation-legacy' if legacy else 'playstation-modern'

    def supports_device(self, signature: str) -> bool:
        """Return whether a device signature matches the PlayStation family.

        Args:
            signature: Device identifier string.

        Returns:
            True when the signature matches the active PlayStation family.

        """
        normalized = signature.lower()
        tokens = self._legacy_signatures if self._legacy else self._modern_signatures
        return any(token in normalized for token in tokens)
