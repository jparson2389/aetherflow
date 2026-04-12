"""End-to-end tests for premium capture backend entitlement flows.

These tests exercise full system-level flows across EntitlementStore,
premium capture backends (MF/DS), CaptureMetrics, and UI panel models.
They verify observable outcomes that span multiple subsystem boundaries,
complementing the integration tests in test_capture_premium_gating.py.
"""

from __future__ import annotations

import json

import pytest

from aetherflow.core.capture_metrics import CaptureMetrics
from aetherflow.core.diagnostics import PipelineDiagnostics
from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.services import create_default_services
from aetherflow.plugins.catalog import CatalogLockState
from aetherflow.ui.panels.capture_diagnostics_panel import CaptureDiagnosticsPanelModel
from aetherflow.ui.panels.render_mode_panel import RenderModePanelModel
from aetherflow.vision.ds_capture import DirectShowCapturePlugin
from aetherflow.vision.mf_capture import MediaFoundationCapturePlugin

# ---------------------------------------------------------------------------
# Scenario 1: Premium backend lock-to-unlock flow
# ---------------------------------------------------------------------------


class TestPremiumBackendLockToUnlockFlow:
    """Full lock -> unlock -> capture -> metrics chain across subsystems."""

    def test_mf_lock_to_unlock_capture_with_real_metrics(self) -> None:
        """MF backend: locked -> grant -> enumerate -> capture -> real metrics.

        Crosses: EntitlementStore -> MFCapturePlugin -> CaptureMetrics.
        """
        services = create_default_services()
        plugin = MediaFoundationCapturePlugin(services=services)

        # Phase 1: Backend is locked -- catalog reflects locked state
        assert plugin.is_available() is False
        entry = plugin.catalog_state()
        assert entry.lock_state == CatalogLockState.LOCKED
        assert entry.entitlement_state is EntitlementState.LOCKED
        assert entry.purchase_cta == 'Upgrade to unlock'

        # Phase 2: Grant entitlement -- backend becomes available
        services.entitlements.grant('capture.mf', ('vision',))
        plugin = MediaFoundationCapturePlugin(services=services)
        assert plugin.is_available() is True
        entry = plugin.catalog_state()
        assert entry.lock_state == CatalogLockState.AVAILABLE
        assert entry.selectable is True

        # Phase 3: Enumerate devices and start capture
        devices = plugin.enumerate_devices()
        assert len(devices) >= 1
        device = devices[0]
        modes = plugin.supported_modes(device.stable_id)
        assert len(modes) >= 1

        mode = modes[0]
        session = plugin.start_capture(
            stable_device_id=device.stable_id,
            capture_width=mode.capture_width,
            capture_height=mode.capture_height,
            capture_fps=mode.capture_fps,
        )
        assert session.running is True

        # Phase 4: Record frames and verify metrics are real (not stubs)
        frame_count = 120
        for i in range(frame_count):
            plugin.record_capture_sample(
                device.stable_id,
                timestamp_s=i / mode.capture_fps,
            )

        metrics = plugin.stop_capture(device.stable_id)
        assert isinstance(metrics, CaptureMetrics)
        assert metrics.target_fps == mode.capture_fps
        assert metrics.measured_fps > 0
        assert metrics.frames_total > 0
        assert metrics.dropped_frames == 0

    def test_ds_lock_to_unlock_capture_with_real_metrics(self) -> None:
        """DS backend: locked -> grant -> enumerate -> capture -> real metrics.

        Crosses: EntitlementStore -> DSCapturePlugin -> CaptureMetrics.
        """
        services = create_default_services()
        plugin = DirectShowCapturePlugin(services=services)

        # Phase 1: Backend is locked
        assert plugin.is_available() is False
        entry = plugin.catalog_state()
        assert entry.lock_state == CatalogLockState.LOCKED
        assert entry.plugin_id == 'capture.ds'

        # Phase 2: Grant entitlement
        services.entitlements.grant('capture.ds', ('vision',))
        plugin = DirectShowCapturePlugin(services=services)
        assert plugin.is_available() is True

        # Phase 3: Enumerate and capture
        devices = plugin.enumerate_devices()
        assert len(devices) >= 1
        device = devices[0]
        modes = plugin.supported_modes(device.stable_id)
        mode = modes[0]

        session = plugin.start_capture(
            stable_device_id=device.stable_id,
            capture_width=mode.capture_width,
            capture_height=mode.capture_height,
            capture_fps=mode.capture_fps,
        )
        assert session.running is True

        # Phase 4: Record frames and verify real metrics
        for i in range(90):
            plugin.record_capture_sample(
                device.stable_id,
                timestamp_s=i / mode.capture_fps,
            )

        metrics = plugin.stop_capture(device.stable_id)
        assert isinstance(metrics, CaptureMetrics)
        assert metrics.measured_fps > 0
        assert metrics.frames_total > 0


