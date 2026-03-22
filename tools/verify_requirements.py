from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parents[1]
LOGS_PATH = ROOT / 'logs'
REPORT_PATH = ROOT / 'docs' / 'requirements-report.md'
EVIDENCE_PATH = LOGS_PATH / 'verify-requirements-evidence.md'
REPO_ROOTS = ('src', 'include', 'host', 'tools', 'docs', 'scripts', 'tests', 'proto')
PLACEHOLDER_MARKERS = (
    'TODO',
    'placeholder',
    'should implement',
    'This file should implement',
    'This header should define',
    'Additional functions and logic can be added here',
    'Worker logic here',
)


def is_mature_file(path: str, raw: str) -> bool:
    """Return True when heuristics classify a file as mature."""
    if not raw:
        return False
    if 'evidence: mature' in raw:
        return True

    normalized = path.replace('\\', '/')
    if normalized.endswith('_pb2.py') or normalized.endswith('_pb2_grpc.py'):
        return True

    ext = Path(path).suffix.lower()
    size = len(raw)
    if ext == '.py':
        def_count = raw.count('def ')
        class_count = raw.count('class ')
        return size >= 1500 and (def_count >= 3 or class_count >= 2)
    if ext == '.ps1':
        return size >= 500 and raw.lower().count('function ') >= 1
    if ext == '.md':
        return size >= 2000
    if ext in {'.ini', '.cpp', '.hpp', '.h', '.proto'}:
        return size >= 500
    return size >= 1500


def is_placeholder(path: str, raw: str) -> bool:
    """Return True when heuristics classify a file as placeholder-like."""
    if not raw:
        return True
    if 'evidence: mature' in raw or is_mature_file(path, raw):
        return False
    if len(raw) < 2000 and 'minimal' in raw.lower():
        return True
    return any(marker.lower() in raw.lower() for marker in PLACEHOLDER_MARKERS)


def is_thin_code(path: str, raw: str) -> bool:
    """Return True when code exists but is structurally too thin."""
    normalized = path.replace('\\', '/')
    if normalized.endswith('_pb2.py') or normalized.endswith('_pb2_grpc.py'):
        return False

    ext = Path(path).suffix.lower()
    if ext not in {'.py', '.ps1', '.cpp', '.hpp', '.h', '.proto'}:
        return False
    if not raw:
        return True
    if len(raw) < 500:
        return True
    if ext == '.py':
        def_count = raw.count('def ')
        class_count = raw.count('class ')
        if 'def' not in raw:
            return True
        if len(raw) < 800 and def_count < 2:
            return True
        if len(raw) >= 1500 and (def_count >= 3 or class_count >= 2):
            return False
    if ext == '.ps1':
        if len(raw) >= 500 and raw.lower().count('function ') >= 1:
            return False
    return False


def read_file_safe(path: Path) -> str:
    """Read a file as UTF-8, returning an empty string on failure."""
    try:
        return path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return ''


def write_evidence_index(
    *,
    evidence_path: Path,
    roots: list[Path],
    repo_root: Path,
) -> None:
    """Write the repository evidence index used by verification tooling."""
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '# Repository Evidence Index',
        '',
        f'Generated: {__import__("datetime").datetime.now().astimezone().isoformat()}',
        '',
        'Legend:',
        '- placeholder=true: file is empty or contains explicit scaffolding markers',
        '  (TODO, placeholder, should implement, etc.). Large structured files are',
        '  not marked placeholder. Use # evidence: mature to opt out.',
        '',
    ]

    for root in roots:
        if not root.exists():
            continue
        for file_path in sorted(root.rglob('*')):
            if not file_path.is_file():
                continue
            if '__pycache__' in file_path.parts:
                continue
            if file_path.name == '__init__.py' and file_path.stat().st_size == 0:
                continue

            raw = read_file_safe(file_path)
            placeholder = is_placeholder(str(file_path), raw) or is_thin_code(
                str(file_path), raw
            )
            markers = [
                marker
                for marker in PLACEHOLDER_MARKERS
                if marker.lower() in raw.lower()
            ]
            if file_path.stat().st_size == 0:
                markers.append('empty-file')
            rel = file_path.relative_to(repo_root).as_posix()
            lines.append(
                f'- path="{rel}" size={file_path.stat().st_size} '
                f'placeholder={"true" if placeholder else "false"} '
                f'markers="{";".join(markers)}"'
            )

    evidence_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def run_regrade(*, repo_root: Path) -> None:
    """Generate the requirements report via the proof verifier."""
    result = subprocess.run(
        ['uv', 'run', 'python', 'tools/proof_verifier.py', '--regrade'],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            'Evidence-based verification report generation failed.\n'
            f'{(result.stdout or "")}{(result.stderr or "")}'.strip()
        )


def main() -> int:
    """CLI entrypoint for repo-owned verify-requirements."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    LOGS_PATH.mkdir(parents=True, exist_ok=True)
    roots = [ROOT / part for part in REPO_ROOTS]
    write_evidence_index(evidence_path=EVIDENCE_PATH, roots=roots, repo_root=ROOT)
    run_regrade(repo_root=ROOT)

    logger.info('Wrote {}', REPORT_PATH)
    logger.info('Evidence index: {}', EVIDENCE_PATH)

    if args.debug:
        logger.info('Debug mode enabled for verify_requirements.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
