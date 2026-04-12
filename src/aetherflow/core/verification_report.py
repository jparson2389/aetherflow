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
        acceptance_criteria: Acceptance-criterion labels declared in the plan (e.g. ``["AC1", "AC2"]``).
        app_surface: GUI or startup surface exposed by the feature (plan-declared).
        developer_alert: Developer-facing alert message (plan-declared).
        performance_claim: Whether the item makes a latency, FPS, or throughput assertion.
        performance_threshold: Human-readable performance threshold (e.g. ``"60 FPS sustained"``).
        performance_evidence_type: Evidence type classifying the measurement (e.g. ``"sustained-drop-detection"``).
        performance_evidence_location: Repository-relative path to the performance evidence artifact.
        enforce_metadata: Whether evaluate_plan_item() should require the full
            canonical docs/PLAN.md metadata set before considering evidence.

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
    acceptance_criteria: list[str] = field(default_factory=list)
    app_surface: str | None = None
    developer_alert: str | None = None
    performance_claim: bool = False
    performance_threshold: str | None = None
    performance_evidence_type: str | None = None
    performance_evidence_location: str | None = None
    enforce_metadata: bool = False


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
        criteria_covered: Criterion labels from the proof-matrix criterion column (e.g. ``["AC1"]``).
        app_testable: Whether the item should generate app-check alerts.
        app_surface: GUI or startup surface exposed by the feature.
        developer_alert: Developer-facing alert message.
        performance_artifact_pass_fail: Pass/fail conclusions for each performance artifact entry.

    """

    reviewer_status: str
    reviewer: str | None
    reviewed_at: str | None
    acceptance_criteria: list[str]
    proof_types: list[str]
    entry_points: list[str]
    failure_coverages: list[str]
    criteria_covered: list[str]
    app_testable: bool
    app_surface: str | None
    developer_alert: str | None
    performance_artifact_pass_fail: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ValidationExecution:
    """Capture one executed validation command outcome.

    Attributes:
        command: Exact validation command string.
        exit_code: Process exit code (`None` when command is rejected pre-run).
        passed: Whether validation succeeded.
        requirement_links: Requirement labels linked to this validation.

    """

    command: str
    exit_code: int | None
    passed: bool
    requirement_links: list[str] = field(default_factory=list)


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
        validation_results: Per-command execution outcomes including exit codes.
        exit_codes: Command-to-exit-code mapping.
        requirement_links: Requirement labels tied to validation evidence.
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
    validation_results: list[ValidationExecution] = field(default_factory=list)
    exit_codes: dict[str, int | None] = field(default_factory=dict)
    requirement_links: dict[str, list[str]] = field(default_factory=dict)
    approved_by: str | None = None
    app_testable: bool = False
    app_surface: str | None = None
    developer_alert: str | None = None

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-serializable payload."""
        reviewer_status = 'approved' if self.approved_by else 'pending'
        payload = asdict(self)
        payload['reviewer_status'] = reviewer_status
        return payload


_ITEM_HEADER_RE = re.compile(r'^- \[.\] `(?P<id>AF-[^`]+)`\s+(?P<title>.+)$')
_TARGET_RE = re.compile(r'^\s*>\s+\*\*Target File:\*\*\s+`(?P<path>[^`]+)`')
_VALIDATION_RE = re.compile(r'^\s*>\s+\*\*Validation:\*\*\s+`(?P<command>[^`]+)`')
_REVIEWER_STATUS_RE = re.compile(r'^- Reviewer Status:\s*(?P<value>.+)$')
_REVIEWER_RE = re.compile(r'^- Reviewer:\s*(?P<value>.+)$')
_REVIEWED_AT_RE = re.compile(r'^- Reviewed At:\s*(?P<value>.+)$')
_APP_TESTABLE_RE = re.compile(r'^- App-Testable:\s*(?P<value>.+)$')
_APP_SURFACE_RE = re.compile(r'^- App Surface:\s*(?P<value>.+)$')
_DEVELOPER_ALERT_RE = re.compile(r'^- Developer Alert:\s*(?P<value>.+)$')
_ACCEPTANCE_RE = re.compile(r'^- AC\d+:\s*(?P<value>.+)$')

