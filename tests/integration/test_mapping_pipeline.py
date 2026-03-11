from aetherflow.core.profiles import InputProfile, SensitivityLayer


def test_profile_translates_buttons_with_deadzone_defaults() -> None:
    profile = InputProfile.default('Default')
    profile.button_map['A'] = 'X'

    output = profile.translate({'A': True, 'LX': 0.03})

    assert output['X'] is True
    assert output['LX'] == 0.0


def test_profile_applies_curve_smoothing_and_sensitivity_layers() -> None:
    profile = InputProfile.default('Default')
    profile.curve_exponent = 2.0
    profile.smoothing_alpha = 0.5
    profile.sensitivity_layers.append(SensitivityLayer(name='aim', multiplier=2.0))

    first = profile.translate({'LX': 0.5})
    second = profile.translate({'LX': 1.0})

    assert first['LX'] == 0.5
    assert second['LX'] == 1.25
