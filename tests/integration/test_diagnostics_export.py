from __future__ import annotations

import json
from pathlib import Path

from aetherflow.core.diagnostics_export import DiagnosticsExporter

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_diagnostics_export_contains_expected_sections() -> None:
    exporter = DiagnosticsExporter()
    exporter.add_plugin({'plugin_id': 'input.xinput', 'version': '1.0.0'})
    exporter.add_worker({'worker_id': 'worker-1', 'health': 'RUNNING'})
    exporter.add_env({'name': 'default', 'python_version': '3.12'})
    exporter.record_log('boot-complete')
    exporter.record_overflow(count=2)
    exporter.record_restart(count=1)

    payload = exporter.export()

    assert payload['plugins'][0]['plugin_id'] == 'input.xinput'
    assert payload['workers'][0]['health'] == 'RUNNING'
    assert payload['envs'][0]['python_version'] == '3.12'
    assert payload['logs']['recent'] == ['boot-complete']
    assert payload['overflow_counters']['frame_overflows'] == 2
    assert payload['restart_counters']['worker_restarts'] == 1


def test_diagnostics_export_writes_report() -> None:
    report_path = PROJECT_ROOT / 'logs' / 'diagnostics_export.json'
    if report_path.exists():
        report_path.unlink()

    exporter = DiagnosticsExporter()
    exporter.record_log('export-ready')
    exporter.write_report(report_path)

    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding='utf-8'))
    assert payload['logs']['recent'] == ['export-ready']
