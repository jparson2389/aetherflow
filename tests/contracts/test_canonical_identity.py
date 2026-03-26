from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_AGENTS_RULES = PROJECT_ROOT / 'AGENTS.md'


def test_canonical_package_root_is_aetherflow() -> None:
    assert (PROJECT_ROOT / 'src' / 'aetherflow').is_dir()
    assert not (PROJECT_ROOT / 'src' / 'aetherlink').exists()


def test_project_docs_reference_aetherflow_canonical_paths() -> None:
    prd_text = (PROJECT_ROOT / 'docs' / 'PRD.md').read_text(encoding='utf-8')
    readme_text = (PROJECT_ROOT / 'README.md').read_text(encoding='utf-8')

    if not _AGENTS_RULES.exists():
        pytest.skip('AGENTS.md not present in this environment')

    project_rules = _AGENTS_RULES.read_text(encoding='utf-8')

    for text in (readme_text, project_rules):
        assert 'src/aetherflow/' in text
        assert 'src/aetherlink/' not in text

    assert '`include/plugin_system.hpp`' in prd_text
    assert 'src/aetherflow/plugins/include/plugin_system.hpp' not in prd_text
