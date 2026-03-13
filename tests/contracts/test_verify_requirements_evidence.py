"""Contract tests for verify-requirements evidence heuristics.

Asserts that key files have expected placeholder status to prevent regression
when heuristics change. Run verify-requirements.ps1 first, or the test will
run it.
"""

import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = PROJECT_ROOT / 'logs' / 'verify-requirements-evidence.md'

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
    'scripts/package-windows.ps1': True,
    'scripts/run-e2e.ps1': True,
    'tools/prompts.py': True,
    'src/aetherflow/input/xinput.py': True,
    'src/aetherflow/input/kbm.py': True,
    'src/aetherflow/input/playstation.py': True,
    'src/aetherflow/vision/ds_capture.py': True,
    'src/aetherflow/vision/obs_capture.py': True,
    'src/aetherflow/ui/panels/environment_panel.py': False,
}


def _run_verify_requirements() -> None:
    """Run verify-requirements.ps1 to refresh evidence."""
    script = PROJECT_ROOT / '.cursor' / 'workflows' / 'verify-requirements.ps1'
    subprocess.run(
        [
            'powershell',
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            str(script),
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )


def _parse_evidence() -> dict[str, bool]:
    """Parse evidence index and return path -> placeholder mapping."""
    if not EVIDENCE_PATH.exists():
        _run_verify_requirements()
    text = EVIDENCE_PATH.read_text(encoding='utf-8')
    result = {}
    pattern = re.compile(r'path="([^"]+)"[^"]*placeholder=(true|false)')
    for m in pattern.finditer(text):
        result[m.group(1).replace('\\', '/')] = m.group(2).lower() == 'true'
    return result


def test_verify_requirements_evidence_golden_expectations() -> None:
    """Assert golden files have expected placeholder status."""
    evidence = _parse_evidence()
    for path, expected in GOLDEN_EXPECTATIONS.items():
        if path not in evidence:
            # File may not exist or may be under a different root
            full = PROJECT_ROOT / path
            if not full.exists():
                continue
            # Run workflow to ensure evidence is fresh
            _run_verify_requirements()
            evidence = _parse_evidence()
        assert path in evidence, f'Path {path} not in evidence index'
        actual = evidence[path]
        assert actual == expected, (
            f'Placeholder mismatch for {path}: expected {expected}, got {actual}'
        )
