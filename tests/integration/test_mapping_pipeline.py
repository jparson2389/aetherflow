from aetherflow.core.profiles import InputProfile


def test_profile_translates_buttons_with_deadzone_defaults() -> None:
    profile = InputProfile.default("Default")
    profile.button_map["A"] = "X"

    output = profile.translate({"A": True, "LX": 0.03})

    assert output["X"] is True
    assert output["LX"] == 0.0
