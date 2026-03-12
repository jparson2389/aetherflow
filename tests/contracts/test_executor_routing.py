from __future__ import annotations

import json
from pathlib import Path

from tools import plan_exec
from tools.json_utils import PM_NEXT_RESPONSE_FORMAT

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_manifest() -> dict:
    manifest_path = PROJECT_ROOT / 'agent_manifest.json'
    return json.loads(manifest_path.read_text(encoding='utf-8'))


def test_pm_next_schema_has_no_agent_field() -> None:
    """PM-next must not expose an 'agent' field in its schema."""
    # Textual schema hint in plan_exec
    assert '"agent"' not in plan_exec.SCHEMA_PM_NEXT

    # Formal response_format schema in json_utils
    schema = PM_NEXT_RESPONSE_FORMAT['json_schema']['schema']
    work_item_schema = schema['properties']['work_items']['items']
    required = set(work_item_schema['required'])
    props = work_item_schema['properties']

    assert 'agent' not in required
    assert 'agent' not in props
    assert {'id', 'title', 'acceptance', 'notes'}.issubset(required)


def test_pm_work_item_model_has_no_agent_field() -> None:
    """PMWorkItem model should not carry an 'agent' attribute."""
    fields = plan_exec.PMWorkItem.model_fields
    assert 'agent' not in fields
    for key in ('id', 'title', 'acceptance', 'notes'):
        assert key in fields


def test_extract_phase_work_items_populates_roles() -> None:
    """PLAN.md items must carry the Role field parsed into PlanWorkItem.role."""
    plan_text = (PROJECT_ROOT / 'docs' / 'PLAN.md').read_text(encoding='utf-8')
    items = {item.id: item for item in plan_exec.extract_phase_work_items(plan_text)}

    assert items['af_00_01'].role == 'core-runtime'
    assert items['af_00_04'].role == 'trust-security'
    assert items['af_02_01'].role == 'native-io-capture'
    assert items['af_04_01'].role == 'runtime-services'
    assert items['af_05_01'].role == 'trust-security'


def test_role_to_alias_and_context_resolve_from_manifest() -> None:
    """Role-to-alias and role-to-context must resolve via helper functions."""
    manifest = _load_manifest()

    assert plan_exec.resolve_role_alias(manifest, 'core-runtime') == 'architect'
    assert plan_exec.resolve_role_alias(manifest, 'trust-security') == 'trust-security'
    assert plan_exec.resolve_role_alias(manifest, 'platform-entitlements') == 'runtime-services'
    assert plan_exec.resolve_role_alias(manifest, 'ui-shell') == 'ui-ux'

    ctx = plan_exec.resolve_role_context(manifest, 'trust-security')
    assert 'security-focused Windows engineer' in ctx


def test_build_role_scoped_impl_system_prepends_role_context() -> None:
    """Implementation system prompt must be prefixed with the role context."""
    manifest = _load_manifest()
    base = 'BASE_IMPL_SYSTEM'

    scoped = plan_exec.build_role_scoped_impl_system(
        manifest=manifest,
        role='core-runtime',
        base_system=base,
    )

    # Role context should appear before the base system prompt.
    core_ctx = plan_exec.resolve_role_context(manifest, 'core-runtime')
    assert scoped.startswith(core_ctx)
    assert scoped.endswith(base)
