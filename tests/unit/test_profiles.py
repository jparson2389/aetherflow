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
    profile.sensitivity_layers.append(SensitivityLayer(name='hip', multiplier=1.2))

    exported = profile.export()
    imported = InputProfile.import_profile(exported)

    assert imported.name == 'Default'
    assert imported.button_map['A'] == 'B'
    assert imported.sensitivity_layers[0].name == 'hip'
    assert imported.sensitivity_layers[0].multiplier == 1.2


def test_profile_store_fast_switch_tracks_active() -> None:
    store = ProfileStore()
    base = store.create('Default')
    alt = store.clone(base.profile_id, 'Competitive')

    store.switch_active(alt.profile_id)

    assert store.active_profile_id == alt.profile_id