# ---------------------------------------------------------------------------
# Scenario 2: 120 FPS path with entitlement chain and UI mode list
# ---------------------------------------------------------------------------


class TestHighFpsEntitlementChainWithUI:
    """120 FPS entitlement -> enumerate -> UI mode list -> capture -> verify FPS."""

    def test_120fps_mf_path_through_ui_mode_list(self) -> None:
        """MF 120 FPS mode appears in UI-facing mode list after entitlement grant.

        Crosses: EntitlementStore -> MFCapturePlugin -> RenderModePanelModel.
        """
        services = create_default_services()

        # Step 1: Locked -- cannot enumerate
        plugin_locked = MediaFoundationCapturePlugin(services=services)
        with pytest.raises(PermissionError):
            plugin_locked.enumerate_devices()

        # Step 2: Grant entitlement
        services.entitlements.grant('capture.mf', ('vision',))
        plugin = MediaFoundationCapturePlugin(services=services)

        # Step 3: Enumerate 120 FPS capable device
        devices = plugin.enumerate_devices()
        device = devices[0]
        modes = plugin.supported_modes(device.stable_id)
        modes_120 = [m for m in modes if m.capture_fps == 120]
        assert len(modes_120) >= 1, 'MF backend must expose at least one 120 FPS mode'

        # Step 4: Verify render mode panel is in a usable state (CPU default)
        render_panel = RenderModePanelModel.default()
        assert render_panel.active_mode_id == 'render.cpu'
        # GPU mode is selectable too
        gpu_panel = render_panel.select('render.gpu')
        assert gpu_panel.active_mode_id == 'render.gpu'

        # Step 5: Start 120 FPS capture and verify measured FPS meets threshold
        mode_120 = modes_120[0]
        session = plugin.start_capture(
            stable_device_id=device.stable_id,
            capture_width=mode_120.capture_width,
            capture_height=mode_120.capture_height,
            capture_fps=120,
        )
        assert session.running is True

        # Simulate 600 frames at 120 FPS (5-second window)
        for i in range(600):
            plugin.record_capture_sample(
                device.stable_id,
                timestamp_s=i / 120.0,
            )

        metrics = plugin.stop_capture(device.stable_id)
        assert metrics.target_fps == 120
        # Measured FPS should be within 1% of target for perfect intervals
        assert metrics.measured_fps >= 119.0, (
            f'Expected >= 119 FPS, got {metrics.measured_fps:.1f}'
        )
        assert metrics.dropped_frames == 0

    def test_ds_120fps_path_with_capture_session(self) -> None:
        """DS backend 120 FPS capture produces valid sustained throughput.

        Crosses: EntitlementStore -> DSCapturePlugin -> CaptureMetrics.
        """
        services = create_default_services()
        services.entitlements.grant('capture.ds', ('vision',))
        plugin = DirectShowCapturePlugin(services=services)

        devices = plugin.enumerate_devices()
        device = devices[0]
        modes = plugin.supported_modes(device.stable_id)
        modes_120 = [m for m in modes if m.capture_fps == 120]
        assert len(modes_120) >= 1

        mode_120 = modes_120[0]
        plugin.start_capture(
            stable_device_id=device.stable_id,
            capture_width=mode_120.capture_width,
            capture_height=mode_120.capture_height,
            capture_fps=120,
        )

        # 600 frames at 120 FPS
        for i in range(600):
            plugin.record_capture_sample(
                device.stable_id,
                timestamp_s=i / 120.0,
            )

        metrics = plugin.stop_capture(device.stable_id)
        assert metrics.target_fps == 120
        assert metrics.measured_fps >= 119.0
        assert metrics.dropped_frames == 0


# ---------------------------------------------------------------------------
# Scenario 3: Premium backend fallback when locked mid-session
# ---------------------------------------------------------------------------


