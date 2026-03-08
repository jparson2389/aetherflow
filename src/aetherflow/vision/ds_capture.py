"""Premium DirectShow capture model."""

from __future__ import annotations

from aetherflow.vision.mf_capture import MediaFoundationCapturePlugin


class DirectShowCapturePlugin(MediaFoundationCapturePlugin):
    """DirectShow variant of the premium capture backend."""
