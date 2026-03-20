# ruff: noqa: D101,D102,D103

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

AuditStatus = Literal[
    'satisfied', 'weak-evidence', 'missing', 'manual-review', 'structural'
]

REPO_ROOT = Path(__file__).resolve().parents[4]
PLAN_CANDIDATE_PATTERNS = ('*PLAN*.md', '*.plan.md')
PLAN_EXCLUDE_TOKENS = (
    'report',
    'requirements',
    'task',
    'tasks-',
    'plan_exec_report',
    'lazy-agent-report',
)


@dataclass(slots=True)
class ValidationResult:
    command: str
    returncode: int
    output: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass(slots=True)
class AuditEntry:
    line_number: int
    text: str
    status: AuditStatus
    reasons: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)


@dataclass(slots=True)
class PlanSection:
    number: str
    title: str
    heading_line: int
    lines: list[tuple[int, str]] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)
    path_references: list[str] = field(default_factory=list)

    @property
    def task_title(self) -> str:
        return f'{self.number} {self.title}'.strip()

    @property
    def combined_text(self) -> str:
        content = [self.title]
        content.extend(text for _, text in self.lines)
        return '\n'.join(content)


@dataclass(slots=True)
class ChecklistTask:
    number: str
    title: str
    checked: bool
    indent: int
    line_number: int
    children: list[ChecklistTask] = field(default_factory=list)

    @property
    def key(self) -> str:
        return normalize_text(self.title)


@dataclass(slots=True)
class TaskAuditEntry:
    task: ChecklistTask
    status: AuditStatus
    reasons: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)
    matching_section: str | None = None


