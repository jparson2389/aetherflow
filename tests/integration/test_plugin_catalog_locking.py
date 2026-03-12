from aetherflow.core.services import create_default_services
from aetherflow.plugins.catalog import CatalogLockState
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion
from aetherflow.plugins.registry import PluginRegistry


def test_locked_premium_plugin_never_becomes_selectable() -> None:
    services = create_default_services()
    registry = PluginRegistry(services=services)
    manifest = PluginManifest(
        plugin_id='capture.mf',
        name='MF Capture',
        version=PluginVersion.parse('1.0.0'),
        api_version='1.0',
        plugin_type=PluginType.CAPTURE,
        entrypoint='capture.mf.dll',
        signed=True,
        premium=True,
        required_entitlements=['vision'],
        requires_worker=False,
        signature_scheme='Authenticode',
        digest_algorithm='SHA-256',
        rsa_key_bits=3072,
        publisher_thumbprint='aetherflow-publisher',
        trust_root_thumbprint='aetherflow-root',
    )

    registry.register(manifest)
    item = registry.catalog()[0]

    assert item.lock_state is CatalogLockState.LOCKED
    assert item.selectable is False
    assert item.purchase_cta == 'Upgrade to unlock'
    assert item.lock_reason == 'locked-premium-plugin'
    assert item.entitlement_state.value == 'LOCKED'
    assert item.premium is True
    assert item.required_entitlements == ('vision',)
    assert item.plugin_type is PluginType.CAPTURE
