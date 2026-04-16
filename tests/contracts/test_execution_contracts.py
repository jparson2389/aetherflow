from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path
from typing import get_args

import pytest

from aetherflow.core.shared_memory_layout import (
    FrameMetadata,
    FramePixelFormat,
    OverflowPolicy,
    PixelFormat,
    RingBufferCursors,
    SharedMemoryLayout,
)
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

REQUIRED_PROTO_MESSAGES = {
    'CaptureMode': set(),
    'CaptureStartRequest': {'uint32 timeout_ms = 4;'},
    'CaptureStopRequest': set(),
    'OperationStatus': {'uint32 retry_budget_remaining = 4;'},
    'WorkerHeartbeat': set(),
    'WorkerLog': set(),
    'PluginLoadResult': {'string error_code = 4;', 'string error_message = 5;'},
    'DiagnosticsExportRequest': set(),
    'DiagnosticsExportResponse': set(),
}

REQUIRED_CAPTURE_RPCS = {
    'StartCapture',
    'StopCapture',
    'ReportHeartbeat',
    'ForwardWorkerLog',
    'ReportPluginLoadResult',
    'ExportDiagnostics',
}


def _parse_proto_message_blocks(proto_text: str) -> dict[str, str]:
    """Extract top-level message blocks from the capture proto text."""
    return {
        match.group('name'): match.group('body')
        for match in re.finditer(
            r'message\s+(?P<name>\w+)\s*\{(?P<body>.*?)\n\}',
            proto_text,
            flags=re.DOTALL,
        )
    }


def _parse_capture_rpc_names(proto_text: str) -> set[str]:
    """Extract RPC names declared in the capture service."""
    return {
        match.group('name')
        for match in re.finditer(r'rpc\s+(?P<name>\w+)\s*\(', proto_text)
    }


def _assert_capture_proto_contract(proto_text: str) -> None:
    """Assert that required messages, fields, and RPC names exist."""
    message_blocks = _parse_proto_message_blocks(proto_text)
    rpc_names = _parse_capture_rpc_names(proto_text)

    missing_messages = sorted(set(REQUIRED_PROTO_MESSAGES) - set(message_blocks))
    assert not missing_messages, f'Missing proto messages: {missing_messages}'

    for message_name, required_fields in REQUIRED_PROTO_MESSAGES.items():
        message_body_lines = {
            line.strip()
            for line in message_blocks[message_name].splitlines()
            if line.strip() and not line.strip().startswith('//')
        }
        missing_fields = sorted(required_fields - message_body_lines)
        assert not missing_fields, f'Missing fields in {message_name}: {missing_fields}'

    missing_rpcs = sorted(REQUIRED_CAPTURE_RPCS - rpc_names)
    assert not missing_rpcs, f'Missing capture RPCs: {missing_rpcs}'


def _parse_doc_rpc_table(doc_text: str) -> dict[str, dict[str, str]]:
    """Parse RPC rows from the Timeouts and Retry Posture table in the capture docs.

    Returns:
        Mapping of RPC name to a dict with 'timeout' and 'retry' keys.
    """
    result: dict[str, dict[str, str]] = {}
    for match in re.finditer(
        r'\|\s*`(?P<rpc>\w+)`\s*\|\s*(?P<timeout>[^|]+?)\s*\|\s*(?P<retry>[^|]+?)\s*\|',
        doc_text,
    ):
        result[match.group('rpc')] = {
            'timeout': match.group('timeout').strip(),
            'retry': match.group('retry').strip(),
        }
    return result


def test_capture_proto_defines_required_control_plane_messages() -> None:
    proto_text = (PROJECT_ROOT / 'proto' / 'capture.proto').read_text(encoding='utf-8')

    _assert_capture_proto_contract(proto_text)


def test_capture_proto_contract_rejects_missing_required_message() -> None:
    """Negative path: removing a required message must fail contract checks."""
    proto_text = (PROJECT_ROOT / 'proto' / 'capture.proto').read_text(encoding='utf-8')
    broken_proto = proto_text.replace(
        'message WorkerHeartbeat {', 'message RemovedWorkerHeartbeat {', 1
    )

    with pytest.raises(AssertionError, match='Missing proto messages'):
        _assert_capture_proto_contract(broken_proto)


def test_capture_proto_contract_rejects_missing_required_field() -> None:
    """Negative path: commenting out a required field must fail field-level contract checks."""
    proto_text = (PROJECT_ROOT / 'proto' / 'capture.proto').read_text(encoding='utf-8')
    broken_proto = proto_text.replace(
        'uint32 timeout_ms = 4;', '// uint32 timeout_ms = 4;', 1
    )

    with pytest.raises(AssertionError, match='Missing fields in CaptureStartRequest'):
        _assert_capture_proto_contract(broken_proto)


def test_capture_proto_docs_define_timeout_and_retry_posture() -> None:
    """Semantic check: every required RPC must appear as a table row with correct timeout."""
    doc_text = (PROJECT_ROOT / 'docs' / 'proto' / 'capture.md').read_text(
        encoding='utf-8'
    )

    rpc_table = _parse_doc_rpc_table(doc_text)
    missing_rpcs = sorted(REQUIRED_CAPTURE_RPCS - set(rpc_table))
    assert not missing_rpcs, f'Missing RPC rows in docs table: {missing_rpcs}'

    for rpc_name, entry in rpc_table.items():
        assert entry['timeout'] == '750 ms', (
            f'Unexpected timeout for {rpc_name}: {entry["timeout"]}'
        )

    retry_once_rpcs = {'StartCapture', 'StopCapture', 'ReportPluginLoadResult'}
    no_retry_rpcs = {'ReportHeartbeat', 'ForwardWorkerLog', 'ExportDiagnostics'}
    for rpc_name in retry_once_rpcs:
        assert (
            rpc_table[rpc_name]['retry'] == 'Retry once on transient transport errors.'
        ), f'Unexpected retry posture for {rpc_name}: {rpc_table[rpc_name]["retry"]}'
    for rpc_name in no_retry_rpcs:
        assert rpc_table[rpc_name]['retry'] == 'No automatic retries.', (
            f'Unexpected retry posture for {rpc_name}: {rpc_table[rpc_name]["retry"]}'
        )

    assert 'heartbeat interval: 500 ms' in doc_text
    assert '2 missed heartbeats' in doc_text
    assert '3 consecutive missed heartbeats' in doc_text


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
    layout = SharedMemoryLayout()

    assert layout.ring_slot_count == 4
    assert layout.overflow_policy is OverflowPolicy.DROP_OLDEST
    assert layout.default_pixel_format is FramePixelFormat.BGR24
    assert get_args(PixelFormat) == ('BGR24', 'NV12', 'YUY2', 'MJPEG', 'RGB32')
    assert [field.name for field in fields(FrameMetadata)] == [
        'width',
        'height',
        'pixel_format',
        'stride_bytes',
        'timestamp_ns',
        'sequence_number',
    ]
    assert [field.name for field in fields(RingBufferCursors)] == [
        'producer_cursor',
        'consumer_cursor',
        'overflow_count',
    ]
