#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from loguru import logger

SEVERITY_ORDER: Final[dict[str, int]] = {
    'HIGH': 0,
    'MEDIUM': 1,
    'LOW': 2,
}
THIRD_PARTY_MARKERS: Final[tuple[str, ...]] = (
    '/.venv/',
    '/venv/',
    '/site-packages/',
    '/dist-packages/',
)


@dataclass(slots=True)
class Issue:
    """Represent a single Bandit issue block.

    Attributes:
        title: Short Bandit rule label.
        description: Human-readable finding description.
        test_id: Bandit test identifier.
        severity: Severity string as reported by Bandit.
        confidence: Confidence string as reported by Bandit.
        file_path: Normalized relative file path.
        line_number: Source line number.
        code_snippet: Optional code excerpt from the report.

    """

    title: str
    description: str
    test_id: str
    severity: str
    confidence: str
    file_path: str
    line_number: int
    code_snippet: str = ''

    @property
    def is_third_party(self) -> bool:
        """Return whether the finding points at a dependency path."""
        normalized = f'/{self.file_path.strip("/").lower()}/'
        return any(marker in normalized for marker in THIRD_PARTY_MARKERS)

    @property
    def location(self) -> str:
        """Return a compact file and line reference."""
        return f'{self.file_path}:{self.line_number}'


@dataclass(slots=True)
class ReportSummary:
    """Represent parsed report data.

    Attributes:
        loc: Total lines of code from the report metrics.
        nosec: Number of skipped lines from the report metrics.
        issues: Parsed issue collection.

    """

    loc: int
    nosec: int
    issues: list[Issue]

    @property
    def repo_issues(self) -> list[Issue]:
        """Return findings located in repository-controlled files."""
        return [issue for issue in self.issues if not issue.is_third_party]

    @property
    def third_party_issues(self) -> list[Issue]:
        """Return findings located in dependencies or virtualenv paths."""
        return [issue for issue in self.issues if issue.is_third_party]


def _normalize_whitespace(value: str) -> str:
    """Collapse HTML-derived whitespace to single spaces.

    Args:
        value: Raw HTML or extracted text.

    Returns:
        Cleaned text with entities unescaped.

    """
    decoded = html.unescape(value)
    return re.sub(r'\s+', ' ', decoded).strip()


def _normalize_path(path_text: str) -> str:
    """Normalize Bandit report paths to slash-separated relative paths.

    Args:
        path_text: Raw path text from the HTML report.

    Returns:
        Cleaned path string suitable for display.

    """
    normalized = _normalize_whitespace(path_text).replace('\\', '/')
    while normalized.startswith('./'):
        normalized = normalized[2:]
    return normalized.lstrip('/')


def _extract_required(pattern: str, content: str, field_name: str) -> str:
    """Extract a required field from a chunk of report HTML.

    Args:
        pattern: Regex pattern with a single capture group.
        content: HTML chunk to inspect.
        field_name: Friendly field name for errors.

    Returns:
        Extracted string value.

    Raises:
        ValueError: If the field is missing from the chunk.

    """
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match is None:
        raise ValueError(f'Missing {field_name!r} in issue block.')
    return _normalize_whitespace(match.group(1))


def parse_bandit_html(report_path: Path) -> ReportSummary:
    """Parse a Bandit HTML report into structured summary data.

    Args:
        report_path: Path to the HTML report.

    Returns:
        Parsed report summary data.

    """
    content = report_path.read_text(encoding='utf-8')
    loc = int(_extract_required(r'<span id="loc">(\d+)</span>', content, 'loc'))
    nosec = int(_extract_required(r'<span id="nosec">(\d+)</span>', content, 'nosec'))

    issues: list[Issue] = []
    for chunk in re.split(r'<div id="issue-\d+">', content)[1:]:
        title = _extract_required(r'<b>\s*([^:<]+):\s*</b>', chunk, 'issue title')
        description = _extract_required(
            r'<b>\s*[^:<]+:\s*</b>\s*(.*?)<br>',
            chunk,
            'issue description',
        )
        test_id = _extract_required(
            r'<b>\s*Test ID:\s*</b>\s*([^<]+)<br>', chunk, 'test'
        )
        severity = _extract_required(
            r'<b>\s*Severity:\s*</b>\s*([^<]+)<br>',
            chunk,
            'severity',
        ).upper()
        confidence = _extract_required(
            r'<b>\s*Confidence:\s*</b>\s*([^<]+)<br>',
            chunk,
            'confidence',
        ).upper()
        file_path = _normalize_path(
            _extract_required(
                r'<b>\s*File:\s*</b>\s*<a [^>]*>(.*?)</a><br>',
                chunk,
                'file path',
            )
        )
        line_number = int(
            _extract_required(
                r'<b>\s*Line number:\s*</b>\s*(\d+)<br>',
                chunk,
                'line number',
            )
        )
        code_match = re.search(r'<pre>(.*?)</pre>', chunk, re.DOTALL | re.IGNORECASE)
        code_snippet = _normalize_whitespace(code_match.group(1)) if code_match else ''
        issues.append(
            Issue(
                title=title,
                description=description,
                test_id=test_id,
                severity=severity,
                confidence=confidence,
                file_path=file_path,
                line_number=line_number,
                code_snippet=code_snippet,
            )
        )

    return ReportSummary(loc=loc, nosec=nosec, issues=issues)


