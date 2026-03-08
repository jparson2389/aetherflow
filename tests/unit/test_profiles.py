from aetherflow.core.profiles import InputProfile


def test_profile_clone_preserves_mapping_and_changes_identity() -> None:
    profile = InputProfile.default("Default")
    profile.button_map["A"] = "B"

    clone = profile.clone("Competitive")

    assert clone.name == "Competitive"
    assert clone.profile_id != profile.profile_id
    assert clone.button_map["A"] == "B"
