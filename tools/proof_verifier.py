"""Proof-first verification driver for Aetherflow plan items."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from loguru import logger

from aetherflow.core.developer_app_checks import PendingAppCheckStore
from aetherflow.core.verification_report import (
    PlanItem,
    VerificationResult,
    evaluate_plan_item,
    generate_results,
    parse_plan_items,
    write_results,
)


def parse_plan_metadata(plan_path: Path) -> list[PlanItem]:
    """Read PLAN.md and extract AF-* items with all metadata fields.

    Args:
        plan_path: Path to PLAN.md.

    Returns:
        Parsed plan items with metadata fields populated from PLAN.md.

    """
    plan_text = plan_path.read_text(encoding='utf-8')
    return parse_plan_items(plan_text)


def verify_item(
    item_id: str,
    plan_path: Path,
    evidence_dir: Path,
    logs_dir: Path,
) -> VerificationResult:
    """Evaluate one item against the evidence standard.

    Args:
        item_id: Stable work-item identifier.
        plan_path: Path to PLAN.md.
        evidence_dir: Directory containing evidence packs.
        logs_dir: Directory where verification JSONs are written.

    Returns:
        Verification result for the given item.

    Raises:
        ValueError: If item_id is not found in the plan.

    """
    repo_root = plan_path.parent.parent
    logger.debug('Verifying item {} against evidence in {}.', item_id, evidence_dir)
    items = parse_plan_metadata(plan_path)
    matching = [item for item in items if item.item_id == item_id]
    if not matching:
        raise ValueError(f'Item not found in plan: {item_id}')
    item = matching[0]
    result = evaluate_plan_item(repo_root=repo_root, item=item)
    build_verification_json(item_id=item_id, result=result, logs_dir=logs_dir)
    return result


def build_verification_json(
    item_id: str, result: VerificationResult, logs_dir: Path
) -> None:
    """Write logs/verification/<item-id>.json from a verification result.

    Args:
        item_id: Stable work-item identifier.
        result: Verification result to serialise.
        logs_dir: Directory where the JSON file will be written.

    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_path = logs_dir / f'{item_id}.json'
    output_path.write_text(
        json.dumps(result.to_payload(), indent=2) + '\n',
        encoding='utf-8',
    )
    logger.debug('Wrote verification JSON: {}', output_path)


def build_requirements_report(
    results: list[VerificationResult], output_path: Path
) -> None:
    """Generate docs/requirements-report.md from evidence states.

    Delegates entirely to write_results() from verification_report so that
    report content is always evidence-state-based, never heuristic.

    Args:
        results: Verification results to summarise.
        output_path: Path where the report will be written.

    """
    results_dir = output_path.parent / '..' / 'logs' / 'verification'
    results_dir = results_dir.resolve()
    write_results(
        report_path=output_path,
        results_dir=results_dir,
        results=results,
    )


def run_regrade(
    plan_path: Path,
    evidence_dir: Path,
    logs_dir: Path,
    report_path: Path,
) -> list[VerificationResult]:
    """Full pass: evaluate all items, write JSONs, write report, sync alerts.

    Args:
        plan_path: Path to PLAN.md.
        evidence_dir: Directory containing evidence packs.
        logs_dir: Directory where per-item verification JSONs are written.
        report_path: Output path for the requirements report.

    Returns:
        Evaluated verification results for all plan items.

    """
    repo_root = plan_path.parent.parent
    logger.debug('Running full regrade; evidence directory: {}.', evidence_dir)
    results = generate_results(repo_root=repo_root, plan_path=plan_path)

    logs_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        build_verification_json(
            item_id=result.item_id, result=result, logs_dir=logs_dir
        )

    write_results(report_path=report_path, results_dir=logs_dir, results=results)

    store = PendingAppCheckStore(
        pending_path=logs_dir / 'pending_app_checks.json',
        snapshot_path=logs_dir / 'status_snapshot.json',
    )
    store.sync_results(results)

    logger.info(
        'Regrade complete: {} items evaluated, report written to {}.',
        len(results),
        report_path,
    )
    return results


def _build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured argument parser.

    """
    parser = argparse.ArgumentParser(
        description='Proof-first verification driver for Aetherflow plan items.'
    )
    parser.add_argument(
        '--regrade',
        action='store_true',
        help='Run a full regrade pass for all plan items.',
    )
    parser.add_argument(
        '--plan',
        type=Path,
        default=Path('docs/PLAN.md'),
        help='Path to PLAN.md (default: docs/PLAN.md).',
    )
    parser.add_argument(
        '--report',
        type=Path,
        default=Path('docs/requirements-report.md'),
        help='Output path for the requirements report.',
    )
    parser.add_argument(
        '--results-dir',
        type=Path,
        default=Path('logs/verification'),
        help='Directory for per-item verification JSON files.',
    )
    return parser


def main() -> int:
    """CLI entry point.

    Returns:
        Process exit code (0 on success).

    """
    args = _build_argument_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    plan_path = repo_root / args.plan
    report_path = repo_root / args.report
    results_dir = repo_root / args.results_dir
    evidence_dir = repo_root / 'docs' / 'evidence'

    if args.regrade:
        results = run_regrade(
            plan_path=plan_path,
            evidence_dir=evidence_dir,
            logs_dir=results_dir,
            report_path=report_path,
        )
        logger.info('Regrade produced {} results.', len(results))
    else:
        logger.warning('No action specified. Use --regrade to evaluate all plan items.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
