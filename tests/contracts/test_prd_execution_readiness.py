from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_prd_is_self_contained_and_citation_free() -> None:
    prd_text = (PROJECT_ROOT / "docs" / "PRD.md").read_text(encoding="utf-8")

    assert "filecite" not in prd_text
    assert "turn4file0" not in prd_text


def test_prd_defines_runtime_budgets_and_failure_ux() -> None:
    prd_text = (PROJECT_ROOT / "docs" / "PRD.md").read_text(encoding="utf-8")
    prd_text_lower = prd_text.lower()

    assert "median <= 8 ms" in prd_text
    assert "p95 <= 12 ms" in prd_text
    assert "queue depth" in prd_text
    assert "sustained drop" in prd_text
    assert "plugin crash" in prd_text_lower
    assert "worker unrecoverable loop" in prd_text_lower
    assert "manual reload" in prd_text_lower


def test_prd_defines_signing_and_capture_contracts() -> None:
    prd_text = (PROJECT_ROOT / "docs" / "PRD.md").read_text(encoding="utf-8")

    assert "Authenticode" in prd_text
    assert "RSA-3072" in prd_text
    assert "60 FPS baseline required" in prd_text
    assert "120 FPS validated path required" in prd_text
    assert "240 FPS remains capability-based only" in prd_text


def test_plan_splits_phase_zero_and_tracks_new_contract_work() -> None:
    plan_text = (PROJECT_ROOT / "docs" / "PLAN.md").read_text(encoding="utf-8")

    assert "AF-00-02" in plan_text
    assert "AF-00-03" in plan_text
    assert "AF-00-04" in plan_text
    assert "Publish control-plane proto surface" in plan_text
    assert "shared-memory ring semantics" in plan_text
    assert "Publish signing and runtime-state ABI" in plan_text
    assert "failure-UX state model" in plan_text


def test_plan_signoff_packets_define_sla_and_fallbacks() -> None:
    auth_text = (
        PROJECT_ROOT / "docs" / "sign-offs" / "auth-provider.md"
    ).read_text(encoding="utf-8")
    bundle_text = (
        PROJECT_ROOT / "docs" / "sign-offs" / "bundle-format.md"
    ).read_text(encoding="utf-8")

    for text in (auth_text, bundle_text):
        assert "Fallback" in text
        assert "24 hours" in text or "24-hour" in text