def _severity_sort_key(issue: Issue) -> tuple[int, str, str, int]:
    """Build a stable priority sort key for findings.

    Args:
        issue: Issue to rank.

    Returns:
        Tuple used for sorting.

    """
    return (
        SEVERITY_ORDER.get(issue.severity, len(SEVERITY_ORDER)),
        issue.test_id,
        issue.file_path,
        issue.line_number,
    )


def render_summary(summary: ReportSummary, max_findings: int = 5) -> str:
    """Render a concise, human-readable summary for the parsed report.

    Args:
        summary: Parsed report summary.
        max_findings: Maximum in-repo findings to list explicitly.

    Returns:
        Multi-line text summary.

    """
    severity_counts = Counter(issue.severity for issue in summary.issues)
    test_counts = Counter(issue.test_id for issue in summary.issues)
    repo_hotspots = Counter(issue.file_path for issue in summary.repo_issues)
    lines = [
        'Bandit report summary',
        '',
        f'Lines of code: {summary.loc}',
        f'Suppressed with #nosec: {summary.nosec}',
        f'Total issues: {len(summary.issues)}',
        f'In-repo findings: {len(summary.repo_issues)}',
        f'Third-party findings: {len(summary.third_party_issues)}',
        (
            'Severity mix: '
            f'HIGH {severity_counts.get("HIGH", 0)} | '
            f'MEDIUM {severity_counts.get("MEDIUM", 0)} | '
            f'LOW {severity_counts.get("LOW", 0)}'
        ),
    ]

    if summary.third_party_issues and len(summary.third_party_issues) > len(
        summary.repo_issues
    ):
        lines.append('Most findings come from third-party or virtualenv paths.')

    if test_counts:
        common_tests = ', '.join(
            f'{test_id} ({count})'
            for test_id, count in sorted(
                test_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        )
        lines.append(f'Most common tests: {common_tests}')

    if repo_hotspots:
        hotspot_text = ', '.join(
            f'{path} ({count})'
            for path, count in sorted(
                repo_hotspots.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        )
        lines.append(f'Repo hotspots: {hotspot_text}')

    prioritized_repo_issues = sorted(summary.repo_issues, key=_severity_sort_key)
    if prioritized_repo_issues:
        lines.extend(['', 'Priority in-repo findings:'])
        for issue in prioritized_repo_issues[:max_findings]:
            lines.append(
                f'- [{issue.severity}/{issue.confidence}] {issue.test_id} '
                f'at {issue.location} - {issue.description}'
            )
    elif summary.third_party_issues:
        lines.extend(
            [
                '',
                'Priority note:',
                '- No in-repo findings were detected; the current report appears to '
                'be dependency-heavy.',
            ]
        )
    else:
        lines.extend(['', 'Priority note:', '- No findings detected.'])

    if summary.third_party_issues:
        sample_third_party = ', '.join(
            issue.location
            for issue in sorted(summary.third_party_issues, key=_severity_sort_key)[:3]
        )
        lines.extend(
            [
                '',
                f'Third-party examples: {sample_third_party}',
            ]
        )

    return '\n'.join(lines).strip() + '\n'


def summarize_report(report_path: Path, *, max_findings: int = 5) -> str:
    """Parse and summarize one Bandit HTML report.

    Args:
        report_path: Path to the HTML report.
        max_findings: Maximum number of in-repo findings to list explicitly.

    Returns:
        Human-readable report summary text.

    """
    summary = parse_bandit_html(report_path)
    return render_summary(summary=summary, max_findings=max_findings)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured argument parser.

    """
    parser = argparse.ArgumentParser(
        description='Summarize a Bandit HTML report into a concise text report.'
    )
    parser.add_argument('report_path', type=Path, help='Path to a Bandit HTML report.')
    parser.add_argument(
        '--max-findings',
        type=int,
        default=5,
        help='Maximum number of in-repo findings to list explicitly.',
    )
    return parser


def main() -> int:
    """Run the summary CLI.

    Returns:
        Process exit code.

    """
    logger.remove()
    logger.add(sys.stderr, level='WARNING')
    args = build_argument_parser().parse_args()

    try:
        report_summary = summarize_report(
            args.report_path, max_findings=args.max_findings
        )
    except Exception as error:  # pragma: no cover - defensive CLI path
        logger.error('Failed to summarize report {}: {}', args.report_path, error)
        return 1

    sys.stdout.write(report_summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
