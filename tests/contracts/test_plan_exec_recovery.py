import json
import re
from pathlib import Path

import pytest

from tools import plan_exec
from tools.apply_writes import capture_existing_file_snapshots, validate_writes_payload
from tools.validation_gate import (
    GateResult,
    ValidationReport,
    extract_target_files,
    extract_validation_command,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _legacy_work_item_id(phase: str, title: str) -> str:
    phase_token = re.sub(r'[^a-z0-9]+', '_', phase.lower()).strip('_') or 'item'
    title_token = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_') or 'item'
    return f'{phase_token}__{title_token}'


def test_work_item_id_is_stable_across_plan_reformat() -> None:
    inline_title = (
        '`AF-00-01` Canonicalize repo identity and self-contained docs. '
        '`PRD Refs:` `§1`, `§2`, `REQ-01`.'
    )
    short_title = '`AF-00-01` Canonicalize repo identity and self-contained docs.'

    assert plan_exec.extract_work_item_token(inline_title) == 'AF-00-01'
    assert plan_exec.work_item_id('Phase 0', inline_title) == 'af_00_01'
    assert plan_exec.work_item_id('Phase 0', short_title) == 'af_00_01'


def test_plan_reformat_produces_instruction_blocks_for_af_00_01() -> None:
    plan_text = (PROJECT_ROOT / 'docs' / 'PLAN.md').read_text(encoding='utf-8')
    items = {item.id: item for item in plan_exec.extract_phase_work_items(plan_text)}

    af_00_01 = items['af_00_01']

    assert af_00_01.instructions
    assert extract_target_files(af_00_01.instructions) == [
        'docs/PRD.md',
        'README.md',
        'AGENTS.md',
        'tests/contracts/test_canonical_identity.py',
        'tests/contracts/test_prd_execution_readiness.py',
    ]
    assert extract_validation_command(af_00_01.instructions) == (
        'uv run pytest '
        'tests/contracts/test_canonical_identity.py::'
        'test_canonical_package_root_is_aetherflow '
        'tests/contracts/test_canonical_identity.py::'
        'test_project_docs_reference_aetherflow_canonical_paths '
        'tests/contracts/test_prd_execution_readiness.py::'
        'test_prd_is_self_contained_and_citation_free'
    )


def test_load_or_initialize_plan_state_preserves_status_across_plan_reformat(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_path = tmp_path / 'plan_state.json'
    legacy_title = (
        '`AF-00-01` Canonicalize repo identity and self-contained docs. '
        '`PRD Refs:` `§1`, `§2`, `REQ-01`.'
    )
    state_path.write_text(
        json.dumps(
            {
                'version': 1,
                'updated_at': '2026-03-11T00:00:00',
                'items': [
                    {
                        'id': _legacy_work_item_id('Phase 0', legacy_title),
                        'phase': 'Phase 0',
                        'title': legacy_title,
                        'instructions': '',
                        'status': 'done',
                        'notes': 'Certified',
                        'updated_at': '2026-03-11T00:00:00',
                        'missing': [],
                        'evidence': ['docs/PRD.md'],
                    }
                ],
                'history': [],
            },
            indent=2,
        )
        + '\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(plan_exec, 'STATE_PATH', state_path)

    plan_items = plan_exec.extract_phase_work_items(
        '## Phase 0 - Canonical Identity And Execution Contracts\n\n'
        '- [ ] `AF-00-01` Canonicalize repo identity and self-contained docs.\n'
        '> **Target File:** `docs/PRD.md`\n'
    )
    state = plan_exec.load_or_initialize_plan_state(plan_items)

    assert state['items'][0]['id'] == 'af_00_01'
    assert state['items'][0]['status'] == 'done'
    assert state['items'][0]['notes'] == 'Certified'


def test_verified_status_counts_as_complete_for_progression() -> None:
    state = {
        'items': [
            {'id': 'af_00_01', 'phase': 'Phase 0', 'status': 'verified'},
            {'id': 'af_00_02a', 'phase': 'Phase 0', 'status': 'missing'},
            {'id': 'af_01_01', 'phase': 'Phase 1', 'status': 'missing'},
        ]
    }

    phase, open_items = plan_exec.next_open_work_items(state)

    assert phase == 'Phase 0'
    assert [item['id'] for item in open_items] == ['af_00_02a']


def test_prompt_placeholder_path_is_rejected() -> None:
    with pytest.raises(ValueError, match='Path not in allowed locations'):
        validate_writes_payload(
            {
                'writes': [
                    {
                        'path': 'replace/with/real/path.py',
                        'content': "def run() -> None:\n    '''Summary.'''\n",
                    }
                ],
                'notes': 'Reject placeholder paths.',
            }
        )


def test_reconcile_state_with_repo_promotes_missing_item_when_validation_passes(
    tmp_path: Path,
) -> None:
    docs_path = tmp_path / 'docs'
    docs_path.mkdir()
    (docs_path / 'artifact.md').write_text('# ready\n', encoding='utf-8')
    state = {
        'items': [
            {
                'id': 'af_00_04',
                'phase': 'Phase 0',
                'title': '`AF-00-04` Publish signing and runtime-state ABI.',
                'instructions': (
                    '**PRD Refs:** `§5.3`, `§7`, `§8`, `REQ-02`, `REQ-03`\n'
                    '**Target File:** `docs/artifact.md`\n'
                    '**Validation:** `uv run pytest tests/contracts/test_frozen_contracts.py`\n'
                    '**Behavior:** publish trust and runtime-state semantics.\n'
                ),
                'status': 'missing',
                'notes': '',
                'updated_at': '2026-03-12T00:00:00',
                'missing': [],
                'evidence': [],
            },
            {
                'id': 'af_01_01',
                'phase': 'Phase 1',
                'title': '`AF-01-01` Later item.',
                'instructions': '',
                'status': 'missing',
                'notes': '',
                'updated_at': '2026-03-12T00:00:00',
                'missing': [],
                'evidence': [],
            },
        ],
        'history': [],
    }

    def fake_runner(
        repo_root: Path, instructions: str, _changed_files: list[str]
    ) -> ValidationReport:
        assert repo_root == tmp_path
        assert _changed_files == []
        assert 'docs/artifact.md' in instructions
        return ValidationReport(
            all_passed=True,
            layers=[
                GateResult(
                    layer=1,
                    passed=True,
                    evidence=['docs/artifact.md'],
                    errors=[],
                    target_files=['docs/artifact.md'],
                )
            ],
            changed_files=[],
            validation_command='uv run pytest tests/contracts/test_frozen_contracts.py',
            target_files=['docs/artifact.md'],
        )

    updates = plan_exec.reconcile_state_with_repo(
        state,
        repo_root=tmp_path,
        validation_runner=fake_runner,
        audit_path=tmp_path / 'audit.md',
    )
    phase, open_items = plan_exec.next_open_work_items(state)

    assert len(updates) == 1
    assert state['items'][0]['status'] == 'done'
    assert state['items'][0]['evidence'] == ['docs/artifact.md']
    assert state['history'][0]['status'] == 'done'
    assert phase == 'Phase 1'
    assert [item['id'] for item in open_items] == ['af_01_01']


def test_reconcile_state_with_repo_promotes_blocked_item_before_selection(
    tmp_path: Path,
) -> None:
    state = {
        'items': [
            {
                'id': 'af_00_04',
                'phase': 'Phase 0',
                'title': '`AF-00-04` Frozen contracts.',
                'instructions': '**Target File:** `docs/artifact.md`\n',
                'status': 'blocked',
                'notes': 'old failure',
                'updated_at': '2026-03-12T00:00:00',
                'missing': ['old failure'],
                'evidence': [],
            },
            {
                'id': 'af_00_05',
                'phase': 'Phase 0',
                'title': '`AF-00-05` Still open.',
                'instructions': '**Target File:** `docs/next.md`\n',
                'status': 'missing',
                'notes': '',
                'updated_at': '2026-03-12T00:00:00',
                'missing': [],
                'evidence': [],
            },
        ],
        'history': [],
    }

    def fake_runner(
        _repo_root: Path, _instructions: str, _changed_files: list[str]
    ) -> ValidationReport:
        target = 'docs/artifact.md' if 'artifact' in _instructions else 'docs/next.md'
        passed = target == 'docs/artifact.md'
        return ValidationReport(
            all_passed=passed,
            layers=[
                GateResult(
                    layer=1,
                    passed=passed,
                    evidence=[target] if passed else [],
                    errors=[] if passed else [f'MISSING: {target}'],
                    target_files=[target],
                )
            ],
            changed_files=[],
            target_files=[target],
        )

    plan_exec.reconcile_state_with_repo(
        state,
        repo_root=tmp_path,
        validation_runner=fake_runner,
        audit_path=tmp_path / 'audit.md',
    )
    phase, open_items = plan_exec.next_open_work_items(state)

    assert state['items'][0]['status'] == 'done'
    assert phase == 'Phase 0'
    assert [item['id'] for item in open_items] == ['af_00_05']


def test_reconcile_state_with_repo_preserves_incomplete_item_when_repo_fails(
    tmp_path: Path,
) -> None:
    state = {
        'items': [
            {
                'id': 'af_00_04',
                'phase': 'Phase 0',
                'title': '`AF-00-04` Frozen contracts.',
                'instructions': '**Target File:** `docs/missing.md`\n',
                'status': 'missing',
                'notes': '',
                'updated_at': '2026-03-12T00:00:00',
                'missing': [],
                'evidence': [],
            }
        ],
        'history': [],
    }

    def fake_runner(
        _repo_root: Path, _instructions: str, _changed_files: list[str]
    ) -> ValidationReport:
        return ValidationReport(
            all_passed=False,
            layers=[
                GateResult(
                    layer=1,
                    passed=False,
                    evidence=[],
                    errors=['MISSING: docs/missing.md'],
                    target_files=['docs/missing.md'],
                )
            ],
            changed_files=[],
            target_files=['docs/missing.md'],
        )

    updates = plan_exec.reconcile_state_with_repo(
        state,
        repo_root=tmp_path,
        validation_runner=fake_runner,
        audit_path=tmp_path / 'audit.md',
    )

    assert updates == []
    assert state['items'][0]['status'] == 'missing'
    assert state['history'] == []


def test_build_retry_prompt_includes_current_file_contents(tmp_path: Path) -> None:
    src_path = tmp_path / 'src' / 'aetherflow' / 'core'
    src_path.mkdir(parents=True)
    file_path = src_path / 'plugin_system.py'
    file_path.write_text("value = 'current-state'\n", encoding='utf-8')
    payload = {
        'writes': [
            {
                'path': 'src/aetherflow/core/plugin_system.py',
                'content': "value = 'next-state'\n",
            }
        ],
        'notes': 'overwrite existing file',
    }

    snapshots = capture_existing_file_snapshots(tmp_path, payload)
    prompt = plan_exec.build_retry_prompt(
        'Physical validation gate failed.',
        repo_root=tmp_path,
        changed_files=['src/aetherflow/core/plugin_system.py'],
        snapshots=snapshots,
    )

    assert 'Physical validation gate failed.' in prompt
    assert "value = 'current-state'" in prompt
    assert 'Pre-write SHA256:' in prompt
