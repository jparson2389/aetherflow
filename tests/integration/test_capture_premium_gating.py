"""Premium capture backend entitlement gating tests."""

import pytest

from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.services import create_default_services
from aetherflow.plugins.catalog import CatalogLockState
from aetherflow.vision.ds_capture import DirectShowCapturePlugin
from aetherflow.vision.mf_capture import MediaFoundationCapturePlugin

# --- Media Foundation backend gating ---


def test_media_foundation_capture_is_hidden_without_entitlement() -> None:
    """MF backend is unavailable and unselectable when no entitlement is granted."""
    plugin = MediaFoundationCapturePlugin(services=create_default_services())

    assert plugin.is_available() is False
    assert plugin.catalog_state().selectable is False


def test_media_foundation_capture_formats_locked_until_entitled() -> None:
    """MF format selector returns empty formats when locked, populated when granted."""
    services = create_default_services()
    plugin = MediaFoundationCapturePlugin(services=services)

    locked_selector = plugin.format_selector()
    assert locked_selector.formats == []
    assert locked_selector.unavailable_reason == 'Upgrade to unlock'

    services.entitlements.grant('capture.mf', ('vision',))
    plugin = MediaFoundationCapturePlugin(services=services)
    unlocked_selector = plugin.format_selector()
    assert 'NV12' in unlocked_selector.formats


def test_media_foundation_catalog_state_locked_when_no_entitlement() -> None:
    """MF catalog entry has LOCKED state and lock reason when not entitled."""
    services = create_default_services()
    plugin = MediaFoundationCapturePlugin(services=services)

    entry = plugin.catalog_state()
    assert entry.lock_state == CatalogLockState.LOCKED
    assert entry.entitlement_state is EntitlementState.LOCKED
    assert entry.lock_reason == 'locked-premium-plugin'
    assert entry.purchase_cta == 'Upgrade to unlock'


def test_media_foundation_catalog_state_available_when_entitled() -> None:
    """MF catalog entry becomes AVAILABLE when entitlement is granted."""
    services = create_default_services()
    services.entitlements.grant('capture.mf', ('vision',))
    plugin = MediaFoundationCapturePlugin(services=services)

    entry = plugin.catalog_state()
    assert entry.lock_state == CatalogLockState.AVAILABLE
    assert entry.selectable is True
    assert entry.purchase_cta is None


def test_media_foundation_enumerate_devices_blocked_when_locked() -> None:
    """MF enumerate_devices raises when entitlement is locked."""
    services = create_default_services()
    plugin = MediaFoundationCapturePlugin(services=services)

    with pytest.raises(PermissionError, match='locked'):
        plugin.enumerate_devices()


def test_media_foundation_enumerate_devices_works_when_entitled() -> None:
    """MF enumerate_devices returns device list when entitled."""
    services = create_default_services()
    services.entitlements.grant('capture.mf', ('vision',))
    plugin = MediaFoundationCapturePlugin(services=services)

    devices = plugin.enumerate_devices()
    assert isinstance(devices, list)


def test_media_foundation_supported_modes_include_120fps() -> None:
    """MF supported modes include at least one 120 FPS mode."""
    services = create_default_services()
    services.entitlements.grant('capture.mf', ('vision',))
    plugin = MediaFoundationCapturePlugin(services=services)

    devices = plugin.enumerate_devices()
    all_modes = [
        mode for device in devices for mode in plugin.supported_modes(device.stable_id)
    ]
    assert any(mode.capture_fps == 120 for mode in all_modes)


def test_media_foundation_start_stop_capture_cycle() -> None:
    """MF start/stop capture yields measurable metrics."""
    services = create_default_services()
    services.entitlements.grant('capture.mf', ('vision',))
    plugin = MediaFoundationCapturePlugin(services=services)

    devices = plugin.enumerate_devices()
    assert devices
    device = devices[0]
    modes = plugin.supported_modes(device.stable_id)
    mode_120 = next((m for m in modes if m.capture_fps == 120), None)
    assert mode_120 is not None

    session = plugin.start_capture(
        stable_device_id=device.stable_id,
        capture_width=mode_120.capture_width,
        capture_height=mode_120.capture_height,
        capture_fps=mode_120.capture_fps,
    )
    assert session.running is True

    # Simulate frames
    for i in range(120):
        plugin.record_capture_sample(
            device.stable_id,
            timestamp_s=i / 120.0,
        )

    metrics = plugin.stop_capture(device.stable_id)
    assert metrics.target_fps == 120
    assert metrics.measured_fps > 0


# --- DirectShow backend gating ---


def test_directshow_capture_is_hidden_without_entitlement() -> None:
    """DS backend is unavailable when no entitlement is granted."""
    services = create_default_services()
    plugin = DirectShowCapturePlugin(services=services)

    assert plugin.is_available() is False
    assert plugin.catalog_state().selectable is False


def test_directshow_capture_locked_state_has_correct_plugin_id() -> None:
    """DS backend uses its own plugin ID, distinct from MF."""
    services = create_default_services()
    plugin = DirectShowCapturePlugin(services=services)

    entry = plugin.catalog_state()
    assert entry.plugin_id == 'capture.ds'
    assert entry.lock_state == CatalogLockState.LOCKED


def test_directshow_capture_available_when_entitled() -> None:
    """DS backend becomes available when entitlement is granted."""
    services = create_default_services()
    services.entitlements.grant('capture.ds', ('vision',))
    plugin = DirectShowCapturePlugin(services=services)

    assert plugin.is_available() is True
    entry = plugin.catalog_state()
    assert entry.selectable is True


def test_directshow_enumerate_devices_blocked_when_locked() -> None:
    """DS enumerate_devices raises when entitlement is locked."""
    services = create_default_services()
    plugin = DirectShowCapturePlugin(services=services)

    try:
        plugin.enumerate_devices()
    except PermissionError as exc:
        assert 'locked' in str(exc).lower()
    else:
        raise AssertionError('Expected PermissionError when locked')


def test_directshow_formats_locked_until_entitled() -> None:
    """DS format selector returns empty formats when locked."""
    services = create_default_services()
    plugin = DirectShowCapturePlugin(services=services)

    locked_selector = plugin.format_selector()
    assert locked_selector.formats == []
    assert locked_selector.unavailable_reason == 'Upgrade to unlock'


# --- Grace period ---


def test_premium_backend_grace_period_allows_temporary_access() -> None:
    """Premium backend is available during grace period."""
    services = create_default_services()
    services.entitlements.activate_grace('capture.mf', ('vision',))
    plugin = MediaFoundationCapturePlugin(services=services)

    assert plugin.is_available() is True
    entry = plugin.catalog_state()
    assert entry.lock_state == CatalogLockState.GRACE
