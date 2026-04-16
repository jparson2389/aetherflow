from aetherflow.core.profiles import InputProfile, ProfileStore, SensitivityLayer


def test_profile_clone_preserves_mapping_and_changes_identity() -> None:
    profile = InputProfile.default('Default')
    profile.button_map['A'] = 'B'

    clone = profile.clone('Competitive')

    assert clone.name == 'Competitive'
    assert clone.profile_id != profile.profile_id
    assert clone.button_map['A'] == 'B'


def test_profile_export_import_round_trip() -> None:
    profile = InputProfile.default('Default')
    profile.button_map['A'] = 'B'
    profile.smoothing_alpha = 0.4
    profile.sensitivity_layers.append(SensitivityLayer(name='hip', multiplier=1.2))

    exported = profile.export()
    imported = InputProfile.import_profile(exported)

    assert imported.name == 'Default'
    assert imported.button_map['A'] == 'B'
    assert imported.smoothing_alpha == 0.4
    assert imported.sensitivity_layers[0].name == 'hip'
    assert imported.sensitivity_layers[0].multiplier == 1.2


def test_profile_store_fast_switch_tracks_active() -> None:
    store = ProfileStore()
    base = store.create('Default')
    alt = store.clone(base.profile_id, 'Competitive')

    store.switch_active(alt.profile_id)

    assert store.active_profile_id == alt.profile_id


def test_profile_import_rejects_invalid_deadzone() -> None:
    payload = {
        'profile_id': 'profile-1',
        'name': 'Default',
        'button_map': {},
        'deadzone': 1.5,
        'curve_exponent': 1.0,
        'smoothing_alpha': 1.0,
        'sensitivity_layers': [],
    }

    try:
        InputProfile.import_profile(payload)
    except ValueError as exc:
        assert 'deadzone' in str(exc)
    else:
        raise AssertionError('Expected invalid profile payload to be rejected.')


def test_profile_store_rejects_blank_profile_name() -> None:
    store = ProfileStore()

    try:
        store.create('   ')
    except ValueError as exc:
        assert 'Profile name' in str(exc)
    else:
        raise AssertionError('Expected blank profile name to be rejected.')
