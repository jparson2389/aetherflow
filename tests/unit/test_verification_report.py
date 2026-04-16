from __future__ import annotations

from pathlib import Path

from src.aetherflow.core.verification_report import (
    PlanItem,
    VerificationResult,
    evaluate_plan_item,
)


def _write_evidence_pack(
    path: Path,
    *,
    reviewer_status: str,
    app_testable: bool = False,
) -> None:
    path.write_text(
        '\n'.join(
            [
                '# Evidence Pack',
                '',
                '- Reviewer Status: ' + reviewer_status,
                '- Reviewer: qa.lead',
                '- Reviewed At: 2026-03-16T12:00:00Z',
                '- App-Testable: ' + ('yes' if app_testable else 'no'),
                '- App Surface: main-window',
                '- Developer Alert: New feature added, check for functionality',
                '',
                '## Acceptance Criteria',
                '- AC1: Feature is reachable from its intended entry point.',
                '',
                '## Proof Matrix',
                '| Criterion | Proof Type | Evidence | Entry Point | Failure Coverage |',
                '| --- | --- | --- | --- | --- |',
                (
                    '| AC1 | integration | tests/integration/test_feature.py | '
                    'main-window | invalid configuration rejected |'
                ),
                '',
                '## Sign-Off',
                '- Status: ' + reviewer_status,
                '- Notes: Reviewed.',
                '',
            ]
        ),
        encoding='utf-8',
    )


def test_item_without_evidence_pack_is_coded(tmp_path: Path) -> None:
    target_path = tmp_path / 'src' / 'feature.py'
    target_path.parent.mkdir(parents=True)
    target_path.write_text("def run() -> str:\n    return 'ok'\n", encoding='utf-8')

    item = PlanItem(
        item_id='AF-10-01',
        title='Example item',
        targets=[Path('src/feature.py')],
        validations=['uv run pytest tests/unit/test_example.py'],
        evidence_pack=Path('docs/evidence/AF-10-01.md'),
        feature_class='service',
        entry_point='main-window',
        required_proofs=['integration'],
        failure_modes=['invalid configuration rejected'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert result.status == 'coded'
    assert 'Missing evidence pack' in result.gaps[0]


def test_item_with_unsigned_evidence_pack_is_evidenced(tmp_path: Path) -> None:
    target_path = tmp_path / 'src' / 'feature.py'
    target_path.parent.mkdir(parents=True)
    target_path.write_text("def run() -> str:\n    return 'ok'\n", encoding='utf-8')
    evidence_path = tmp_path / 'docs' / 'evidence' / 'AF-10-01.md'
    evidence_path.parent.mkdir(parents=True)
    _write_evidence_pack(evidence_path, reviewer_status='pending')

    item = PlanItem(
        item_id='AF-10-01',
        title='Example item',
        targets=[Path('src/feature.py')],
        validations=['uv run pytest tests/unit/test_example.py'],
        evidence_pack=Path('docs/evidence/AF-10-01.md'),
        feature_class='service',
        entry_point='main-window',
        required_proofs=['integration'],
        failure_modes=['invalid configuration rejected'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert result.status == 'evidenced'
    assert 'Reviewer sign-off is not approved' in result.gaps[0]


def test_item_with_approved_evidence_pack_and_validation_is_verified(
    tmp_path: Path,
) -> None:
    target_path = tmp_path / 'src' / 'feature.py'
    target_path.parent.mkdir(parents=True)
    target_path.write_text("def run() -> str:\n    return 'ok'\n", encoding='utf-8')
    evidence_path = tmp_path / 'docs' / 'evidence' / 'AF-10-01.md'
    evidence_path.parent.mkdir(parents=True)
    _write_evidence_pack(evidence_path, reviewer_status='approved', app_testable=True)

    item = PlanItem(
        item_id='AF-10-01',
        title='Example item',
        targets=[Path('src/feature.py')],
        validations=['uv run pytest tests/unit/test_example.py'],
        evidence_pack=Path('docs/evidence/AF-10-01.md'),
        feature_class='service',
        entry_point='main-window',
        required_proofs=['integration'],
        failure_modes=['invalid configuration rejected'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert isinstance(result, VerificationResult)
    assert result.status == 'verified'
    assert result.app_testable is True
    assert result.developer_alert == 'New feature added, check for functionality'


def test_item_can_be_retired_without_evidence_pack(tmp_path: Path) -> None:
    item = PlanItem(
        item_id='AF-00-01',
        title='Legacy bootstrap item',
        targets=[Path('docs/obsolete.md')],
        validations=[],
        evidence_pack=None,
        feature_class='workflow',
        entry_point='docs',
        required_proofs=[],
        failure_modes=[],
        lifecycle_state='retired',
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )

    assert result.status == 'retired'
    assert result.gaps == []


def test_verified_payload_includes_validation_exit_codes_and_requirement_links(
    tmp_path: Path,
) -> None:
    target_path = tmp_path / 'src' / 'feature.py'
    target_path.parent.mkdir(parents=True)
    target_path.write_text("def run() -> str:\n    return 'ok'\n", encoding='utf-8')

    evidence_path = tmp_path / 'docs' / 'evidence' / 'AF-10-03.md'
    evidence_path.parent.mkdir(parents=True)
    _write_evidence_pack(evidence_path, reviewer_status='approved', app_testable=False)

    item = PlanItem(
        item_id='AF-10-03',
        title='Validation payload coverage item',
        targets=[Path('src/feature.py')],
        validations=['uv run pytest tests/unit/test_example.py'],
        evidence_pack=Path('docs/evidence/AF-10-03.md'),
        feature_class='boundary',
        entry_point='capture control contract',
        required_proofs=['integration'],
        failure_modes=['invalid configuration rejected'],
        acceptance_criteria=['AC1', 'AC2'],
    )

    result = evaluate_plan_item(
        repo_root=tmp_path,
        item=item,
        validation_runner=lambda _repo_root, _command: True,
    )
    payload = result.to_payload()

    assert payload['validation_commands'] == [
        'uv run pytest tests/unit/test_example.py'
    ]
    assert payload['exit_codes'] == {'uv run pytest tests/unit/test_example.py': 0}
    assert payload['requirement_links'] == {
        'acceptance_criteria': ['AC1', 'AC2'],
        'required_failure_modes': ['invalid configuration rejected'],
    }
