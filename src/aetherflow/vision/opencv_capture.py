"""Deterministic OpenCV capture model."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import ClassVar, Protocol

from aetherflow.core.capture_metrics import CaptureMetrics, CaptureMetricsTracker


@dataclass(frozen=True, slots=True)
class CaptureDevice:
    """Capture device descriptor."""

    stable_id: str
    name: str
    device_id: str
    backend_index: int


@dataclass(frozen=True, slots=True)
class CaptureMode:
    """Runtime capture mode descriptor."""

    capture_width: int
    capture_height: int
    capture_fps: int
    pixel_format_in: str
    pixel_format_out: str
    zero_copy_supported: bool
    hdr_supported: bool
    notes: str

    @property
    def fps(self) -> int:
        """Backward-compatible alias for capture_fps."""
        return self.capture_fps

    @property
    def pixel_format(self) -> str:
        """Backward-compatible alias for pixel_format_in."""
        return self.pixel_format_in


@dataclass(slots=True)
class CaptureSession:
    """Active capture session for one device/mode pair."""

    device: CaptureDevice
    mode: CaptureMode
    metrics: CaptureMetricsTracker
    running: bool = True


class CaptureProbe(Protocol):
    """Probe backend for capture devices and their supported modes."""

    def enumerate_devices(self) -> list[CaptureDevice]:
        """Return discovered capture devices."""

    def supported_modes(self, device: CaptureDevice) -> list[CaptureMode]:
        """Return supported modes for a discovered device."""


class WindowsOpenCVCaptureProbe:
    """Windows-friendly capture probe using OS device IDs plus deterministic mode probes."""

    _FALLBACK_CANDIDATE_MODES: tuple[tuple[int, int, int], ...] = (
        (1920, 1080, 30),
        (1920, 1080, 60),
        (1920, 1080, 120),
        (1920, 1080, 144),
        (1920, 1080, 240),
        (2560, 1440, 30),
        (2560, 1440, 60),
        (2560, 1440, 120),
        (2560, 1440, 144),
        (2560, 1440, 240),
        (3840, 2160, 30),
        (3840, 2160, 60),
    )
    _DEVICE_CAPABILITY_RULES: ClassVar[
        dict[tuple[str, str], tuple[tuple[int, int, int], ...]]
    ] = {
        # Elgato 4K X
        ('0fd9', '0066'): (
            (1920, 1080, 120),
            (2560, 1440, 240),
        ),
        # Elgato 4K S capture path, based on device-specific capture support.
        ('0fd9', '00af'): (
            (1920, 1080, 30),
            (1920, 1080, 60),
            (1920, 1080, 120),
            (1920, 1080, 240),
            (2560, 1440, 30),
            (2560, 1440, 60),
            (2560, 1440, 120),
            (2560, 1440, 144),
            (3840, 2160, 30),
            (3840, 2160, 60),
        ),
    }

    def __init__(self) -> None:
        """Initialise empty probe caches."""
        self._devices: list[CaptureDevice] | None = None
        self._mode_cache: dict[str, list[CaptureMode]] = {}

    def enumerate_devices(self) -> list[CaptureDevice]:
        """Return capture devices keyed by a stable ID derived from device_id."""
        if self._devices is None:
            records = self._query_windows_capture_devices()
            self._devices = [
                CaptureDevice(
                    stable_id=_stable_id_from_device_id(record['device_id']),
                    name=record['name'],
                    device_id=record['device_id'],
                    backend_index=index,
                )
                for index, record in enumerate(records)
            ]
        return list(self._devices)

    def supported_modes(self, device: CaptureDevice) -> list[CaptureMode]:
        """Return supported modes for a discovered device."""
        cached = self._mode_cache.get(device.stable_id)
        if cached is not None:
            return list(cached)

        modes = self._fallback_modes_for(device)
        self._mode_cache[device.stable_id] = modes
        return list(modes)

    def _query_windows_capture_devices(self) -> list[dict[str, str]]:
        """Query Windows for camera/capture devices and their instance IDs."""
        command = [
            'powershell',
            '-NoProfile',
            '-NonInteractive',
            '-Command',
            (
                '$devices = Get-PnpDevice | Where-Object { '
                "$_.Class -in @('Camera','Image','MEDIA') -and $_.FriendlyName "
                '} | Select-Object FriendlyName,InstanceId; '
                '$devices | ConvertTo-Json -Compress'
            ),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []
        if result.returncode != 0 or not result.stdout.strip():
            return []
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
        rows = payload if isinstance(payload, list) else [payload]
        devices = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            friendly_name = str(row.get('FriendlyName') or '').strip()
            device_id = str(row.get('InstanceId') or '').strip()
            if not friendly_name or not device_id:
                continue
            devices.append(
                {
                    'name': friendly_name,
                    'device_id': device_id or f'opencv-index:{index}',
                }
            )
        return devices

    def _fallback_modes_for(self, device: CaptureDevice) -> list[CaptureMode]:
        """Return deterministic candidate modes based on the probed device ID."""
        device_id_lower = device.device_id.casefold()
        modes = [
            CaptureMode(
                capture_width=width,
                capture_height=height,
                capture_fps=fps,
                pixel_format_in=_pixel_format_for_mode(
                    width=width, height=height, fps=fps
                ),
                pixel_format_out='BGR',
                zero_copy_supported=False,
                hdr_supported=_hdr_supported_for_device_mode(
                    device_id=device_id_lower,
                    width=width,
                    height=height,
                    fps=fps,
                ),
                notes=_notes_for_device_mode(
                    device_id=device_id_lower,
                    width=width,
                    height=height,
                    fps=fps,
                ),
            )
            for width, height, fps in self._FALLBACK_CANDIDATE_MODES
            if self._mode_allowed_for_device(
                width=width,
                height=height,
                fps=fps,
                device_id=device_id_lower,
            )
        ]
        return modes

    def _mode_allowed_for_device(
        self,
        *,
        width: int,
        height: int,
        fps: int,
        device_id: str,
    ) -> bool:
        """Gate candidate modes using explicit VID/PID rules plus conservative fallback."""
        vid_pid = _extract_vid_pid(device_id)
        if vid_pid in self._DEVICE_CAPABILITY_RULES:
            return (width, height, fps) in self._DEVICE_CAPABILITY_RULES[vid_pid]

        # Unknown devices stay conservative until runtime validation proves more.
        if fps in {120, 144, 240}:
            return False
        if fps in {30, 60}:
            return width <= 1920 and height <= 1080
        return False


class OpenCVCapturePlugin:
    """Default OpenCV-based capture provider."""

    def __init__(self, *, probe: CaptureProbe | None = None) -> None:
        """Initialise the plugin with no active sessions."""
        self._probe = probe or WindowsOpenCVCaptureProbe()
        self._active_sessions: dict[str, CaptureSession] = {}

    def enumerate_devices(self) -> list[CaptureDevice]:
        """Return available capture devices."""
        return self._probe.enumerate_devices()

    def supported_modes(self, stable_device_id: str) -> list[CaptureMode]:
        """Return supported modes for a device."""
        device = self._resolve_device(stable_device_id)
        return self._probe.supported_modes(device)

    def start_capture(
        self,
        *,
        stable_device_id: str,
        capture_width: int,
        capture_height: int,
        capture_fps: int,
    ) -> CaptureSession:
        """Start capture for a supported device/mode combination."""
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
        """Stop capture for a device and return the final metrics snapshot."""
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
        """Record one capture sample for an active session."""
        session = self._active_session(stable_device_id)
        session.metrics.record_frame(timestamp_s=timestamp_s, dropped=dropped)

    def metrics_for(self, stable_device_id: str) -> CaptureMetrics:
        """Return the current metrics snapshot for an active session."""
        session = self._active_session(stable_device_id)
        return session.metrics.snapshot(target_fps=session.mode.capture_fps)

    def _resolve_device(self, stable_device_id: str) -> CaptureDevice:
        """Return a known device or raise for an unknown identifier."""
        for device in self.enumerate_devices():
            if device.stable_id == stable_device_id:
                return device
        raise KeyError(f'Unknown capture device: {stable_device_id}')

    def _resolve_mode(
        self,
        *,
        stable_device_id: str,
        capture_width: int,
        capture_height: int,
        capture_fps: int,
    ) -> CaptureMode:
        """Return a supported mode or raise for an unsupported combination."""
        for mode in self.supported_modes(stable_device_id):
            if (
                mode.capture_width == capture_width
                and mode.capture_height == capture_height
                and mode.capture_fps == capture_fps
            ):
                return mode
        raise ValueError('unsupported capture mode rejected')

    def _active_session(self, stable_device_id: str) -> CaptureSession:
        """Return the active session for a device."""
        session = self._active_sessions.get(stable_device_id)
        if session is None or not session.running:
            raise RuntimeError(f'Capture not running for {stable_device_id}')
        return session


def _stable_id_from_device_id(device_id: str) -> str:
    """Return a deterministic stable ID derived from an OS device identifier."""
    normalized = re.sub(r'[^a-z0-9]+', '-', device_id.casefold()).strip('-')
    return f'capture-{normalized}'


def _extract_vid_pid(device_id: str) -> tuple[str, str] | None:
    """Extract ``VID`` and ``PID`` values from a Windows instance ID."""
    match = re.search(r'vid_([0-9a-f]{4}).*pid_([0-9a-f]{4})', device_id.casefold())
    if match is None:
        return None
    return match.group(1), match.group(2)


def _pixel_format_for_mode(*, width: int, height: int, fps: int) -> str:
    """Return a deterministic input pixel format for a candidate mode."""
    if fps >= 240 or (width >= 3840 and height >= 2160):
        return 'MJPEG'
    if fps >= 60:
        return 'NV12'
    return 'RGB32'


def _hdr_supported_for_device_mode(
    *,
    device_id: str,
    width: int,
    height: int,
    fps: int,
) -> bool:
    """Return whether HDR is supported for a specific device mode."""
    vid_pid = _extract_vid_pid(device_id)
    return vid_pid == ('0fd9', '00af') and (width, height, fps) in {
        (1920, 1080, 30),
        (1920, 1080, 60),
    }


def _notes_for_device_mode(
    *,
    device_id: str,
    width: int,
    height: int,
    fps: int,
) -> str:
    """Return descriptive notes for a specific device mode."""
    vid_pid = _extract_vid_pid(device_id)
    if vid_pid == ('0fd9', '00af'):
        suffix = (
            ' HDR'
            if _hdr_supported_for_device_mode(
                device_id=device_id,
                width=width,
                height=height,
                fps=fps,
            )
            else ''
        )
        return f'USB-C 3.2 Gen1 5Gbps capture profile{suffix}'
    return 'Probed candidate mode'
