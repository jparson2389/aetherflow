# Benchmark Subsystem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `tools/benchmark/` subsystem that measures model capability against the exact structured-output contracts Aetherflow's automation loop already uses, plus raw runtime throughput via `llama-bench.exe`.

**Architecture:** The benchmark reuses `tools/agent_call.py`, `tools/prompts.py`, `tools/gbnf_grammars.py`, `tools/validation_gate.py`, and `tools/models.ini` — it is an instrumented, repeatable version of the real automation path, not a separate harness. Server config (`base_url`, `api_key`, `grammar_capable`) comes from `agent_manifest.json`. Role-to-model resolution uses the `stage_to_alias` map in `agent_manifest.json`, not abstract names.

**Tech Stack:** Python 3.12, pydantic v2, openai SDK (local llama-server backend), sqlite3 (stdlib), uv, pytest

---

## Config Sources (read before implementing anything)

Two files govern all model resolution — never hardcode paths or URLs:

<!-- prettier-ignore-start -->
| File                  | What it provides                                           |
|-----------------------|------------------------------------------------------------|
| `agent_manifest.json` | `base_url`, `api_key`, `grammar_capable`, `stage_to_alias` |
| `tools/models.ini`    | GGUF model path, ctx-size, draft config per alias          |
<!-- prettier-ignore-end -->

Stage→alias mapping (from `agent_manifest.json`):

```
pm_verify  → pm        (verifier suite)
pm_next    → pm        (planner suite)
quick_fix  → quick-fix (repair suite)
```

> **Note:** `architect` is a valid alias in `models.ini` and `required_aliases`, but is not yet in `stage_to_alias`. Task 0 adds it before any benchmark code is written.

## File Map

### New files

```
docs/automation-loop/model-benchmark-contract.md   ← Phase 0 contract (markdown only)

tools/benchmark/__init__.py
tools/benchmark/result_types.py    ← BenchmarkCase, BenchmarkResult pydantic models
tools/benchmark/persistence.py     ← JSONL writer + SQLite aggregate store
tools/benchmark/scorers.py         ← hard gates + soft scores + failure tag constants
tools/benchmark/validators.py      ← thin wrappers around pydantic model validation
tools/benchmark/registry.py        ← case registry: suite name → list[BenchmarkCase]
tools/benchmark/cli.py             ← typer/argparse CLI

tools/benchmark/runtime/__init__.py
tools/benchmark/runtime/capability_runner.py  ← runs cases via OpenAI SDK (reuses agent_call internals)
tools/benchmark/runtime/server_process.py     ← llama-server lifecycle (start/stop/health)
tools/benchmark/runtime/llama_bench_runner.py ← invokes llama-bench.exe, stores JSONL

tools/benchmark/cases/__init__.py
tools/benchmark/cases/verifier.py  ← pm_verify stage cases
tools/benchmark/cases/coder.py     ← architect stage cases
tools/benchmark/cases/planner.py   ← pm_next stage cases
tools/benchmark/cases/repair.py    ← quick-fix stage cases

tools/benchmark/schemas/__init__.py
tools/benchmark/schemas/verdict.py  ← imports PMVerdict from tools.plan_exec
tools/benchmark/schemas/writes.py   ← imports WriteEntry, WritesPayload from tools.validation_gate
tools/benchmark/schemas/plan.py     ← imports PlanWorkItem, PMWorkItem from tools.plan_exec

tools/benchmark/reports/__init__.py
tools/benchmark/reports/aggregate.py       ← rolls up JSONL rows into summary dicts
tools/benchmark/reports/markdown_report.py ← renders summary → markdown

tools/benchmark/models.ini          ← model name → GGUF path for llama-bench (not aliases)
tools/benchmark_runner.py           ← thin top-level entrypoint (delegates to cli.py)

scripts/run-benchmark.ps1           ← PowerShell convenience wrapper

tests/unit/test_benchmark_result_types.py
tests/unit/test_benchmark_scorers.py
tests/unit/test_benchmark_validators.py
tests/unit/test_benchmark_registry.py
tests/contracts/test_benchmark_case_contracts.py
tests/contracts/test_benchmark_schema_alignment.py
```

### Modified files

```
tools/plan_exec.py   ← ensure AgentManifest, PMVerdict, PMWorkItem, PlanWorkItem are importable
                       (they already are — just verify, do not restructure)
.gitignore           ← add logs/benchmark/raw/ and logs/benchmark/sqlite/ if not present
```

### Output directories (create at runtime, not in git)

```
logs/benchmark/raw/      ← JSONL result rows, one file per run
logs/benchmark/reports/  ← markdown reports
logs/benchmark/sqlite/   ← benchmark.db aggregate store
```

---

## Stage 1 — Capability path: verifier + coder suites, result logging, reports

### Task 0: Patch `agent_manifest.json` to add the `architect` stage

**Files:**

- Modify: `agent_manifest.json`

The `stage_to_alias` map in `agent_manifest.json` does not yet include `architect`.
The coder benchmark suite uses `stage='architect'` and the contract tests verify
stage→alias consistency against this map. Add it before writing any benchmark code.

- [ ] **Step 1: Add `"architect": "architect"` to `stage_to_alias` and add `llama_bench_exe` path**

Open `agent_manifest.json` and apply both additions:

```json
"stage_to_alias": {
    "pm_next": "pm",
    "pm_verify": "pm",
    "architect": "architect",
    "quick_fix": "quick-fix",
    "manual_research": "researcher"
},
"llama_bench_exe": "C:\\Users\\Dada\\AI_Tools\\llama.cpp\\build\\bin\\Release\\llama-bench.exe"
```

- [ ] **Step 2: Verify the file is valid JSON**

```bash
python -c "import json; json.load(open('agent_manifest.json')); print('valid')"
```

Expected: `valid`

- [ ] **Step 3: Commit**

```bash
git add agent_manifest.json
git commit -m "chore: add architect to stage_to_alias in agent_manifest.json"
```

---

### Task 1: Write the benchmark contract doc

**Files:**

- Create: `docs/automation-loop/model-benchmark-contract.md`

- [ ] **Step 1: Create the contract doc**

```markdown
# Model Benchmark Contract

## Authoritative benchmark path

`llama-server` for capability benchmarking (same path as the automation loop).
`llama-bench.exe` for raw runtime throughput only.

## Schemas benchmarked

| Suite    | Stage     | Alias     | Schema        |
|----------|-----------|-----------|---------------|
| verifier | pm_verify | pm        | PMVerdict     |
| coder    | architect | architect | WritesPayload |
| planner  | pm_next   | pm        | PMResponse    |
| repair   | quick-fix | quick-fix | WritesPayload |

## Pass/fail thresholds by suite

| Suite    | Pydantic-valid (hard) | Instruction pass (soft) |
|----------|-----------------------|-------------------------|
| verifier | ≥ 95%                 | ≥ 90%                   |
| coder    | ≥ 90%                 | ≥ 80%                   |
| planner  | ≥ 90%                 | ≥ 75%                   |
| repair   | ≥ 85%                 | ≥ 75%                   |

## Hard gates (all must pass for result.success = True)

1. response received (not empty)
2. not truncated
3. valid JSON
4. Pydantic-valid against target schema
5. no extra prose outside JSON

## Soft scores (0.0–1.0 each)

- instruction_adherence
- completeness
- semantic_usefulness
- minimality

## Failure tags

extra_prose | invalid_json | wrong_root_type | missing_required_field |
enum_violation | hallucinated_field | truncated_output |
ignored_instruction | bad_repair

## Retry policy

Max 2 retries per case. Record each attempt separately.
```

- [ ] **Step 2: Commit**

```bash
git add docs/automation-loop/model-benchmark-contract.md
git commit -m "docs: add model benchmark contract"
```

---

### Task 2: Scaffold package + result_types

**Files:**

