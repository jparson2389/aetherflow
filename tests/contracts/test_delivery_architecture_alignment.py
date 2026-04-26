from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_normalized_text(path: Path) -> str:
    return ' '.join(path.read_text(encoding='utf-8').split())


def test_alignment_docs_define_host_owned_supervision() -> None:
    prd_text = _read_normalized_text(PROJECT_ROOT / 'docs' / 'PRD.md')
    plan_text = _read_normalized_text(PROJECT_ROOT / 'docs' / 'PLAN.md')
    agents_text = _read_normalized_text(PROJECT_ROOT / 'AGENTS.md')
    decision_text = _read_normalized_text(
        PROJECT_ROOT / 'docs' / 'architecture' / 'runtime-authority-decision.md'
    )

    assert 'worker supervisor and IPC endpoints' in prd_text
    assert 'Supervision authority is host-owned' in plan_text
    assert 'host-owned worker supervision' in plan_text
    assert 'Aetherflow.exe/host is the supervisor of record.' in agents_text
    assert '`Aetherflow.exe` is the supervisor of record.' in decision_text
    assert (
        'Host-owned state is authoritative for start, stop, restart, heartbeat,'
        in decision_text
    )


def test_alignment_docs_define_shell_survivability() -> None:
    prd_text = _read_normalized_text(PROJECT_ROOT / 'docs' / 'PRD.md')
    agents_text = _read_normalized_text(PROJECT_ROOT / 'AGENTS.md')
    decision_text = _read_normalized_text(
        PROJECT_ROOT / 'docs' / 'architecture' / 'runtime-authority-decision.md'
    )

    assert 'keep the host and shell alive' in prd_text
    assert 'must remain alive when plugins or workers fail' in agents_text
    assert 'durable client and rendering surface' in decision_text


def test_alignment_docs_define_out_of_process_python_workers() -> None:
    prd_text = _read_normalized_text(PROJECT_ROOT / 'docs' / 'PRD.md')
    plan_text = _read_normalized_text(PROJECT_ROOT / 'docs' / 'PLAN.md')
    agents_text = _read_normalized_text(PROJECT_ROOT / 'AGENTS.md')

    assert 'All Python scripts and vision processing run out of process' in prd_text
    assert 'Python-side adapters only where needed for shell clients' in plan_text
    assert 'Python workers and vision/script workloads stay out of process' in (
        agents_text
    )


def test_alignment_notes_capture_requirements_conflicts_and_buckets() -> None:
    notes_text = _read_normalized_text(
        PROJECT_ROOT
        / 'docs'
        / 'architecture'
        / 'delivery-architecture-alignment-notes.md'
    )

    assert '§5.1' in notes_text
    assert '§7.2' in notes_text
    assert '§7.4' in notes_text
    assert '§9.1' in notes_text
    assert '§9.7' in notes_text
    assert '§10.1' in notes_text
    assert 'runtime orchestration, plugin manager, shared logic' in notes_text
    assert 'C1' in notes_text
    assert 'H2' in notes_text
    assert 'host-supervision gap' in notes_text
    assert 'IPC gap' in notes_text
    assert 'delivery-packaging gap' in notes_text
    assert 'correctness-only defect' in notes_text


def test_delivery_runtime_layout_declares_required_packaged_root_entries() -> None:
    runtime_layout_path = (
        PROJECT_ROOT / 'docs' / 'architecture' / 'delivery-runtime-layout.md'
    )
    runtime_layout_text = _read_normalized_text(runtime_layout_path)

    assert 'Canonical Root Tree' in runtime_layout_text
    assert 'Aetherflow.exe' in runtime_layout_text
    assert 'aetherflow_settings.ini' in runtime_layout_text
    assert 'qt.conf' in runtime_layout_text
    assert 'lib/' in runtime_layout_text
    assert 'plugins/' in runtime_layout_text
    assert 'scripts/' in runtime_layout_text
    assert 'version_info.json' in runtime_layout_text


def test_delivery_runtime_layout_declares_dual_executable_roles() -> None:
    runtime_layout_text = _read_normalized_text(
        PROJECT_ROOT / 'docs' / 'architecture' / 'delivery-runtime-layout.md'
    )

    assert 'root `Aetherflow.exe` is the small wrapper/bootstrap executable' in (
        runtime_layout_text
    )
    assert '`lib/Aetherflow2.exe` is the primary runtime executable' in (
        runtime_layout_text
    )
    assert 'different roles, not duplicate binaries' in runtime_layout_text


def test_delivery_runtime_layout_declares_canonical_plugin_translation_placement() -> (
    None
):
    runtime_layout_text = _read_normalized_text(
        PROJECT_ROOT / 'docs' / 'architecture' / 'delivery-runtime-layout.md'
    )

    assert 'contains plugin translation files both at the root of `plugins/`' in (
        runtime_layout_text
    )
    assert '`lib/translations/plugins/<PluginName>/`' in runtime_layout_text
    assert 'Canonical placement for plugin translation files is' in runtime_layout_text


