"""Evidence-based verification reporting for plan items."""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from loguru import logger


@dataclass(slots=True)
class PlanItem:
    """Represent one implementation-plan item.

    Attributes:
        item_id: Stable work-item identifier.
        title: Human-readable work-item title.
        targets: Repository-relative target files from the plan.
        validations: Validation commands declared in the plan.
        evidence_pack: Optional evidence-pack path.
        feature_class: Feature category used for proof expectations.
        entry_point: Intended way the behavior is exercised.
        required_proofs: Required proof types for the item.
        failure_modes: Required failure or edge conditions.
        lifecycle_state: Optional lifecycle override such as `retired`.

    """

    item_id: str
    title: str
    targets: list[Path]
    validations: list[str]
    evidence_pack: Path | None
    feature_class: str | None = None
    entry_point: str | None = None
    required_proofs: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    lifecycle_state: str | None = None


@dataclass(slots=True)
class EvidencePack:
    """Represent parsed evidence-pack metadata.

    Attributes:
        reviewer_status: Reviewer decision from the sign-off section.
        reviewer: Reviewer identity.
        reviewed_at: Review timestamp.
        acceptance_criteria: Acceptance criteria declared in the pack.
        proof_types: Proof types declared in the proof matrix.
        entry_points: Entry points declared in the proof matrix.
        failure_coverages: Failure coverage entries from the proof matrix.
        app_testable: Whether the item should generate app-check alerts.
        app_surface: GUI or startup surface exposed by the feature.
        developer_alert: Developer-facing alert message.

    """

    reviewer_status: str
    reviewer: str | None
    reviewed_at: str | None
    acceptance_criteria: list[str]
    proof_types: list[str]
    entry_points: list[str]
    failure_coverages: list[str]
    app_testable: bool
    app_surface: str | None
    developer_alert: str | None


