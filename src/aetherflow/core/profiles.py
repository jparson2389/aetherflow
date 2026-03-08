"""Profile and mapping primitives for the controller pipeline."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(slots=True)
class InputProfile:
    """Mutable controller mapping profile."""

    profile_id: str
    name: str
    button_map: dict[str, str] = field(default_factory=dict)
    deadzone: float = 0.05

    @classmethod
    def default(cls, name: str) -> InputProfile:
        """Create the default profile.

        Args:
            name: Profile display name.

        Returns:
            A default profile.

        """
        return cls(profile_id=str(uuid4()), name=name)

    def clone(self, name: str) -> InputProfile:
        """Clone the profile under a new identity.

        Args:
            name: Name for the cloned profile.

        Returns:
            A cloned profile instance.

        """
        clone = deepcopy(self)
        clone.profile_id = str(uuid4())
        clone.name = name
        return clone

    def translate(self, events: dict[str, bool | float]) -> dict[str, bool | float]:
        """Translate input events through the mapping profile.

        Args:
            events: Raw input events keyed by control name.

        Returns:
            Translated output events.

        """
        translated: dict[str, bool | float] = {}
        for key, value in events.items():
            mapped_key = self.button_map.get(key, key)
            if (
                isinstance(value, float)
                and key.startswith("L")
                and abs(value) < self.deadzone
            ):
                translated[mapped_key] = 0.0
                continue
            translated[mapped_key] = value
        return translated
