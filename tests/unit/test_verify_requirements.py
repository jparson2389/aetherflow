from __future__ import annotations

from pathlib import Path

from tools import verify_requirements


def test_generated_proto_files_are_never_placeholder() -> None:
    assert verify_requirements.is_mature_file(
        'src/aetherflow/proto/capture_pb2.py',
        'descriptor = object()\n',
    )
    assert not verify_requirements.is_placeholder(
        'src/aetherflow/proto/capture_pb2.py',
        'descriptor = object()\n',
    )


def test_write_evidence_index_records_relative_placeholder_status(tmp_path: Path) -> None:
    src_path = tmp_path / 'src'
    src_path.mkdir()
    target = src_path / 'feature.py'
    target.write_text('# TODO\n', encoding='utf-8')

    evidence_path = tmp_path / 'logs' / 'verify-requirements-evidence.md'
    verify_requirements.write_evidence_index(
        evidence_path=evidence_path,
        roots=[src_path],
        repo_root=tmp_path,
    )

    text = evidence_path.read_text(encoding='utf-8')
    assert 'path="src/feature.py"' in text
    assert 'placeholder=true' in text
