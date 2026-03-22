from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def test_verify_requirements_generates_evidence_based_outputs() -> None:
    result = subprocess.run(
        ['uv', 'run', 'python', '-m', 'tools.verify_requirements'],
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
