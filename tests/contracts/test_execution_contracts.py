from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from src.aetherflow.core.plugin_system import Plugin, RuntimeState

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_PLUGIN_FIELDS = [
    'plugin_id',
    'name',
    'version',
    'api_version',
    'plugin_type',
    'required_entitlements',
    'requires_drivers',
    'requires_worker',
]

EXPECTED_RUNTIME_STATES = [
    'RUNNING',
    'DEGRADED',
    'RECOVERING',
    'FAILED',
    'LOCKED',
    'GRACE',
]


def test_capture_proto_defines_required_control_plane_messages() -> None:
    proto_text = (PROJECT_ROOT / 'proto' / 'capture.proto').read_text(encoding='utf-8')

    assert 'message CaptureStartRequest' in proto_text
    assert 'message CaptureStopRequest' in proto_text
    assert 'message WorkerHeartbeat' in proto_text
    assert 'message WorkerLog' in proto_text
    assert 'message PluginLoadResult' in proto_text
    assert 'message DiagnosticsExportRequest' in proto_text
    assert 'rpc StartCapture' in proto_text
    assert 'rpc StopCapture' in proto_text
    assert 'rpc ReportHeartbeat' in proto_text
    assert 'rpc ExportDiagnostics' in proto_text


def test_capture_proto_docs_define_timeout_and_retry_posture() -> None:
    doc_text = (PROJECT_ROOT / 'docs' / 'proto' / 'capture.md').read_text(
        encoding='utf-8'
    )

    assert 'StartCapture' in doc_text
    assert 'StopCapture' in doc_text
    assert 'ReportHeartbeat' in doc_text
    assert 'ForwardWorkerLog' in doc_text
    assert 'ReportPluginLoadResult' in doc_text
    assert 'ExportDiagnostics' in doc_text
    assert 'timeout' in doc_text.lower()
    assert 'retry' in doc_text.lower()


def test_python_plugin_mirror_matches_frozen_native_header_fields() -> None:
    header_text = (PROJECT_ROOT / 'include' / 'plugin_system.hpp').read_text(
        encoding='utf-8'
    )

    assert [field.name for field in fields(Plugin)] == EXPECTED_PLUGIN_FIELDS
    assert 'enum class RuntimeState' in header_text
    assert 'struct Plugin' in header_text
    for field_name in EXPECTED_PLUGIN_FIELDS:
        assert field_name in header_text


def test_runtime_state_matches_prd_required_states() -> None:
    state_values = [state.value for state in RuntimeState]

    assert state_values == EXPECTED_RUNTIME_STATES


def test_shared_memory_layout_defines_ring_metadata_and_overflow_policy() -> None:
    layout_text = (
        PROJECT_ROOT / 'src' / 'aetherflow' / 'core' / 'shared_memory_layout.py'
    ).read_text(encoding='utf-8')

    assert 'FramePixelFormat' in layout_text
    assert 'OverflowPolicy' in layout_text
    assert 'stride_bytes' in layout_text
    assert 'sequence_number' in layout_text
    assert 'timestamp_ns' in layout_text
    assert 'ring_slot_count' in layout_text
    assert 'producer_cursor' in layout_text
    assert 'consumer_cursor' in layout_text
    assert 'overflow_count' in layout_text