- Create: `tools/benchmark/__init__.py`
- Create: `tools/benchmark/result_types.py`
- Create: `tools/benchmark/runtime/__init__.py`
- Create: `tools/benchmark/cases/__init__.py`
- Create: `tools/benchmark/schemas/__init__.py`
- Create: `tools/benchmark/reports/__init__.py`
- Test: `tests/unit/test_benchmark_result_types.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_benchmark_result_types.py
from __future__ import annotations
import pytest
from tools.benchmark.result_types import BenchmarkCase, BenchmarkResult, AttemptResult


def test_benchmark_case_requires_stage():
    with pytest.raises(Exception):
        BenchmarkCase(suite='verifier', prompt='hi', expected_schema='PMVerdict')


def test_attempt_result_success_false_when_no_json():
    a = AttemptResult(raw_output='not json', valid_json=False,
                      pydantic_valid=False, no_extra_prose=False,
                      truncated=False, tags=['invalid_json'],
                      latency_ms=100, tokens_generated=10)
    assert not a.success


def test_benchmark_result_aggregates_attempts():
    case = BenchmarkCase(suite='verifier', stage='pm_verify', alias='pm',
                         prompt='test', expected_schema='PMVerdict')
    result = BenchmarkResult(case=case, attempts=[], final_success=False,
                             run_id='abc', model_alias='pm', model_path='x.gguf')
    assert result.retry_count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/unit/test_benchmark_result_types.py -v
```

Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Create empty `__init__.py` files**

```python
# tools/benchmark/__init__.py
# tools/benchmark/runtime/__init__.py
# tools/benchmark/cases/__init__.py
# tools/benchmark/schemas/__init__.py
# tools/benchmark/reports/__init__.py
```

(all empty)

- [ ] **Step 4: Implement result_types.py**

```python
# tools/benchmark/result_types.py
'''Pydantic models for benchmark case definitions and result records.'''
from __future__ import annotations
from pydantic import BaseModel, Field, computed_field


class BenchmarkCase(BaseModel):
    '''Definition of a single benchmark case.'''
    suite: str
    stage: str               # pm_verify | pm_next | architect | quick_fix
    alias: str               # pm | architect | quick-fix  (from stage_to_alias)
    prompt: str
    expected_schema: str     # class name: PMVerdict | WritesPayload | PMResponse
    system_prompt: str = ''
    use_grammar: bool = False
    description: str = ''


class AttemptResult(BaseModel):
    '''Result of a single LLM call attempt.'''
    raw_output: str
    valid_json: bool
    pydantic_valid: bool
    no_extra_prose: bool
    truncated: bool
    parsed: dict | None = None
    tags: list[str] = Field(default_factory=list)
    latency_ms: float
    tokens_generated: int
    instruction_adherence: float = 0.0
    completeness: float = 0.0
    semantic_usefulness: float = 0.0
    minimality: float = 0.0

    @computed_field
    @property
    def success(self) -> bool:
        '''True only when all hard gates pass.'''
        return (self.valid_json and self.pydantic_valid
                and self.no_extra_prose and not self.truncated)


class BenchmarkResult(BaseModel):
    '''Full record for one case execution (possibly multiple attempts).'''
    run_id: str
    model_alias: str
    model_path: str
    case: BenchmarkCase
    attempts: list[AttemptResult]
    final_success: bool
    timestamp: str = ''

    @computed_field
    @property
    def retry_count(self) -> int:
        '''Number of attempts beyond the first.'''
        return max(0, len(self.attempts) - 1)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_benchmark_result_types.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add tools/benchmark/ tests/unit/test_benchmark_result_types.py
git commit -m "feat: scaffold benchmark package and result_types"
```

---

### Task 3: Add persistence (JSONL + SQLite)

**Files:**

- Create: `tools/benchmark/persistence.py`
- Test: `tests/unit/test_benchmark_result_types.py` (extend)

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_benchmark_result_types.py`:

```python
import tempfile, json
from pathlib import Path
from tools.benchmark.persistence import BenchmarkStore


def test_store_writes_jsonl(tmp_path):
    store = BenchmarkStore(base_dir=tmp_path)
    case = BenchmarkCase(suite='verifier', stage='pm_verify', alias='pm',
                         prompt='x', expected_schema='PMVerdict')
    result = BenchmarkResult(case=case, attempts=[], final_success=False,
                             run_id='r1', model_alias='pm', model_path='m.gguf',
                             timestamp='2026-01-01T00:00:00')
    store.save(result)
    rows = list((tmp_path / 'raw').glob('*.jsonl'))
    assert len(rows) == 1
    data = json.loads(rows[0].read_text().strip())
    assert data['run_id'] == 'r1'


def test_store_queries_by_suite(tmp_path):
    store = BenchmarkStore(base_dir=tmp_path)
    case = BenchmarkCase(suite='verifier', stage='pm_verify', alias='pm',
                         prompt='x', expected_schema='PMVerdict')
    result = BenchmarkResult(case=case, attempts=[], final_success=True,
                             run_id='r2', model_alias='pm', model_path='m.gguf',
                             timestamp='2026-01-01T00:00:00')
    store.save(result)
    rows = store.query(suite='verifier')
    assert len(rows) == 1
    assert rows[0]['run_id'] == 'r2'
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/unit/test_benchmark_result_types.py -v -k "store"
```

Expected: `ImportError`

- [ ] **Step 3: Implement persistence.py**

```python
# tools/benchmark/persistence.py
'''JSONL writer and SQLite aggregate store for benchmark results.'''
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from tools.benchmark.result_types import BenchmarkResult

_SCHEMA = '''
CREATE TABLE IF NOT EXISTS results (
    run_id TEXT,
    suite TEXT,
    stage TEXT,
    alias TEXT,
    model_path TEXT,
    final_success INTEGER,
    retry_count INTEGER,
    timestamp TEXT,
    tags TEXT,
    raw JSON
)
'''


