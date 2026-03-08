from aetherflow.core.services import create_default_services
from aetherflow.vision.mf_capture import MediaFoundationCapturePlugin


def test_media_foundation_capture_is_hidden_without_entitlement() -> None:
    plugin = MediaFoundationCapturePlugin(services=create_default_services())

    assert plugin.is_available() is False
    assert plugin.catalog_state().selectable is False
