from pathlib import Path

from aetherflow.core.services import create_default_services
from aetherflow.plugins.manifest import (
    PluginDistribution,
    PluginManifest,
    PluginType,
    PluginVersion,
)
from aetherflow.plugins.registry import PluginRegistry


def test_signed_plugin_loads_and_appears_in_catalog(tmp_path: Path) -> None:
    services = create_default_services()
    registry = PluginRegistry(services=services)
    artifact_path = tmp_path / 'capture.opencv.dll'
    artifact_path.write_bytes(b'dll')
    manifest = PluginManifest(
        plugin_id='capture.opencv',
        name='OpenCV Capture',
        version=PluginVersion.parse('1.0.0'),
        api_version='1.0',
        plugin_type=PluginType.CAPTURE,
        entrypoint='capture.opencv.dll',
        distribution=PluginDistribution.BUILTIN,
        artifact_path=artifact_path,
        premium=False,
        required_entitlements=[],
        requires_worker=False,
    )

    result = registry.register(manifest)
    entry = registry.catalog()[0]

    assert result.loaded is True
    assert registry.get('capture.opencv') == manifest
    assert entry.plugin_id == 'capture.opencv'
    assert entry.lock_state.value == 'AVAILABLE'
    assert entry.entitlement_state.value == 'LOADED'
    assert entry.premium is False
    assert entry.plugin_type is PluginType.CAPTURE
    assert entry.version == '1.0.0'
