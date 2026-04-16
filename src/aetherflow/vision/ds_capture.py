"""Premium DirectShow capture model."""

from __future__ import annotations

from typing import ClassVar

from aetherflow.core.services import AppServices
from aetherflow.plugins.manifest import (
    PluginDistribution,
    PluginManifest,
    PluginType,
    PluginVersion,
)
from aetherflow.vision.mf_capture import MediaFoundationCapturePlugin


class DirectShowCapturePlugin(MediaFoundationCapturePlugin):
    """DirectShow variant of the premium capture backend.

    Inherits the full capture pipeline from MediaFoundationCapturePlugin
    but uses its own plugin identity (capture.ds) and DirectShow-specific
    format support. The actual OS calls are stubbed since the Python side
    runs in WSL; the capability declarations and entitlement gating are real.
    """

    PLUGIN_ID: ClassVar[str] = 'capture.ds'
    PLUGIN_NAME: ClassVar[str] = 'DS Capture'
    ENTRYPOINT: ClassVar[str] = 'capture.ds.dll'
    SUPPORTED_FORMATS: ClassVar[list[str]] = ['YUY2', 'RGB24', 'MJPEG']

    _BUILTIN_DEVICES: ClassVar[list[dict[str, str | int]]] = [
        {
            'stable_id': 'ds-capture-default',
            'name': 'DirectShow Default Device',
            'device_id': 'DS\\DEFAULT\\CAPTURE',
            'backend_index': 0,
        },
    ]

    _BUILTIN_MODES: ClassVar[list[tuple[int, int, int, str, bool]]] = [
        # (width, height, fps, pixel_format, zero_copy)
        (1920, 1080, 30, 'YUY2', False),
        (1920, 1080, 60, 'YUY2', False),
        (1920, 1080, 120, 'MJPEG', False),
        (2560, 1440, 60, 'MJPEG', False),
    ]

    def __init__(self, *, services: AppServices) -> None:
        """Create the DirectShow capture plugin model.

        Args:
            services: Shared application services for entitlement checks.

        """
        super().__init__(services=services)
        # Override manifest with DS-specific identity
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