# PLAN.md metadata fields
_FEATURE_CLASS_RE = re.compile(r'^\s*>\s+\*\*Feature-Class:\*\*\s+`(?P<value>[^`]+)`')
_ENTRY_POINT_RE = re.compile(r'^\s*>\s+\*\*Entry-Point:\*\*\s+`(?P<value>[^`]+)`')
_REQUIRED_PROOF_RE = re.compile(
    r'^\s*>\s+\*\*Required-Proof-Types:\*\*\s+`(?P<value>[^`]+)`'
)
_APP_TESTABLE_RE_PLAN = re.compile(
    r'^\s*>\s+\*\*App-Testable:\*\*\s+`(?P<value>[^`]+)`'
)
_LIFECYCLE_RE = re.compile(r'^\s*>\s+\*\*Lifecycle:\*\*\s+`(?P<value>[^`]+)`')
_PLAN_AC_LABEL_RE = re.compile(r'^\s*> - (AC\d+):')
_REQUIRED_FAILURE_MODES_RE = re.compile(
    r'^\s*>\s+\*\*Required-Failure-Modes:\*\*\s+`(?P<value>[^`]+)`'
)
_PLAN_APP_SURFACE_RE = re.compile(r'^\s*>\s+\*\*App-Surface:\*\*\s+`(?P<value>[^`]+)`')
_PLAN_DEVELOPER_ALERT_RE = re.compile(
    r'^\s*>\s+\*\*Developer-Alert-Message:\*\*\s+`(?P<value>[^`]+)`'
)
_PERFORMANCE_CLAIM_RE = re.compile(
    r'^\s*>\s+\*\*Performance-Claim:\*\*\s+`(?P<value>[^`]+)`'
)
_PERFORMANCE_THRESHOLD_RE = re.compile(
    r'^\s*>\s+\*\*Performance-Threshold:\*\*\s+`(?P<value>[^`]+)`'
)
_PERFORMANCE_EVIDENCE_TYPE_RE = re.compile(
    r'^\s*>\s+\*\*Performance-Evidence-Type:\*\*\s+`(?P<value>[^`]+)`'
)
_PERFORMANCE_EVIDENCE_LOCATION_RE = re.compile(
    r'^\s*>\s+\*\*Performance-Evidence-Location:\*\*\s+`(?P<value>[^`]+)`'
)