@dataclass(slots=True)
class VerificationResult:
    """Capture the verification outcome for one plan item.

    Attributes:
        item_id: Stable work-item identifier.
        title: Human-readable work-item title.
        status: Computed lifecycle state.
        gaps: Gaps that prevented stronger promotion.
        evidence_pack: Evidence-pack path, if any.
        validation_commands: Validation commands attached to the item.
        approved_by: Reviewer identity if approved.
        app_testable: Whether the item should surface startup app checks.
        app_surface: Surface name for app-testable features.
        developer_alert: Developer-facing alert message.

    """

    item_id: str
    title: str
    status: str
    gaps: list[str]
    evidence_pack: str | None
    validation_commands: list[str]
    approved_by: str | None
    app_testable: bool
    app_surface: str | None
    developer_alert: str | None

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-serializable payload."""
        reviewer_status = 'approved' if self.approved_by else 'pending'
        payload = asdict(self)
        payload['reviewer_status'] = reviewer_status
        return payload


_ITEM_HEADER_RE = re.compile(r'^- \[.\] `(?P<id>AF-[^`]+)`\s+(?P<title>.+)$')
_TARGET_RE = re.compile(r'^\s*> \*\*Target File:\*\* `(?P<path>[^`]+)`')
_VALIDATION_RE = re.compile(r'^\s*> \*\*Validation:\*\* `(?P<command>[^`]+)`')
_REVIEWER_STATUS_RE = re.compile(r'^- Reviewer Status:\s*(?P<value>.+)$')
_REVIEWER_RE = re.compile(r'^- Reviewer:\s*(?P<value>.+)$')
_REVIEWED_AT_RE = re.compile(r'^- Reviewed At:\s*(?P<value>.+)$')
_APP_TESTABLE_RE = re.compile(r'^- App-Testable:\s*(?P<value>.+)$')
_APP_SURFACE_RE = re.compile(r'^- App Surface:\s*(?P<value>.+)$')
_DEVELOPER_ALERT_RE = re.compile(r'^- Developer Alert:\s*(?P<value>.+)$')
_ACCEPTANCE_RE = re.compile(r'^- AC\d+:\s*(?P<value>.+)$')

# PLAN.md metadata fields
_FEATURE_CLASS_RE = re.compile(r'^\s*> \*\*Feature-Class:\*\* `(?P<value>[^`]+)`')
_ENTRY_POINT_RE = re.compile(r'^\s*> \*\*Entry-Point:\*\* `(?P<value>[^`]+)`')
_REQUIRED_PROOF_RE = re.compile(r'^\s*> \*\*Required-Proof-Types:\*\* `(?P<value>[^`]+)`')
_APP_TESTABLE_RE_PLAN = re.compile(r'^\s*> \*\*App-Testable:\*\* `(?P<value>[^`]+)`')
_LIFECYCLE_RE = re.compile(r'^\s*> \*\*Lifecycle:\*\* `(?P<value>[^`]+)`')


def default_evidence_pack_path(item_id: str) -> Path:
    """Return the default evidence-pack path for a plan item.

    Args:
        item_id: Stable work-item identifier.

    Returns:
        Repository-relative evidence-pack path.

    """
    return Path('docs') / 'evidence' / f'{item_id}.md'


def parse_plan_items(plan_text: str) -> list[PlanItem]:
    """Parse plan items from `docs/PLAN.md`.

    Args:
        plan_text: Raw plan markdown.

    Returns:
        Parsed plan items in document order.

    """
    items: list[PlanItem] = []
    current: PlanItem | None = None

    for raw_line in plan_text.splitlines():
        match = _ITEM_HEADER_RE.match(raw_line)
        if match:
            current = PlanItem(
                item_id=match.group('id'),
                title=match.group('title').strip(),
                targets=[],
                validations=[],
                evidence_pack=default_evidence_pack_path(match.group('id')),
            )
            items.append(current)
            continue

        if current is None:
            continue

        target_match = _TARGET_RE.match(raw_line)
        if target_match:
            current.targets.append(Path(target_match.group('path').strip()))
            continue

        validation_match = _VALIDATION_RE.match(raw_line)
        if validation_match:
            current.validations.append(validation_match.group('command').strip())
            continue

        feature_class_match = _FEATURE_CLASS_RE.match(raw_line)
        if feature_class_match:
            current.feature_class = feature_class_match.group('value').strip()
            continue

        entry_point_match = _ENTRY_POINT_RE.match(raw_line)
        if entry_point_match:
            current.entry_point = entry_point_match.group('value').strip()
            continue

        required_proof_match = _REQUIRED_PROOF_RE.match(raw_line)
        if required_proof_match:
            raw_proofs = required_proof_match.group('value').strip()
            current.required_proofs = [
                p.strip() for p in raw_proofs.split(',') if p.strip()
            ]
            continue

        lifecycle_match = _LIFECYCLE_RE.match(raw_line)
        if lifecycle_match:
            current.lifecycle_state = lifecycle_match.group('value').strip()
            continue

    return items


def parse_evidence_pack(path: Path) -> EvidencePack:
    """Parse an evidence pack from markdown.

    Args:
        path: Evidence-pack path.

    Returns:
        Parsed evidence-pack metadata.

    Raises:
        ValueError: If the pack is missing required sections.

    """
    text = path.read_text(encoding='utf-8')
    lines = [line.rstrip() for line in text.splitlines()]

    reviewer_status = _extract_required_scalar(lines, _REVIEWER_STATUS_RE, path)
    reviewer = _extract_optional_scalar(lines, _REVIEWER_RE)
    reviewed_at = _extract_optional_scalar(lines, _REVIEWED_AT_RE)
    app_testable_raw = _extract_optional_scalar(lines, _APP_TESTABLE_RE) or 'no'
    app_surface = _extract_optional_scalar(lines, _APP_SURFACE_RE)
    developer_alert = _extract_optional_scalar(lines, _DEVELOPER_ALERT_RE)

    acceptance_criteria = _extract_section_bullets(lines, '## Acceptance Criteria')
    if not acceptance_criteria:
        raise ValueError(f'Missing acceptance criteria in {path.as_posix()}')

    proof_types, entry_points, failure_coverages = _extract_proof_matrix(lines, path)
    return EvidencePack(
        reviewer_status=reviewer_status.casefold(),
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        acceptance_criteria=acceptance_criteria,
        proof_types=proof_types,
        entry_points=entry_points,
        failure_coverages=failure_coverages,
        app_testable=app_testable_raw.strip().casefold() in {'yes', 'true'},
        app_surface=app_surface,
        developer_alert=developer_alert,
    )


def _extract_required_scalar(
    lines: list[str], pattern: re.Pattern[str], path: Path
) -> str:
    """Extract a required scalar value from a markdown bullet.

    Args:
        lines: Markdown lines.
        pattern: Compiled regex pattern.
        path: Source file path.

    Returns:
        Extracted value.

    Raises:
        ValueError: If the field is missing.

    """
    value = _extract_optional_scalar(lines, pattern)
    if value is None:
        raise ValueError(f'Missing required metadata in {path.as_posix()}')
    return value


def _extract_optional_scalar(lines: list[str], pattern: re.Pattern[str]) -> str | None:
    """Extract an optional scalar value from markdown bullets.

    Args:
        lines: Markdown lines.
        pattern: Compiled regex pattern.

    Returns:
        Extracted value when present.

    """
    for line in lines:
        match = pattern.match(line)
        if match:
            return match.group('value').strip()
    return None


def _extract_section_bullets(lines: list[str], heading: str) -> list[str]:
    """Extract simple bullet values from a markdown section.

    Args:
        lines: Markdown lines.
        heading: Heading name to scan.

    Returns:
        Collected bullet values.

    """
    values: list[str] = []
    in_section = False
    for line in lines:
        if line == heading:
            in_section = True
            continue
        if in_section and line.startswith('## '):
            break
        if in_section:
            match = _ACCEPTANCE_RE.match(line)
            if match:
                values.append(match.group('value').strip())
    return values


def _extract_proof_matrix(
    lines: list[str], path: Path
) -> tuple[list[str], list[str], list[str]]:
    """Extract proof-matrix columns from markdown.

    Args:
        lines: Markdown lines.
        path: Source file path.

    Returns:
        Proof types, entry points, and failure coverage lists.

    Raises:
        ValueError: If the matrix is missing.

    """
    proof_types: list[str] = []
    entry_points: list[str] = []
    failure_coverages: list[str] = []
    in_section = False

    for line in lines:
        if line == '## Proof Matrix':
            in_section = True
            continue
        if in_section and line.startswith('## '):
            break
        if in_section and line.startswith('| AC'):
            parts = [part.strip() for part in line.strip('|').split('|')]
            if len(parts) >= 5:
                proof_types.append(parts[1].casefold())
                entry_points.append(parts[3])
                failure_coverages.append(parts[4])

    if not proof_types:
        raise ValueError(f'Missing proof matrix in {path.as_posix()}')
    return proof_types, entry_points, failure_coverages


def evaluate_plan_item(
    *,
    repo_root: Path,
    item: PlanItem,
    validation_runner: Callable[[Path, str], bool] | None = None,
) -> VerificationResult:
    """Evaluate one plan item against the evidence standard.

    Args:
        repo_root: Repository root path.
        item: Plan item to evaluate.
        validation_runner: Optional validation runner for tests.

    Returns:
        Verification result for the item.

    """
    if item.lifecycle_state == 'retired':
        return VerificationResult(
            item_id=item.item_id,
            title=item.title,
            status='retired',
            gaps=[],
            evidence_pack=item.evidence_pack.as_posix() if item.evidence_pack else None,
            validation_commands=item.validations,
            approved_by=None,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        )

    missing_targets = [
        target.as_posix()
        for target in item.targets
        if not (repo_root / target).exists()
    ]
    if missing_targets:
        return VerificationResult(
            item_id=item.item_id,
            title=item.title,
            status='drafted',
            gaps=[f'Missing target files: {", ".join(missing_targets)}'],
            evidence_pack=item.evidence_pack.as_posix() if item.evidence_pack else None,
            validation_commands=item.validations,
            approved_by=None,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        )

    if item.evidence_pack is None or not (repo_root / item.evidence_pack).exists():
        return VerificationResult(
            item_id=item.item_id,
            title=item.title,
            status='coded',
            gaps=['Missing evidence pack'],
            evidence_pack=item.evidence_pack.as_posix() if item.evidence_pack else None,
            validation_commands=item.validations,
            approved_by=None,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        )

    pack_path = repo_root / item.evidence_pack
    try:
        evidence_pack = parse_evidence_pack(pack_path)
    except ValueError as error:
        return VerificationResult(
            item_id=item.item_id,
            title=item.title,
            status='evidenced',
            gaps=[str(error)],
            evidence_pack=item.evidence_pack.as_posix(),
            validation_commands=item.validations,
            approved_by=None,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        )

    if evidence_pack.reviewer_status == 'retired':
        return VerificationResult(
            item_id=item.item_id,
            title=item.title,
            status='retired',
            gaps=[],
            evidence_pack=item.evidence_pack.as_posix(),
            validation_commands=item.validations,
            approved_by=evidence_pack.reviewer,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        )

    gaps = _collect_evidence_gaps(item=item, evidence_pack=evidence_pack)
    if evidence_pack.reviewer_status != 'approved':
        gaps.append('Reviewer sign-off is not approved')

    validation_ok = True
    runner = validation_runner or _default_validation_runner
    for command in item.validations:
        if not runner(repo_root, command):
            validation_ok = False
            gaps.append(f'Validation failed: {command}')

    status = 'verified' if not gaps and validation_ok else 'evidenced'
    return VerificationResult(
        item_id=item.item_id,
        title=item.title,
        status=status,
        gaps=gaps,
        evidence_pack=item.evidence_pack.as_posix(),
        validation_commands=item.validations,
        approved_by=evidence_pack.reviewer if status == 'verified' else None,
        app_testable=evidence_pack.app_testable if status == 'verified' else False,
        app_surface=evidence_pack.app_surface if status == 'verified' else None,
        developer_alert=evidence_pack.developer_alert if status == 'verified' else None,
    )


def _collect_evidence_gaps(*, item: PlanItem, evidence_pack: EvidencePack) -> list[str]:
    """Collect gaps between plan expectations and evidence metadata.

    Args:
        item: Plan item under review.
        evidence_pack: Parsed evidence pack.

    Returns:
        Missing-evidence gap list.

    """
    gaps: list[str] = []
    normalized_proofs = {proof.casefold() for proof in evidence_pack.proof_types}
    for required in item.required_proofs:
        if required.casefold() not in normalized_proofs:
            gaps.append(f'Missing required proof type: {required}')

    normalized_failures = ' '.join(evidence_pack.failure_coverages).casefold()
    for failure_mode in item.failure_modes:
        if failure_mode.casefold() not in normalized_failures:
            gaps.append(f'Missing failure coverage: {failure_mode}')

    if item.entry_point:
        normalized_entries = {entry.casefold() for entry in evidence_pack.entry_points}
        if item.entry_point.casefold() not in normalized_entries:
            gaps.append(f'Entry point not exercised: {item.entry_point}')
    return gaps


def _default_validation_runner(repo_root: Path, command: str) -> bool:
    """Run a validation command using the repo validation gate.

    Args:
        repo_root: Repository root path.
        command: Validation command string.

    Returns:
        True when the command succeeds.

    """
    argv = _parse_validation_command(command, repo_root=repo_root)
    if argv is None:
        logger.warning('Validation command is not allowed: {}', command)
        return False
    result = subprocess.run(
        argv,
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.warning(
            'Validation failed for {}: {}',
            command,
            ((result.stdout or '') + (result.stderr or '')).strip(),
        )
    return result.returncode == 0


def _parse_validation_command(command: str, *, repo_root: Path) -> list[str] | None:
    """Parse supported validation commands into argv form.

    Args:
        command: Raw command string.
        repo_root: Repository root path.

    Returns:
        Parsed argv list when allowed, otherwise `None`.

    """
    argv = [
        _strip_wrapping_quotes(token) for token in shlex.split(command, posix=False)
    ]
    if not argv:
        return None
    if argv[:3] == ['uv', 'run', 'pytest']:
        return argv
    if argv[:4] == ['uv', 'run', 'ruff', 'check']:
        return argv
    if argv[0].casefold() in {'powershell', 'pwsh'}:
        executable = shutil.which(argv[0]) or argv[0]
        normalized = list(argv)
        normalized[0] = executable
        if len(normalized) < 5:
            return None
        if normalized[1:4] != ['-ExecutionPolicy', 'Bypass', '-File']:
            return None
        script_path = (repo_root / normalized[4]).resolve()
        if repo_root.resolve() not in script_path.parents:
            return None
        normalized[4] = str(script_path)
        return normalized
    return None


def _strip_wrapping_quotes(token: str) -> str:
    """Strip a single pair of matching wrapping quotes from a token.

    Args:
        token: Command token.

    Returns:
        Unwrapped token when quoted, otherwise the original token.

    """
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
        return token[1:-1]
    return token


def generate_results(repo_root: Path, plan_path: Path) -> list[VerificationResult]:
    """Generate verification results for all plan items.

    Args:
        repo_root: Repository root path.
        plan_path: Path to `docs/PLAN.md`.

    Returns:
        Verification results for all parsed items.

    """
    plan_text = plan_path.read_text(encoding='utf-8')
    items = parse_plan_items(plan_text)
    items = _apply_repo_defaults(items)
    return [evaluate_plan_item(repo_root=repo_root, item=item) for item in items]


def _apply_repo_defaults(items: list[PlanItem]) -> list[PlanItem]:
    """Apply repo-specific defaults for current plan items.

    Args:
        items: Parsed plan items.

    Returns:
        Plan items with default lifecycle and proof expectations.

    """
    defaults: dict[str, dict[str, object]] = {
        'AF-00-01': {'lifecycle_state': 'retired'},
        'AF-00-02a': {
            'feature_class': 'boundary',
            'entry_point': 'verify-env.ps1',
            'required_proofs': ['contract'],
            'failure_modes': ['missing toolchain detected'],
        },
        'AF-00-02b': {
            'feature_class': 'boundary',
            'entry_point': 'build-native.ps1',
            'required_proofs': ['contract'],
            'failure_modes': ['native boundary violation rejected'],
        },
        'AF-00-03': {
            'feature_class': 'boundary',
            'entry_point': 'capture control contract',
            'required_proofs': ['contract'],
            'failure_modes': ['missing control-plane message rejected'],
        },
        'AF-00-04': {
            'feature_class': 'boundary',
            'entry_point': 'plugin abi mirror',
            'required_proofs': ['contract'],
            'failure_modes': ['missing runtime state rejected'],
        },
        'AF-00-05': {
            'feature_class': 'workflow',
            'entry_point': 'sign-off packets',
            'required_proofs': ['contract'],
            'failure_modes': ['missing fallback guidance rejected'],
        },
        'AF-01-01': {
            'feature_class': 'service',
            'entry_point': 'signed plugin loading',
            'required_proofs': ['integration'],
            'failure_modes': ['unsigned plugin blocked'],
        },
        'AF-01-02': {
            'feature_class': 'ui',
            'entry_point': 'status hud',
            'required_proofs': ['integration'],
            'failure_modes': ['unauthorized navigation blocked'],
        },
        'AF-02-02': {
            'feature_class': 'ui',
            'entry_point': 'driver status panel',
            'required_proofs': ['integration'],
            'failure_modes': ['driver masking failure surfaced'],
        },
        'AF-04-02': {
            'feature_class': 'service',
            'entry_point': 'environment panel',
            'required_proofs': ['integration'],
            'failure_modes': ['invalid bundle rejected'],
        },
    }

    for item in items:
        item_defaults = defaults.get(item.item_id, {})
        # Lifecycle state from PLAN.md takes precedence; fall back to hardcoded default.
        if item.lifecycle_state is None and 'lifecycle_state' in item_defaults:
            item.lifecycle_state = str(item_defaults['lifecycle_state'])
        # Feature metadata: prefer values already parsed from PLAN.md; fall back to defaults.
        if item.feature_class is None:
            item.feature_class = (
                str(item_defaults.get('feature_class', '')) or None
            )
        if item.entry_point is None:
            item.entry_point = (
                str(item_defaults.get('entry_point', '')) or None
            )
        if not item.required_proofs:
            item.required_proofs = list(  # type: ignore
                item_defaults.get('required_proofs', [])  # type: ignore
            )
        if not item.failure_modes:
            item.failure_modes = list(  # type: ignore
                item_defaults.get('failure_modes', [])  # type: ignore
            )
    return items


def write_results(
    *,
    report_path: Path,
    results_dir: Path,
    results: list[VerificationResult],
) -> None:
    """Write the requirements report and per-item result files.

    Args:
        report_path: Requirements report output path.
        results_dir: Directory for per-item JSON payloads.
        results: Evaluated verification results.

    """
    results_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    for result in results:
        (results_dir / f'{result.item_id}.json').write_text(
            json.dumps(result.to_payload(), indent=2) + '\n',
            encoding='utf-8',
        )

    summary_order = ['retired', 'drafted', 'coded', 'evidenced', 'verified', 'complete']
    summary_counts = {
        state: sum(1 for result in results if result.status == state)
        for state in summary_order
    }

    lines = [
        '# Requirements Report',
        '',
        '## Summary',
        f'- Retired: {summary_counts["retired"]}',
        f'- Drafted: {summary_counts["drafted"]}',
        f'- Coded: {summary_counts["coded"]}',
        f'- Evidenced: {summary_counts["evidenced"]}',
        f'- Verified: {summary_counts["verified"]}',
        f'- Complete: {summary_counts["complete"]}',
        '',
        '## Coverage by Plan Item',
    ]

    for result in results:
        lines.extend(
            [
                '',
                f'### {result.item_id} - {result.title}',
                f'- Status: {result.status}',
            ]
        )
        if result.gaps:
            lines.append(f'- Gaps: {"; ".join(result.gaps)}')
        if result.evidence_pack:
            lines.append(f'- Evidence Pack: {result.evidence_pack}')
        if result.validation_commands:
            lines.append(f'- Validation: {", ".join(result.validation_commands)}')
        if result.approved_by:
            lines.append(f'- Reviewer: {result.approved_by}')
        if result.app_testable:
            lines.append('- App-Testable: yes')
            if result.app_surface:
                lines.append(f'- App Surface: {result.app_surface}')

    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