class BenchmarkStore:
    '''Persists benchmark results to JSONL (raw) and SQLite (aggregate).'''

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path(__file__).resolve().parents[2] / 'logs' / 'benchmark'
        self._raw_dir = base_dir / 'raw'
        self._db_path = base_dir / 'sqlite' / 'benchmark.db'
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as con:
            con.execute(_SCHEMA)

    def save(self, result: BenchmarkResult) -> None:
        '''Append result to JSONL and upsert into SQLite.'''
        date_tag = result.timestamp[:10] if result.timestamp else datetime.now().strftime('%Y-%m-%d')
        jsonl_path = self._raw_dir / f'{date_tag}.jsonl'
        row = result.model_dump()
        with jsonl_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row) + '\n')

        all_tags: list[str] = []
        for attempt in result.attempts:
            all_tags.extend(attempt.tags)
        with sqlite3.connect(self._db_path) as con:
            con.execute(
                'INSERT INTO results VALUES (?,?,?,?,?,?,?,?,?,?)',
                (result.run_id, result.case.suite, result.case.stage,
                 result.model_alias, result.model_path,
                 int(result.final_success), result.retry_count,
                 result.timestamp, json.dumps(all_tags), json.dumps(row))
            )

    def query(self, suite: str | None = None,
              alias: str | None = None) -> list[dict]:
        '''Return rows matching optional suite and alias filters.'''
        clauses, params = [], []
        if suite:
            clauses.append('suite = ?')
            params.append(suite)
        if alias:
            clauses.append('alias = ?')
            params.append(alias)
        where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
        with sqlite3.connect(self._db_path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(f'SELECT raw FROM results {where}', params).fetchall()
        return [json.loads(r['raw']) for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_benchmark_result_types.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tools/benchmark/persistence.py tests/unit/test_benchmark_result_types.py
git commit -m "feat: add benchmark persistence (JSONL + SQLite)"
```

---

### Task 4: Add scorers and validators

**Files:**

- Create: `tools/benchmark/scorers.py`
- Create: `tools/benchmark/validators.py`
- Test: `tests/unit/test_benchmark_scorers.py`
- Test: `tests/unit/test_benchmark_validators.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_benchmark_scorers.py
from tools.benchmark.scorers import (
    FAILURE_TAGS, check_hard_gates, FailureTag
)


def test_failure_tags_are_strings():
    assert all(isinstance(t, str) for t in FAILURE_TAGS)


def test_hard_gates_pass_for_valid_json_output():
    gates = check_hard_gates('{"status": "pass", "missing": [], "notes": ""}')
    assert gates['valid_json'] is True
    assert gates['truncated'] is False
    assert gates['no_extra_prose'] is True


def test_hard_gates_fail_for_prose_prefix():
    gates = check_hard_gates('Here is the result:\n{"status": "pass", "missing": [], "notes": ""}')
    assert gates['no_extra_prose'] is False
    assert FailureTag.EXTRA_PROSE in gates['tags']


def test_hard_gates_fail_for_empty():
    gates = check_hard_gates('')
    assert gates['valid_json'] is False
    assert FailureTag.INVALID_JSON in gates['tags']
```

```python
# tests/unit/test_benchmark_validators.py
from tools.benchmark.validators import validate_against_schema


def test_validate_pmverdict_passes():
    raw = '{"status": "pass", "missing": [], "notes": ""}'
    ok, parsed, tags = validate_against_schema(raw, 'PMVerdict')
    assert ok
    assert parsed is not None
    assert tags == []


def test_validate_pmverdict_fails_on_bad_status():
    raw = '{"status": "maybe", "missing": [], "notes": ""}'
    ok, parsed, tags = validate_against_schema(raw, 'PMVerdict')
    assert not ok
    assert 'enum_violation' in tags
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/unit/test_benchmark_scorers.py tests/unit/test_benchmark_validators.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement scorers.py**

```python
# tools/benchmark/scorers.py
'''Hard gate checks, failure tag constants, and soft score helpers.'''
from __future__ import annotations

import json
from enum import StrEnum


class FailureTag(StrEnum):
    EXTRA_PROSE = 'extra_prose'
    INVALID_JSON = 'invalid_json'
    WRONG_ROOT_TYPE = 'wrong_root_type'
    MISSING_REQUIRED_FIELD = 'missing_required_field'
    ENUM_VIOLATION = 'enum_violation'
    HALLUCINATED_FIELD = 'hallucinated_field'
    TRUNCATED_OUTPUT = 'truncated_output'
    IGNORED_INSTRUCTION = 'ignored_instruction'
    BAD_REPAIR = 'bad_repair'


FAILURE_TAGS: list[str] = [t.value for t in FailureTag]


def check_hard_gates(raw: str) -> dict:
    '''Check all hard gates and return a dict of results plus accumulated tags.'''
    tags: list[str] = []
    result: dict = {
        'valid_json': False,
        'truncated': False,
        'no_extra_prose': False,
        'tags': tags,
    }
    stripped = raw.strip()
    if not stripped:
        tags.append(FailureTag.INVALID_JSON)
        return result

    # Truncation heuristic: ends mid-string or mid-object
    result['truncated'] = stripped.endswith(('...', ','))
    if result['truncated']:
        tags.append(FailureTag.TRUNCATED_OUTPUT)

    # Extra prose: content before the first { or [
    first_brace = min(
        (stripped.find(c) for c in ('{', '[') if c in stripped),
        default=-1
    )
    if first_brace < 0:
        tags.append(FailureTag.INVALID_JSON)
        return result

    preamble = stripped[:first_brace].strip()
    result['no_extra_prose'] = preamble == ''
    if preamble:
        tags.append(FailureTag.EXTRA_PROSE)

    # JSON parse
    json_str = stripped[first_brace:]
    try:
        json.loads(json_str)
        result['valid_json'] = True
    except json.JSONDecodeError:
        tags.append(FailureTag.INVALID_JSON)

    return result
```

- [ ] **Step 4: Implement validators.py**

```python
# tools/benchmark/validators.py
'''Thin schema validation wrappers that import real Pydantic models.'''
from __future__ import annotations

import json
from pydantic import ValidationError

from tools.benchmark.scorers import FailureTag

from tools.plan_exec import PMVerdict, PlanWorkItem, PMResponse
from tools.validation_gate import WritesPayload

_SCHEMA_MAP = {
    'PMVerdict': PMVerdict,
    'PMResponse': PMResponse,
    'PlanWorkItem': PlanWorkItem,
    'WritesPayload': WritesPayload,
}


def validate_against_schema(
    raw: str, schema_name: str
) -> tuple[bool, dict | None, list[str]]:
    '''Validate raw JSON string against a named schema.

    Returns:
        (success, parsed_dict_or_None, failure_tags)
    '''
    tags: list[str] = []
    stripped = raw.strip()
    first_brace = min(
        (stripped.find(c) for c in ('{', '[') if c in stripped), default=-1
    )
    if first_brace < 0:
        return False, None, [FailureTag.INVALID_JSON]

    try:
        obj = json.loads(stripped[first_brace:])
    except json.JSONDecodeError:
        return False, None, [FailureTag.INVALID_JSON]

    if not isinstance(obj, dict):
        return False, None, [FailureTag.WRONG_ROOT_TYPE]

    model_cls = _SCHEMA_MAP.get(schema_name)
    if model_cls is None:
        raise ValueError(f'Unknown schema: {schema_name}')

    try:
        model_cls.model_validate(obj)
        return True, obj, []
    except ValidationError as exc:
        for err in exc.errors():
            etype = err.get('type', '')
            if 'enum' in etype or 'literal' in etype:
                tags.append(FailureTag.ENUM_VIOLATION)
            elif 'missing' in etype:
                tags.append(FailureTag.MISSING_REQUIRED_FIELD)
            else:
                tags.append(FailureTag.HALLUCINATED_FIELD)
        return False, obj, list(dict.fromkeys(tags))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_benchmark_scorers.py tests/unit/test_benchmark_validators.py -v
```

Expected: all PASS

- [ ] **Step 6: Lint**

```bash
uv run ruff check tools/benchmark/scorers.py tools/benchmark/validators.py --fix
```

- [ ] **Step 7: Commit**

```bash
git add tools/benchmark/scorers.py tools/benchmark/validators.py \
        tests/unit/test_benchmark_scorers.py tests/unit/test_benchmark_validators.py
git commit -m "feat: add benchmark scorers and validators"
```

---

### Task 5: Add capability_runner

**Files:**

- Create: `tools/benchmark/runtime/capability_runner.py`

> **Key constraint:** Do not recreate OpenAI client setup. Import `_build_messages` and `_build_extra_body` from `tools.agent_call`. Load `base_url`/`api_key`/`grammar_capable` from `agent_manifest.json`. Load model path from `tools/models.ini`.

- [ ] **Step 1: Implement capability_runner.py**

```python
# tools/benchmark/runtime/capability_runner.py
'''Runs a BenchmarkCase through the real structured-output path.

Reuses tools.agent_call internals and loads config from agent_manifest.json
and tools/models.ini. Never reconstructs its own OpenAI client setup.
'''
from __future__ import annotations

import configparser
import json
import time
from pathlib import Path
from typing import Any

from loguru import logger
from openai import OpenAI

from tools.agent_call import _build_extra_body, _build_messages
from tools.benchmark.result_types import AttemptResult, BenchmarkCase, BenchmarkResult
from tools.benchmark.scorers import check_hard_gates
from tools.benchmark.validators import validate_against_schema

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = _REPO_ROOT / 'agent_manifest.json'
_MODELS_INI_PATH = _REPO_ROOT / 'tools' / 'models.ini'

MAX_RETRIES = 2


def _load_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST_PATH.read_text(encoding='utf-8'))


def _load_model_path(alias: str) -> str:
    cfg = configparser.ConfigParser()
    cfg.read(_MODELS_INI_PATH)
    if alias in cfg and 'model' in cfg[alias]:
        return cfg[alias]['model']
    if '*' in cfg and 'model' in cfg['*']:
        return cfg['*']['model']
    raise KeyError(f'No model path found for alias: {alias!r}')


def run_case(case: BenchmarkCase, run_id: str) -> BenchmarkResult:
    '''Execute a benchmark case with retries and return a full result record.'''
    manifest = _load_manifest()
    base_url: str = manifest['base_url']
    api_key: str = manifest.get('api_key', 'none')
    grammar_capable: bool = bool(manifest.get('grammar_capable', False))
    model_path = _load_model_path(case.alias)

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=300)
    attempts: list[AttemptResult] = []

    for attempt_n in range(MAX_RETRIES + 1):
        messages = _build_messages(case.system_prompt, case.prompt)
        use_local = '127.0.0.1' in base_url or 'localhost' in base_url
        extra_body = _build_extra_body(model=case.alias, use_local_backend=use_local)

        kwargs: dict[str, Any] = {
            'model': case.alias,
            'messages': messages,
        }
        if extra_body:
            kwargs['extra_body'] = extra_body

        t0 = time.monotonic()
        try:
            resp = client.chat.completions.create(**kwargs)
            raw = (resp.choices[0].message.content or '').strip()
            usage = resp.usage
            tokens = usage.completion_tokens if usage else 0
        except Exception as exc:
            logger.warning('Attempt {} failed with exception: {}', attempt_n, exc)
            attempts.append(AttemptResult(
                raw_output='', valid_json=False, pydantic_valid=False,
                no_extra_prose=False, truncated=False,
                tags=['invalid_json'], latency_ms=0, tokens_generated=0,
            ))
            continue
        finally:
            latency_ms = (time.monotonic() - t0) * 1000

        gates = check_hard_gates(raw)
        ok, parsed, schema_tags = (False, None, []) if not gates['valid_json'] \
            else validate_against_schema(raw, case.expected_schema)

        all_tags = list(dict.fromkeys(gates['tags'] + schema_tags))
        attempt = AttemptResult(
            raw_output=raw,
            valid_json=gates['valid_json'],
            pydantic_valid=ok,
            no_extra_prose=gates['no_extra_prose'],
            truncated=gates['truncated'],
            parsed=parsed,
            tags=all_tags,
            latency_ms=latency_ms,
            tokens_generated=tokens,
        )
        attempts.append(attempt)
        if attempt.success:
            break
        logger.debug('Attempt {} failed, tags={}', attempt_n, all_tags)

    final_success = any(a.success for a in attempts)
    return BenchmarkResult(
        run_id=run_id,
        model_alias=case.alias,
        model_path=model_path,
        case=case,
        attempts=attempts,
        final_success=final_success,
        timestamp=time.strftime('%Y-%m-%dT%H:%M:%S'),
    )
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
uv run python -c "from tools.benchmark.runtime.capability_runner import run_case; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Lint**

```bash
uv run ruff check tools/benchmark/runtime/capability_runner.py --fix
```

- [ ] **Step 4: Commit**

```bash
git add tools/benchmark/runtime/capability_runner.py
git commit -m "feat: add capability_runner reusing agent_call internals"
```

---

### Task 6: Add verifier cases (pm_verify stage)

**Files:**

- Create: `tools/benchmark/schemas/verdict.py`
- Create: `tools/benchmark/cases/verifier.py`

- [ ] **Step 1: Create schema wrapper**

```python
# tools/benchmark/schemas/verdict.py
'''Re-exports PMVerdict from plan_exec for benchmark use.'''
from tools.plan_exec import PMVerdict

__all__ = ['PMVerdict']
```

- [ ] **Step 2: Create verifier cases**

```python
# tools/benchmark/cases/verifier.py
'''Benchmark cases for the pm_verify stage (alias: pm).

Cases are shaped like real PM verify calls: given a work item description
and an implementation summary, the model must return a PMVerdict JSON object
with status, missing list, and notes.
'''
from __future__ import annotations
from tools.benchmark.result_types import BenchmarkCase
from tools.prompts import SYSTEM_PM_VERIFY  # confirmed constant name in tools/prompts.py line 154


def _case(description: str, prompt: str) -> BenchmarkCase:
    return BenchmarkCase(
        suite='verifier',
        stage='pm_verify',
        alias='pm',
        expected_schema='PMVerdict',
        system_prompt=SYSTEM_PM_VERIFY,
        description=description,
        prompt=prompt,
    )


CASES: list[BenchmarkCase] = [
    _case(
        description='pass: all acceptance criteria met',
        prompt=(
            'Work item: "Add health endpoint"\n'
            'Acceptance: ["GET /health returns 200", "response is JSON"]\n'
            'Implementation: Added GET /health route returning {"status": "ok"} with 200.\n'
            'Verify and return PMVerdict JSON.'
        ),
    ),
    _case(
        description='fail: missing required criterion',
        prompt=(
            'Work item: "Add health endpoint"\n'
            'Acceptance: ["GET /health returns 200", "response is JSON", "logs request"]\n'
            'Implementation: Added GET /health returning 200 JSON. No logging added.\n'
            'Verify and return PMVerdict JSON.'
        ),
    ),
    _case(
        description='fail: placeholder implementation detected',
        prompt=(
            'Work item: "Implement entitlement check"\n'
            'Acceptance: ["calls EntitlementStore.evaluate()", "returns bool"]\n'
            'Implementation: Added check() function that returns True.\n'
            'Verify and return PMVerdict JSON.'
        ),
    ),
    _case(
        description='fail: thin implementation with no logic',
        prompt=(
            'Work item: "Worker supervisor restart budget"\n'
            'Acceptance: ["tracks restart count", "stops after 3 failures", '
            '"logs each restart"]\n'
            'Implementation: pass\n'
            'Verify and return PMVerdict JSON.'
        ),
    ),
]
```

> **Note:** Check the actual constant name for the PM verify system prompt in `tools/prompts.py` — it may be `SYSTEM_PM_VERIFY` or similar. Import the correct name.

- [ ] **Step 3: Verify cases import cleanly**

```bash
uv run python -c "from tools.benchmark.cases.verifier import CASES; print(len(CASES), 'cases')"
```

Expected: `4 cases`

- [ ] **Step 5: Lint**

```bash
uv run ruff check tools/benchmark/cases/verifier.py tools/benchmark/schemas/verdict.py --fix
```

- [ ] **Step 6: Commit**

```bash
git add tools/benchmark/cases/verifier.py tools/benchmark/schemas/verdict.py
git commit -m "feat: add verifier benchmark cases (pm_verify stage)"
```

---

### Task 7: Add coder cases (architect stage)

**Files:**

- Create: `tools/benchmark/schemas/writes.py`
- Create: `tools/benchmark/cases/coder.py`

- [ ] **Step 1: Create schema wrapper**

```python
# tools/benchmark/schemas/writes.py
'''Re-exports WritesPayload from validation_gate for benchmark use.'''
from tools.validation_gate import WritesPayload

__all__ = ['WritesPayload']
```

- [ ] **Step 2: Create coder cases**

```python
# tools/benchmark/cases/coder.py
'''Benchmark cases for the architect stage (alias: architect).

Cases require generating a WritesPayload JSON object: repo-relative writes
only, no extra prose, exact JSON, interfaces preserved.
'''
from __future__ import annotations
from tools.benchmark.result_types import BenchmarkCase
from tools.prompts import SYSTEM_JSON_WRITES


def _case(description: str, prompt: str) -> BenchmarkCase:
    return BenchmarkCase(
        suite='coder',
        stage='architect',
        alias='architect',
        expected_schema='WritesPayload',
        system_prompt=SYSTEM_JSON_WRITES,
        description=description,
        prompt=prompt,
    )


CASES: list[BenchmarkCase] = [
    _case(
        description='simple function: writes valid JSON, no prose',
        prompt=(
            'Write a Python function `add(a, b)` that returns a + b. '
            'Place it in src/aetherflow/utils/math_utils.py. '
            'Return only the WritesPayload JSON.'
        ),
    ),
    _case(
        description='single file only: does not write unrequested files',
        prompt=(
            'Add a module-level constant `VERSION = "0.1.0"` to '
            'src/aetherflow/utils/version.py. '
            'Return only the WritesPayload JSON. Write exactly one file.'
        ),
    ),
    _case(
        description='preserve existing interface: do not rename function',
        prompt=(
            'Add type annotations to the existing `evaluate` method in '
            'src/aetherflow/core/entitlements.py without changing its signature. '
            'Return only the WritesPayload JSON.'
        ),
    ),
    _case(
        description='minimal writes: only files mentioned in prompt',
        prompt=(
            'Add a log statement to the top of `src/aetherflow/main.py`. '
            'Return only the WritesPayload JSON. '
            'Do not modify any other files.'
        ),
    ),
]
```

- [ ] **Step 3: Verify cases import cleanly**

```bash
uv run python -c "from tools.benchmark.cases.coder import CASES; print(len(CASES), 'cases')"
```

Expected: `4 cases`

- [ ] **Step 4: Lint**

```bash
uv run ruff check tools/benchmark/cases/coder.py tools/benchmark/schemas/writes.py --fix
```

- [ ] **Step 5: Commit**

```bash
git add tools/benchmark/cases/coder.py tools/benchmark/schemas/writes.py
git commit -m "feat: add coder benchmark cases (architect stage)"
```

---

### Task 8: Add markdown report

**Files:**

- Create: `tools/benchmark/reports/aggregate.py`
- Create: `tools/benchmark/reports/markdown_report.py`

- [ ] **Step 1: Implement aggregate.py**

```python
# tools/benchmark/reports/aggregate.py
'''Aggregates raw BenchmarkResult dicts into suite-level summaries.'''
from __future__ import annotations
from collections import defaultdict


def summarise(rows: list[dict]) -> dict[str, dict]:
    '''Roll up result rows into per-suite statistics.

    Returns a dict keyed by suite name with counts and pass rates.
    '''
    suites: dict[str, dict] = defaultdict(lambda: {
        'total': 0, 'passed': 0, 'tags': defaultdict(int),
        'avg_latency_ms': 0.0, 'alias': '',
    })
    for row in rows:
        suite = row.get('case', {}).get('suite', 'unknown')
        s = suites[suite]
        s['total'] += 1
        s['alias'] = row.get('model_alias', '')
        if row.get('final_success'):
            s['passed'] += 1
        for attempt in row.get('attempts', []):
            for tag in attempt.get('tags', []):
                s['tags'][tag] += 1
            s['avg_latency_ms'] += attempt.get('latency_ms', 0)

    for suite, s in suites.items():
        total_attempts = sum(
            len(r.get('attempts', [])) for r in rows
            if r.get('case', {}).get('suite') == suite
        )
        s['pass_rate'] = s['passed'] / s['total'] if s['total'] else 0.0
        s['avg_latency_ms'] = (
            s['avg_latency_ms'] / total_attempts if total_attempts else 0.0
        )
        s['tags'] = dict(s['tags'])

    return dict(suites)
```

- [ ] **Step 2: Implement markdown_report.py**

```python
# tools/benchmark/reports/markdown_report.py
'''Renders a suite summary dict into a markdown report.'''
from __future__ import annotations
from datetime import datetime


def render(summary: dict[str, dict], model_path: str = '') -> str:
    '''Render suite summary to a markdown string answering routing questions.'''
    lines = [
        f'# Benchmark Report — {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        '',
        f'**Model:** `{model_path}`' if model_path else '',
        '',
        '## Suite Results',
        '',
        '| Suite | Alias | Pass Rate | Avg Latency | Top Failure Tags |',
        '|-------|-------|-----------|-------------|-----------------|',
    ]
    for suite, s in sorted(summary.items()):
        top_tags = ', '.join(
            f'{t}({n})' for t, n in
            sorted(s.get('tags', {}).items(), key=lambda x: -x[1])[:3]
        ) or '—'
        lines.append(
            f'| {suite} | {s.get("alias","")} | '
            f'{s.get("pass_rate", 0):.0%} | '
            f'{s.get("avg_latency_ms", 0):.0f}ms | {top_tags} |'
        )
    lines += [
        '',
        '## Routing Recommendations',
        '',
        '| Question | Answer |',
        '|----------|--------|',
    ]
    for suite, s in sorted(summary.items()):
        rate = s.get('pass_rate', 0)
        alias = s.get('alias', '?')
        verdict = '✅ suitable' if rate >= 0.85 else '⚠️ marginal' if rate >= 0.70 else '❌ unsuitable'
        lines.append(f'| Safest for {suite}? | {alias} — {verdict} ({rate:.0%}) |')

    return '\n'.join(l for l in lines if l is not None)
```

- [ ] **Step 3: Verify imports**

```bash
uv run python -c "from tools.benchmark.reports.aggregate import summarise; from tools.benchmark.reports.markdown_report import render; print('ok')"
```

- [ ] **Step 4: Lint**

```bash
uv run ruff check tools/benchmark/reports/ --fix
```

- [ ] **Step 5: Commit**

```bash
git add tools/benchmark/reports/
git commit -m "feat: add benchmark aggregate and markdown report"
```

---

### Task 9: Add CLI and top-level entrypoint

**Files:**

- Create: `tools/benchmark/cli.py`
- Create: `tools/benchmark_runner.py`
- Create: `scripts/run-benchmark.ps1`

- [ ] **Step 1: Implement cli.py**

```python
# tools/benchmark/cli.py
'''CLI entrypoint for the benchmark subsystem.

Usage:
  uv run python -m tools.benchmark.cli run-capability --suite verifier
  uv run python -m tools.benchmark.cli run-capability --suite coder
  uv run python -m tools.benchmark.cli run-capability --all-core
  uv run python -m tools.benchmark.cli report --latest
'''
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path

from loguru import logger

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPORT_DIR = _REPO_ROOT / 'logs' / 'benchmark' / 'reports'


def _run_suite(suite_name: str) -> list[dict]:
    from tools.benchmark.cases import verifier, coder
    from tools.benchmark.runtime.capability_runner import run_case
    from tools.benchmark.persistence import BenchmarkStore

    suite_map = {
        'verifier': verifier.CASES,
        'coder': coder.CASES,
    }
    cases = suite_map.get(suite_name)
    if cases is None:
        logger.error('Unknown suite: {}', suite_name)
        sys.exit(1)

    store = BenchmarkStore()
    results = []
    for case in cases:
        run_id = str(uuid.uuid4())[:8]
        logger.info('Running case: {} [{}]', case.description, suite_name)
        result = run_case(case, run_id=run_id)
        store.save(result)
        status = '✅' if result.final_success else '❌'
        logger.info('{} {} retries={}', status, case.description, result.retry_count)
        results.append(result.model_dump())
    return results


def _cmd_run_capability(args: argparse.Namespace) -> int:
    from tools.benchmark.reports.aggregate import summarise
    from tools.benchmark.reports.markdown_report import render

    suites = ['verifier', 'coder'] if args.all_core else [args.suite]
    all_rows: list[dict] = []
    for suite in suites:
        all_rows.extend(_run_suite(suite))

    summary = summarise(all_rows)
    report = render(summary)
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = _REPORT_DIR / f'{ts}.md'
    out.write_text(report, encoding='utf-8')
    (_REPORT_DIR / 'latest.md').write_text(report, encoding='utf-8')
    logger.info('Report written to {}', out)
    print(report)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    latest = _REPORT_DIR / 'latest.md'
    if not latest.exists():
        logger.error('No report found. Run capability first.')
        return 1
    print(latest.read_text(encoding='utf-8'))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog='benchmark')
    sub = ap.add_subparsers(dest='command')

    run_cap = sub.add_parser('run-capability')
    run_cap.add_argument('--suite', default='verifier',
                         choices=['verifier', 'coder', 'planner', 'repair'])
    run_cap.add_argument('--all-core', action='store_true')

    sub.add_parser('report')

    args = ap.parse_args()
    if args.command == 'run-capability':
        return _cmd_run_capability(args)
    if args.command == 'report':
        return _cmd_report(args)
    ap.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 2: Create top-level runner**

```python
# tools/benchmark_runner.py
'''Top-level benchmark runner — delegates to tools.benchmark.cli.'''
import sys

from tools.benchmark.cli import main

if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 3: Create PowerShell wrapper**

```powershell
# scripts/run-benchmark.ps1
param(
    [string]$Suite = "verifier",
    [switch]$AllCore,
    [switch]$Report
)

if ($Report) {
    uv run python -m tools.benchmark.cli report
} elseif ($AllCore) {
    uv run python -m tools.benchmark.cli run-capability --all-core
} else {
    uv run python -m tools.benchmark.cli run-capability --suite $Suite
}
```

- [ ] **Step 4: Verify CLI help works**

```bash
uv run python -m tools.benchmark.cli --help
```

Expected: shows `run-capability` and `report` subcommands

- [ ] **Step 5: Lint**

```bash
uv run ruff check tools/benchmark/cli.py tools/benchmark_runner.py --fix
```

- [ ] **Step 6: Commit**

```bash
git add tools/benchmark/cli.py tools/benchmark_runner.py scripts/run-benchmark.ps1
git commit -m "feat: add benchmark CLI and PowerShell runner"
```

---

### Task 10: Add contract tests for schema alignment

**Files:**

- Create: `tests/contracts/test_benchmark_schema_alignment.py`

- [ ] **Step 1: Write tests**

```python
# tests/contracts/test_benchmark_schema_alignment.py
'''Verifies benchmark schemas stay locked to the real automation contracts.

These tests fail if someone refactors plan_exec or validation_gate
without updating the benchmark schema wrappers.
'''
from __future__ import annotations
import inspect
from tools.plan_exec import PMVerdict, PMResponse, PlanWorkItem
from tools.validation_gate import WritesPayload
from tools.benchmark.schemas.verdict import PMVerdict as BenchPMVerdict
from tools.benchmark.schemas.writes import WritesPayload as BenchWritesPayload
from tools.benchmark.validators import _SCHEMA_MAP


def test_benchmark_pmverdict_is_same_class():
    assert BenchPMVerdict is PMVerdict


def test_benchmark_writespayload_is_same_class():
    assert BenchWritesPayload is WritesPayload


def test_schema_map_contains_all_expected_keys():
    expected = {'PMVerdict', 'PMResponse', 'PlanWorkItem', 'WritesPayload'}
    assert expected.issubset(set(_SCHEMA_MAP.keys()))


def test_pmverdict_has_required_fields():
    fields = set(PMVerdict.model_fields.keys())
    assert {'status', 'missing', 'notes'}.issubset(fields)


def test_writespayload_has_writes_field():
    fields = set(WritesPayload.model_fields.keys())
    assert 'writes' in fields
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/contracts/test_benchmark_schema_alignment.py -v
```

Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add tests/contracts/test_benchmark_schema_alignment.py
git commit -m "test: add benchmark schema alignment contract tests"
```

---

## Stage 2 — Planner + repair suites, registry, scoring tests

### Task 11: Add planner cases (pm_next stage)

**Files:**

- Create: `tools/benchmark/schemas/plan.py`
- Create: `tools/benchmark/cases/planner.py`

- [ ] **Step 1: Create schema wrapper**

```python
# tools/benchmark/schemas/plan.py
'''Re-exports plan-related models from plan_exec for benchmark use.'''
from tools.plan_exec import PlanWorkItem, PMResponse

__all__ = ['PlanWorkItem', 'PMResponse']
```

- [ ] **Step 2: Create planner cases**

```python
# tools/benchmark/cases/planner.py
'''Benchmark cases for the pm_next stage (alias: pm).

Cases require generating a PMResponse JSON: next work items with
required fields, no overlong notes, deterministic structure.
'''
from __future__ import annotations
from tools.benchmark.result_types import BenchmarkCase
from tools.prompts import SYSTEM_PM_NEXT  # confirmed constant name in tools/prompts.py line 117


def _case(description: str, prompt: str) -> BenchmarkCase:
    return BenchmarkCase(
        suite='planner',
        stage='pm_next',
        alias='pm',
        expected_schema='PMResponse',
        system_prompt=SYSTEM_PM_NEXT,
        description=description,
        prompt=prompt,
    )


CASES: list[BenchmarkCase] = [
    _case(
        description='selects next open item by id',
        prompt=(
            'Open items: [{"id": "P1-001", "phase": "P1", "title": "Add health endpoint", '
            '"status": "open"}]. Select the next work item and return PMResponse JSON.'
        ),
    ),
    _case(
        description='does not invent items not in the list',
        prompt=(
            'Open items: [{"id": "P1-002", "phase": "P1", "title": "Add logging", '
            '"status": "open"}]. Select the next work item and return PMResponse JSON. '
            'Do not select items that are not in the list.'
        ),
    ),
    _case(
        description='keeps required fields present',
        prompt=(
            'Open items: [{"id": "P2-001", "phase": "P2", "title": "Worker restart budget", '
            '"status": "open"}]. Select and return PMResponse JSON with all required fields.'
        ),
    ),
]
```

- [ ] **Step 3: Verify import**

```bash
uv run python -c "from tools.benchmark.cases.planner import CASES; print(len(CASES), 'cases')"
```

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check tools/benchmark/cases/planner.py tools/benchmark/schemas/plan.py --fix
git add tools/benchmark/cases/planner.py tools/benchmark/schemas/plan.py
git commit -m "feat: add planner benchmark cases (pm_next stage)"
```

---

### Task 12: Add repair cases (quick-fix stage)

**Files:**

- Create: `tools/benchmark/cases/repair.py`

- [ ] **Step 1: Create repair cases**

```python
# tools/benchmark/cases/repair.py
'''Benchmark cases for the quick_fix stage (alias: quick-fix).

Cases focus on repairing broken structured output:
fix invalid JSON, wrong enum, missing required field, bad repair.

Uses SYSTEM_JSON_WRITES (tools/prompts.py line 60) — no separate repair prompt
constant exists. The repair instruction is carried in the user prompt.
'''
from __future__ import annotations
from tools.benchmark.result_types import BenchmarkCase
from tools.prompts import SYSTEM_JSON_WRITES


def _case(description: str, prompt: str) -> BenchmarkCase:
    return BenchmarkCase(
        suite='repair',
        stage='quick_fix',
        alias='quick-fix',
        expected_schema='WritesPayload',
        system_prompt=SYSTEM_JSON_WRITES,
        description=description,
        prompt=prompt,
    )


CASES: list[BenchmarkCase] = [
    _case(
        description='repair: fix invalid JSON (unclosed brace)',
        prompt=(
            'The following WritesPayload JSON is malformed. Fix it and return '
            'only the corrected JSON:\n'
            '{"writes": [{"path": "src/foo.py", "content": "x = 1"}\n'
            '(missing closing bracket and brace)'
        ),
    ),
    _case(
        description='repair: fix missing required field (content)',
        prompt=(
            'The following WritesPayload JSON is missing a required field. '
            'Fix it and return only the corrected JSON:\n'
            '{"writes": [{"path": "src/foo.py"}]}'
        ),
    ),
    _case(
        description='repair: do not change unrelated fields',
        prompt=(
            'The following WritesPayload JSON has an invalid path (outside allowed prefix). '
            'Fix only the path to be under src/aetherflow/. '
            'Do not change the content field:\n'
            '{"writes": [{"path": "secret/key.py", "content": "KEY = 123"}]}'
        ),
    ),
]
```

- [ ] **Step 2: Verify import and commit**

```bash
uv run python -c "from tools.benchmark.cases.repair import CASES; print(len(CASES), 'cases')"
uv run ruff check tools/benchmark/cases/repair.py --fix
git add tools/benchmark/cases/repair.py
git commit -m "feat: add repair benchmark cases (quick-fix stage)"
```

---

### Task 13: Add registry

**Files:**

- Create: `tools/benchmark/registry.py`
- Test: `tests/unit/test_benchmark_registry.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_benchmark_registry.py
from tools.benchmark.registry import get_cases, SUITE_NAMES


def test_all_core_suites_present():
    assert set(SUITE_NAMES) >= {'verifier', 'coder', 'planner', 'repair'}


def test_get_cases_returns_list():
    cases = get_cases('verifier')
    assert isinstance(cases, list)
    assert len(cases) > 0


def test_get_cases_unknown_suite_raises():
    import pytest
    with pytest.raises(KeyError):
        get_cases('nonexistent')


def test_all_cases_have_required_fields():
    for suite in SUITE_NAMES:
        for case in get_cases(suite):
            assert case.suite == suite
            assert case.stage
            assert case.alias
            assert case.expected_schema
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/unit/test_benchmark_registry.py -v
```

- [ ] **Step 3: Implement registry.py**

```python
# tools/benchmark/registry.py
'''Central registry mapping suite names to their BenchmarkCase lists.'''
from __future__ import annotations
from tools.benchmark.result_types import BenchmarkCase

from tools.benchmark.cases.verifier import CASES as VERIFIER_CASES
from tools.benchmark.cases.coder import CASES as CODER_CASES
from tools.benchmark.cases.planner import CASES as PLANNER_CASES
from tools.benchmark.cases.repair import CASES as REPAIR_CASES

_REGISTRY: dict[str, list[BenchmarkCase]] = {
    'verifier': VERIFIER_CASES,
    'coder': CODER_CASES,
    'planner': PLANNER_CASES,
    'repair': REPAIR_CASES,
}

SUITE_NAMES: list[str] = list(_REGISTRY.keys())


def get_cases(suite: str) -> list[BenchmarkCase]:
    '''Return the case list for a suite. Raises KeyError for unknown suites.'''
    return _REGISTRY[suite]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_benchmark_registry.py -v
```

- [ ] **Step 5: Update cli.py to use registry**

In `tools/benchmark/cli.py`, replace the manual `suite_map` dict in `_run_suite` with:

```python
from tools.benchmark.registry import get_cases
cases = get_cases(suite_name)
```

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check tools/benchmark/ --fix
git add tools/benchmark/registry.py tools/benchmark/cli.py \
        tests/unit/test_benchmark_registry.py
git commit -m "feat: add benchmark registry + wire into CLI"
```

---

### Task 14: Add case contract tests

**Files:**

- Create: `tests/contracts/test_benchmark_case_contracts.py`

- [ ] **Step 1: Write tests**

```python
# tests/contracts/test_benchmark_case_contracts.py
'''Verifies all benchmark cases have valid stage→alias→schema mappings.

These tests fail if a case is added with an alias not in agent_manifest.json
or a schema name not in validators._SCHEMA_MAP.
'''
from __future__ import annotations
import json
from pathlib import Path

from tools.benchmark.registry import SUITE_NAMES, get_cases
from tools.benchmark.validators import _SCHEMA_MAP

_MANIFEST = json.loads(
    (Path(__file__).resolve().parents[2] / 'agent_manifest.json').read_text()
)
_VALID_ALIASES = set(_MANIFEST.get('required_aliases', [])) | set(
    _MANIFEST.get('optional_aliases', [])
)
_VALID_STAGES = set(_MANIFEST.get('stage_to_alias', {}).keys())


def test_all_case_aliases_in_manifest():
    for suite in SUITE_NAMES:
        for case in get_cases(suite):
            assert case.alias in _VALID_ALIASES, (
                f'{suite}/{case.description}: alias {case.alias!r} '
                f'not in agent_manifest.json required_aliases'
            )


def test_all_case_schemas_in_validator_map():
    for suite in SUITE_NAMES:
        for case in get_cases(suite):
            assert case.expected_schema in _SCHEMA_MAP, (
                f'{suite}/{case.description}: schema {case.expected_schema!r} '
                f'not in validators._SCHEMA_MAP'
            )


def test_all_case_stage_alias_pairs_consistent():
    '''Every case.stage must exist in stage_to_alias and map to case.alias.

    This test intentionally fails rather than silently skipping unknown stages —
    if a stage is missing from agent_manifest.json, the contract is broken.
    '''
    stage_to_alias = _MANIFEST.get('stage_to_alias', {})
    for suite in SUITE_NAMES:
        for case in get_cases(suite):
            assert case.stage in stage_to_alias, (
                f'{suite}/{case.description}: stage {case.stage!r} '
                f'is not in agent_manifest.json stage_to_alias. '
                f'Add it before running the benchmark.'
            )
            expected_alias = stage_to_alias[case.stage]
            assert case.alias == expected_alias, (
                f'{suite}/{case.description}: stage {case.stage!r} '
                f'maps to {expected_alias!r} but case has alias {case.alias!r}'
            )
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/contracts/test_benchmark_case_contracts.py -v
```

Expected: all PASS

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest tests/unit/ tests/contracts/ -q
```

Expected: all PASS, no regressions

- [ ] **Step 4: Commit**

```bash
git add tests/contracts/test_benchmark_case_contracts.py
git commit -m "test: add benchmark case contract tests (alias + schema alignment)"
```

---

## Stage 3 — llama-bench runner + aggregate reports

### Task 15: Add server_process.py

**Files:**

- Create: `tools/benchmark/runtime/server_process.py`

- [ ] **Step 1: Implement server_process.py**

```python
# tools/benchmark/runtime/server_process.py
'''llama-server lifecycle management for benchmark runs.

Starts, polls health, and stops a llama-server process for a given
model alias. Uses the same models.ini and agent_manifest.json config.
'''
from __future__ import annotations

import configparser
import subprocess
import time
from pathlib import Path

import urllib.request
import urllib.error
from loguru import logger

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODELS_INI = _REPO_ROOT / 'tools' / 'models.ini'


class ServerProcess:
    '''Manages a llama-server subprocess for benchmarking.'''

    def __init__(self, alias: str, port: int = 8080) -> None:
        self.alias = alias
        self.port = port
        self._proc: subprocess.Popen | None = None
        cfg = configparser.ConfigParser()
        cfg.read(_MODELS_INI)
        defaults = dict(cfg['*']) if '*' in cfg else {}
        section = dict(cfg[alias]) if alias in cfg else {}
        merged = {**defaults, **section}
        self.model_path = merged.get('model', '')
        self.ctx_size = merged.get('ctx-size', '8192')
        self.n_gpu_layers = merged.get('n-gpu-layers', '99')

    def start(self) -> None:
        '''Start llama-server and wait for it to be ready.'''
        cmd = [
            'llama-server',
            '--model', self.model_path,
            '--ctx-size', str(self.ctx_size),
            '--n-gpu-layers', str(self.n_gpu_layers),
            '--port', str(self.port),
        ]
        logger.info('Starting llama-server: {}', ' '.join(cmd))
        self._proc = subprocess.Popen(cmd)
        self._wait_healthy()

    def _wait_healthy(self, timeout: int = 60) -> None:
        url = f'http://127.0.0.1:{self.port}/health'
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        logger.info('llama-server ready on port {}', self.port)
                        return
            except Exception:
                pass
            time.sleep(1)
        raise TimeoutError(f'llama-server did not become healthy within {timeout}s')

    def stop(self) -> None:
        '''Terminate the server process.'''
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
            logger.info('llama-server stopped')

    def __enter__(self) -> 'ServerProcess':
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from tools.benchmark.runtime.server_process import ServerProcess; print('ok')"
```

- [ ] **Step 3: Lint and commit**

```bash
uv run ruff check tools/benchmark/runtime/server_process.py --fix
git add tools/benchmark/runtime/server_process.py
git commit -m "feat: add llama-server lifecycle manager for benchmarks"
```

---

### Task 16: Add llama_bench_runner

**Files:**

- Create: `tools/benchmark/models.ini`
- Create: `tools/benchmark/runtime/llama_bench_runner.py`

> **Why a separate `tools/benchmark/models.ini`:** `tools/models.ini` uses role aliases
> (`[pm]`, `[architect]`) because `llama-server` is a router that never loads a model into
> VRAM — it exposes whichever models the server was started with. `llama-bench` is different:
> it loads a GGUF file directly and needs a real path. `tools/benchmark/models.ini` maps
> benchmark model names to absolute GGUF paths for this purpose.

- [ ] **Step 1: Create `tools/benchmark/models.ini`**

Populate it with the models you want to benchmark. Use the same model names and paths
from `C:\Users\Dada\AI_Tools\models.ini` for the ones you care about. Example structure:

```ini
; Benchmark model registry — maps model names to GGUF paths for llama-bench.
; Section names are arbitrary identifiers used in --model CLI argument.
; Do NOT use role aliases here — llama-bench loads the file directly.

[Qwen2.5-Coder-14B-Q5_K_M]
model = C:\Users\Dada\AI_Tools\models\qwen2.5-coder-14b-instruct-q5_k_m.gguf

[Qwen2.5-14B-Instruct-Q5_K_M]
model = C:\Users\Dada\AI_Tools\models\Qwen2.5-14B-Instruct-Q5_K_M.gguf
```

Add any other models from `C:\Users\Dada\AI_Tools\models.ini` you want throughput data for.

- [ ] **Step 2: Implement llama_bench_runner.py**

```python
# tools/benchmark/runtime/llama_bench_runner.py
'''Runs llama-bench.exe and stores normalized JSONL throughput rows.

Collects: pp (prompt processing), tg (token generation), pg (prompt+gen),
tokens/sec, batch size, threads, GPU offload, context depth.
Never attempts schema or semantic scoring — throughput only.

Config sources:
- agent_manifest.json        → llama_bench_exe (full path to llama-bench.exe)
- tools/benchmark/models.ini → model name → GGUF path
  (separate from tools/models.ini which uses role aliases for the server router)

DLL note: llama-bench.exe depends on ggml.dll, ggml-cuda.dll, llama.dll etc.
that live alongside the exe. subprocess.run sets cwd to the exe directory so
Windows finds them via the default DLL search path.
'''
from __future__ import annotations

import configparser
import json
import subprocess
import time
import uuid
from pathlib import Path

from loguru import logger

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFEST_PATH = _REPO_ROOT / 'agent_manifest.json'
_BENCH_MODELS_INI = _REPO_ROOT / 'tools' / 'benchmark' / 'models.ini'
_OUTPUT_DIR = _REPO_ROOT / 'logs' / 'benchmark' / 'raw'


def _load_exe_path() -> Path:
    '''Read llama_bench_exe from agent_manifest.json.'''
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding='utf-8'))
    exe = manifest.get('llama_bench_exe', '')
    if not exe:
        raise KeyError(
            'llama_bench_exe not set in agent_manifest.json. '
            'Add: "llama_bench_exe": "C:\\\\...\\\\llama-bench.exe"'
        )
    return Path(exe)