# Evidence pack performance artifact fields
_PERF_PASS_FAIL_RE = re.compile(r'^- Pass-Fail:\s*(?P<value>.+)$')


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
                enforce_metadata=True,
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

        ac_label_match = _PLAN_AC_LABEL_RE.match(raw_line)
        if ac_label_match:
            current.acceptance_criteria.append(ac_label_match.group(1))
            continue

        failure_modes_match = _REQUIRED_FAILURE_MODES_RE.match(raw_line)
        if failure_modes_match:
            raw_modes = failure_modes_match.group('value').strip()
            current.failure_modes = [
                m.strip() for m in raw_modes.split(',') if m.strip()
            ]
            continue

        app_surface_match = _PLAN_APP_SURFACE_RE.match(raw_line)
        if app_surface_match:
            current.app_surface = app_surface_match.group('value').strip()
            continue

        developer_alert_match = _PLAN_DEVELOPER_ALERT_RE.match(raw_line)
        if developer_alert_match:
            current.developer_alert = developer_alert_match.group('value').strip()
            continue

        performance_claim_match = _PERFORMANCE_CLAIM_RE.match(raw_line)
        if performance_claim_match:
            current.performance_claim = (
                performance_claim_match.group('value').strip().casefold() == 'true'
            )
            continue

        performance_threshold_match = _PERFORMANCE_THRESHOLD_RE.match(raw_line)
        if performance_threshold_match:
            current.performance_threshold = performance_threshold_match.group(
                'value'
            ).strip()
            continue

        performance_evidence_type_match = _PERFORMANCE_EVIDENCE_TYPE_RE.match(raw_line)
        if performance_evidence_type_match:
            current.performance_evidence_type = performance_evidence_type_match.group(
                'value'
            ).strip()
            continue

        performance_evidence_location_match = _PERFORMANCE_EVIDENCE_LOCATION_RE.match(
            raw_line
        )
        if performance_evidence_location_match:
            current.performance_evidence_location = (
                performance_evidence_location_match.group('value').strip()
            )
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

    criteria_covered, proof_types, entry_points, failure_coverages = (
        _extract_proof_matrix(lines, path)
    )
    performance_artifact_pass_fail = _extract_performance_artifact_pass_fail(lines)
    return EvidencePack(
        reviewer_status=reviewer_status.casefold(),
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        acceptance_criteria=acceptance_criteria,
        proof_types=proof_types,
        entry_points=entry_points,
        failure_coverages=failure_coverages,
        criteria_covered=criteria_covered,
        app_testable=app_testable_raw.strip().casefold() in {'yes', 'true'},
        app_surface=app_surface,
        developer_alert=developer_alert,
        performance_artifact_pass_fail=performance_artifact_pass_fail,
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
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Extract proof-matrix columns from markdown.

    Args:
        lines: Markdown lines.
        path: Source file path.

    Returns:
        Criteria covered, proof types, entry points, and failure coverage lists.

    Raises:
        ValueError: If the matrix is missing.

    """
    criteria_covered: list[str] = []
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
                criteria_covered.append(parts[0])
                proof_types.append(parts[1].casefold())
                entry_points.append(parts[3])
                failure_coverages.append(parts[4])

    if not proof_types:
        raise ValueError(f'Missing proof matrix in {path.as_posix()}')
    return criteria_covered, proof_types, entry_points, failure_coverages


def _extract_performance_artifact_pass_fail(lines: list[str]) -> list[str]:
    """Extract pass/fail conclusions from the Performance Artifacts section.

    Args:
        lines: Markdown lines.

    Returns:
        List of pass/fail values from ``- Pass-Fail:`` entries in the section.

    """
    values: list[str] = []
    in_section = False
    for line in lines:
        if line == '## Performance Artifacts':
            in_section = True
            continue
        if in_section and line.startswith('## '):
            break
        if in_section:
            match = _PERF_PASS_FAIL_RE.match(line)
            if match:
                values.append(match.group('value').strip().casefold())
    return values


def evaluate_plan_item(
    *,
    repo_root: Path,
    item: PlanItem,
    validation_runner: Callable[[Path, str], bool | ValidationExecution] | None = None,
) -> VerificationResult:
    """Evaluate one plan item against the evidence standard.

    Args:
        repo_root: Repository root path.
        item: Plan item to evaluate.
        validation_runner: Optional validation runner for tests.

    Returns:
        Verification result for the item.

    """
    requirement_links = {
        'acceptance_criteria': list(item.acceptance_criteria),
        'required_failure_modes': list(item.failure_modes),
    }

    if item.lifecycle_state == 'retired':
        return VerificationResult(
            item_id=item.item_id,
            title=item.title,
            status='retired',
            gaps=[],
            evidence_pack=item.evidence_pack.as_posix() if item.evidence_pack else None,
            validation_commands=item.validations,
            validation_results=[],
            exit_codes={},
            requirement_links=requirement_links,
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
            validation_results=[],
            exit_codes={},
            requirement_links=requirement_links,
            approved_by=None,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        )

    metadata_gaps = _collect_metadata_gaps(item) if item.enforce_metadata else []
    if metadata_gaps:
        return VerificationResult(
            item_id=item.item_id,
            title=item.title,
            status='coded',
            gaps=metadata_gaps,
            evidence_pack=item.evidence_pack.as_posix() if item.evidence_pack else None,
            validation_commands=item.validations,
            validation_results=[],
            exit_codes={},
            requirement_links=requirement_links,
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
            validation_results=[],
            exit_codes={},
            requirement_links=requirement_links,
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
            validation_results=[],
            exit_codes={},
            requirement_links=requirement_links,
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
            validation_results=[],
            exit_codes={},
            requirement_links=requirement_links,
            approved_by=evidence_pack.reviewer,
            app_testable=False,
            app_surface=None,
            developer_alert=None,
        )

    gaps = _collect_evidence_gaps(item=item, evidence_pack=evidence_pack)
    if evidence_pack.reviewer_status != 'approved':
        gaps.append('[review/sign-off-gap] Reviewer sign-off is not approved')

    validation_ok = True
    validation_results: list[ValidationExecution] = []
    runner = validation_runner or _default_validation_runner
    for command in item.validations:
        execution = _run_validation(
            runner=runner,
            repo_root=repo_root,
            command=command,
            requirement_links=item.acceptance_criteria,
        )
        validation_results.append(execution)
        if not execution.passed:
            validation_ok = False
            gaps.append(f'[validation-gap] Validation failed: {command}')

    exit_codes = {entry.command: entry.exit_code for entry in validation_results}
    status = 'verified' if not gaps and validation_ok else 'evidenced'
    return VerificationResult(
        item_id=item.item_id,
        title=item.title,
        status=status,
        gaps=gaps,
        evidence_pack=item.evidence_pack.as_posix(),
        validation_commands=item.validations,
        validation_results=validation_results,
        exit_codes=exit_codes,
        requirement_links=requirement_links,
        approved_by=evidence_pack.reviewer if status == 'verified' else None,
        app_testable=evidence_pack.app_testable if status == 'verified' else False,
        app_surface=evidence_pack.app_surface if status == 'verified' else None,
        developer_alert=evidence_pack.developer_alert if status == 'verified' else None,
    )


def _collect_metadata_gaps(item: PlanItem) -> list[str]:
    """Collect required metadata fields missing from the plan item declaration.

    Active items must declare all required fields explicitly in docs/PLAN.md.
    Missing fields are surfaced as verification gaps rather than silently tolerated.

    Args:
        item: Plan item to check.

    Returns:
        List of missing-metadata gap messages, empty if all required fields present.

    """
    gaps: list[str] = []
    if not item.feature_class:
        gaps.append('[metadata-gap] Missing required plan metadata: Feature-Class')
    if not item.entry_point:
        gaps.append('[metadata-gap] Missing required plan metadata: Entry-Point')
    if not item.required_proofs:
        gaps.append(
            '[metadata-gap] Missing required plan metadata: Required-Proof-Types'
        )
    if not item.failure_modes:
        gaps.append(
            '[metadata-gap] Missing required plan metadata: Required-Failure-Modes'
        )
    if not item.acceptance_criteria:
        gaps.append(
            '[metadata-gap] Missing required plan metadata: Acceptance Criteria'
        )
    if item.performance_claim:
        if not item.performance_threshold:
            gaps.append(
                '[metadata-gap] Missing required plan metadata: Performance-Threshold'
            )
        if not item.performance_evidence_type:
            gaps.append(
                '[metadata-gap] Missing required plan metadata: Performance-Evidence-Type'
            )
        if not item.performance_evidence_location:
            gaps.append(
                '[metadata-gap] Missing required plan metadata: Performance-Evidence-Location'
            )
    return gaps


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
            gaps.append(f'[ac-coverage-gap] Missing required proof type: {required}')

    normalized_failures = ' '.join(evidence_pack.failure_coverages).casefold()
    for failure_mode in item.failure_modes:
        if failure_mode.casefold() not in normalized_failures:
            gaps.append(
                f'[failure-coverage-gap] Missing failure coverage: {failure_mode}'
            )

    if item.entry_point:
        normalized_entries = {entry.casefold() for entry in evidence_pack.entry_points}
        if item.entry_point.casefold() not in normalized_entries:
            gaps.append(
                f'[ac-coverage-gap] Entry point not exercised: {item.entry_point}'
            )

    if item.acceptance_criteria:
        covered = {c.casefold() for c in evidence_pack.criteria_covered}
        for ac_label in item.acceptance_criteria:
            if ac_label.casefold() not in covered:
                gaps.append(
                    f'[ac-coverage-gap] Acceptance criterion not covered in proof matrix: {ac_label}'
                )

    if item.performance_claim:
        pass_fail = evidence_pack.performance_artifact_pass_fail
        if not pass_fail:
            gaps.append(
                '[performance-proof-gap] Missing performance proof: no performance artifacts in evidence pack'
            )
        elif any(v != 'pass' for v in pass_fail):
            gaps.append(
                '[performance-proof-gap] Performance threshold not met: one or more performance artifacts failed'
            )

    return gaps


def _run_validation(
    *,
    runner: Callable[[Path, str], bool | ValidationExecution],
    repo_root: Path,
    command: str,
    requirement_links: list[str],
) -> ValidationExecution:
    """Normalize runner outputs into a `ValidationExecution` result.

    Args:
        runner: Validation runner callback.
        repo_root: Repository root path.
        command: Validation command string.
        requirement_links: Requirement labels tied to this command.

    Returns:
        Normalized validation execution data.

    """
    raw = runner(repo_root, command)
    if isinstance(raw, ValidationExecution):
        links = list(raw.requirement_links) or list(requirement_links)
        return ValidationExecution(
            command=raw.command,
            exit_code=raw.exit_code,
            passed=raw.passed,
            requirement_links=links,
        )

    return ValidationExecution(
        command=command,
        exit_code=0 if raw else 1,
        passed=bool(raw),
        requirement_links=list(requirement_links),
    )


def _default_validation_runner(repo_root: Path, command: str) -> ValidationExecution:
    """Run a validation command using the repo validation gate.

    Args:
        repo_root: Repository root path.
        command: Validation command string.

    Returns:
        Validation execution details for the command.

    """
    argv = _parse_validation_command(command, repo_root=repo_root)
    if argv is None:
        logger.warning('Validation command is not allowed: {}', command)
        return ValidationExecution(
            command=command,
            exit_code=None,
            passed=False,
            requirement_links=[],
        )
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
    return ValidationExecution(
        command=command,
        exit_code=result.returncode,
        passed=result.returncode == 0,
        requirement_links=[],
    )


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
        executable = shutil.which(argv[0])
        if executable is None:
            return None
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
    """Apply backward-compatibility lifecycle defaults for legacy items.

    All active AF-* item metadata (feature_class, entry_point, required_proofs,
    failure_modes, app_surface, developer_alert, performance_claim) is now
    canonical in docs/PLAN.md and parsed directly by parse_plan_items().
    This function only supplies the lifecycle fallback for AF-00-01 in case an
    older copy of the plan omits the Lifecycle field.

    Args:
        items: Parsed plan items.

    Returns:
        Plan items with lifecycle fallback applied where needed.

    """
    for item in items:
        if item.item_id == 'AF-00-01' and item.lifecycle_state is None:
            item.lifecycle_state = 'retired'
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
