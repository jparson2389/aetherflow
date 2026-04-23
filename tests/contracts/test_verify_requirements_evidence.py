"""Contract tests for verify-requirements evidence heuristics."""

import re
from pathlib import Path

from tools.verify_requirements import REPO_ROOTS, write_evidence_index

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Golden expectations: path -> expected placeholder (True/False).
# Mature files must be placeholder=False; known stubs must be placeholder=True.
GOLDEN_EXPECTATIONS = {
    'tools/plan_exec.py': False,
    'tools/validation_gate.py': False,
    'tools/agent_call.py': False,
    'src/aetherflow/core/entitlements.py': False,
    'src/aetherflow/core/shared_memory_layout.py': False,
    'src/aetherflow/proto/capture_pb2.py': False,
    'docs/PLAN.md': False,
    'docs/PRD.md': False,
    'docs/governance/constraint-inventory.md': False,
    'scripts/package-windows.ps1': True,
    'scripts/run-e2e.ps1': True,
    'tools/prompts.py': True,
    'src/aetherflow/input/xinput.py': True,
    'src/aetherflow/input/kbm.py': False,
    'src/aetherflow/input/playstation.py': True,
    'src/aetherflow/vision/ds_capture.py': False,
    'src/aetherflow/vision/obs_capture.py': True,
    'src/aetherflow/ui/panels/environment_panel.py': False,
}


def _run_verify_requirements(tmp_path: Path) -> Path:
    """Write evidence index under tmp_path (no tracked logs/)."""
    evidence_path = tmp_path / 'verify-requirements-evidence.md'
    roots = [PROJECT_ROOT / part for part in REPO_ROOTS]
    write_evidence_index(
        evidence_path=evidence_path,
        roots=roots,
        repo_root=PROJECT_ROOT,
    )
    return evidence_path


def _parse_evidence(evidence_path: Path) -> dict[str, bool]:
    """Parse evidence index and return path -> placeholder mapping."""
    text = evidence_path.read_text(encoding='utf-8')
    result: dict[str, bool] = {}
    pattern = re.compile(r'path="([^"]+)"[^"]*placeholder=(true|false)')
    for m in pattern.finditer(text):
        result[m.group(1).replace('\\', '/')] = m.group(2).lower() == 'true'
    return result


def test_verify_requirements_evidence_golden_expectations(tmp_path: Path) -> None:
    """Assert golden files have expected placeholder status."""
    evidence_path = _run_verify_requirements(tmp_path)
    evidence = _parse_evidence(evidence_path)
    for path, expected in GOLDEN_EXPECTATIONS.items():
        full = PROJECT_ROOT / path
        if not full.exists():
            continue
        assert path in evidence, f'Path {path} not in evidence index'
        actual = evidence[path]
        assert actual == expected, (
            f'Placeholder mismatch for {path}: expected {expected}, got {actual}'
        )
