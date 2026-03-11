from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_canonical_package_root_is_aetherflow() -> None:
    assert (PROJECT_ROOT / 'src' / 'aetherflow').is_dir()
    assert not (PROJECT_ROOT / 'src' / 'aetherlink').exists()


def test_project_docs_reference_aetherflow_canonical_paths() -> None:
    prd_text = (PROJECT_ROOT / 'docs' / 'PRD.md').read_text(encoding='utf-8')
    project_rules = (
        PROJECT_ROOT / '.agents' / 'rules' / 'project-specific.md'
    ).read_text(encoding='utf-8')

    assert 'src/aetherflow/' in project_rules
    assert 'src/aetherflow/' not in project_rules
    assert '`include/plugin_system.hpp`' in prd_text
    assert 'src/aetherflow/plugins/include/plugin_system.hpp' not in prd_text
