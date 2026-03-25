from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def resolve_plan_log(logs_dir: Path, log_file_path: str | None) -> Path:
    """Resolve the plan execution log to inspect."""
    if log_file_path:
        candidate = Path(log_file_path)
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if not candidate.exists():
            raise FileNotFoundError(
                f"Specified LogFilePath '{log_file_path}' does not exist."
            )
        return candidate

    candidates = sorted(
        logs_dir.glob('plan_execution_*.log'),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError('No plan_execution_*.log files found under logs/.')
    return candidates[0]


def _collect_git_status(cwd: Path) -> list[str]:
    """Return `git status --porcelain` lines when inside a git worktree."""
    inside = subprocess.run(
        ['git', 'rev-parse', '--is-inside-work-tree'],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if inside.returncode != 0:
        return []
    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def _format_section_list(title: str, items: list[str]) -> list[str]:
    """Format a markdown section with bullet items."""
    if not items:
        return [f'### {title}', '', '- (none)', '']
    lines = [f'### {title}', '']
    for item in sorted(set(items)):
        lines.append(f'- {item}')
    lines.append('')
    return lines


def build_report(*, cwd: Path, log_file_path: str | None = None) -> Path:
    """Generate a plan execution report markdown file."""
    logs_dir = cwd / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)

    plan_log_path = resolve_plan_log(logs_dir, log_file_path)
    report_path = logs_dir / (
        f'plan_exec_report_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}.md'
    )

    log_lines = plan_log_path.read_text(encoding='utf-8').splitlines()
    timestamps = []
    for line in log_lines:
        if ' | ' not in line:
            continue
        prefix = line.split(' | ', 1)[0]
        if len(prefix) >= 23:
            timestamps.append(prefix)
    run_window = '(no timestamps found)'
    if timestamps:
        run_window = f'{timestamps[0]} -> {timestamps[-1]}'

    state_lines = [line for line in log_lines if '[state]' in line]
    summary_lines = [line for line in log_lines if 'Execution Summary |' in line]
    error_lines = [line for line in log_lines if ' ERROR ' in line]
    warning_lines = [line for line in log_lines if ' WARNING ' in line]
    pm_failure_lines = [
        line for line in log_lines if 'PM verify failed' in line or '[pm_next]' in line
    ]

    status = 'Success'
    status_reason = 'No ERROR lines detected in plan execution log.'
    if error_lines:
        status = 'Failed'
        status_reason = error_lines[-1]
    elif pm_failure_lines:
        status = 'Partial'
        status_reason = pm_failure_lines[-1]

    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for line in _collect_git_status(cwd):
        status_code = line[:2]
        path = line[3:].strip()
        if status_code == '??' or 'A' in status_code:
            added.append(path)
        elif 'D' in status_code:
            deleted.append(path)
        else:
            modified.append(path)

    report_lines = [
        '# Plan Execution Report',
        '',
        f'Generated: {datetime.now().astimezone().isoformat()}',
        f'Source log: {plan_log_path}',
        f'Log file: {plan_log_path.name}',
        f'Run window: {run_window}',
        '',
        '## Overall Status',
        '',
        f'- **Status**: {status}',
        f'- **Reason**: {status_reason}',
        '',
        '## Plan State Snapshots',
        '',
        '## Execution Summaries',
        '',
        '## Warnings And Errors',
        '',
    ]
    if state_lines:
        report_lines.extend(f'- {line}' for line in state_lines)
    else:
        report_lines.append('- (no [state] lines found)')
    report_lines.extend(['', '## Execution Summaries', ''])
    if summary_lines:
        report_lines.extend(f'- {line}' for line in summary_lines)
    else:
        report_lines.append('- (no Execution Summary lines found)')
    report_lines.extend(['', '## Warnings And Errors', ''])
    if warning_lines:
        report_lines.extend(['### Warnings', ''])
        report_lines.extend(f'- {line}' for line in warning_lines)
        report_lines.append('')
    if error_lines:
        report_lines.extend(['### Errors', ''])
        report_lines.extend(f'- {line}' for line in error_lines)
        report_lines.append('')

    report_lines.extend(_format_section_list('New Files (Untracked/Added)', added))
    report_lines.extend(_format_section_list('Modified Files', modified))
    report_lines.extend(_format_section_list('Deleted Files', deleted))
    report_path.write_text('\n'.join(report_lines) + '\n', encoding='utf-8')
    return report_path


def main() -> int:
    """CLI entrypoint for plan execution report generation."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--log-file-path')
    args = parser.parse_args()
    build_report(cwd=Path.cwd(), log_file_path=args.log_file_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
