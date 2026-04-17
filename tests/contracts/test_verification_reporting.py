from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_verify_requirements_generates_evidence_based_outputs(tmp_path: Path) -> None:
    """Full regrade outputs must be structurally valid; use tmp to avoid dirtying git."""
    out_dir = tmp_path / 'verification'
    report_path = tmp_path / 'requirements-report.md'
    evidence_path = tmp_path / 'verify-requirements-evidence.md'
    result = subprocess.run(
        [
            'uv',
            'run',
            'python',
            '-m',
            'tools.verify_requirements',
            '--results-dir',
            str(out_dir),
            '--report',
            str(report_path),
            '--evidence-index',
            str(evidence_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    report_text = report_path.read_text(encoding='utf-8')
    result_path = out_dir / 'AF-00-02b.json'
    pending_path = out_dir / 'pending_app_checks.json'

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


def test_parser_reads_canonical_metadata_from_plan() -> None:
    """Parser must read failure_modes, app_surface, developer_alert, and performance_claim
    directly from docs/PLAN.md — not from code defaults."""
    from aetherflow.core.verification_report import (
        _apply_repo_defaults,
        parse_plan_items,
    )

    plan_text = (PROJECT_ROOT / 'docs' / 'PLAN.md').read_text(encoding='utf-8')
    items = _apply_repo_defaults(parse_plan_items(plan_text))
    by_id = {item.item_id: item for item in items}

    # Every active item must have failure_modes from the plan, not from defaults
    active = [item for item in items if item.lifecycle_state != 'retired']
    missing_failure_modes = [item.item_id for item in active if not item.failure_modes]
    assert not missing_failure_modes, (
        f'Active items with no failure_modes (check docs/PLAN.md): {missing_failure_modes}'
    )

    # App-testable items must surface their app_surface from the plan
    app_testable_items = {'AF-01-02', 'AF-02-02', 'AF-04-02'}
    for item_id in app_testable_items:
        item = by_id[item_id]
        assert item.app_surface, f'{item_id}: app_surface not parsed from docs/PLAN.md'
        assert item.developer_alert, (
            f'{item_id}: developer_alert not parsed from docs/PLAN.md'
        )

    # Performance-claim items must be flagged
    assert by_id['AF-03-01'].performance_claim, 'AF-03-01: performance_claim not parsed'
    assert by_id['AF-03-02'].performance_claim, 'AF-03-02: performance_claim not parsed'

    # Non-performance items must not be incorrectly flagged
    assert not by_id['AF-01-01'].performance_claim, (
        'AF-01-01: performance_claim must be False'
    )


def test_parser_reads_performance_threshold_fields_from_plan() -> None:
    """Performance-Threshold, Performance-Evidence-Type, and Performance-Evidence-Location
    must be parsed from docs/PLAN.md for Performance-Claim: true items."""
    from aetherflow.core.verification_report import parse_plan_items

    plan_text = (PROJECT_ROOT / 'docs' / 'PLAN.md').read_text(encoding='utf-8')
    items = parse_plan_items(plan_text)
    by_id = {item.item_id: item for item in items}

    af0301 = by_id['AF-03-01']
    assert af0301.performance_threshold, 'AF-03-01: performance_threshold not parsed'
    assert af0301.performance_evidence_type, (
        'AF-03-01: performance_evidence_type not parsed'
    )
    assert af0301.performance_evidence_location, (
        'AF-03-01: performance_evidence_location not parsed'
    )

    af0302 = by_id['AF-03-02']
    assert af0302.performance_threshold, 'AF-03-02: performance_threshold not parsed'
    assert af0302.performance_evidence_type, (
        'AF-03-02: performance_evidence_type not parsed'
    )
    assert af0302.performance_evidence_location, (
        'AF-03-02: performance_evidence_location not parsed'
    )


def test_performance_gate_missing_artifact_yields_evidenced(tmp_path: Path) -> None:
    """A performance-claim item with no performance artifacts in the evidence pack
    must be blocked at evidenced with a missing-proof gap."""
    from aetherflow.core.verification_report import PlanItem, evaluate_plan_item

    pack = tmp_path / 'docs' / 'evidence' / 'AF-99-01.md'
    pack.parent.mkdir(parents=True)
    pack.write_text(
        '# AF-99-01 Evidence Pack\n\n'
        '- Reviewer Status: approved\n'
        '- Reviewer: qa.lead\n'
        '- Reviewed At: 2026-03-27T00:00:00Z\n'
        '- App-Testable: no\n\n'
        '## Acceptance Criteria\n\n'
        '- AC1: 60 FPS sustained.\n\n'
        '## Proof Matrix\n\n'
        '| Criterion | Proof Type | Evidence | Entry Point | Failure Coverage |\n'
        '| --- | --- | --- | --- | --- |\n'
        '| AC1 | integration | tests/foo.py | capture | drop rejected |\n\n'
        '## Sign-Off\n\n'
        '- Status: approved\n',
        encoding='utf-8',
    )
    (tmp_path / 'src').mkdir()

    item = PlanItem(
        item_id='AF-99-01',
        title='Fake item',
        targets=[],
        validations=[],
        evidence_pack=pack.relative_to(tmp_path),
        feature_class='service',
        entry_point='capture',
        required_proofs=['integration'],
        failure_modes=['drop rejected'],
        acceptance_criteria=['AC1'],
        performance_claim=True,
        performance_threshold='60 FPS sustained',
        performance_evidence_type='sustained-drop-detection',
        performance_evidence_location='tests/foo.py',
    )
    result = evaluate_plan_item(repo_root=tmp_path, item=item)
    assert result.status == 'evidenced'
    assert any('Missing performance proof' in g for g in result.gaps)


def test_performance_gate_fail_artifact_yields_evidenced(tmp_path: Path) -> None:
    """A performance-claim item whose evidence pack has a Pass-Fail: fail artifact
    must be blocked at evidenced with a threshold-not-met gap."""
    from aetherflow.core.verification_report import PlanItem, evaluate_plan_item

    pack = tmp_path / 'docs' / 'evidence' / 'AF-99-02.md'
    pack.parent.mkdir(parents=True)
    pack.write_text(
        '# AF-99-02 Evidence Pack\n\n'
        '- Reviewer Status: approved\n'
        '- Reviewer: qa.lead\n'
        '- Reviewed At: 2026-03-27T00:00:00Z\n'
        '- App-Testable: no\n\n'
        '## Acceptance Criteria\n\n'
        '- AC1: 120 FPS validated path.\n\n'
        '## Proof Matrix\n\n'
        '| Criterion | Proof Type | Evidence | Entry Point | Failure Coverage |\n'
        '| --- | --- | --- | --- | --- |\n'
        '| AC1 | integration | tests/foo.py | capture | premium backend blocked |\n\n'
        '## Performance Artifacts\n\n'
        '- Artifact-Path: tests/foo.py::test_fps\n'
        '- Measured-Value: capability-enumeration only\n'
        '- Threshold: 120 FPS sustained throughput\n'
        '- Pass-Fail: fail\n\n'
        '## Sign-Off\n\n'
        '- Status: approved\n',
        encoding='utf-8',
    )

    item = PlanItem(
        item_id='AF-99-02',
        title='Fake item 2',
        targets=[],
        validations=[],
        evidence_pack=pack.relative_to(tmp_path),
        feature_class='service',
        entry_point='capture',
        required_proofs=['integration'],
        failure_modes=['premium backend blocked'],
        acceptance_criteria=['AC1'],
        performance_claim=True,
        performance_threshold='120 FPS validated path',
        performance_evidence_type='capability-enumeration',
        performance_evidence_location='tests/foo.py',
    )
    result = evaluate_plan_item(repo_root=tmp_path, item=item)
    assert result.status == 'evidenced'
    assert any('Performance threshold not met' in g for g in result.gaps)


def test_performance_gate_all_pass_artifacts_can_verify(tmp_path: Path) -> None:
    """A performance-claim item with all Pass-Fail: pass artifacts and an approved
    sign-off must be eligible for verified status."""
    from aetherflow.core.verification_report import PlanItem, evaluate_plan_item

    pack = tmp_path / 'docs' / 'evidence' / 'AF-99-03.md'
    pack.parent.mkdir(parents=True)
    pack.write_text(
        '# AF-99-03 Evidence Pack\n\n'
        '- Reviewer Status: approved\n'
        '- Reviewer: qa.lead\n'
        '- Reviewed At: 2026-03-27T00:00:00Z\n'
        '- App-Testable: no\n\n'
        '## Acceptance Criteria\n\n'
        '- AC1: 60 FPS sustained.\n\n'
        '## Proof Matrix\n\n'
        '| Criterion | Proof Type | Evidence | Entry Point | Failure Coverage |\n'
        '| --- | --- | --- | --- | --- |\n'
        '| AC1 | integration | tests/foo.py | capture | drop rejected |\n\n'
        '## Performance Artifacts\n\n'
        '- Artifact-Path: tests/foo.py::test_sustained_drop\n'
        '- Measured-Value: measured_fps=50.0 < target_fps=60\n'
        '- Threshold: 60 FPS sustained\n'
        '- Pass-Fail: pass\n\n'
        '## Sign-Off\n\n'
        '- Status: approved\n',
        encoding='utf-8',
    )

    item = PlanItem(
        item_id='AF-99-03',
        title='Fake item 3',
        targets=[],
        validations=[],
        evidence_pack=pack.relative_to(tmp_path),
        feature_class='service',
        entry_point='capture',
        required_proofs=['integration'],
        failure_modes=['drop rejected'],
        acceptance_criteria=['AC1'],
        performance_claim=True,
        performance_threshold='60 FPS sustained',
        performance_evidence_type='sustained-drop-detection',
        performance_evidence_location='tests/foo.py',
    )
    result = evaluate_plan_item(repo_root=tmp_path, item=item)
    assert result.status == 'verified'
    assert not result.gaps


def test_no_active_item_promoted_by_metadata_defaults() -> None:
    """No active item should pass the metadata gap check via hardcoded defaults.
    All required fields must be present in docs/PLAN.md itself."""
    from aetherflow.core.verification_report import (
        _collect_metadata_gaps,
        parse_plan_items,
    )

    # Parse without applying any defaults at all
    plan_text = (PROJECT_ROOT / 'docs' / 'PLAN.md').read_text(encoding='utf-8')
    items_raw = parse_plan_items(plan_text)

    active_raw = [item for item in items_raw if item.lifecycle_state != 'retired']
    failures = []
    for item in active_raw:
        gaps = _collect_metadata_gaps(item)
        if gaps:
            failures.append(f'{item.item_id}: {gaps}')

    assert not failures, (
        'Active items have metadata gaps in docs/PLAN.md (must be fixed in plan, not in code):\n'
        + '\n'.join(failures)
    )


def test_all_active_af_items_have_complete_required_metadata() -> None:
    """Every active AF item must declare all required metadata fields in docs/PLAN.md."""
    from aetherflow.core.verification_report import (
        _apply_repo_defaults,
        parse_plan_items,
    )

    plan_text = (PROJECT_ROOT / 'docs' / 'PLAN.md').read_text(encoding='utf-8')
    items = _apply_repo_defaults(parse_plan_items(plan_text))
    active = [item for item in items if item.lifecycle_state != 'retired']

    failures: list[str] = []
    for item in active:
        missing: list[str] = []
        if not item.feature_class:
            missing.append('feature_class')
        if not item.entry_point:
            missing.append('entry_point')
        if not item.required_proofs:
            missing.append('required_proofs')
        if not item.failure_modes:
            missing.append('failure_modes')
        if not item.acceptance_criteria:
            missing.append('acceptance_criteria')
        if item.performance_claim:
            if not item.performance_threshold:
                missing.append('performance_threshold')
            if not item.performance_evidence_type:
                missing.append('performance_evidence_type')
            if not item.performance_evidence_location:
                missing.append('performance_evidence_location')
        if missing:
            failures.append(f'{item.item_id}: missing {missing}')

    assert not failures, (
        'Active AF items missing required metadata in docs/PLAN.md:\n'
        + '\n'.join(failures)
    )
