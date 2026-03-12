from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _collect_items_with_gates(plan_text: str) -> list[str]:
    items: list[str] = []
    current_id: str | None = None
    has_gate = False

    for line in plan_text.splitlines():
        if line.startswith('- [ ] `AF-'):
            if current_id and not has_gate:
                items.append(current_id)
            current_id = line.split('`')[1]
            has_gate = False
            continue
        if current_id and '**Completion Gates:**' in line:
            has_gate = True
    if current_id and not has_gate:
        items.append(current_id)
    return items


_VALID_ROLES = {
    'core-runtime',
    'trust-security',
    'platform-entitlements',
    'native-io-capture',
    'runtime-services',
    'ui-shell',
}


def _collect_items_missing_role(plan_text: str) -> list[str]:
    items: list[str] = []
    current_id: str | None = None
    has_role = False

    for line in plan_text.splitlines():
        if line.startswith('- [ ] `AF-'):
            if current_id and not has_role:
                items.append(current_id)
            current_id = line.split('`')[1]
            has_role = False
            continue
        if current_id and '> **Role:**' in line:
            has_role = True
            # Extract the role name inside backticks, if present.
            parts = line.split('`')
            if len(parts) >= 2:
                role = parts[1]
                assert role in _VALID_ROLES, (
                    f'Invalid role {role!r} for item {current_id!r}'
                )
    if current_id and not has_role:
        items.append(current_id)
    return items


def test_plan_has_completion_policy_and_gates() -> None:
    plan_text = (PROJECT_ROOT / 'docs' / 'PLAN.md').read_text(encoding='utf-8')

    assert 'Completion Policy (All Work Items)' in plan_text

    missing_gates = _collect_items_with_gates(plan_text)
    assert missing_gates == [], 'Missing Completion Gates for: ' + ', '.join(
        missing_gates
    )


def test_plan_items_have_roles() -> None:
    """Every AF work item must declare a valid Role."""
    plan_text = (PROJECT_ROOT / 'docs' / 'PLAN.md').read_text(encoding='utf-8')

    missing_roles = _collect_items_missing_role(plan_text)
    assert missing_roles == [], 'Missing Role for: ' + ', '.join(missing_roles)
