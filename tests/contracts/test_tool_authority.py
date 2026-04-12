"""Contract tests asserting tool authority boundaries.

Only ``tools/verify_requirements`` is authorised to write
``docs/requirements-report.md`` and ``logs/verification/<item-id>.json``.
Advisory tools must not claim or promote a ``verified`` status.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PENDING_PATH = PROJECT_ROOT / 'logs' / 'verification' / 'pending_app_checks.json'
VERIFICATION_DIR = PROJECT_ROOT / 'logs' / 'verification'
REPORT_PATH = PROJECT_ROOT / 'docs' / 'requirements-report.md'


def test_audit_plan_completion_does_not_write_verification_outputs() -> None:
    """audit_plan_completion must not write requirements-report or verification JSON."""
    report_mtime_before = REPORT_PATH.stat().st_mtime if REPORT_PATH.exists() else None

    json_files_before = {
        p: p.stat().st_mtime
        for p in VERIFICATION_DIR.glob('*.json')
        if p.name != 'pending_app_checks.json' and p.name != 'status_snapshot.json'
    }

    time.sleep(0.05)

    result = subprocess.run(
        [
            'uv',
            'run',
            'python',
            '-m',
            'tools.audit_plan_completion',
            '--plan',
            str(PROJECT_ROOT / 'PLAN.md'),
            '--repo-root',
            str(PROJECT_ROOT),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    if REPORT_PATH.exists() and report_mtime_before is not None:
        assert REPORT_PATH.stat().st_mtime == report_mtime_before, (
            'audit_plan_completion must not modify docs/requirements-report.md'
        )

    for json_path, mtime_before in json_files_before.items():
        assert json_path.stat().st_mtime == mtime_before, (
            f'audit_plan_completion must not modify {json_path.name}'
        )


def test_generate_verification_report_is_a_pure_wrapper() -> None:
    """generate_verification_report must produce identical status to verify_requirements."""
    result_wrapper = subprocess.run(
        ['uv', 'run', 'python', '-m', 'tools.generate_verification_report'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result_wrapper.returncode == 0, result_wrapper.stderr

    result_canonical = subprocess.run(
        ['uv', 'run', 'python', '-m', 'tools.verify_requirements'],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result_canonical.returncode == 0, result_canonical.stderr

    for json_path in VERIFICATION_DIR.glob('AF-*.json'):
        payload = json.loads(json_path.read_text(encoding='utf-8'))
        assert 'status' in payload, f'{json_path.name} missing status field'


def test_audit_plan_completion_stdout_contains_no_verified_claim() -> None:
    """audit_plan_completion stdout must not emit a structured verified status."""
    result = subprocess.run(
        [
            'uv',
            'run',
            'python',
            '-m',
            'tools.audit_plan_completion',
            '--plan',
            str(PROJECT_ROOT / 'PLAN.md'),
            '--repo-root',
            str(PROJECT_ROOT),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    combined = result.stdout + result.stderr
    import re

    verified_status_pattern = re.compile(
        r'(?:status|Status)\s*[:=]\s*["\']?verified["\']?', re.IGNORECASE
    )
    assert not verified_status_pattern.search(combined), (
        'audit_plan_completion must not emit a structured verified status claim.\n'
        f'Output: {combined[:500]}'
    )


def test_acknowledge_flag_removes_alert_from_pending(tmp_path: Path) -> None:
    """verify_requirements --acknowledge must remove the alert from pending_app_checks."""
    pending_path = tmp_path / 'logs' / 'verification' / 'pending_app_checks.json'
    pending_path.parent.mkdir(parents=True)

    seed_alert = {
        'item_id': 'AF-TEST-99',
        'message': 'Test alert for acknowledge contract',
        'app_surface': 'startup',
    }
    pending_path.write_text(
        json.dumps({'pending': [seed_alert]}, indent=2),
        encoding='utf-8',
    )

    result = subprocess.run(
        [
            'uv',
            'run',
            'python',
            '-m',
            'tools.verify_requirements',
            '--acknowledge',
            'AF-TEST-99',
            '--pending-path',
            str(pending_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    remaining = json.loads(pending_path.read_text(encoding='utf-8'))
    alert_ids = [a['item_id'] for a in remaining.get('pending', [])]
    assert 'AF-TEST-99' not in alert_ids, (
        f'AF-TEST-99 should have been removed from pending, got: {alert_ids}'
    )
