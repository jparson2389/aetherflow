from __future__ import annotations

import importlib
import os
import subprocess
from pathlib import Path

from loguru import logger as loguru_logger

from tools import plan_exec

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_importing_plan_exec_does_not_register_plan_execution_sink(
    monkeypatch,
) -> None:
    add_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_add(*args: object, **kwargs: object) -> int:
        add_calls.append((args, kwargs))
        return 1

    monkeypatch.setattr(loguru_logger, 'add', fake_add)

    importlib.reload(plan_exec)

    assert add_calls == []


def test_main_creates_one_plan_execution_log_per_run(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(plan_exec, 'LOG_DIR', tmp_path)

    def fake_run(_argv: list[str] | None = None) -> int:
        plan_exec.logger.info('inside run')
        return 0

    monkeypatch.setattr(plan_exec, '_run_plan_exec', fake_run)

    assert plan_exec.main([]) == 0
    assert plan_exec.main([]) == 0

    log_paths = sorted(tmp_path.glob('plan_execution_*.log'))

    assert len(log_paths) == 2
    for log_path in log_paths:
        text = log_path.read_text(encoding='utf-8')
        assert 'inside run' in text
        assert text.count('inside run') == 1


def test_unrelated_logs_do_not_appear_without_active_plan_exec_sink(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(plan_exec, 'LOG_DIR', tmp_path)
    plan_exec.logger.warning('outside before')

    def fake_run(_argv: list[str] | None = None) -> int:
        plan_exec.logger.info('inside run')
        return 0

    monkeypatch.setattr(plan_exec, '_run_plan_exec', fake_run)

    assert list(tmp_path.glob('plan_execution_*.log')) == []
    assert plan_exec.main([]) == 0
    plan_exec.logger.warning('outside after')

    log_path = next(tmp_path.glob('plan_execution_*.log'))
    text = log_path.read_text(encoding='utf-8')

    assert 'inside run' in text
    assert 'outside before' not in text
    assert 'outside after' not in text


def test_plan_exec_report_uses_a_single_newest_run_log(tmp_path: Path) -> None:
    logs_dir = tmp_path / 'logs'
    logs_dir.mkdir()
    older_log = logs_dir / 'plan_execution_2026-03-17_110000.log'
    newer_log = logs_dir / 'plan_execution_2026-03-17_120000.log'
    older_log.write_text(
        '2026-03-17 11:00:00.000 | WARNING  | tests.old:run:1 - old warning\n',
        encoding='utf-8',
    )
    newer_log.write_text(
        '\n'.join(
            [
                '2026-03-17 12:00:00.000 | INFO     | tools.plan_exec:main:1 - start',
                '2026-03-17 12:00:01.000 | WARNING  | tools.plan_exec:main:2 - new warning',
            ]
        )
        + '\n',
        encoding='utf-8',
    )
    os.utime(older_log, (1_710_690_000, 1_710_690_000))
    os.utime(newer_log, (1_710_693_600, 1_710_693_600))

    result = subprocess.run(
        ['uv', 'run', 'python', '-m', 'tools.plan_exec_report'],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            'PYTHONPATH': str(PROJECT_ROOT),
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr

    report_path = max(
        logs_dir.glob('plan_exec_report_*.md'), key=lambda path: path.stat().st_mtime
    )
    report_text = report_path.read_text(encoding='utf-8')

    assert 'Source log:' in report_text
    assert 'plan_execution_2026-03-17_120000.log' in report_text
    assert (
        'Run window: 2026-03-17 12:00:00.000 -> 2026-03-17 12:00:01.000' in report_text
    )
    assert 'new warning' in report_text
    assert 'old warning' not in report_text


def test_plan_exec_report_emits_section_headers_once(tmp_path: Path) -> None:
    logs_dir = tmp_path / 'logs'
    logs_dir.mkdir()
    log_path = logs_dir / 'plan_execution_2026-03-17_120000.log'
    log_path.write_text(
        '\n'.join(
            [
                '2026-03-17 12:00:00.000 | INFO     | tools.plan_exec:main:1 - start',
                '2026-03-17 12:00:01.000 | INFO     | tools.plan_exec:main:2 - [state] done',
                '2026-03-17 12:00:02.000 | INFO     | tools.plan_exec:main:3 - Execution Summary | ok',
            ]
        )
        + '\n',
        encoding='utf-8',
    )

    result = subprocess.run(
        ['uv', 'run', 'python', '-m', 'tools.plan_exec_report'],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            'PYTHONPATH': str(PROJECT_ROOT),
        },
    )

    assert result.returncode == 0, result.stdout + result.stderr

    report_path = max(
        logs_dir.glob('plan_exec_report_*.md'), key=lambda path: path.stat().st_mtime
    )
    report_text = report_path.read_text(encoding='utf-8')

    assert report_text.count('## Plan State Snapshots') == 1
    assert report_text.count('## Execution Summaries') == 1
    assert report_text.count('## Warnings And Errors') == 1
