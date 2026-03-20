# Fix: AC Coverage Check in `_collect_evidence_gaps()`

## Context

`_collect_evidence_gaps()` validates proof-type, failure-mode, and entry-point coverage against
`PlanItem` metadata, but it never cross-references whether every acceptance criterion declared in
`docs/PLAN.md` has a matching row in the evidence pack's Proof Matrix. As a result, an item with
AC1–AC3 in PLAN.md can reach `status='verified'` with a single AC1 row in the pack, because the
gate only verifies that the declared `Required-Proof-Types` key is present — not that all ACs are
individually covered.

**Affected verified items (plan ACs > proof matrix rows):** AF-00-02b, AF-00-03, AF-00-04,
AF-00-05, AF-01-01, AF-01-02, AF-02-02, AF-04-02.

---

## Root Cause (5 missing pieces, all in one file)

| #   | Location                   | Missing                                                              |
| --- | -------------------------- | -------------------------------------------------------------------- |
| 1   | `PlanItem` dataclass       | `acceptance_criteria: list[str]` field (AC labels from PLAN.md)      |
| 2   | `parse_plan_items()`       | regex + accumulation for `> - AC1:` lines                            |
| 3   | `EvidencePack` dataclass   | `criteria_covered: list[str]` field (col-1 labels from proof matrix) |
| 4   | `_extract_proof_matrix()`  | `parts[0]` (criterion label) read but discarded                      |
| 5   | `_collect_evidence_gaps()` | no loop checking every PLAN.md AC against `criteria_covered`         |

---

## Implementation Plan

**All changes are in one file:** `src/aetherflow/core/verification_report.py`
**Tests go in:** `tests/contracts/test_proof_verifier.py`

### 1. Write failing tests first (TDD)

Add three new tests to `tests/contracts/test_proof_verifier.py`:

- `test_partial_ac_coverage_produces_gap` — `PlanItem.acceptance_criteria = ["AC1","AC2","AC3"]`,
  evidence pack proof matrix has only one row for AC1 (single `proof_types` entry). Assert
  `evaluate_plan_item()` returns `status='evidenced'` and gaps contain a message for AC2 and AC3.

- `test_full_ac_coverage_clears_ac_gap` — `PlanItem.acceptance_criteria = ["AC1","AC2"]`, evidence
  pack has two proof matrix rows (AC1 and AC2). Assert `status='verified'` with no AC gaps (given
  approved reviewer status and matching proof types).

- `test_item_without_plan_acs_skips_ac_check` — `PlanItem.acceptance_criteria = []`. Assert no
  gap message begins with `'Acceptance criterion not covered'`.

Use the existing `_make_item()` helper; extend it to accept `acceptance_criteria: list[str] | None`
and pass it through to `PlanItem`. Use the existing `_write_evidence_pack()` helper to control how
many matrix rows are generated.

### 2. Add `_PLAN_AC_LABEL_RE` regex constant (line ~130, near other `_*_RE` constants)

```python
_PLAN_AC_LABEL_RE = re.compile(r'^\s*> - (AC\d+):')
```

### 3. Add `acceptance_criteria` field to `PlanItem` (after `failure_modes`)

```python
acceptance_criteria: list[str] = field(default_factory=list)
```

Update the class docstring to document the new attribute.

### 4. Extend `parse_plan_items()` accumulator (after `lifecycle_match` block, ~line 204)

```python
ac_label_match = _PLAN_AC_LABEL_RE.match(raw_line)
if ac_label_match:
    current.acceptance_criteria.append(ac_label_match.group(1))
    continue
```

### 5. Add `criteria_covered` field to `EvidencePack` (after `failure_coverages`)

```python
criteria_covered: list[str]
```

Update the class docstring to document the new attribute.

### 6. Update `_extract_proof_matrix()` to capture criterion column

Change return type annotation from `tuple[list[str], list[str], list[str]]` to
`tuple[list[str], list[str], list[str], list[str]]`.

Add `criteria_covered: list[str] = []` alongside `proof_types`. Inside the row loop:

```python
criteria_covered.append(parts[0])   # e.g. "AC1"
proof_types.append(parts[1].casefold())
```

Return `criteria_covered, proof_types, entry_points, failure_coverages`.

### 7. Update `parse_evidence_pack()` to unpack and pass `criteria_covered`

```python
criteria_covered, proof_types, entry_points, failure_coverages = _extract_proof_matrix(lines, path)
```

Add `criteria_covered=criteria_covered` to the `EvidencePack(...)` constructor call.

### 8. Add AC coverage check to `_collect_evidence_gaps()`

Append at the end of the function body, after the entry-point block:

```python
if item.acceptance_criteria:
    covered = {c.casefold() for c in evidence_pack.criteria_covered}
    for ac_label in item.acceptance_criteria:
        if ac_label.casefold() not in covered:
            gaps.append(f'Acceptance criterion not covered in proof matrix: {ac_label}')
```

---

## Critical Files

| File                                         | Changes                                    |
| -------------------------------------------- | ------------------------------------------ |
| `src/aetherflow/core/verification_report.py` | All 7 implementation steps above           |
| `tests/contracts/test_proof_verifier.py`     | 3 new tests + extend `_make_item()` helper |

---

## Verification

```bash
# 1. New tests should be RED before implementation, GREEN after
uv run pytest tests/contracts/test_proof_verifier.py -v

# 2. Re-grade all items — previously false-positive "verified" items should downgrade
uv run python tools/proof_verifier.py

# 3. Full quality gate
uv run pytest && uv run ruff check . && uv run bandit -r src/
```

**Expected re-grade outcome:** AF-00-02b, AF-00-03, AF-00-04, AF-00-05, AF-01-01, AF-01-02,
AF-02-02, AF-04-02 should all move from `verified` → `evidenced` with new gaps listing each
uncovered AC label.
