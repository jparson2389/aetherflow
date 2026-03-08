from aetherflow.core.services import create_default_services
from aetherflow.plugins.manifest import PluginManifest, PluginType, PluginVersion
from aetherflow.plugins.registry import PluginRegistry


def test_signed_plugin_loads_and_appears_in_catalog() -> None:
    services = create_default_services()
    registry = PluginRegistry(services=services)
    manifest = PluginManifest(
        plugin_id="capture.opencv",
        name="OpenCV Capture",
        version=PluginVersion.parse("1.0.0"),
        api_version="1.0",
        plugin_type=PluginType.CAPTURE,
        entrypoint="capture.opencv.dll",
        signed=True,
        premium=False,
        required_entitlements=[],
        requires_worker=False,
        signature_scheme="Authenticode",
        digest_algorithm="SHA-256",
        rsa_key_bits=3072,
        publisher_thumbprint="aetherflow-publisher",
        trust_root_thumbprint="aetherflow-root",
    )

    result = registry.register(manifest)

    assert result.loaded is True
    assert registry.get("capture.opencv") == manifest
    assert registry.catalog()[0].plugin_id == "capture.opencv"