def slugify(value: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug or 'plan'


def normalize_text(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', value.lower()).strip()


def resolve_path(path_value: str | None, *, repo_root: Path) -> Path | None:
    if not path_value:
        return None
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def discover_root_plan_candidates(repo_root: Path) -> list[Path]:
    candidates: dict[str, Path] = {}
    for pattern in PLAN_CANDIDATE_PATTERNS:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            if path.parent != repo_root:
                continue
            name = path.name.lower()
            if any(token in name for token in PLAN_EXCLUDE_TOKENS):
                continue
            candidates[str(path.resolve())] = path.resolve()
    return sorted(candidates.values(), key=lambda path: path.name.lower())


def resolve_plan_path(plan_value: str | None, *, repo_root: Path) -> Path:
    if plan_value:
        plan_path = resolve_path(plan_value, repo_root=repo_root)
        if plan_path is None or not plan_path.exists():
            msg = f'Plan file not found: {plan_value}'
            raise SystemExit(msg)
        return plan_path

    preferred = repo_root / 'REWORK_PLAN.md'
    if preferred.exists():
        return preferred.resolve()

    root_candidates = discover_root_plan_candidates(repo_root)
    if len(root_candidates) > 1:
        rendered = '\n'.join(f'- {path.relative_to(repo_root)}' for path in root_candidates)
        raise SystemExit(
            'Multiple repo-root implementation plans match autodetection.\n'
            f'{rendered}\n'
            'Pass --plan explicitly.'
        )
    if len(root_candidates) == 1:
        return root_candidates[0]

    fallback = repo_root / 'docs' / 'PLAN.md'
    if fallback.exists():
        return fallback.resolve()
    raise SystemExit('Unable to autodetect a plan file. Pass --plan explicitly.')


def derive_task_list_path(plan_path: Path, *, repo_root: Path) -> Path:
    return repo_root / 'tasks' / f'tasks-{slugify(plan_path.stem)}.md'


def resolve_task_list_path(
    task_list_value: str | None, *, plan_path: Path, repo_root: Path
) -> Path:
    if task_list_value:
        resolved = resolve_path(task_list_value, repo_root=repo_root)
        if resolved is None:
            raise SystemExit(f'Unable to resolve task list path: {task_list_value}')
        return resolved
    return derive_task_list_path(plan_path, repo_root=repo_root)


def is_structural_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if stripped.startswith('#'):
        return True
    if stripped.startswith('<') and stripped.endswith('>'):
        return True
    if re.fullmatch(r'[-=*`_]{3,}', stripped):
        return True
    return False


def extract_path_references(text: str) -> list[str]:
    matches: list[str] = []

    markdown_link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    for label, target in markdown_link_pattern.findall(text):
        for value in (label, target):
            if '/' in value or '\\' in value:
                matches.append(value.strip('`'))

    inline_code_pattern = re.compile(r'`([^`]+)`')
    for inline in inline_code_pattern.findall(text):
        if '/' in inline or '\\' in inline:
            matches.append(inline)

    raw_path_pattern = re.compile(r'(?<![A-Za-z0-9_.-])(?:[A-Za-z]:\\|\.{0,2}[\\/])?[\w.\-\\/]+\.([A-Za-z0-9]{1,8})')
    for match in raw_path_pattern.finditer(text):
        matches.append(match.group(0))

    cleaned: list[str] = []
    seen: set[str] = set()
    for match in matches:
        candidate = match.strip().rstrip('.,:;)')
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        cleaned.append(candidate)
    return cleaned


def extract_validation_commands(text: str) -> list[str]:
    commands: list[str] = []
    validation_match = re.search(r'Validation:\s*(.+)$', text)
    if validation_match:
        commands.append(validation_match.group(1).strip().strip('`'))
    for inline in re.findall(r'`([^`]+)`', text):
        stripped = inline.strip()
        if stripped.startswith(('uv run ', 'python ', 'pytest ', 'ruff ')):
            commands.append(stripped)
    return list(dict.fromkeys(commands))


def run_validation(command: str, *, repo_root: Path) -> ValidationResult:
    completed = subprocess.run(
        command,
        cwd=repo_root,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout or '') + (completed.stderr or '')
    return ValidationResult(
        command=command,
        returncode=completed.returncode,
        output=output.strip(),
    )


def _fallback_identifier_hits(token: str, *, repo_root: Path) -> list[str]:
    evidence: list[str] = []
    normalized_token = token.casefold()
    for path in repo_root.rglob('*'):
        if not path.is_file():
            continue
        if any(part in {'logs', 'tasks'} for part in path.parts):
            continue
        if path.suffix.lower() == '.md':
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            if normalized_token not in line.casefold():
                continue
            evidence.append(
                f'{path.relative_to(repo_root).as_posix()}:{line_number}:{line.strip()}'
            )
            if len(evidence) >= 3:
                return evidence
    return evidence


def repo_identifier_hits(text: str, *, repo_root: Path) -> list[str]:
    tokens = re.findall(r'[A-Za-z][A-Za-z0-9_]{3,}', text)
    candidate_tokens = [
        token
        for token in tokens
        if token.lower() not in {'plan', 'task', 'tests', 'proof', 'verified'}
    ]
    evidence: list[str] = []
    seen: set[str] = set()
    rg_path = shutil.which('rg')
    for token in candidate_tokens[:6]:
        if rg_path is None:
            token_hits = _fallback_identifier_hits(token, repo_root=repo_root)
        else:
            try:
                completed = subprocess.run(
                    [
                        rg_path,
                        '-n',
                        '--fixed-strings',
                        '--glob',
                        '!logs/**',
                        '--glob',
                        '!tasks/**',
                        '--glob',
                        '!*.md',
                        token,
                        str(repo_root),
                    ],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError:
                token_hits = _fallback_identifier_hits(token, repo_root=repo_root)
            else:
                if completed.returncode != 0 or not completed.stdout.strip():
                    continue
                token_hits = [completed.stdout.splitlines()[0]]
        for line in token_hits:
            if line in seen:
                continue
            seen.add(line)
            evidence.append(line)
            if len(evidence) >= 3:
                return evidence
    return evidence


def classify_text_entry(
    text: str, *, repo_root: Path, run_validations: bool
) -> tuple[AuditStatus, list[str], list[str], list[ValidationResult]]:
    if is_structural_line(text):
        return 'structural', ['structural line'], [], []

    reasons: list[str] = []
    evidence: list[str] = []
    validation_results: list[ValidationResult] = []
    resolved_paths: list[Path] = []

    for reference in extract_path_references(text):
        ref_path = resolve_path(reference, repo_root=repo_root)
        if ref_path is not None and ref_path.exists():
            resolved_paths.append(ref_path)
            try:
                rendered = ref_path.relative_to(repo_root)
            except ValueError:
                rendered = ref_path
            evidence.append(f'path exists: {rendered}')
        else:
            reasons.append(f'missing path: {reference}')

    if run_validations:
        for command in extract_validation_commands(text):
            result = run_validation(command, repo_root=repo_root)
            validation_results.append(result)
            if result.passed:
                evidence.append(f'validation passed: {command}')
            else:
                reasons.append(f'validation failed: {command}')

    identifier_hits = repo_identifier_hits(text, repo_root=repo_root)
    evidence.extend(identifier_hits)

    if validation_results and all(result.passed for result in validation_results):
        return 'satisfied', reasons, evidence, validation_results
    if resolved_paths and not any(reason.startswith('missing path:') for reason in reasons):
        return 'satisfied', reasons, evidence, validation_results
    if reasons and not evidence:
        return 'missing', reasons, evidence, validation_results
    if evidence:
        return 'weak-evidence', reasons, evidence, validation_results
    return 'manual-review', ['no machine-verifiable evidence'], [], validation_results


def audit_plan(
    plan_path: Path, *, repo_root: Path, run_validations: bool
) -> list[AuditEntry]:
    entries: list[AuditEntry] = []
    for line_number, text in enumerate(plan_path.read_text(encoding='utf-8').splitlines(), start=1):
        if not text.strip():
            continue
        status, reasons, evidence, validation_results = classify_text_entry(
            text,
            repo_root=repo_root,
            run_validations=run_validations,
        )
        entries.append(
            AuditEntry(
                line_number=line_number,
                text=text.rstrip(),
                status=status,
                reasons=reasons,
                evidence=evidence,
                validation_results=validation_results,
            )
        )
    return entries


def parse_plan_sections(plan_path: Path) -> list[PlanSection]:
    section_pattern = re.compile(r'^\s*###\s+(\d+\.)\s+(.+?)\s*$')
    higher_heading_pattern = re.compile(r'^\s*##\s+')
    bullet_pattern = re.compile(r'^\s*-\s+(.+?)\s*$')
    sections: list[PlanSection] = []
    current: PlanSection | None = None

    for line_number, text in enumerate(plan_path.read_text(encoding='utf-8').splitlines(), start=1):
        section_match = section_pattern.match(text)
        if section_match:
            current = PlanSection(
                number=section_match.group(1),
                title=section_match.group(2).strip(),
                heading_line=line_number,
            )
            sections.append(current)
            continue
        if current is not None and higher_heading_pattern.match(text):
            current = None
            continue
        if current is None:
            continue
        current.lines.append((line_number, text))
        bullet_match = bullet_pattern.match(text)
        if bullet_match:
            bullet_text = bullet_match.group(1).strip()
            current.bullets.append(bullet_text)
            current.path_references.extend(extract_path_references(bullet_text))
        else:
            current.path_references.extend(extract_path_references(text))

    return sections


def render_task_list(plan_path: Path, sections: list[PlanSection], *, repo_root: Path) -> str:
    relevant_files = [plan_path.relative_to(repo_root).as_posix()]
    relevant_files.extend(
        path
        for section in sections
        for path in section.path_references
        if not Path(path).is_absolute()
    )
    relevant_files.extend(
        [
            '.codex/skills/lazy-agent/scripts/audit_plan_completion.py',
            f'tasks/tasks-{slugify(plan_path.stem)}.md',
        ]
    )

    deduped_files: list[str] = []
    seen: set[str] = set()
    for path in relevant_files:
        candidate = path.replace('\\', '/')
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped_files.append(candidate)

    lines = ['## Relevant Files', '']
    for file_path in deduped_files:
        lines.append(f'- `{file_path}` - Referenced by the implementation plan or audit workflow.')
    lines.extend(
        [
            '',
            '### Notes',
            '',
            '- Keep this checklist aligned with the implementation plan as work completes.',
            '- Update the markdown checkboxes immediately after completing each sub-task.',
            '',
            '## Instructions for Completing Tasks',
            '',
            '**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`.',
            '',
            'Example:',
            '- `- [ ] 1.1 Read file` -> `- [x] 1.1 Read file` (after completing)',
            '',
            'Update the file after completing each sub-task, not just after completing an entire parent task.',
            '',
            '## Tasks',
            '',
            '- [ ] 0.0 Create feature branch',
            f'  - [ ] 0.1 Create and checkout a new branch for this feature (e.g., `git checkout -b feature/{slugify(plan_path.stem)}`)',
        ]
    )

    for index, section in enumerate(sections, start=1):
        lines.append(f'- [ ] {index}.0 {section.title}')
        subtasks = section.bullets or ['Review the implementation scope and complete this section.']
        for sub_index, bullet in enumerate(subtasks, start=1):
            lines.append(f'  - [ ] {index}.{sub_index} {bullet}')
    lines.append('')
    return '\n'.join(lines)


def bootstrap_task_list(
    plan_path: Path, task_list_path: Path, *, repo_root: Path
) -> None:
    task_list_path.parent.mkdir(parents=True, exist_ok=True)
    sections = parse_plan_sections(plan_path)
    rendered = render_task_list(plan_path, sections, repo_root=repo_root)
    task_list_path.write_text(rendered, encoding='utf-8')


def load_task_list(task_list_path: Path) -> list[ChecklistTask]:
    if not task_list_path.exists():
        return []

    task_pattern = re.compile(
        r'^(?P<indent>\s*)-\s+\[(?P<checked>[ xX])\]\s+(?P<number>\d+\.\d+)\s+(?P<title>.+?)\s*$'
    )
    tasks: list[ChecklistTask] = []
    stack: list[ChecklistTask] = []

    for line_number, line in enumerate(task_list_path.read_text(encoding='utf-8').splitlines(), start=1):
        match = task_pattern.match(line)
        if not match:
            continue
        task = ChecklistTask(
            number=match.group('number'),
            title=match.group('title').strip(),
            checked=match.group('checked').lower() == 'x',
            indent=len(match.group('indent')),
            line_number=line_number,
        )
        while stack and stack[-1].indent >= task.indent:
            stack.pop()
        if stack:
            stack[-1].children.append(task)
        else:
            tasks.append(task)
        stack.append(task)
    return tasks


def flatten_tasks(tasks: list[ChecklistTask]) -> list[ChecklistTask]:
    items: list[ChecklistTask] = []
    for task in tasks:
        items.append(task)
        items.extend(flatten_tasks(task.children))
    return items


def section_lookup(sections: list[PlanSection]) -> dict[str, PlanSection]:
    lookup: dict[str, PlanSection] = {}
    for section in sections:
        keys = {
            normalize_text(section.title),
            normalize_text(section.task_title),
        }
        for bullet in section.bullets:
            keys.add(normalize_text(bullet))
        for key in keys:
            if key:
                lookup[key] = section
    return lookup


def audit_checklist(
    tasks: list[ChecklistTask],
    *,
    sections: list[PlanSection],
    repo_root: Path,
    run_validations: bool,
) -> list[TaskAuditEntry]:
    lookup = section_lookup(sections)
    audits: list[TaskAuditEntry] = []

    for task in flatten_tasks(tasks):
        section = lookup.get(task.key)
        if section is None or not task.number.endswith('.0'):
            text = task.title
        else:
            text = section.combined_text
        status, reasons, evidence, validation_results = classify_text_entry(
            text,
            repo_root=repo_root,
            run_validations=run_validations,
        )
        audits.append(
            TaskAuditEntry(
                task=task,
                status=status,
                reasons=reasons,
                evidence=evidence,
                validation_results=validation_results,
                matching_section=section.task_title if section else None,
            )
        )
    return audits


def render_validation_snippets(results: list[ValidationResult]) -> list[str]:
    lines: list[str] = []
    for result in results:
        status = 'pass' if result.passed else f'fail ({result.returncode})'
        lines.append(f'  - `{result.command}` -> {status}')
    return lines


def render_report(
    *,
    plan_path: Path,
    task_list_path: Path,
    line_entries: list[AuditEntry],
    task_entries: list[TaskAuditEntry],
    repo_root: Path,
) -> str:
    status_counts: dict[AuditStatus, int] = {
        'satisfied': 0,
        'weak-evidence': 0,
        'missing': 0,
        'manual-review': 0,
        'structural': 0,
    }
    for entry in line_entries:
        status_counts[entry.status] += 1

    checked_tasks = [entry for entry in task_entries if entry.task.checked]
    unchecked_tasks = [entry for entry in task_entries if not entry.task.checked]
    checked_without_evidence = [
        entry for entry in checked_tasks if entry.status in {'missing', 'manual-review'}
    ]
    unchecked_with_evidence = [
        entry for entry in unchecked_tasks if entry.status in {'satisfied', 'weak-evidence'}
    ]
    resume_here = [
        entry
        for entry in unchecked_tasks
        if entry.task.number.endswith('.0') and not entry.task.number.startswith('0.')
    ][:5]

    lines = [
        '# Lazy-Agent Plan Audit',
        '',
        f'- Plan: `{plan_path.relative_to(repo_root).as_posix()}`',
        f'- Task List: `{task_list_path.relative_to(repo_root).as_posix()}`',
        '',
        '## Task Summary',
        '',
        f'- Checked tasks: {len(checked_tasks)}',
        f'- Unchecked tasks: {len(unchecked_tasks)}',
        f'- Checked tasks lacking repo evidence: {len(checked_without_evidence)}',
        f'- Unchecked tasks with repo evidence: {len(unchecked_with_evidence)}',
        '',
        '## Resume Here',
        '',
    ]

    if resume_here:
        for entry in resume_here:
            lines.append(
                f'- `{entry.task.number}` {entry.task.title} '
                f'[{entry.status}]'
            )
    else:
        lines.append('- (no unchecked tasks found)')

    lines.extend(['', '## Checklist Audit', ''])
    if task_entries:
        for entry in task_entries:
            checkmark = 'x' if entry.task.checked else ' '
            section_note = (
                f' -> section `{entry.matching_section}`'
                if entry.matching_section
                else ' -> no matching plan section'
            )
            lines.append(
                f'- [{checkmark}] `{entry.task.number}` {entry.task.title}: '
                f'`{entry.status}`{section_note}'
            )
            for reason in entry.reasons[:3]:
                lines.append(f'  - reason: {reason}')
            for evidence in entry.evidence[:3]:
                lines.append(f'  - evidence: {evidence}')
            lines.extend(render_validation_snippets(entry.validation_results))
    else:
        lines.append('- (no checklist present)')

    lines.extend(
        [
            '',
            '## Plan Line Summary',
            '',
            f"- satisfied: {status_counts['satisfied']}",
            f"- weak-evidence: {status_counts['weak-evidence']}",
            f"- missing: {status_counts['missing']}",
            f"- manual-review: {status_counts['manual-review']}",
            f"- structural: {status_counts['structural']}",
            '',
            '## High-Risk Lines',
            '',
        ]
    )

    high_risk = [
        entry
        for entry in line_entries
        if entry.status in {'missing', 'manual-review'}
    ][:15]
    if high_risk:
        for entry in high_risk:
            lines.append(f'- L{entry.line_number}: `{entry.status}` {entry.text}')
    else:
        lines.append('- (no high-risk lines)')

    lines.extend(['', '## Line-by-Line Audit', ''])
    for entry in line_entries:
        lines.append(f'- L{entry.line_number} `{entry.status}`: {entry.text}')
        for reason in entry.reasons[:3]:
            lines.append(f'  - reason: {reason}')
        for evidence in entry.evidence[:3]:
            lines.append(f'  - evidence: {evidence}')
        lines.extend(render_validation_snippets(entry.validation_results))

    lines.append('')
    return '\n'.join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Audit actual implementation progress against a plan and task list.'
    )
    parser.add_argument('--plan', help='Implementation plan path. Autodetects when omitted.')
    parser.add_argument('--task-list', help='Task list path. Defaults to tasks/tasks-<plan-stem>.md.')
    parser.add_argument('--repo-root', default=str(REPO_ROOT), help='Repository root.')
    parser.add_argument('--output', help='Markdown output path.')
    parser.add_argument(
        '--run-validations',
        action='store_true',
        help='Execute validation commands referenced by the plan/task list.',
    )
    parser.add_argument(
        '--bootstrap-task-list',
        action='store_true',
        help='Create the default task list if it does not already exist.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    plan_path = resolve_plan_path(args.plan, repo_root=repo_root)
    task_list_path = resolve_task_list_path(
        args.task_list,
        plan_path=plan_path,
        repo_root=repo_root,
    )

    if args.bootstrap_task_list and not task_list_path.exists():
        bootstrap_task_list(plan_path, task_list_path, repo_root=repo_root)

    sections = parse_plan_sections(plan_path)
    line_entries = audit_plan(
        plan_path,
        repo_root=repo_root,
        run_validations=args.run_validations,
    )
    task_entries = audit_checklist(
        load_task_list(task_list_path),
        sections=sections,
        repo_root=repo_root,
        run_validations=args.run_validations,
    )

    output_path = (
        resolve_path(args.output, repo_root=repo_root)
        if args.output
        else repo_root / 'logs' / f'lazy-agent-report-{slugify(plan_path.stem)}.md'
    )
    if output_path is None:
        raise SystemExit('Unable to resolve output path.')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_report(
            plan_path=plan_path,
            task_list_path=task_list_path,
            line_entries=line_entries,
            task_entries=task_entries,
            repo_root=repo_root,
        ),
        encoding='utf-8',
    )
    print(output_path.relative_to(repo_root).as_posix())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
