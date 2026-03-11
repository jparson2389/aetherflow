"""Profile and mapping primitives for the controller pipeline."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from uuid import uuid4


def _coerce_float(value: object, *, field_name: str) -> float:
    """Coerce a JSON-compatible payload value to ``float``.

    Args:
        value: Raw payload value.
        field_name: Payload field name for error reporting.

    Returns:
        The coerced floating-point value.

    Raises:
        TypeError: If the payload value is not float-compatible.

    """
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError(f'{field_name} must be float-compatible.')


@dataclass(frozen=True, slots=True)
class SensitivityLayer:
    """Sensitivity multiplier layer for mapping profiles."""

    name: str
    multiplier: float
    active: bool = True

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable layer payload."""
        return {
            'name': self.name,
            'multiplier': self.multiplier,
            'active': self.active,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> SensitivityLayer:
        """Create a layer from a serialized payload."""
        return cls(
            name=str(payload['name']),
            multiplier=_coerce_float(
                payload['multiplier'],
                field_name='multiplier',
            ),
            active=bool(payload.get('active', True)),
        )


@dataclass(slots=True)
class InputProfile:
    """Mutable controller mapping profile."""

    profile_id: str
    name: str
    button_map: dict[str, str] = field(default_factory=dict)
    deadzone: float = 0.05
    curve_exponent: float = 1.0
    smoothing_alpha: float = 1.0
    sensitivity_layers: list[SensitivityLayer] = field(default_factory=list)
    _last_values: dict[str, float] = field(default_factory=dict, repr=False)

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
        clone._last_values = {}
        return clone

    def translate(self, events: dict[str, bool | float]) -> dict[str, bool | float]:
        """Translate input events through the mapping profile.

        Args:
            events: Raw input events keyed by control name.

        Returns:
            Translated output events.

        """
        translated: dict[str, bool | float] = {}
        sensitivity_multiplier = 1.0
        for layer in self.sensitivity_layers:
            if layer.active:
                sensitivity_multiplier *= layer.multiplier
        for key, value in events.items():
            mapped_key = self.button_map.get(key, key)
            if (
                isinstance(value, float)
                and key.startswith('L')
                and abs(value) < self.deadzone
            ):
                translated[mapped_key] = 0.0
                continue
            if isinstance(value, float):
                adjusted = value
                if self.curve_exponent != 1.0:
                    adjusted = (abs(adjusted) ** self.curve_exponent) * (
                        1 if adjusted >= 0 else -1
                    )
                adjusted *= sensitivity_multiplier
                if self.smoothing_alpha < 1.0:
                    previous = self._last_values.get(mapped_key)
                    if previous is not None:
                        adjusted = (
                            self.smoothing_alpha * adjusted
                            + (1.0 - self.smoothing_alpha) * previous
                        )
                self._last_values[mapped_key] = adjusted
                translated[mapped_key] = adjusted
            else:
                translated[mapped_key] = value
        return translated

    def export(self) -> dict[str, object]:
        """Export the profile to a JSON-serializable dictionary."""
        return {
            'profile_id': self.profile_id,
            'name': self.name,
            'button_map': dict(self.button_map),
            'deadzone': self.deadzone,
            'curve_exponent': self.curve_exponent,
            'smoothing_alpha': self.smoothing_alpha,
            'sensitivity_layers': [
                layer.as_dict() for layer in self.sensitivity_layers
            ],
        }

    @classmethod
    def import_profile(cls, payload: dict[str, object]) -> InputProfile:
        """Import a profile from a JSON-compatible payload."""
        raw_layers = payload.get('sensitivity_layers')
        layer_list = raw_layers if isinstance(raw_layers, list) else []
        layers = [
            SensitivityLayer.from_dict(raw)
            for raw in layer_list if isinstance(raw, dict)
        ]
        raw_button_map = payload.get('button_map')
        button_map_dict = raw_button_map if isinstance(raw_button_map, dict) else {}
        profile = cls(
            profile_id=str(payload['profile_id']),
            name=str(payload['name']),
            button_map={str(k): str(v) for k, v in button_map_dict.items()},
            deadzone=_coerce_float(
                payload.get('deadzone', 0.05),
                field_name='deadzone',
            ),
            curve_exponent=_coerce_float(
                payload.get('curve_exponent', 1.0),
                field_name='curve_exponent',
            ),
            smoothing_alpha=_coerce_float(
                payload.get('smoothing_alpha', 1.0),
                field_name='smoothing_alpha',
            ),
            sensitivity_layers=layers,
        )
        return profile



@dataclass(slots=True)
class ProfileStore:
    """Manage profile CRUD and active profile selection."""

    profiles: dict[str, InputProfile] = field(default_factory=dict)
    active_profile_id: str | None = None

    def create(self, name: str) -> InputProfile:
        """Create and register a new profile."""
        profile = InputProfile.default(name)
        self.profiles[profile.profile_id] = profile
        if self.active_profile_id is None:
            self.active_profile_id = profile.profile_id
        return profile

    def clone(self, profile_id: str, name: str) -> InputProfile:
        """Clone an existing profile."""
        profile = self.profiles[profile_id].clone(name)
        self.profiles[profile.profile_id] = profile
        return profile

    def delete(self, profile_id: str) -> None:
        """Delete a profile by ID."""
        self.profiles.pop(profile_id, None)
        if self.active_profile_id == profile_id:
            self.active_profile_id = next(iter(self.profiles), None)

    def switch_active(self, profile_id: str) -> None:
        """Fast-switch the active profile."""
        if profile_id not in self.profiles:
            raise KeyError(f'Unknown profile: {profile_id}')
        self.active_profile_id = profile_id

    def export_profile(self, profile_id: str) -> dict[str, object]:
        """Export a profile by ID."""
        return self.profiles[profile_id].export()

    def import_profile(self, payload: dict[str, object]) -> InputProfile:
        """Import a profile and register it."""
        profile = InputProfile.import_profile(payload)
        self.profiles[profile.profile_id] = profile
        if self.active_profile_id is None:
            self.active_profile_id = profile.profile_id
        return profile
