# Artifact Storage Policy

## Purpose

Define what belongs in git versus what is generated at runtime or kept local.
This policy stops the chronic loop where `logs/verification/*.json` files are
committed, deleted, or re-tracked across PRs.

## Storage Tiers

### Tier 1 — Canonical tracked

Authoritative source material that defines repo truth and must be versioned.

Examples:

- Governance docs under `docs/governance/` (including this policy)
- Ledger YAML under `docs/governance/ledger/`
- Frozen contracts under `proto/`
- Hand-authored evidence packs referenced by plan items (paths only; see Tier 3)

### Tier 2 — Generated runtime

Produced by `uv run python -m tools.verify_requirements` or related tooling.
Regenerate on demand; never commit to git.

Examples:

- `logs/verification/*.json` (per-item verification artifacts)
- `logs/verification/status_snapshot.json`
- `docs/requirements-report.md`
- `logs/verify-requirements-evidence.md`

CI must run the canonical verification command before pytest so a clean
checkout has these files locally without requiring git-tracked copies.

### Tier 3 — Local-only

Working artifacts that support review but are not canonical repo state.

Examples:

- `docs/evidence/*.md` (evidence packs maintained during verification work)

## Enforcement

<!-- prettier-ignore-start -->
| Mechanism | Requirement |
|-----------|-------------|
| `.gitignore` | `logs/verification/*.json` ignored exactly once; no `!logs/verification/` negation |
| Contract tests | Assert gitignore policy; no file-existence replay gates on generated JSON |
| CI | `uv run python -m tools.verify_requirements` before `uv run pytest` |
<!-- prettier-ignore-end -->

## Related Documents

- `docs/governance/constraint-inventory.md` — CI-051 through CI-054
- `docs/governance/constraint-ledger-schema.md` — ledger file locations
- `docs/verify-requirements-pipeline.md` — generation flow and authority
