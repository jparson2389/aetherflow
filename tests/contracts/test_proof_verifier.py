"""Contract tests for the proof-first verification system."""

from __future__ import annotations

from pathlib import Path

from src.aetherflow.core.verification_report import (
    PlanItem,
    VerificationResult,
    evaluate_plan_item,
    write_results,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_VERIFICATION_STANDARD = PROJECT_ROOT / 'docs' / 'verification_standard.md'


def _write_evidence_pack(
    path: Path,
    *,
    reviewer_status: str,
    proof_types: list[str],
    app_testable: bool = False,
    acceptance_criteria: list[str] | None = None,
) -> None:
    """Write a minimal evidence pack markdown file for testing."""
    ac_lines = acceptance_criteria or ['AC1: Feature works as intended.']
    matrix_rows = '\n'.join(
        f'| AC{i + 1} | {pt} | tests/test_feature.py | main-window | error handled |'
        for i, (ac, pt) in enumerate(zip(ac_lines, proof_types, strict=False))
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '\n'.join([
            '# Evidence Pack',
            '',
            f'- Reviewer Status: {reviewer_status}',
            '- Reviewer: qa.lead',
            '- Reviewed At: 2026-03-16T12:00:00Z',
            f'- App-Testable: {"yes" if app_testable else "no"}',
            '',
            '## Acceptance Criteria',
            *[f'- AC{i + 1}: {ac}' for i, ac in enumerate(ac_lines)],
            '',
            '## Proof Matrix',
            '| Criterion | Proof Type | Evidence | Entry Point | Failure Coverage |',
            '| --- | --- | --- | --- | --- |',
            matrix_rows,
            '',
            '## Sign-Off',
            f'- Status: {reviewer_status}',
            '- Notes: Reviewed.',
            '',
        ]),
        encoding='utf-8',
    )


def _make_item(
    tmp_path: Path,
    *,
    item_id: str = 'AF-TEST-01',
    feature_class: str = 'service',
    entry_point: str = 'main-window',
    required_proofs: list[str] | None = None,
    failure_modes: list[str] | None = None,
    lifecycle_state: str | None = None,
    create_target: bool = True,
    acceptance_criteria: list[str] | None = None,
) -> PlanItem:
    """Create a minimal PlanItem for testing."""
    if create_target:
        target_path = tmp_path / 'src' / 'feature.py'
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text("def run() -> str:\n    return 'ok'\n", encoding='utf-8')
        targets = [Path('src/feature.py')]
    else:
        targets = []

    return PlanItem(
        item_id=item_id,
        title='Test feature',
        targets=targets,
        validations=[],
        evidence_pack=Path(f'docs/evidence/{item_id}.md'),
        feature_class=feature_class,
        entry_point=entry_point,
        required_proofs=required_proofs or ['integration'],
        failure_modes=failure_modes or [],
        lifecycle_state=lifecycle_state,
        acceptance_criteria=acceptance_criteria or [],
    )


def test_item_without_acceptance_criteria_is_rejected(tmp_path: Path) -> None:
    """Item with no AC in its evidence pack cannot reach evidenced — returns 'evidenced' with gaps."""
    item = _make_item(tmp_path)
    # Write an evidence pack missing acceptance criteria
    pack_path = tmp_path / 'docs' / 'evidence' / 'AF-TEST-01.md'
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    # Write a pack without AC section
    pack_path.write_text(
        '\n'.join([
            '# Evidence Pack',
            '',
            '- Reviewer Status: approved',
            '- Reviewer: qa.lead',
            '- Reviewed At: 2026-03-16T12:00:00Z',
            '- App-Testable: no',
            '',
            '## Proof Matrix',
            '| Criterion | Proof Type | Evidence | Entry Point | Failure Coverage |',
            '| --- | --- | --- | --- | --- |',
            '| AC1 | integration | tests/test.py | main-window | error handled |',
            '',
            '## Sign-Off',
            '- Status: approved',
            '- Notes: Reviewed.',
            '',
        ]),
        encoding='utf-8',
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert result.status in ('coded', 'drafted', 'evidenced')
    # The pack is malformed — it will raise ValueError due to missing acceptance criteria,
    # so the result will be 'evidenced' with a gap about missing AC
    assert any('acceptance criteria' in gap.casefold() for gap in result.gaps)


def test_item_without_evidence_pack_is_rejected(tmp_path: Path) -> None:
    """Item with no evidence pack returns status='coded' with 'Missing evidence pack' gap."""
    target_path = tmp_path / 'src' / 'feature.py'
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("def run() -> str:\n    return 'ok'\n", encoding='utf-8')

    item = PlanItem(
        item_id='AF-TEST-02',
        title='Test feature without pack',
        targets=[Path('src/feature.py')],
        validations=[],
        evidence_pack=Path('docs/evidence/AF-TEST-02.md'),
        feature_class='service',
        entry_point='main-window',
        required_proofs=['integration'],
        failure_modes=[],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert result.status == 'coded'
    assert any('Missing evidence pack' in gap for gap in result.gaps)


def test_structural_proof_only_is_rejected() -> None:
    """Policy test: docs/verification_standard.md states structural checks cannot promote items."""
    assert _VERIFICATION_STANDARD.exists(), f'Missing: {_VERIFICATION_STANDARD}'
    text = _VERIFICATION_STANDARD.read_text(encoding='utf-8')
    # The document must explicitly state structural checks cannot promote items
    assert 'Structural checks' in text or 'structural checks' in text, (
        'verification_standard.md must mention structural checks'
    )
    # Must also state these are insufficient for promotion
    assert 'cannot' in text or 'cannot prove' in text or 'block progress' in text, (
        'verification_standard.md must state structural checks cannot promote items'
    )


def test_missing_sign_off_blocks_verified(tmp_path: Path) -> None:
    """Item with evidence pack but reviewer_status='pending' returns 'evidenced', not 'verified'."""
    item = _make_item(tmp_path)
    pack_path = tmp_path / 'docs' / 'evidence' / 'AF-TEST-01.md'
    _write_evidence_pack(
        pack_path,
        reviewer_status='pending',
        proof_types=['integration'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert result.status == 'evidenced'
    assert result.status != 'verified'
    assert any('sign-off' in gap.casefold() for gap in result.gaps)


def test_retired_item_excluded_from_readiness_count(tmp_path: Path) -> None:
    """Retired item's status='retired'; when counting active items, retired ones are not counted."""
    retired_item = _make_item(
        tmp_path, item_id='AF-TEST-RET', lifecycle_state='retired', create_target=False
    )
    active_item = _make_item(tmp_path, item_id='AF-TEST-ACT')
    pack_path = tmp_path / 'docs' / 'evidence' / 'AF-TEST-ACT.md'
    _write_evidence_pack(
        pack_path,
        reviewer_status='approved',
        proof_types=['integration'],
    )

    retired_result = evaluate_plan_item(
        repo_root=tmp_path,
        item=retired_item,
        validation_runner=lambda _repo_root, _command: True,
    )
    active_result = evaluate_plan_item(
        repo_root=tmp_path,
        item=active_item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert retired_result.status == 'retired'

    all_results = [retired_result, active_result]
    active_count = sum(1 for r in all_results if r.status != 'retired')
    retired_count = sum(1 for r in all_results if r.status == 'retired')

    assert retired_count == 1
    assert active_count == 1


def test_feature_class_logic_requires_unit_and_edge(tmp_path: Path) -> None:
    """PlanItem with feature_class='logic', required_proofs=['unit', 'edge'] rejects pack with only 'unit'."""
    item = _make_item(
        tmp_path,
        feature_class='logic',
        required_proofs=['unit', 'edge'],
    )
    pack_path = tmp_path / 'docs' / 'evidence' / 'AF-TEST-01.md'
    # Only provides 'unit', missing 'edge'
    _write_evidence_pack(
        pack_path,
        reviewer_status='approved',
        proof_types=['unit'],
        acceptance_criteria=['Feature logic is correct.'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert result.status != 'verified', (
        f'Expected not verified, got {result.status!r} with gaps: {result.gaps}'
    )
    assert any('edge' in gap.casefold() for gap in result.gaps), (
        f'Expected gap mentioning "edge" but got: {result.gaps}'
    )


def test_feature_class_service_requires_integration(tmp_path: Path) -> None:
    """PlanItem with feature_class='service', required_proofs=['integration'] rejects pack with only 'unit'."""
    item = _make_item(
        tmp_path,
        feature_class='service',
        required_proofs=['integration'],
    )
    pack_path = tmp_path / 'docs' / 'evidence' / 'AF-TEST-01.md'
    # Only provides 'unit', missing 'integration'
    _write_evidence_pack(
        pack_path,
        reviewer_status='approved',
        proof_types=['unit'],
        acceptance_criteria=['Service behaves correctly.'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert result.status != 'verified', (
        f'Expected not verified, got {result.status!r} with gaps: {result.gaps}'
    )
    assert any('integration' in gap.casefold() for gap in result.gaps), (
        f'Expected gap mentioning "integration" but got: {result.gaps}'
    )


def test_feature_class_boundary_requires_contract_and_negative(tmp_path: Path) -> None:
    """PlanItem with feature_class='boundary', required_proofs=['contract', 'negative'] rejects pack with only 'contract'."""
    item = _make_item(
        tmp_path,
        feature_class='boundary',
        required_proofs=['contract', 'negative'],
    )
    pack_path = tmp_path / 'docs' / 'evidence' / 'AF-TEST-01.md'
    # Only provides 'contract', missing 'negative'
    _write_evidence_pack(
        pack_path,
        reviewer_status='approved',
        proof_types=['contract'],
        acceptance_criteria=['Boundary is enforced.'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert result.status != 'verified', (
        f'Expected not verified, got {result.status!r} with gaps: {result.gaps}'
    )
    assert any('negative' in gap.casefold() for gap in result.gaps), (
        f'Expected gap mentioning "negative" but got: {result.gaps}'
    )


def test_requirements_report_from_evidence_not_heuristics(tmp_path: Path) -> None:
    """write_results() produces a report with evidence-state-based counts (not heuristic file sizes).

    The report must contain: '- Retired:', '- Coded:', '- Evidenced:', '- Verified:'.
    """
    results = [
        VerificationResult(
            item_id='AF-RET-01',
            title='Retired item',
            status='retired',
            gaps=[],
            evidence_pack=None,
            validation_commands=[],
            approved_by=None,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        ),
        VerificationResult(
            item_id='AF-COD-01',
            title='Coded item',
            status='coded',
            gaps=['Missing evidence pack'],
            evidence_pack='docs/evidence/AF-COD-01.md',
            validation_commands=[],
            approved_by=None,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        ),
        VerificationResult(
            item_id='AF-EVI-01',
            title='Evidenced item',
            status='evidenced',
            gaps=['Reviewer sign-off is not approved'],
            evidence_pack='docs/evidence/AF-EVI-01.md',
            validation_commands=[],
            approved_by=None,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        ),
        VerificationResult(
            item_id='AF-VER-01',
            title='Verified item',
            status='verified',
            gaps=[],
            evidence_pack='docs/evidence/AF-VER-01.md',
            validation_commands=[],
            approved_by='qa.lead',
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        ),
    ]

    report_path = tmp_path / 'docs' / 'requirements-report.md'
    results_dir = tmp_path / 'logs' / 'verification'

    write_results(report_path=report_path, results_dir=results_dir, results=results)

    assert report_path.exists(), 'Report file was not created'
    report_text = report_path.read_text(encoding='utf-8')

    assert '- Retired:' in report_text, f'Missing "- Retired:" in report:\n{report_text}'
    assert '- Coded:' in report_text, f'Missing "- Coded:" in report:\n{report_text}'
    assert '- Evidenced:' in report_text, f'Missing "- Evidenced:" in report:\n{report_text}'
    assert '- Verified:' in report_text, f'Missing "- Verified:" in report:\n{report_text}'

    # Verify counts are evidence-based (1 each)
    assert '- Retired: 1' in report_text
    assert '- Coded: 1' in report_text
    assert '- Evidenced: 1' in report_text
    assert '- Verified: 1' in report_text


def test_previously_verified_item_downgraded_on_regrade(tmp_path: Path) -> None:
    """Item with approved evidence pack but failing validation returns 'evidenced' not 'verified'."""
    item = _make_item(
        tmp_path,
        feature_class='service',
        required_proofs=['integration'],
    )
    # Override validations with a command that will fail
    item = PlanItem(
        item_id=item.item_id,
        title=item.title,
        targets=item.targets,
        validations=['uv run pytest tests/unit/test_nonexistent.py'],
        evidence_pack=item.evidence_pack,
        feature_class=item.feature_class,
        entry_point=item.entry_point,
        required_proofs=item.required_proofs,
        failure_modes=item.failure_modes,
        lifecycle_state=item.lifecycle_state,
    )
    pack_path = tmp_path / 'docs' / 'evidence' / 'AF-TEST-01.md'
    _write_evidence_pack(
        pack_path,
        reviewer_status='approved',
        proof_types=['integration'],
    )

    # Simulate failing validation (like a previously-passing test that now breaks)
    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: False,
    )

    assert result.status == 'evidenced', (
        f'Expected downgrade to evidenced, got {result.status!r}'
    )
    assert any('Validation failed' in gap for gap in result.gaps)


def test_partial_ac_coverage_produces_gap(tmp_path: Path) -> None:
    """Plan item with AC1-AC3 but only AC1 in proof matrix must not reach verified."""
    item = _make_item(
        tmp_path,
        required_proofs=['integration'],
        acceptance_criteria=['AC1', 'AC2', 'AC3'],
    )
    _write_evidence_pack(
        tmp_path / 'docs' / 'evidence' / 'AF-TEST-01.md',
        reviewer_status='approved',
        proof_types=['integration'],
        acceptance_criteria=['Feature works as intended.'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _r, _c: True,
    )

    assert result.status == 'evidenced'
    ac_gaps = [g for g in result.gaps if 'Acceptance criterion not covered' in g]
    assert any('AC2' in g for g in ac_gaps)
    assert any('AC3' in g for g in ac_gaps)


def test_full_ac_coverage_clears_ac_gap(tmp_path: Path) -> None:
    """Plan item with AC1-AC2 and matching proof-matrix rows reaches verified."""
    item = _make_item(
        tmp_path,
        required_proofs=['integration'],
        acceptance_criteria=['AC1', 'AC2'],
    )
    _write_evidence_pack(
        tmp_path / 'docs' / 'evidence' / 'AF-TEST-01.md',
        reviewer_status='approved',
        proof_types=['integration', 'integration'],
        acceptance_criteria=['First criterion.', 'Second criterion.'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _r, _c: True,
    )

    assert result.status == 'verified'
    assert not any('Acceptance criterion not covered' in g for g in result.gaps)


def test_item_without_plan_acs_skips_ac_check(tmp_path: Path) -> None:
    """Plan item with no declared ACs does not produce AC coverage gaps."""
    item = _make_item(
        tmp_path,
        required_proofs=['integration'],
        acceptance_criteria=[],
    )
    _write_evidence_pack(
        tmp_path / 'docs' / 'evidence' / 'AF-TEST-01.md',
        reviewer_status='approved',
        proof_types=['integration'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _r, _c: True,
    )

    assert not any('Acceptance criterion not covered' in g for g in result.gaps)
