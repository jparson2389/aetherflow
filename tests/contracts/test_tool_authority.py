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
    report_existed_before = REPORT_PATH.exists()
    report_mtime_before = REPORT_PATH.stat().st_mtime if report_existed_before else None

    json_files_before = {
        p: p.stat().st_mtime
        for p in VERIFICATION_DIR.glob('*.json')
        if p.name != 'pending_app_checks.json' and p.name != 'status_snapshot.json'
    }
    json_names_before = {p.name for p in json_files_before}

    time.sleep(0.05)

    result = subprocess.run(
        [
            'uv',
            'run',
            'python',
            '-m',
            'tools.audit_plan_completion',
            '--plan',
            str(PROJECT_ROOT / 'docs' / 'PLAN.md'),
            '--repo-root',
            str(PROJECT_ROOT),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    assert REPORT_PATH.exists() == report_existed_before, (
        'audit_plan_completion must not create docs/requirements-report.md'
    )
    if REPORT_PATH.exists() and report_mtime_before is not None:
        assert REPORT_PATH.stat().st_mtime == report_mtime_before, (
            'audit_plan_completion must not modify docs/requirements-report.md'
        )

    for json_path, mtime_before in json_files_before.items():
        assert json_path.stat().st_mtime == mtime_before, (
            f'audit_plan_completion must not modify {json_path.name}'
        )

    json_names_after = {
        p.name
        for p in VERIFICATION_DIR.glob('*.json')
        if p.name != 'pending_app_checks.json' and p.name != 'status_snapshot.json'
    }
    new_json_names = json_names_after - json_names_before
    assert not new_json_names, (
        f'audit_plan_completion must not create new verification JSON files: {sorted(new_json_names)}'
    )


def test_generate_verification_report_is_a_pure_wrapper(tmp_path: Path) -> None:
    """generate_verification_report must produce identical status to verify_requirements."""
    wrapper_dir = tmp_path / 'wrapper'
    canonical_dir = tmp_path / 'canonical'
    wrapper_report = wrapper_dir / 'requirements-report.md'
    canonical_report = canonical_dir / 'requirements-report.md'
    canonical_evidence = canonical_dir / 'verify-requirements-evidence.md'

    result_wrapper = subprocess.run(
        [
            'uv',
            'run',
            'python',
            '-m',
            'tools.generate_verification_report',
            '--results-dir',
            str(wrapper_dir),
            '--report',
            str(wrapper_report),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result_wrapper.returncode == 0, result_wrapper.stderr

    result_canonical = subprocess.run(
        [
            'uv',
            'run',
            'python',
            '-m',
            'tools.verify_requirements',
            '--results-dir',
            str(canonical_dir),
            '--report',
            str(canonical_report),
            '--evidence-index',
            str(canonical_evidence),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result_canonical.returncode == 0, result_canonical.stderr

    wrapper_jsons = sorted(wrapper_dir.glob('AF-*.json'))
    canonical_jsons = sorted(canonical_dir.glob('AF-*.json'))
    assert [p.name for p in wrapper_jsons] == [p.name for p in canonical_jsons], (
        'wrapper and canonical runs must emit the same AF-*.json filenames'
    )

    for w_path, c_path in zip(wrapper_jsons, canonical_jsons, strict=True):
        w_payload = json.loads(w_path.read_text(encoding='utf-8'))
        c_payload = json.loads(c_path.read_text(encoding='utf-8'))
        assert 'status' in w_payload, f'{w_path.name} missing status field'
        assert w_payload['status'] == c_payload['status'], (
            f'status mismatch for {w_path.name}: wrapper={w_payload["status"]!r} '
            f'canonical={c_payload["status"]!r}'
        )


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
            str(PROJECT_ROOT / 'docs' / 'PLAN.md'),
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


def test_acknowledge_flag_missing_alert_returns_error(tmp_path: Path) -> None:
    """verify_requirements --acknowledge must fail when no alert matches."""
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
            'AF-TEST-404',
            '--pending-path',
            str(pending_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0, 'Missing alert acknowledge should return non-zero.'
    combined = (result.stdout or '') + (result.stderr or '')
    assert 'No pending alert found to acknowledge' in combined

    remaining = json.loads(pending_path.read_text(encoding='utf-8'))
    alert_ids = [a['item_id'] for a in remaining.get('pending', [])]
    assert 'AF-TEST-99' in alert_ids, (
        f'AF-TEST-99 should remain pending, got: {alert_ids}'
    )
