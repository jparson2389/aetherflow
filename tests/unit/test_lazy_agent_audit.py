from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    PROJECT_ROOT
    / '.codex'
    / 'skills'
    / 'lazy-agent'
    / 'scripts'
    / 'audit_plan_completion.py'
)


def _load_lazy_agent_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location('lazy_agent_audit_test', SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_plan_path_prefers_repo_root_rework_plan(tmp_path: Path) -> None:
    module = _load_lazy_agent_module()
    docs_dir = tmp_path / 'docs'
    docs_dir.mkdir()
    rework_path = tmp_path / 'REWORK_PLAN.md'
    rework_path.write_text('# Rework\n', encoding='utf-8')
    (docs_dir / 'PLAN.md').write_text('# Docs Plan\n', encoding='utf-8')

    resolved = module.resolve_plan_path(None, repo_root=tmp_path)
    task_list = module.resolve_task_list_path(
        None,
        plan_path=resolved,
        repo_root=tmp_path,
    )

    assert resolved == rework_path.resolve()
    assert task_list == (tmp_path / 'tasks' / 'tasks-rework-plan.md')


def test_resolve_plan_path_fails_when_repo_root_candidates_are_ambiguous(
    tmp_path: Path,
) -> None:
    module = _load_lazy_agent_module()
    docs_dir = tmp_path / 'docs'
    docs_dir.mkdir()
    (docs_dir / 'PLAN.md').write_text('# Docs Plan\n', encoding='utf-8')
    (tmp_path / 'Alpha_PLAN.md').write_text('# Alpha\n', encoding='utf-8')
    (tmp_path / 'Beta_PLAN.md').write_text('# Beta\n', encoding='utf-8')

    with pytest.raises(SystemExit, match='Multiple repo-root implementation plans'):
        module.resolve_plan_path(None, repo_root=tmp_path)


def test_bootstrap_task_list_matches_generate_tasks_shape(tmp_path: Path) -> None:
    module = _load_lazy_agent_module()
    plan_path = tmp_path / 'REWORK_PLAN.md'
    plan_path.write_text(
        '\n'.join(
            [
                '# Plan',
                '',
                '### 1. Define the first slice',
                '- Update `src/aetherflow/core/implemented.py`',
                '- Add `tests/unit/test_implemented.py`',
                '',
                '### 2. Finish the second slice',
                '- Update `src/aetherflow/core/missing.py`',
            ]
        )
        + '\n',
        encoding='utf-8',
    )
    task_list_path = tmp_path / 'tasks' / 'tasks-rework-plan.md'

    module.bootstrap_task_list(plan_path, task_list_path, repo_root=tmp_path)
    rendered = task_list_path.read_text(encoding='utf-8')

    assert '## Relevant Files' in rendered
    assert '## Instructions for Completing Tasks' in rendered
    assert '## Tasks' in rendered
    assert '- [ ] 0.0 Create feature branch' in rendered
    assert '- [ ] 1.0 Define the first slice' in rendered
    assert '  - [ ] 1.1 Update `src/aetherflow/core/implemented.py`' in rendered


def test_main_writes_task_oriented_report_for_explicit_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_lazy_agent_module()
    plan_path = tmp_path / 'REWORK_PLAN.md'
    implemented_path = tmp_path / 'src' / 'aetherflow' / 'core'
    implemented_path.mkdir(parents=True)
    (implemented_path / 'implemented.py').write_text(
        "def run() -> None:\n    '''Execute.'''\n",
        encoding='utf-8',
    )
    plan_path.write_text(
        '\n'.join(
            [
                '# Plan',
                '',
                '### 1. Implement existing module',
                '- Create `src/aetherflow/core/implemented.py`',
                '',
                '### 2. Implement missing module',
                '- Create `src/aetherflow/core/missing.py`',
            ]
        )
        + '\n',
        encoding='utf-8',
    )

    monkeypatch.setattr(
        sys,
        'argv',
        [
            'audit_plan_completion.py',
            '--plan',
            'REWORK_PLAN.md',
            '--repo-root',
            str(tmp_path),
            '--bootstrap-task-list',
        ],
    )
    assert module.main() == 0

    task_list_path = tmp_path / 'tasks' / 'tasks-rework-plan.md'
    task_list_text = task_list_path.read_text(encoding='utf-8')
    task_list_text = task_list_text.replace(
        '- [ ] 2.0 Implement missing module', '- [x] 2.0 Implement missing module'
    )
    task_list_path.write_text(task_list_text, encoding='utf-8')

    monkeypatch.setattr(
        sys,
        'argv',
        [
            'audit_plan_completion.py',
            '--plan',
            'REWORK_PLAN.md',
            '--repo-root',
            str(tmp_path),
        ],
    )
    assert module.main() == 0

    report_path = tmp_path / 'logs' / 'lazy-agent-report-rework-plan.md'
    report = report_path.read_text(encoding='utf-8')

    assert '- Plan: `REWORK_PLAN.md`' in report
    assert '- Task List: `tasks/tasks-rework-plan.md`' in report
    assert '## Resume Here' in report
    assert '`1.0` Implement existing module' in report
    assert 'Checked tasks lacking repo evidence: 1' in report
    assert 'Unchecked tasks with repo evidence:' in report


def test_repo_identifier_hits_falls_back_when_rg_is_unavailable(tmp_path: Path) -> None:
    module = _load_lazy_agent_module()
    source_path = tmp_path / 'src' / 'aetherflow' / 'core'
    source_path.mkdir(parents=True)
    (source_path / 'implemented.py').write_text(
        "def build_feature() -> None:\n    '''Execute.'''\n",
        encoding='utf-8',
    )

    hits = module.repo_identifier_hits(
        'Create build_feature support in the implementation layer.',
        repo_root=tmp_path,
    )

    assert hits
    assert any('implemented.py' in hit for hit in hits)
