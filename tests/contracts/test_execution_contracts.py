from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_capture_proto_defines_required_control_plane_messages() -> None:
    proto_text = (PROJECT_ROOT / "proto" / "capture.proto").read_text(encoding="utf-8")

    assert "message CaptureStartRequest" in proto_text
    assert "message CaptureStopRequest" in proto_text
    assert "message WorkerHeartbeat" in proto_text
    assert "message WorkerLog" in proto_text
    assert "message PluginLoadResult" in proto_text
    assert "message DiagnosticsExportRequest" in proto_text
    assert "rpc StartCapture" in proto_text
    assert "rpc StopCapture" in proto_text
    assert "rpc ReportHeartbeat" in proto_text
    assert "rpc ExportDiagnostics" in proto_text


def test_plugin_system_contract_defines_trust_and_runtime_states() -> None:
    header_text = (PROJECT_ROOT / "include" / "plugin_system.hpp").read_text(
        encoding="utf-8"
    )

    assert "PluginRuntimeState" in header_text
    assert "kGrace" in header_text
    assert "kLocked" in header_text
    assert "SignaturePolicy" in header_text
    assert "rsa_key_bits" in header_text
    assert "publisher_thumbprint" in header_text


def test_shared_memory_layout_defines_ring_metadata_and_overflow_policy() -> None:
    layout_text = (
        PROJECT_ROOT / "src" / "aetherflow" / "core" / "shared_memory_layout.py"
    ).read_text(encoding="utf-8")

    assert "FramePixelFormat" in layout_text
    assert "OverflowPolicy" in layout_text
    assert "stride_bytes" in layout_text
    assert "sequence_number" in layout_text
    assert "timestamp_ns" in layout_text
    assert "ring_slot_count" in layout_text
