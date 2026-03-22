from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / 'logs' / 'quality-gate.log'


def write_log(message: str, *, log_path: Path = LOG_PATH) -> None:
    """Append a message to the quality gate log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as handle:
        handle.write(f'{message}\n')


def run_quality_step(
    label: str,
    command: list[str],
    *,
    cwd: Path,
    log_path: Path = LOG_PATH,
) -> None:
    """Run one quality gate command and raise on non-zero exit."""
    write_log(f'--- {label} ---', log_path=log_path)
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    output = f'{result.stdout or ""}{result.stderr or ""}'.strip()
    if output:
        write_log(output, log_path=log_path)
    if result.returncode != 0:
        message = f'{label} failed with exit code {result.returncode}'
        write_log(message, log_path=log_path)
        raise RuntimeError(message)


def scoped_python_targets(repo_root: Path, paths: list[str]) -> list[str]:
    """Return unique in-repo Python files from a changed-file list."""
    scoped: list[str] = []
    seen: set[str] = set()
    for raw_path in paths:
        candidate = raw_path.strip()
        if not candidate or candidate in seen:
            continue
        target = repo_root / candidate
        if target.is_file() and target.suffix == '.py':
            scoped.append(candidate)
            seen.add(candidate)
    return scoped


def run_quality_gate(repo_root: Path, paths: list[str] | None = None) -> int:
    """Run the repo-owned quality gate, optionally scoped to changed Python files."""
    log_path = repo_root / 'logs' / 'quality-gate.log'
    write_log('=== Quality Gate ===', log_path=log_path)
    scoped_paths = scoped_python_targets(repo_root, paths or [])
    if paths and not scoped_paths:
        message = 'No Python files in scope. Skipping lint/format/test.'
        write_log(message, log_path=log_path)
        logger.warning(message)
        return 0

    if scoped_paths:
        run_quality_step(
            'ruff check --fix (scoped)',
            ['uv', 'run', 'ruff', 'check', '--fix', '--', *scoped_paths],
            cwd=repo_root,
            log_path=log_path,
        )
        run_quality_step(
            'ruff format (scoped)',
            ['uv', 'run', 'ruff', 'format', '--', *scoped_paths],
            cwd=repo_root,
            log_path=log_path,
        )
    else:
        run_quality_step(
            'ruff check --fix',
            ['uv', 'run', 'ruff', 'check', '--fix', '.'],
            cwd=repo_root,
            log_path=log_path,
        )
        run_quality_step(
            'ruff format',
            ['uv', 'run', 'ruff', 'format', '.'],
            cwd=repo_root,
            log_path=log_path,
        )

    run_quality_step(
        'pytest',
        ['uv', 'run', 'python', '-m', 'pytest'],
        cwd=repo_root,
        log_path=log_path,
    )
    return 0


def main() -> int:
    """CLI entrypoint for the repo-owned quality gate."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--paths', nargs='*', default=[])
    args = parser.parse_args()
    return run_quality_gate(ROOT, args.paths)


if __name__ == '__main__':
    raise SystemExit(main())