def _load_model_path(model_name: str) -> str:
    '''Look up a GGUF path from tools/benchmark/models.ini by model name.'''
    cfg = configparser.ConfigParser()
    cfg.read(_BENCH_MODELS_INI)
    if model_name not in cfg:
        available = cfg.sections()
        raise KeyError(
            f'Model {model_name!r} not in tools/benchmark/models.ini. '
            f'Available: {available}'
        )
    return cfg[model_name]['model']


def run_llama_bench(model_name: str, threads: int = 4,
                    n_gen: int = 128, n_pp: int = 512) -> dict:
    '''Run llama-bench.exe for a model and return a normalized result row.

    Args:
        model_name: Section name from tools/benchmark/models.ini
                    (e.g. "Qwen2.5-Coder-14B-Q5_K_M")
        threads: CPU threads to use
        n_gen: Tokens to generate per run
        n_pp: Prompt tokens to process per run
    '''
    exe_path = _load_exe_path()
    exe_dir = exe_path.parent  # cwd must be here so Windows finds ggml.dll etc.
    model_path = _load_model_path(model_name)

    cmd = [str(exe_path), '-m', model_path, '-t', str(threads),
           '-n', str(n_gen), '-p', str(n_pp), '-o', 'json']
    logger.info('Running llama-bench: {}', ' '.join(cmd))
    t0 = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=exe_dir)
    elapsed = time.monotonic() - t0

    row: dict = {
        'run_id': str(uuid.uuid4())[:8],
        'model_name': model_name,
        'model_path': model_path,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'elapsed_s': round(elapsed, 2),
        'returncode': result.returncode,
        'raw_stdout': result.stdout,
        'metrics': {},
    }

    if result.returncode == 0:
        try:
            row['metrics'] = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.warning('llama-bench output was not JSON')
    else:
        logger.warning('llama-bench exited {}: {}', result.returncode, result.stderr[:200])

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_tag = time.strftime('%Y-%m-%d')
    jsonl_path = _OUTPUT_DIR / f'llama_bench_{date_tag}.jsonl'
    with jsonl_path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row) + '\n')

    logger.info('llama-bench result saved to {}', jsonl_path)
    return row
