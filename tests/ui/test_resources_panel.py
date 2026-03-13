from aetherflow.core.resources_manifest import ResourceEntry, ResourceManifest
from aetherflow.ui.panels.resources_panel import ResourcesPanelModel


def test_resources_panel_marks_locked_items() -> None:
    """Ensure resources panel marks locked premium items."""
    manifest = ResourceManifest(
        version='1.0',
        signature='signed',
        signature_scheme='Authenticode',
        digest_algorithm='SHA-256',
        rsa_key_bits=3072,
        publisher_thumbprint='aetherflow-publisher',
        trust_root_thumbprint='aetherflow-root',
        resources=[
            ResourceEntry(
                resource_id='profile.default',
                kind='profile',
                version='1.0.0',
                sha256='a' * 64,
                size=32,
                premium=False,
            ),
            ResourceEntry(
                resource_id='profile.premium',
                kind='profile',
                version='1.0.0',
                sha256='b' * 64,
                size=64,
                premium=True,
                required_tier='vision',
            ),
        ],
    )

    panel = ResourcesPanelModel.from_manifest(
        manifest,
        unlocked_resource_ids={'profile.default'},
    )

    assert panel.locked_count == 1
    assert panel.resources[0].resource_id == 'profile.default'
    assert panel.resources[1].lock_state == 'locked'
    assert 'upgrade' in panel.resources[1].actions
