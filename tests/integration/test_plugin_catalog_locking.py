from aetherflow.core.services import create_default_services
from aetherflow.plugins.catalog import CatalogLockState
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion
from aetherflow.plugins.registry import PluginRegistry


def test_locked_premium_plugin_never_becomes_selectable() -> None:
    services = create_default_services()
    registry = PluginRegistry(services=services)
    manifest = PluginManifest(
        plugin_id="capture.mf",
        name="MF Capture",
        version=PluginVersion.parse("1.0.0"),
        api_version="1.0",
        plugin_type=PluginType.CAPTURE,
        entrypoint="capture.mf.dll",
        signed=True,
        premium=True,
        required_entitlements=["vision"],
        requires_worker=False,
    )

    registry.register(manifest)
    item = registry.catalog()[0]

    assert item.lock_state is CatalogLockState.LOCKED
    assert item.selectable is False
    assert item.purchase_cta == "Upgrade to unlock"