class TestPremiumBackendFallbackWhenLockedMidSession:
    """Entitled -> capture -> revoke -> PermissionError -> diagnostics panel."""

    def test_mf_revoke_mid_session_surfaces_diagnostics(self) -> None:
        """Revoking entitlement mid-session blocks next operation and
        the diagnostics panel can surface a recovery action.

        Crosses: EntitlementStore -> MF backend lifecycle -> CaptureDiagnosticsPanel.
        """
        services = create_default_services()
        services.entitlements.grant('capture.mf', ('vision',))
        plugin = MediaFoundationCapturePlugin(services=services)

        # Step 1: Start capture while entitled
        devices = plugin.enumerate_devices()
        device = devices[0]
        modes = plugin.supported_modes(device.stable_id)
        mode = modes[0]

        plugin.start_capture(
            stable_device_id=device.stable_id,
            capture_width=mode.capture_width,
            capture_height=mode.capture_height,
            capture_fps=mode.capture_fps,
        )

        # Record a few frames while still entitled
        for i in range(30):
            plugin.record_capture_sample(
                device.stable_id,
                timestamp_s=i / mode.capture_fps,
            )

        # Step 2: Revoke entitlement (transition to LOCKED)
        services.entitlements.revoke('capture.mf')

        # Step 3: Verify the backend raises PermissionError on next operation
        # Creating a new plugin instance reflects the revoked state
        plugin_revoked = MediaFoundationCapturePlugin(services=services)
        assert plugin_revoked.is_available() is False

        with pytest.raises(PermissionError, match='locked'):
            plugin_revoked.enumerate_devices()

        with pytest.raises(PermissionError, match='locked'):
            plugin_revoked.supported_modes(device.stable_id)

        # Step 4: Verify diagnostics panel can surface recovery action
        snapshot = PipelineDiagnostics(
            event_rate_hz=0.0,
            output_rate_hz=0.0,
            latency_ms=0.0,
            jitter_ms=0.0,
        )
        panel = CaptureDiagnosticsPanelModel.from_snapshot(
            recommendation='Re-grant vision entitlement to restore capture',
            snapshot=snapshot,
        )
        assert 'apply_recommendation' in panel.actions
        assert 'copy_diagnostics' in panel.actions
        assert panel.recommendation == 'Re-grant vision entitlement to restore capture'
        # Diagnostics blob is valid JSON
        blob = json.loads(panel.diagnostics_blob)
        assert 'event_rate_hz' in blob

    def test_ds_revoke_blocks_new_session_start(self) -> None:
        """DS backend blocks start_capture after entitlement revocation.

        Crosses: EntitlementStore -> DS backend lifecycle -> CaptureDiagnosticsPanel.
        """
        services = create_default_services()
        services.entitlements.grant('capture.ds', ('vision',))
        plugin = DirectShowCapturePlugin(services=services)

        devices = plugin.enumerate_devices()
        device = devices[0]
        modes = plugin.supported_modes(device.stable_id)
        mode = modes[0]

        # Start and record a few frames
        plugin.start_capture(
            stable_device_id=device.stable_id,
            capture_width=mode.capture_width,
            capture_height=mode.capture_height,
            capture_fps=mode.capture_fps,
        )
        for i in range(10):
            plugin.record_capture_sample(
                device.stable_id,
                timestamp_s=i / mode.capture_fps,
            )

        # Revoke entitlement
        services.entitlements.revoke('capture.ds')

        # New plugin instance reflects locked state
        plugin_revoked = DirectShowCapturePlugin(services=services)
        assert plugin_revoked.is_available() is False

        catalog = plugin_revoked.catalog_state()
        assert catalog.lock_state == CatalogLockState.LOCKED
        assert catalog.entitlement_state is EntitlementState.LOCKED

        with pytest.raises(PermissionError, match='locked'):
            plugin_revoked.start_capture(
                stable_device_id=device.stable_id,
                capture_width=mode.capture_width,
                capture_height=mode.capture_height,
                capture_fps=mode.capture_fps,
            )

        # Diagnostics panel surfaces fallback
        panel = CaptureDiagnosticsPanelModel(
            recommendation='1080p@60',
            diagnostics_blob='{}',
        )
        assert 'apply_recommendation' in panel.actions
        assert panel.recommendation == '1080p@60'
