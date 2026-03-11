import json
import re
from pathlib import Path

import pytest

from tools import plan_exec
from tools.apply_writes import validate_writes_payload
from tools.validation_gate import extract_target_files, extract_validation_command

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
    assert (
        extract_target_files(af_00_01.instructions)
        == [
            'docs/PRD.md',
            'README.md',
            '.agents/rules/project-specific.md',
            'tests/contracts/test_canonical_identity.py',
            'tests/contracts/test_prd_execution_readiness.py',
        ]
    )
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
