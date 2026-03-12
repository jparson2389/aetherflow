from __future__ import annotations

import configparser
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_models_ini() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    raw_text = (PROJECT_ROOT / 'tools' / 'models.ini').read_text(encoding='utf-8')
    # The preset uses a top-level version header that is not an INI section.
    # Strip it before feeding the content to ConfigParser so that only alias
    # sections are parsed.
    lines = raw_text.splitlines()
    if lines and lines[0].startswith('version'):
        raw_text = '\n'.join(lines[1:])
    config.read_string(raw_text)
    return config


def _load_manifest() -> dict:
    manifest_path = PROJECT_ROOT / 'agent_manifest.json'
    return json.loads(manifest_path.read_text(encoding='utf-8'))


def test_models_preset_contains_six_aliases_from_plan() -> None:
    """Preset must define all runtime aliases from Six-Alias Loop plan."""
    config = _load_models_ini()

    for alias in [
        'pm',
        'architect',
        'trust-security',
        'runtime-services',
        'ui-ux',
        'quick-fix',
        'researcher',
    ]:
        assert alias in config.sections(), (
            f'Alias [{alias}] missing from tools/models.ini preset'
        )


def test_manifest_role_and_stage_aliases_exist_in_preset() -> None:
    """Every role_to_alias and stage_to_alias target must exist in models preset."""
    manifest = _load_manifest()
    config = _load_models_ini()

    preset_aliases = set(config.sections())

    role_to_alias = manifest.get('role_to_alias', {})
    assert role_to_alias, 'Manifest must define role_to_alias mapping'

    stage_to_alias = manifest.get('stage_to_alias', {})
    assert stage_to_alias, 'Manifest must define stage_to_alias mapping'

    for role, alias in role_to_alias.items():
        assert alias in preset_aliases, (
            f"Alias '{alias}' for role '{role}' is not present in tools/models.ini"
        )

    for stage, alias in stage_to_alias.items():
        assert alias in preset_aliases, (
            f"Alias '{alias}' for stage '{stage}' is not present in tools/models.ini"
        )


def test_manifest_role_contexts_are_non_empty() -> None:
    """Every executable role must have a non-empty role_to_context entry."""
    manifest = _load_manifest()

    role_to_alias = manifest.get('role_to_alias', {})
    role_to_context = manifest.get('role_to_context', {})

    assert role_to_alias, 'Manifest must define role_to_alias mapping'
    assert role_to_context, 'Manifest must define role_to_context mapping'

    for role in role_to_alias:
        context = role_to_context.get(role, '').strip()
        assert context, f'role_to_context[{role!r}] must be non-empty'