def test_delivery_runtime_layout_maps_source_areas_to_single_roles() -> None:
    runtime_layout_text = _read_normalized_text(
        PROJECT_ROOT / 'docs' / 'architecture' / 'delivery-runtime-layout.md'
    )

    assert 'Source Area Role Mapping' in runtime_layout_text
    assert '`host/`' in runtime_layout_text
    assert '`include/`' in runtime_layout_text
    assert '`proto/`' in runtime_layout_text
    assert '`src/aetherflow/ui/`' in runtime_layout_text
    assert '`src/aetherflow/core/`' in runtime_layout_text
    assert '`src/aetherflow/input/`' in runtime_layout_text
    assert '`src/aetherflow/output/`' in runtime_layout_text
    assert '`src/aetherflow/vision/`' in runtime_layout_text
    assert '`assets/`' in runtime_layout_text
    assert '`tools/`' in runtime_layout_text
    assert 'development-only' in runtime_layout_text


def test_delivery_runtime_layout_maps_artifact_classes_to_sources() -> None:
    runtime_layout_text = _read_normalized_text(
        PROJECT_ROOT / 'docs' / 'architecture' / 'delivery-runtime-layout.md'
    )

    assert 'Artifact Source-of-Truth Mapping' in runtime_layout_text
    assert 'wrapper executable at root' in runtime_layout_text
    assert 'primary runtime executable under `lib/`' in runtime_layout_text
    assert 'host DLLs' in runtime_layout_text
    assert 'plugin DLLs' in runtime_layout_text
    assert 'Python helper payloads under `lib/py/`' in runtime_layout_text
    assert 'support executables under `lib/`' in runtime_layout_text
    assert 'runtime-support payloads under `lib/plugins/`' in runtime_layout_text
    assert 'Qt runtime assets' in runtime_layout_text
    assert 'styles, layouts, and translation assets' in runtime_layout_text
    assert 'packaged user script payloads under `scripts/`' in runtime_layout_text
    assert (
        'managed Python runtime assets under `%LOCALAPPDATA%/AetherflowProject/Aetherflow/python/`'
        in runtime_layout_text
    )


def test_delivery_runtime_layout_declares_runtime_only_subtree_rules() -> None:
    runtime_layout_text = _read_normalized_text(
        PROJECT_ROOT / 'docs' / 'architecture' / 'delivery-runtime-layout.md'
    )

    assert 'Runtime-only Subtree Placement Rules' in runtime_layout_text
    assert '`lib/cv_cpp/`' in runtime_layout_text
    assert '`lib/gpc3/`' in runtime_layout_text
    assert '`lib/cv_python_host/`' in runtime_layout_text
    assert '`lib/py/`' in runtime_layout_text
    assert '`lib/plugins/`' in runtime_layout_text
    assert '`lib/styles/`' in runtime_layout_text
    assert '`lib/translations/core/`' in runtime_layout_text
    assert '`lib/translations/plugins/<PluginName>/`' in runtime_layout_text
    assert '`scripts/_aetherflow_*` bundles' in runtime_layout_text


def test_alignment_notes_define_managed_python_runtime_layout() -> None:
    notes_text = _read_normalized_text(
        PROJECT_ROOT
        / 'docs'
        / 'architecture'
        / 'delivery-architecture-alignment-notes.md'
    )

    # 2.8.1 - managed-python interpreter root
    assert 'managed-python' in notes_text
    assert '%LOCALAPPDATA%' in notes_text

    # 2.8.2 - uv.exe at managed Python root
    assert 'uv.exe' in notes_text

    # 2.8.3 - per-workload root
    assert 'workload' in notes_text

    # 2.8.4 - .aenv virtual environment
    assert '.aenv' in notes_text

    # 2.8.5 - requirements.txt per workload
    assert 'requirements.txt' in notes_text


def test_alignment_notes_classify_python_modules() -> None:
    notes_text = _read_normalized_text(
        PROJECT_ROOT
        / 'docs'
        / 'architecture'
        / 'delivery-architecture-alignment-notes.md'
    )

    # 2.9.1 - shell-only classification
    assert 'Shell-only' in notes_text or 'shell-only' in notes_text

    # 2.9.2 - worker/helper classification
    assert 'Worker and helper' in notes_text or 'worker and helper' in notes_text

    # 2.9.3 - transitional modules
    assert 'Transitional' in notes_text or 'transitional' in notes_text
    assert 'worker_supervisor' in notes_text
    assert 'env_manager' in notes_text


def test_alignment_notes_inventory_stub_components() -> None:
    notes_text = _read_normalized_text(
        PROJECT_ROOT
        / 'docs'
        / 'architecture'
        / 'delivery-architecture-alignment-notes.md'
    )

    # 2.10 - stub inventory with explicit dispositions
    assert 'implement before ship' in notes_text
    assert 'exclude from first delivery tree' in notes_text
    assert 'ipc' in notes_text
    assert 'env_manager' in notes_text
