"""Non-authoritative compatibility wrapper around src/aetherflow/core/verification_report.

This script delegates all evaluation to the canonical evaluator and must not be
treated as a second verification authority. It does not independently compute,
cache, or override status values. The sole authoritative regrade entry point is:

    uv run python -m tools.verify_requirements
"""

from __future__ import annotations

import argparse
from pathlib import Path

from loguru import logger

from aetherflow.core.developer_app_checks import PendingAppCheckStore
from aetherflow.core.verification_report import generate_results, write_results


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI parser.

    Returns:
        Configured CLI parser.

    """
    parser = argparse.ArgumentParser(
        description='Generate evidence-based verification outputs.'
    )
    parser.add_argument('--plan', type=Path, default=Path('docs/PLAN.md'))
    parser.add_argument(
        '--report', type=Path, default=Path('docs/requirements-report.md')
    )
    parser.add_argument('--results-dir', type=Path, default=Path('logs/verification'))
    return parser


def main() -> int:
    """Run the verification report generator.

    Returns:
        Process exit code.

    """
    args = build_argument_parser().parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    results = generate_results(repo_root=repo_root, plan_path=repo_root / args.plan)

    results_dir = repo_root / args.results_dir
    report_path = repo_root / args.report
    write_results(report_path=report_path, results_dir=results_dir, results=results)

    store = PendingAppCheckStore(
        pending_path=results_dir / 'pending_app_checks.json',
        snapshot_path=results_dir / 'status_snapshot.json',
    )
    store.sync_results(results)
    logger.info('Generated verification report for {} plan items.', len(results))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
