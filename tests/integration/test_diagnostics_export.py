from aetherflow.core.diagnostics_export import DiagnosticsExporter


def test_diagnostics_export_contains_expected_sections() -> None:
    exporter = DiagnosticsExporter()

    payload = exporter.export()

    assert 'plugins' in payload
    assert 'workers' in payload
    assert 'envs' in payload
    assert 'logs' in payload
    assert 'overflow_counters' in payload
    assert 'restart_counters' in payload
