from aetherflow.core.resources_manifest import ResourceEntry
from aetherflow.ui.panels.resource_details_modal import ResourceDetailsModalModel


def test_resource_details_modal_shows_lock_state_and_install_action() -> None:
    model = ResourceDetailsModalModel.from_entry(
        ResourceEntry(
            resource_id='profile.premium',
            kind='profile',
            version='1.0.0',
            sha256='abc',
            size=16,
            premium=True,
            required_tier='vision',
        )
    )

    assert model.lock_state == 'locked'
    assert 'install' in model.actions
    assert 'upgrade' in model.actions
    assert model.required_tier == 'vision'