```

- [ ] **Step 3: Add CLI command for llama-bench**

In `tools/benchmark/cli.py`, add to the argparse setup:

```python
bench = sub.add_parser('run-llama-bench')
bench.add_argument('--model', required=True,
                   help='Model name from tools/benchmark/models.ini')
bench.add_argument('--threads', type=int, default=4)
```

And add handler:

```python
if args.command == 'run-llama-bench':
    from tools.benchmark.runtime.llama_bench_runner import run_llama_bench
    row = run_llama_bench(args.model, threads=args.threads)
    print(json.dumps(row, indent=2))
    return 0
```

Example usage:

```bash
uv run python -m tools.benchmark.cli run-llama-bench --model Qwen2.5-Coder-14B-Q5_K_M
```

- [ ] **Step 3: Verify import**

```bash
uv run python -c "from tools.benchmark.runtime.llama_bench_runner import run_llama_bench; print('ok')"
```

- [ ] **Step 4: Lint and commit**

```bash
uv run ruff check tools/benchmark/runtime/llama_bench_runner.py tools/benchmark/cli.py --fix
git add tools/benchmark/runtime/llama_bench_runner.py tools/benchmark/cli.py
git commit -m "feat: add llama-bench runner for throughput metrics"
```

---

### Task 17: Run full quality gate

- [ ] **Step 1: Run all benchmark tests**

```bash
uv run pytest tests/unit/test_benchmark_result_types.py \
              tests/unit/test_benchmark_scorers.py \
              tests/unit/test_benchmark_validators.py \
              tests/unit/test_benchmark_registry.py \
              tests/contracts/test_benchmark_case_contracts.py \
              tests/contracts/test_benchmark_schema_alignment.py \
              -v
