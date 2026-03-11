"""PlayStation input provider model."""


class PlayStationInputPlugin:
    """Minimal PlayStation plugin descriptor."""

    def __init__(self, *, legacy: bool) -> None:
        """Create a PlayStation plugin descriptor.

        Args:
            legacy: Whether the descriptor targets a legacy device family.

        """
        self.device_family = 'playstation-legacy' if legacy else 'playstation-modern'
