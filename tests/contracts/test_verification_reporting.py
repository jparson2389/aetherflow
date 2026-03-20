from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.shell_utils import resolve_powershell_executable

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows-only: requires verify-requirements.ps1 and MSVC')
def test_verify_requirements_generates_evidence_based_outputs() -> None:
    script = PROJECT_ROOT / '.cursor' / 'workflows' / 'verify-requirements.ps1'

    result = subprocess.run(
        [
            resolve_powershell_executable(),
            '-NoProfile',
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            str(script),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    report_text = (PROJECT_ROOT / 'docs' / 'requirements-report.md').read_text(
        encoding='utf-8'
    )
    result_path = PROJECT_ROOT / 'logs' / 'verification' / 'AF-00-02b.json'
    pending_path = PROJECT_ROOT / 'logs' / 'verification' / 'pending_app_checks.json'

    assert '- Retired:' in report_text
    assert '- Coded:' in report_text
    assert '- Evidenced:' in report_text
    assert '- Verified:' in report_text
    assert (
        '### AF-00-01 - Canonicalize repo identity and self-contained docs.'
        in report_text
    )
    assert '- Status: retired' in report_text
    assert result_path.exists()
    assert pending_path.exists()

    result_payload = json.loads(result_path.read_text(encoding='utf-8'))
    assert result_payload['status'] in ('evidenced', 'verified')
    assert result_payload['reviewer_status'] in ('pending', 'approved')