```

Expected: all PASS

- [ ] **Step 2: Run full lint**

```bash
uv run ruff check tools/benchmark/ tools/benchmark_runner.py --fix
```

- [ ] **Step 3: Run security scan**

```bash
uv run bandit -r tools/benchmark/ -ll
```

- [ ] **Step 4: Run full test suite to check for regressions**

```bash
uv run pytest tests/unit/ tests/contracts/ -q
```

Expected: no new failures

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "chore: stage 3 complete — llama-bench runner + quality gate pass"
```

---

## Stage 4 — Use benchmark results to simplify model routing

### Task 18: Simplify routing in plan_exec using benchmark data

> **Do this task only after running real benchmark results** and reviewing `logs/benchmark/reports/latest.md`.

- [ ] **Step 1: Read the latest report**

```bash
uv run python -m tools.benchmark.cli report
```

- [ ] **Step 2: Update `agent_manifest.json` based on findings**

For each role entry in `stage_to_alias`, update the alias to the model that achieved:

- ≥ 95% Pydantic-valid for verifier
- ≥ 90% for coder
- ≥ 90% for planner
- ≥ 85% for repair

If a model fails thresholds for a stage, replace its alias with a passing model or add a fallback note.

- [ ] **Step 3: Remove retry complexity for reliably-passing models**

In `tools/plan_exec.py`, find the retry loop for any model/stage where benchmark shows ≥ 95% first-pass success. Reduce `max_retries` for those combinations.

- [ ] **Step 4: Run tests to verify nothing regressed**

```bash
uv run pytest tests/unit/ tests/contracts/ -q
```

- [ ] **Step 5: Commit**

```bash
git add agent_manifest.json tools/plan_exec.py
git commit -m "refactor: simplify model routing based on benchmark results"
```

---

## Verification checklist

Before closing this plan:

- [ ] `uv run pytest tests/unit/ tests/contracts/ -q` — all pass
- [ ] `uv run ruff check tools/benchmark/ --fix` — clean
- [ ] `uv run bandit -r tools/benchmark/ -ll` — no HIGH/MEDIUM
- [ ] `uv run python -m tools.benchmark.cli --help` — shows all subcommands
- [ ] `logs/benchmark/reports/latest.md` — exists after a dry run
- [ ] `tests/contracts/test_benchmark_case_contracts.py` — all aliases locked to `agent_manifest.json`
