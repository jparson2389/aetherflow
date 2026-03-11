from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _collect_items_with_gates(plan_text: str) -> list[str]:
    items: list[str] = []
    current_id: str | None = None
    has_gate = False

    for line in plan_text.splitlines():
        if line.startswith("- [ ] `AF-"):
            if current_id and not has_gate:
                items.append(current_id)
            current_id = line.split("`")[1]
            has_gate = False
            continue
        if current_id and "**Completion Gates:**" in line:
            has_gate = True
    if current_id and not has_gate:
        items.append(current_id)
    return items


def test_plan_has_completion_policy_and_gates() -> None:
    plan_text = (PROJECT_ROOT / "docs" / "PLAN.md").read_text(encoding="utf-8")

    assert "Completion Policy (All Work Items)" in plan_text

    missing_gates = _collect_items_with_gates(plan_text)
    assert missing_gates == [], (
        "Missing Completion Gates for: " + ", ".join(missing_gates)
    )
