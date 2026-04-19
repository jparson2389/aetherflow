"""Wrap GFM pipe tables with Prettier ignore comments.

Follows ``.claude/rules/markdown-tables.md``:

- ``<!-- prettier-ignore-start -->`` immediately before the table
- ``<!-- prettier-ignore-end -->`` immediately after the table

Skips:

- lines inside fenced `` ``` `` code blocks
- tables already fully inside a prettier-ignore region
- tables that already have the start/end comments adjacent (skipping blank lines)
"""
# ruff: noqa: D103

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PRETTIER_START = '<!-- prettier-ignore-start -->'
PRETTIER_END = '<!-- prettier-ignore-end -->'

RE_PRETTIER_START = re.compile(r'^\s*<!--\s*prettier-ignore-start\s*-->\s*$')
RE_PRETTIER_END = re.compile(r'^\s*<!--\s*prettier-ignore-end\s*-->\s*$')


def is_table_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith('<!--'):
        return False
    return s.startswith('|')


def code_fence_mask(lines: list[str]) -> list[bool]:
    """Mark which lines are inside a fenced code block (fence lines are False)."""
    inside = False
    mask: list[bool] = []
    for line in lines:
        if line.strip().startswith('```'):
            mask.append(False)
            inside = not inside
        else:
            mask.append(inside)
    return mask


def find_table_blocks(lines: list[str], mask: list[bool]) -> list[tuple[int, int]]:
    blocks: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        if mask[i] or not is_table_line(lines[i]):
            i += 1
            continue
        start = i
        while i < n and not mask[i] and is_table_line(lines[i]):
            i += 1
        blocks.append((start, i - 1))
    return blocks


def find_prettier_regions(lines: list[str]) -> list[tuple[int, int]]:
    """Inclusive line indices of prettier-ignore regions (including comment lines)."""
    regions: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        if RE_PRETTIER_START.match(lines[i]):
            start = i
            j = i + 1
            while j < n and not RE_PRETTIER_END.match(lines[j]):
                j += 1
            if j < n:
                regions.append((start, j))
                i = j + 1
            else:
                i += 1
        else:
            i += 1
    return regions


def table_in_any_region(ts: int, te: int, regions: list[tuple[int, int]]) -> bool:
    for rs, rend in regions:
        if rs < ts and te < rend:
            return True
    return False


def has_adjacent_prettier_wrapper(lines: list[str], ts: int, te: int) -> bool:
    """Table is wrapped by adjacent prettier comments (blank lines allowed)."""
    i = ts - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    if i < 0 or not RE_PRETTIER_START.match(lines[i]):
        return False
    j = te + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j >= len(lines):
        return False
    return bool(RE_PRETTIER_END.match(lines[j]))


def should_wrap_table(
    lines: list[str],
    ts: int,
    te: int,
    regions: list[tuple[int, int]],
) -> bool:
    if table_in_any_region(ts, te, regions):
        return False
    if has_adjacent_prettier_wrapper(lines, ts, te):
        return False
    return True


def wrap_tables_in_lines(lines: list[str]) -> tuple[list[str], int]:
    """Return new lines and count of tables wrapped."""
    mask = code_fence_mask(lines)
    blocks = find_table_blocks(lines, mask)
    regions = find_prettier_regions(lines)

    to_wrap = [
        (ts, te) for ts, te in blocks if should_wrap_table(lines, ts, te, regions)
    ]
    if not to_wrap:
        return lines, 0

    out = list(lines)
    for ts, te in sorted(to_wrap, key=lambda b: b[0], reverse=True):
        out.insert(te + 1, PRETTIER_END)
        out.insert(ts, PRETTIER_START)
    return out, len(to_wrap)


DEFAULT_SKIP_DIRS = frozenset(
    {
        '.git',
        '.hg',
        '.svn',
        '.venv',
        'venv',
        'node_modules',
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.ruff_cache',
        'dist',
        'build',
        'out',
        'logs',
    }
)


def iter_markdown_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob('*.md'):
        if any(p in DEFAULT_SKIP_DIRS for p in path.parts):
            continue
        files.append(path)
    files.sort()
    return files


def process_file(path: Path, dry_run: bool) -> int:
    text = path.read_text(encoding='utf-8')
    raw = text.splitlines(keepends=False)
    new_lines, n = wrap_tables_in_lines(raw)
    if n == 0:
        return 0
    if dry_run:
        print(f'{path}: would wrap {n} table(s)')
        return n
    ends_with_newline = text.endswith('\n')
    out = '\n'.join(new_lines)
    if ends_with_newline:
        out += '\n'
    path.write_text(out, encoding='utf-8', newline='\n')
    print(f'{path}: wrapped {n} table(s)')
    return n


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Wrap GFM pipe tables with Prettier ignore comments (see .claude/rules/markdown-tables.md).'
    )
    parser.add_argument(
        '--root',
        type=Path,
        default=REPO_ROOT,
        help='Repository root (default: repo containing tools/)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print files that would change without writing',
    )
    parser.add_argument(
        'paths',
        nargs='*',
        type=Path,
        help='Optional markdown files or directories (default: all *.md under --root)',
    )
    args = parser.parse_args()

    if args.paths:
        md_files: list[Path] = []
        for p in args.paths:
            p = p.resolve()
            if p.is_file():
                if p.suffix.lower() == '.md':
                    md_files.append(p)
            elif p.is_dir():
                md_files.extend(iter_markdown_files(p))
            else:
                print(f'Skip missing path: {p}', file=sys.stderr)
        md_files = sorted(set(md_files))
    else:
        md_files = iter_markdown_files(args.root.resolve())

    total_tables = 0
    total_files = 0
    for path in md_files:
        n = process_file(path, args.dry_run)
        if n:
            total_tables += n
            total_files += 1

    action = 'Would wrap' if args.dry_run else 'Wrapped'
    print(f'{action} {total_tables} table(s) in {total_files} file(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
