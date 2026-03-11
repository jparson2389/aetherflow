from aetherflow.core.services import create_default_services
from aetherflow.vision.mf_capture import MediaFoundationCapturePlugin


def test_media_foundation_capture_is_hidden_without_entitlement() -> None:
    plugin = MediaFoundationCapturePlugin(services=create_default_services())

    assert plugin.is_available() is False
    assert plugin.catalog_state().selectable is False


def test_media_foundation_capture_formats_locked_until_entitled() -> None:
    services = create_default_services()
    plugin = MediaFoundationCapturePlugin(services=services)

    locked_selector = plugin.format_selector()
    assert locked_selector.formats == []
    assert locked_selector.unavailable_reason == 'Upgrade to unlock'

    services.entitlements.grant('capture.mf', ('vision',))
    plugin = MediaFoundationCapturePlugin(services=services)
    unlocked_selector = plugin.format_selector()
    assert 'NV12' in unlocked_selector.formats
