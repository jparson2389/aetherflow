"""Premium Media Foundation capture model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from aetherflow.core.capture_metrics import CaptureMetrics, CaptureMetricsTracker
from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.services import AppServices
from aetherflow.plugins.catalog import (
    CatalogEntry,
    build_catalog_entry,
    lock_state_for_entitlement,
)
from aetherflow.plugins.manifest import (
    PluginDistribution,
    PluginManifest,
    PluginType,
    PluginVersion,
)
from aetherflow.vision.capture_resolver import CaptureResolver
from aetherflow.vision.opencv_capture import CaptureDevice, CaptureMode, CaptureSession


@dataclass(frozen=True, slots=True)
class CaptureFormatSelector:
    """Format selector for premium capture backends."""

    formats: list[str]
    unavailable_reason: str | None = None


class MediaFoundationCapturePlugin:
    """Premium Media Foundation capture backend.

    This backend provides access to Windows Media Foundation capture paths
    including hardware-accelerated NV12/YUY2 pipelines. The actual OS calls
    are stubbed since the Python side runs in WSL; the capability declarations
    and entitlement gating are real.
    """

    PLUGIN_ID: ClassVar[str] = 'capture.mf'
    PLUGIN_NAME: ClassVar[str] = 'MF Capture'
    ENTRYPOINT: ClassVar[str] = 'capture.mf.dll'
    SUPPORTED_FORMATS: ClassVar[list[str]] = ['NV12', 'YUY2', 'MJPEG']

    _BUILTIN_DEVICES: ClassVar[list[dict[str, str | int]]] = [
        {
            'stable_id': 'mf-capture-default',
            'name': 'Media Foundation Default Device',
            'device_id': 'MF\\DEFAULT\\CAPTURE',
            'backend_index': 0,
        },
    ]

    _BUILTIN_MODES: ClassVar[list[tuple[int, int, int, str, bool]]] = [
        # (width, height, fps, pixel_format, zero_copy)
        (1920, 1080, 30, 'NV12', True),
        (1920, 1080, 60, 'NV12', True),
        (1920, 1080, 120, 'NV12', True),
        (2560, 1440, 60, 'NV12', False),
        (2560, 1440, 120, 'YUY2', False),
    ]

    def __init__(self, *, services: AppServices) -> None:
        """Create the premium capture plugin model.

        Args:
            services: Shared application services for entitlement checks.

        """
        self._services = services
        self._manifest = PluginManifest(
            plugin_id=self.PLUGIN_ID,
            name=self.PLUGIN_NAME,
            version=PluginVersion.parse('1.0.0'),
            api_version='1.0',
            plugin_type=PluginType.CAPTURE,
            entrypoint=self.ENTRYPOINT,
            distribution=PluginDistribution.BUILTIN,
            premium=True,
            required_entitlements=['vision'],
            requires_worker=False,
        )
        self._active_sessions: dict[str, CaptureSession] = {}

    def _require_entitlement(self) -> None:
        """Raise PermissionError if the backend is locked."""
        state = self._services.entitlements.evaluate(
            self._manifest.plugin_id,
            tuple(self._manifest.required_entitlements),
        )
        if state is EntitlementState.LOCKED:
            raise PermissionError(
                f'Premium backend {self._manifest.plugin_id!r} is locked. '
                'Grant the required entitlement to use this backend.'
            )

    def is_available(self) -> bool:
        """Return whether the backend is selectable."""
        return (
            self._services.entitlements.evaluate(
                self._manifest.plugin_id,
                tuple(self._manifest.required_entitlements),
            )
            is not EntitlementState.LOCKED
        )

    def catalog_state(self) -> CatalogEntry:
        """Return the catalog state for the plugin."""
        entitlement_state = self._services.entitlements.evaluate(
            self._manifest.plugin_id,
            tuple(self._manifest.required_entitlements),
        )
        lock_state = lock_state_for_entitlement(entitlement_state)
        selectable = entitlement_state is not EntitlementState.LOCKED
        return build_catalog_entry(
            self._manifest,
            lock_state=lock_state,
            selectable=selectable,
            purchase_cta=None if selectable else 'Upgrade to unlock',
            allowed_roles=tuple(role.name for role in self._services.roles),
            entitlement_state=entitlement_state,
            lock_reason='locked-premium-plugin' if not selectable else None,
        )

    def format_selector(self) -> CaptureFormatSelector:
        """Return available format options based on entitlement state."""
        if not self.is_available():
            return CaptureFormatSelector(
                formats=[],
                unavailable_reason='Upgrade to unlock',
            )
        return CaptureFormatSelector(formats=list(self.SUPPORTED_FORMATS))

    def enumerate_devices(self) -> list[CaptureDevice]:
        """Return available capture devices for this backend.

        Raises:
            PermissionError: If the backend entitlement is locked.

        """
        self._require_entitlement()
        return [
            CaptureDevice(
                stable_id=str(d['stable_id']),
                name=str(d['name']),
                device_id=str(d['device_id']),
                backend_index=int(d['backend_index']),
            )
            for d in self._BUILTIN_DEVICES
        ]

    def supported_modes(self, stable_device_id: str) -> list[CaptureMode]:
        """Return supported capture modes for a device.

        Args:
            stable_device_id: Stable device identifier.

        Returns:
            List of supported capture modes.

        """
        self._require_entitlement()
        self._resolve_device(stable_device_id)  # validate device exists
        return [
            CaptureMode(
                capture_width=width,
                capture_height=height,
                capture_fps=fps,
                pixel_format_in=fmt,
                pixel_format_out='BGR',
                zero_copy_supported=zero_copy,
                hdr_supported=False,
                notes=f'Media Foundation {fmt} path',
            )
            for width, height, fps, fmt, zero_copy in self._BUILTIN_MODES
        ]

    def start_capture(
        self,
        *,
        stable_device_id: str,
        capture_width: int,
        capture_height: int,
        capture_fps: int,
    ) -> CaptureSession:
        """Start a capture session for the given device and mode.

        Args:
            stable_device_id: Stable device identifier.
            capture_width: Requested capture width.
            capture_height: Requested capture height.
            capture_fps: Requested capture FPS.

        Returns:
            An active capture session.

        Raises:
            PermissionError: If the backend entitlement is locked.
            ValueError: If the requested mode is not supported.

        """
        self._require_entitlement()
        device = self._resolve_device(stable_device_id)
        mode = self._resolve_mode(
            stable_device_id=stable_device_id,
            capture_width=capture_width,
            capture_height=capture_height,
            capture_fps=capture_fps,
        )
        session = CaptureSession(
            device=device,
            mode=mode,
            metrics=CaptureMetricsTracker(),
        )
        self._active_sessions[stable_device_id] = session
        return session

    def stop_capture(self, stable_device_id: str) -> CaptureMetrics:
        """Stop capture and return final metrics.

        Args:
            stable_device_id: Stable device identifier.

        Returns:
            Final capture metrics snapshot.

        """
        session = self._active_session(stable_device_id)
        session.running = False
        metrics = session.metrics.snapshot(target_fps=session.mode.capture_fps)
        self._active_sessions.pop(stable_device_id, None)
        return metrics

    def record_capture_sample(
        self,
        stable_device_id: str,
        *,
        timestamp_s: float,
        dropped: bool = False,
    ) -> None:
        """Record one capture sample for an active session.

        Args:
            stable_device_id: Stable device identifier.
            timestamp_s: Sample timestamp in seconds.
            dropped: Whether the frame was dropped.

        """
        session = self._active_session(stable_device_id)
        session.metrics.record_frame(timestamp_s=timestamp_s, dropped=dropped)

    def metrics_for(self, stable_device_id: str) -> CaptureMetrics:
        """Return current metrics for an active session.

        Args:
            stable_device_id: Stable device identifier.

        Returns:
            Current metrics snapshot.

        """
        session = self._active_session(stable_device_id)
        return session.metrics.snapshot(target_fps=session.mode.capture_fps)

    def _resolve_device(self, stable_device_id: str) -> CaptureDevice:
        """Return a known device or raise for an unknown identifier."""
        return CaptureResolver.resolve_device(self, stable_device_id)

    def _resolve_mode(
        self,
        *,
        stable_device_id: str,
        capture_width: int,
        capture_height: int,
        capture_fps: int,
    ) -> CaptureMode:
        """Return a supported mode or raise for an unsupported combination."""
        return CaptureResolver.resolve_mode(
            self,
            stable_device_id=stable_device_id,
            capture_width=capture_width,
            capture_height=capture_height,
            capture_fps=capture_fps,
        )

    def _active_session(self, stable_device_id: str) -> CaptureSession:
        """Return the active session for a device."""
        return CaptureResolver.active_session(self._active_sessions, stable_device_id)
