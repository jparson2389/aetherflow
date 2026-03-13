from aetherflow.core.entitlements import RoleName
from aetherflow.core.services import create_default_services
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion
from aetherflow.plugins.registry import PluginRegistry
from aetherflow.ui.panels.plugin_catalog_panel import PluginCatalogPanelModel


def test_catalog_panel_counts_locked_entries() -> None:
    """Ensure catalog panel counts locked entries correctly."""
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
    panel = PluginCatalogPanelModel.from_registry(
        registry,
        role=RoleName.POWER_GAMER,
    )

    assert panel.locked_count == 1
    assert panel.available_count == 0
