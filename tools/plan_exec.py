from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from loguru import logger
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from openai import OpenAI
else:
    try:
        from openai import OpenAI
    except ModuleNotFoundError:  # pragma: no cover
        OpenAI = Any  # type: ignore[misc,assignment]

"""
plan_exec.py — Implementation plan executor with deterministic PM selection, schema repair,
and stricter PM verification handling.

This module orchestrates the execution of PLAN.md work items. It interacts with
LLM agents to select the next item, implement it, run build/quality/validation
gates, and verify semantic completeness. Key improvements over the upstream
version include:

* **Schema repair:** malformed writes payloads are detected and repaired
  when unambiguous (e.g. a single write entry at the top level).
* **Deterministic PM selection:** the PM must select a work item by `id`.
  Titles are validated against the selected id and phase to prevent freeform
  renaming.
* **Stricter PM verify:** verdicts are validated against an explicit schema
  with a cheap repair pass that strips unknown keys. Invalid verdicts no
  longer consume full retry attempts.
* **Structured logging:** invalid selection reasons and validation failures
  are classified for easier debugging and potential quarantine.

The code retains the original retry loop structure but uses a `while` loop
instead of a `for` loop so that certain repairs do not consume an attempt.

"""

try:
    # Prefer the local tools package if available
    from tools.json_utils import (
        PM_NEXT_RESPONSE_FORMAT,
        PM_VERIFY_RESPONSE_FORMAT,
        WRITES_RESPONSE_FORMAT,
        safe_json_from_model,
    )
except ModuleNotFoundError:  # pragma: no cover
    from json_utils import (  # type: ignore[no-redef]
        PM_NEXT_RESPONSE_FORMAT,
        PM_VERIFY_RESPONSE_FORMAT,
        WRITES_RESPONSE_FORMAT,
        safe_json_from_model,
    )

try:
    # Import prompts from local tools
    from tools.prompts import IMPL_SYSTEM, SYSTEM_PM_NEXT, SYSTEM_PM_VERIFY
except ModuleNotFoundError:  # pragma: no cover
    from prompts import (  # type: ignore[no-redef]
        IMPL_SYSTEM,
        SYSTEM_PM_NEXT,
        SYSTEM_PM_VERIFY,
    )

try:
    from tools.context_utils import ContextMonitor, count_tokens
except ModuleNotFoundError:  # pragma: no cover
    from context_utils import (  # type: ignore[no-redef]
        ContextMonitor,
        count_tokens,
    )

try:
    from tools.gbnf_grammars import (
        GBNF_PM_NEXT,
        GBNF_PM_VERIFY,
        GBNF_WRITES,
        is_local_backend,
    )
except ModuleNotFoundError:  # pragma: no cover
    from gbnf_grammars import (  # type: ignore[no-redef]
        GBNF_PM_NEXT,
        GBNF_PM_VERIFY,
        GBNF_WRITES,
        is_local_backend,
    )

try:
    from tools.apply_writes import (  # type: ignore
        ALLOWED_ROOT_FILES,
        ALLOWED_WRITE_PREFIXES,
        DENIED_WRITE_PATHS,
        PLACEHOLDER_WRITE_PATHS,
        validate_writes_payload,
    )
except ModuleNotFoundError:  # pragma: no cover
    from apply_writes import (  # type: ignore[no-redef]
        ALLOWED_ROOT_FILES,
        ALLOWED_WRITE_PREFIXES,
        DENIED_WRITE_PATHS,
        PLACEHOLDER_WRITE_PATHS,
        validate_writes_payload,
    )

try:
    from tools.shell_utils import resolve_powershell_executable
except ModuleNotFoundError:  # pragma: no cover
    from shell_utils import resolve_powershell_executable  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Internal helpers for evidence extraction
# ---------------------------------------------------------------------------


def _gather_gate_evidence(report: Any) -> list[str]:
    """Flatten evidence and error messages from a ValidationReport into a list.

    The ValidationReport from tools.validation_gate contains a list of GateResult
    layers. Each layer may record evidence and errors. This helper returns
    a concatenated list of all non-empty evidence and error strings for
    persistence into plan state/history.
    """
    items: list[str] = []
    try:
        for layer in getattr(report, 'layers', []):
            if getattr(layer, 'errors', None):
                items.extend([e for e in layer.errors if e])
            if getattr(layer, 'evidence', None):
                items.extend([e for e in layer.evidence if e])
    except Exception:
        pass
    return items


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / 'state' / 'plan_state.json'

# Configure Loguru to write to a specific logs folder
LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)
logger.add(
    LOG_DIR / 'plan_execution_{time:YYYY-MM-DD}.log', rotation='1 MB', level='DEBUG'
)

# ---------------------------------------------------------------------------
# Schema hints and constants
# ---------------------------------------------------------------------------

_HINT_PREFIXES = ', '.join(sorted(ALLOWED_WRITE_PREFIXES))
_HINT_ROOT = ', '.join(sorted(ALLOWED_ROOT_FILES))
_HINT_DENIED = ', '.join(sorted(DENIED_WRITE_PATHS))
_HINT_PLACEHOLDER = ', '.join(sorted(PLACEHOLDER_WRITE_PATHS))

_SCHEMA_EXAMPLE = """\
REQUIRED JSON SCHEMA - writes payload:
{
  "writes": [
    {
      "path": "src/aetherflow/<module>/<file>.py",
      "content": "<full file content - single-quoted docstrings only>"
    }
  ],
  "notes": "<one-sentence summary>"
}
"""

SCHEMA_HINT_IMPL = (
    _SCHEMA_EXAMPLE
    + f"""\
HARD RULES:
- Allowed prefixes: {_HINT_PREFIXES}
- Allowed root files: {_HINT_ROOT}
- Forbidden paths (hard block): {_HINT_DENIED}
- Forbidden placeholders (hard block): {_HINT_PLACEHOLDER}
- writes[i].path must NEVER be: src/plugins/*, *.cpp, *.h inside src/
- writes[i].content must NEVER contain triple double-quotes
- Use ONLY single-quoted docstrings with meaningful content.
- All function signatures must include type hints
- All public functions must have a Google-style single-quoted docstring
- All paths must be repository-relative (never absolute).
"""
)

# The PM next and verify schemas are declared here for clarity
SCHEMA_PM_NEXT = """{
  "phase": "Phase 0|Phase 1|Phase 2|Phase 3|Phase 4",
  "work_items": [
    {
      "id": "phaseX_slug",
      "title": "short",
      "acceptance": ["testable bullets"],
      "notes": "short"
    }
  ]
}"""

SCHEMA_PM_VERIFY = """{
  "status": "pass|fail",
  "missing": ["..."],
  "notes": "short"
}"""

# ---------------------------------------------------------------------------
# Helper data models
# ---------------------------------------------------------------------------


class AgentManifest(BaseModel):
    """Validated manifest for LLM router connection."""

    base_url: str
    api_key: str
    grammar_capable: bool | None = None


class PlanWorkItem(BaseModel):
    """A single work item parsed from PLAN.md."""

    id: str
    phase: str
    title: str
    status: Literal['done', 'open']
    instructions: str = ''
    role: str = ''


class StateItem(BaseModel):
    """A persisted work item in plan_state.json."""

    id: str
    phase: str
    title: str
    instructions: str = ''
    status: str = 'missing'
    notes: str = ''
    updated_at: str = ''
    missing: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)

    @field_validator('missing', 'evidence', mode='before')
    @classmethod
    def clean_str_list(cls, v: Any) -> list[str]:
        """Strip and filter empty strings from list fields."""
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if str(x).strip()]

    @field_validator('status', mode='before')
    @classmethod
    def default_missing_status(cls, v: Any) -> str:
        """Fall back to missing if status is blank."""
        return str(v).strip() or 'missing'

    @field_validator('updated_at', mode='before')
    @classmethod
    def default_timestamp(cls, v: Any) -> str:
        """Fall back to current time if updated_at is blank."""
        return str(v).strip() or _now_iso()


COMPLETE_STATUSES = {'done', 'verified'}


def is_complete_status(status: Any) -> bool:
    """Return whether a persisted status counts as complete for progression."""
    return str(status).strip() in COMPLETE_STATUSES


class PMWorkItem(BaseModel):
    """A single work item returned by the PM agent."""

    id: str
    title: str
    acceptance: list[str]
    notes: str


class PMResponse(BaseModel):
    """Full response from the PM next-item selector."""

    phase: str
    work_items: list[PMWorkItem]


class ModelCall(BaseModel):
    """Immutable result from a single LLM call."""

    model_config = {'frozen': True}
    requested_model: str
    actual_model: str
    content: str


class PMVerdict(BaseModel):
    """Verification result returned by the PM verify agent."""

    status: Literal['pass', 'fail']
    missing: list[str]
    notes: str

    @field_validator('missing', mode='before')
    @classmethod
    def clean_missing(cls, v: Any) -> list[str]:
        """Strip and filter empty strings from missing list."""
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if str(x).strip()]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


def resolve_role_alias(manifest: dict[str, Any], role: str) -> str:
    """Resolve a PLAN role to a runtime alias using the manifest."""
    role_to_alias = manifest.get('role_to_alias', {})
    alias = role_to_alias.get(role, '').strip()
    if not alias:
        msg = f'No alias mapping for role {role!r}'
        raise KeyError(msg)
    return alias


def resolve_role_context(manifest: dict[str, Any], role: str) -> str:
    """Resolve a PLAN role to its contextual persona string."""
    role_to_context = manifest.get('role_to_context', {})
    ctx = str(role_to_context.get(role, '')).strip()
    if not ctx:
        msg = f'No role_to_context entry for role {role!r}'
        raise KeyError(msg)
    return ctx


def build_role_scoped_impl_system(
    *,
    manifest: dict[str, Any],
    role: str,
    base_system: str,
) -> str:
    """Prepend role-specific context before the base implementation system prompt."""
    ctx = resolve_role_context(manifest, role)
    return f'{ctx}\n\n{base_system}'


def _slug(value: str) -> str:
    token = re.sub(r'[^a-z0-9]+', '_', value.lower()).strip('_')
    return token or 'item'


_WORK_ITEM_TOKEN_RE = re.compile(
    r'`?(?P<token>AF-\d{2}-\d{2}[a-z]?)`?',
    re.IGNORECASE,
)


def extract_work_item_token(title: str) -> str | None:
    """Extract a stable work-item token from a PLAN title.

    Args:
        title: Raw checklist title text from ``docs/PLAN.md``.

    Returns:
        The normalized token when present, otherwise ``None``.
    """
    match = _WORK_ITEM_TOKEN_RE.search(title)
    if not match:
        return None
    return match.group('token').upper()


def work_item_id(phase: str, title: str) -> str:
    """Build a persistent work-item id.

    Args:
        phase: Phase header associated with the work item.
        title: Raw checklist title text from ``docs/PLAN.md``.

    Returns:
        A stable slug derived from the explicit task token when available.
        Falls back to the legacy phase-and-title slug for titles that do not
        declare a token.
    """
    token = extract_work_item_token(title)
    if token is not None:
        return _slug(token)
    return f'{_slug(phase)}__{_slug(title)}'


def phase_number(phase: str) -> int:
    match = re.search(r'phase\s+(\d+)', phase, re.IGNORECASE)
    if not match:
        return 999
    return int(match.group(1))


def infer_agent_from_instructions(instructions: str, title: str) -> str:
    """Derive agent from Target file path in PLAN.md instructions."""
    match = re.search(r'\*\*Target Files?:\*\*\s*`([^`]+)`', instructions)
    if match:
        path = match.group(1).lower()
        if '/ui/' in path or '/panels/' in path:
            return 'ui-ux'
        return 'architect'
    # Fallback: ui-ux for unambiguous UI titles
    return (
        'ui-ux'
        if re.search(r'\bui\b|\bpanel\b|\bdashboard\b', title.lower())
        else 'architect'
    )


_PHASE_HEADER_RE = re.compile(
    r'^\s*##\s+(?P<phase>Phase\s+\d+)\s+[\u2014\-\u2013]\s+(?P<title>.+?)\s*$',
    re.IGNORECASE,
)
_ITEM_RE = re.compile(r'^\s*-\s*\[(?P<mark>[ xX])\]\s+(?P<title>.+?)\s*$')


def extract_phase_work_items(plan_text: str) -> list[PlanWorkItem]:
    """Parse PLAN.md into structured work items via a line-by-line state machine."""
    items: list[PlanWorkItem] = []
    current_phase: str = ''
    current_item: PlanWorkItem | None = None
    instruction_lines: list[str] = []
    current_role: str = ''

    def _flush_item() -> None:
        nonlocal current_item
        if current_item is not None:
            items.append(
                current_item.model_copy(
                    update={
                        'instructions': '\n'.join(instruction_lines).strip(),
                        'role': current_role,
                    }
                )
            )

    for raw_line in plan_text.splitlines():
        phase_m = _PHASE_HEADER_RE.match(raw_line)
        if phase_m:
            _flush_item()
            current_item = None
            instruction_lines = []
            current_role = ''
            current_phase = phase_m.group('phase').strip()
            continue
        if not current_phase:
            continue
        item_m = _ITEM_RE.match(raw_line)
        if item_m:
            _flush_item()
            instruction_lines = []
            current_role = ''
            mark = item_m.group('mark').strip().lower()
            title = item_m.group('title').strip()
            current_item = PlanWorkItem(
                id=work_item_id(current_phase, title),
                phase=current_phase,
                title=title,
                status='done' if mark == 'x' else 'open',
            )
            continue

        stripped = raw_line.strip()
        if current_item is not None and stripped.startswith('>'):
            body = stripped.lstrip('>').strip()
            if body.startswith('**Role:**'):
                parts = body.split('`')
                if len(parts) >= 2:
                    current_role = parts[1].strip()
            instruction_lines.append(body)
    _flush_item()
    return items


def save_plan_state(state: dict[str, Any]) -> None:
    """Persist the plan execution state to disk."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state['updated_at'] = _now_iso()
    STATE_PATH.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')


def load_or_initialize_plan_state(plan_items: list[PlanWorkItem]) -> dict[str, Any]:
    """Load an existing plan_state.json or initialise from PLAN.md items."""
    existing: dict[str, Any] = {}
    if STATE_PATH.exists():
        try:
            existing = json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            existing = {}

    existing_items: dict[str, dict[str, Any]] = {}
    raw_items = existing.get('items', [])
    if isinstance(raw_items, list):
        for entry in raw_items:
            if not isinstance(entry, dict):
                continue
            try:
                item = StateItem.model_validate(entry)
                if item.id:
                    payload = item.model_dump()
                    existing_items[item.id] = payload
                    alias_id = work_item_id(item.phase, item.title)
                    existing_items.setdefault(alias_id, payload)
            except Exception:
                continue

    merged_items: list[dict[str, Any]] = []
    for plan_item in plan_items:
        key = plan_item.id
        base = {
            'id': key,
            'phase': plan_item.phase,
            'title': plan_item.title,
            'instructions': plan_item.instructions,
            'status': 'missing',
            'notes': '',
            'updated_at': _now_iso(),
            'missing': [],
            'evidence': [],
        }
        if key in existing_items:
            persisted = existing_items[key]
            base.update(persisted)
            base['id'] = key
            base['phase'] = plan_item.phase
            base['title'] = plan_item.title
            base['instructions'] = plan_item.instructions
        merged_items.append(base)

    history = existing.get('history', [])
    if not isinstance(history, list):
        history = []

    if history:
        latest_by_id: dict[str, dict[str, Any]] = {}
        for event in history:
            if not isinstance(event, dict):
                continue
            event_id = str(event.get('id', '')).strip()
            phase = str(event.get('phase', '')).strip()
            title = str(event.get('title', '')).strip()
            status = str(event.get('status', '')).strip()
            if not status:
                continue
            if event_id:
                item_key = event_id
            elif phase and title:
                item_key = work_item_id(phase, title)
            else:
                continue
            latest_by_id[item_key] = event

        for item in merged_items:
            item_id = str(item.get('id', ''))
            replay = latest_by_id.get(item_id)
            if not replay:
                continue
            replay_status = str(replay.get('status', '')).strip()
            if replay_status:
                item['status'] = replay_status
            replay_notes = str(replay.get('notes', '')).strip()
            if replay_notes:
                item['notes'] = replay_notes
            replay_missing = replay.get('missing', [])
            if isinstance(replay_missing, list):
                item['missing'] = [str(x) for x in replay_missing if str(x).strip()]
            replay_files = replay.get('changed_files', [])
            if isinstance(replay_files, list):
                item['evidence'] = [str(x) for x in replay_files if str(x).strip()]

    state = {
        'version': 1,
        'updated_at': _now_iso(),
        'items': merged_items,
        'history': history,
    }
    save_plan_state(state)
    return state


def next_open_work_items(state: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Return the earliest phase with open items and all open items in that phase."""
    items = state.get('items', [])
    if not isinstance(items, list):
        return '', []

    open_items = [
        item
        for item in items
        if isinstance(item, dict) and not is_complete_status(item.get('status'))
    ]
    if not open_items:
        return '', []

    phases = [
        str(item.get('phase') or '').strip()
        for item in open_items
        if isinstance(item, dict)
    ]
    phases = [p for p in phases if p]
    if not phases:
        return '', []

    phase = min(phases, key=phase_number)

    phase_items = [
        item
        for item in items
        if isinstance(item, dict)
        and str(item.get('phase') or '').strip() == phase
        and not is_complete_status(item.get('status'))
    ]
    return phase, phase_items


def update_state_item(
    state: dict[str, Any],
    item_id: str,
    *,
    status: str,
    notes: str = '',
    missing: list[str] | None = None,
    evidence: list[str] | None = None,
) -> None:
    """Update a single persisted state item with new status/notes/missing/evidence."""
    items = state.get('items', [])
    if not isinstance(items, list):
        return
    target: dict[str, Any] | None = None
    for item in items:
        if isinstance(item, dict) and item.get('id') == item_id:
            target = item
            break
    if target is None:
        return

    target['status'] = status
    target['updated_at'] = _now_iso()
    if notes:
        target['notes'] = notes
    if missing is not None:
        target['missing'] = missing
    if evidence is not None:
        target['evidence'] = evidence


def append_history(
    state: dict[str, Any],
    *,
    item_id: str,
    phase: str,
    title: str,
    status: str,
    changed_files: list[str],
    missing: list[str] | None = None,
    notes: str = '',
) -> None:
    """Append a history event for a completed or partial work item."""
    history = state.get('history')
    if not isinstance(history, list):
        history = []
        state['history'] = history
    payload = {
        'timestamp': _now_iso(),
        'id': item_id,
        'phase': phase,
        'title': title,
        'status': status,
        'changed_files': changed_files,
        'missing': missing or [],
        'notes': notes,
    }
    history.append(payload)


def run_ps(path: str, args: list[str] | None = None) -> tuple[int, str]:
    """Run a PowerShell script under .cursor/workflows and return (rc, combined output)."""
    cmd = [
        resolve_powershell_executable(),
        '-ExecutionPolicy',
        'Bypass',
        '-File',
        str(ROOT / path),
    ]
    if args:
        cmd.extend(args)
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or '') + (proc.stderr or '')
    return proc.returncode, out


def apply_writes_relpaths(payload: dict[str, Any]) -> list[str]:
    """Apply writes to disk and return relative paths of changed files."""
    try:
        from tools.apply_writes import apply_writes as _apply  # local import
    except ModuleNotFoundError:  # pragma: no cover
        from apply_writes import apply_writes as _apply  # type: ignore[no-redef]
    changed = _apply(ROOT, payload)
    return [str(p.relative_to(ROOT)) for p in changed]


def is_grammar_capable(manifest: AgentManifest) -> bool:
    """Resolve grammar capability from explicit manifest config or URL heuristic."""
    if manifest.grammar_capable is not None:
        return manifest.grammar_capable
    return is_local_backend(manifest.base_url)


def _build_messages(system: str, user: str) -> list[dict[str, str]]:
    """Build the chat message list for a model call.

    Args:
        system: System prompt content.
        user: User prompt content.

    Returns:
        OpenAI-compatible chat messages.
    """
    return [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': user.rstrip()},
    ]


def _build_extra_body(
    *,
    model: str,
    use_local_backend: bool,
    grammar: str | None = None,
) -> dict[str, Any]:
    """Build backend-specific request fields for local llama.cpp calls.

    Args:
        model: Runtime alias requested from the router.
        use_local_backend: Whether llama.cpp-specific fields are safe to send.
        grammar: Optional GBNF grammar for token-level enforcement.

    Returns:
        Extra request fields for the chat completions call.
    """
    extra_body: dict[str, Any] = {}
    if grammar is not None:
        extra_body['grammar'] = grammar
    if use_local_backend and model == 'pm':
        extra_body['reasoning_format'] = 'deepseek'
    return extra_body


def call(
    client: OpenAI,
    model: str,
    system: str,
    user: str,
    temperature: float | None = None,
    grammar_capable: bool = False,
    response_format: Any = None,
    grammar: str | None = None,
) -> ModelCall:
    """Invoke an LLM and return the raw model response."""
    use_local_overrides = grammar_capable
    kwargs: dict[str, Any] = {
        'model': model,
        'temperature': temperature,
        'messages': _build_messages(system, user),
    }
    extra_body = _build_extra_body(
        model=model,
        use_local_backend=use_local_overrides,
        grammar=grammar if grammar and grammar_capable else None,
    )
    if extra_body:
        kwargs['extra_body'] = extra_body
    if grammar and grammar_capable:
        pass
    elif response_format is not None:
        kwargs['response_format'] = response_format
    resp = client.chat.completions.create(**kwargs)
    content = (resp.choices[0].message.content or '').strip()
    return ModelCall(
        requested_model=model,
        actual_model=(resp.model or '<unknown>'),
        content=content,
    )


def _write_failed_response(stage: str, kind: str, raw_text: str) -> Path:
    """Persist a failed LLM response for later analysis and return its path."""
    logs_dir = ROOT / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    target = logs_dir / f'plan_exec_{stage}_{kind}_{stamp}.txt'
    target.write_text(raw_text, encoding='utf-8')
    return target


def call_json_with_retry(
    client: OpenAI,
    stage: str,
    model: str,
    system: str,
    user: str,
    schema_hint: str,
    temperature: float | None = None,
    grammar_capable: bool = False,
    response_format: dict | None = None,
    grammar: str | None = None,
) -> dict[str, Any]:
    """Invoke an LLM expecting a JSON response.

    When *grammar* is provided and the backend is local, GBNF token-level
    enforcement is used instead of ``response_format``.  If the first
    response fails to parse, a repair prompt is sent.  Raises ValueError
    if both attempts fail.
    """

    debug_dir = ROOT / 'logs'
    debug_dir.mkdir(exist_ok=True)
    safe_stage = stage.replace('/', '_').replace('\\', '_')
    (debug_dir / f'prompt_system_{safe_stage}.txt').write_text(system, encoding='utf-8')
    (debug_dir / f'prompt_user_{safe_stage}.txt').write_text(user, encoding='utf-8')

    initial = call(
        client,
        model,
        system,
        user,
        temperature=temperature,
        grammar_capable=grammar_capable,
        response_format=response_format,
        grammar=grammar,
    )
    logger.debug(
        f'[llm] stage={stage} requested_alias={initial.requested_model} '
        f'actual_model={initial.actual_model} chars={len(initial.content)}'
    )
    if initial.requested_model != initial.actual_model:
        logger.debug(
            f'[llm] stage={stage} alias_resolved '
            f'requested_alias={initial.requested_model} '
            f'actual_model={initial.actual_model}'
        )
    try:
        return safe_json_from_model(stage, initial.content)
    except ValueError:
        first_dump = _write_failed_response(stage, 'first', initial.content)

    repair_user = (
        'Your previous response was invalid for this task.\n'
        'Return ONLY valid JSON with no markdown fences and no prose.\n\n'
        f'Required schema:\n{schema_hint}\n\n'
        'Previous response:\n'
        f'{initial.content}'
    )
    (debug_dir / f'prompt_repair_user_{safe_stage}.txt').write_text(
        repair_user, encoding='utf-8'
    )
    repaired = call(
        client,
        model,
        system,
        repair_user,
        temperature=None,
        grammar_capable=grammar_capable,
        response_format=response_format,
        grammar=grammar,
    )
    logger.debug(
        f'[llm] stage={stage} retry=1 requested_alias={repaired.requested_model} '
        f'actual_model={repaired.actual_model} chars={len(repaired.content)}'
    )
    if repaired.requested_model != repaired.actual_model:
        logger.debug(
            f'[llm] stage={stage} retry=1 alias_resolved=true '
            f'requested_alias={repaired.requested_model} '
            f'actual_model={repaired.actual_model}'
        )
    try:
        return safe_json_from_model(stage, repaired.content)
    except ValueError as exc:
        second_dump = _write_failed_response(stage, 'retry', repaired.content)
        raise ValueError(
            f"Stage '{stage}' returned invalid JSON twice. "
            f"Saved raw responses to '{first_dump}' and '{second_dump}'."
        ) from exc


def _clip(text: str, max_chars: int) -> str:
    """Clip a text to at most max_chars, preserving context around beginning and end."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 500] + '\n...\n' + text[-500:]


def _title_keywords(title: str) -> set[str]:
    stop_words = {'add', 'and', 'deliver', 'implement', 'the', 'with'}
    words = re.findall(r'[a-z0-9]+', title.lower())
    return {word for word in words if len(word) >= 3 and word not in stop_words}


def filter_acceptance_criteria(title: str, acceptance: list[Any]) -> list[str]:
    """Filter acceptance criteria to only those relevant to the title keywords."""
    criteria = [
        item.strip() for item in acceptance if isinstance(item, str) and item.strip()
    ]
    if not criteria:
        return [f'Complete PLAN work item: {title}']
    keywords = _title_keywords(title)
    if not keywords:
        return criteria
    filtered: list[str] = []
    for criterion in criteria:
        text = criterion.lower()
        if any(keyword in text for keyword in keywords):
            filtered.append(criterion)
    if filtered:
        return filtered
    # Fall back to a single scoped criterion rather than phase-wide KPIs.
    return [f'Complete PLAN work item: {title}']


def quality_scope_args(changed_files: list[str]) -> list[str]:
    """Prepare arguments for the quality checker script based on changed files."""
    unique_paths = [p for p in dict.fromkeys(changed_files) if p.strip()]
    if not unique_paths:
        return []
    return ['-Paths', *unique_paths]


def extract_plan_phase_summary(plan: str, max_chars: int = 12000) -> str:
    """Shrink PLAN.md while preserving only Phase sections and their tasks."""
    keep: list[str] = []
    for line in plan.splitlines():
        # Phase headers
        if re.match(r'^\s*## Phase', line, re.I):
            keep.append(line)
            continue
        # Exit Criteria header
        if re.match(r'^\s*Exit Criteria', line, re.I):
            keep.append(line)
            continue
        # Task items (-) or instructions (>)
        if re.match(r'^\s*[-\>]', line):
            keep.append(line)
    result_text = '\n'.join(keep)
    return result_text[:max_chars]


def extract_prd_hard_requirements(prd: str, max_chars: int = 12000) -> str:
    """Extract high-signal PRD sections using regex to survive formatting shifts."""
    keep: list[str] = []
    capture = False
    targets = {'architectural', 'plugin system', 'capture system'}
    for line in prd.splitlines():
        header_match = re.match(r'^\s*##\s+(.*)$', line)
        if header_match:
            header_content = header_match.group(1).lower()
            capture = any(t in header_content for t in targets)
        if capture:
            keep.append(line)
    # Fallback to whole doc if no specific sections were caught
    result_text = '\n'.join(keep) if keep else prd
    return result_text[:max_chars]


# ---------------------------------------------------------------------------
# Implementation payload repair helpers
# ---------------------------------------------------------------------------


def coerce_impl_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """
    Attempt to repair a malformed implementation payload.

    Only unambiguous repairs are allowed. If the payload is already valid or
    cannot be safely repaired the original payload is returned with changed=False.
    Repairs include:
      * Wrapping a top-level dict containing 'path' and 'content' as a single write.
      * Renaming a top-level 'write' key to 'writes'.
      * Converting a dict in 'writes' to a single-item list.
      * Adding a missing 'notes' field as an empty string.
    """
    if not isinstance(payload, dict):
        return payload, False
    changed = False
    new_payload = dict(payload)

    # If 'writes' is missing, try to infer a single write from top-level keys.
    if 'writes' not in new_payload:
        if 'path' in new_payload and 'content' in new_payload:
            # Wrap the single write entry
            new_payload = {
                'writes': [
                    {'path': new_payload['path'], 'content': new_payload['content']}
                ],
                'notes': new_payload.get('notes', ''),
            }
            changed = True
        elif 'write' in new_payload:
            write_obj = new_payload.pop('write')
            if isinstance(write_obj, list):
                new_payload['writes'] = write_obj
            elif isinstance(write_obj, dict):
                new_payload['writes'] = [write_obj]
            changed = True
    else:
        # If writes is a dict rather than list, wrap it.
        if isinstance(new_payload['writes'], dict):
            new_payload['writes'] = [new_payload['writes']]
            changed = True

    # Always ensure notes field exists.
    if 'notes' not in new_payload:
        new_payload['notes'] = ''
        changed = True

    return new_payload, changed


def classify_validate_error(exc: Exception) -> str:
    """Classify a validation error into schema or path failure categories."""
    msg = str(exc).lower()
    if 'path' in msg or 'prefix' in msg or 'root' in msg or 'forbidden' in msg:
        return 'writes_path_fail'
    return 'writes_schema_fail'


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Execute the implementation plan iteratively."""
    ap = argparse.ArgumentParser(prog='tools.plan_exec')
    ap.add_argument('--max-doc-chars', type=int, default=32000)
    ap.add_argument('--state-only', action='store_true')
    ap.add_argument('--plan', default='docs/PLAN.md')
    ap.add_argument('--prd', default='docs/PRD.md')
    ap.add_argument('--manifest', default='agent_manifest.json')
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    # Load manifest and initialise API client
    manifest_data: dict[str, Any] = json.loads(
        (ROOT / args.manifest).read_text(encoding='utf-8')
    )
    manifest = AgentManifest.model_validate(manifest_data)
    grammar_capable = is_grammar_capable(manifest)
    _ctx_monitor = ContextMonitor()
    client = OpenAI(base_url=manifest.base_url, api_key=manifest.api_key, timeout=300)

    # Read source documents
    plan = (ROOT / args.plan).read_text(encoding='utf-8', errors='ignore')
    prd = (
        (ROOT / args.prd).read_text(encoding='utf-8', errors='ignore')
        if (ROOT / args.prd).exists()
        else ''
    )
    max_doc_chars = args.max_doc_chars

    plan_summary = extract_plan_phase_summary(plan, max_doc_chars)
    prd_summary = extract_prd_hard_requirements(prd, max_doc_chars)

    plan_items = extract_phase_work_items(plan)
    plan_items_by_id: dict[str, PlanWorkItem] = {item.id: item for item in plan_items}
    state = load_or_initialize_plan_state(plan_items)
    selected_phase, open_items = next_open_work_items(state)

    if args.state_only:
        return 0

    # Map IDs to instructions and build allowed selection lines
    open_items_by_id: dict[str, dict[str, Any]] = {}
    for item in open_items:
        iid = item.get('id')
        if not iid:
            continue
        open_items_by_id[iid] = item

    # Build a human-readable list of allowed items for the PM
    allowed_lines: list[str] = []
    for item_id, item in open_items_by_id.items():
        title = item.get('title', '')
        instructions = str(item.get('instructions', '')).strip()
        if instructions:
            allowed_lines.append(
                f'- id: {item_id}\n  title: {title}\n  Requirements: {instructions}'
            )
        else:
            allowed_lines.append(f'- id: {item_id}\n  title: {title}')
    allowed_text = '\n'.join(allowed_lines)

    # Log progress
    done_items = [
        i for i in state.get('items', []) if is_complete_status(i.get('status'))
    ]
    done_count = len(done_items)
    total_count = len(state.get('items', []))
    logger.info(
        f'[state] phase={selected_phase} open={len(open_items)} '
        f'completed={done_count}/{total_count}'
    )

    # Construct the PM selection prompt
    pm_prompt = (
        'You are executing the Implementation Plan strictly in order.\n\n'
        'Deterministic execution state:\n'
        f'- Earliest incomplete phase: {selected_phase}\n'
        '- Allowed unfinished work items (choose one id):\n'
        f'{allowed_text}\n\n'
        'Rules:\n'
        "1. You MUST select one work item by its 'id' from the list above.\n"
        f"2. Phase MUST be exactly '{selected_phase}'.\n"
        "3. The 'title' you return must match the selected id.\n"
        "4. Use the 'Requirements' listed under your chosen id to define the scope.\n"
        '5. Attach concrete acceptance criteria based on those specific Requirements.\n\n'
        'Return JSON only.\n\n'
        'PRD excerpt (hard requirements):\n'
        f'{prd_summary}\n\n'
        'PLAN excerpt (phases + bullets + exit criteria):\n'
        f'{plan_summary}\n'
    )

    stage_to_alias = manifest_data.get('stage_to_alias', {})
    pm_alias = stage_to_alias.get('pm_next', 'pm')
    try:
        queue = call_json_with_retry(
            client=client,
            stage='pm_next',
            model=pm_alias,
            system=SYSTEM_PM_NEXT,
            user=pm_prompt,
            schema_hint=SCHEMA_PM_NEXT,
            temperature=None,
            grammar_capable=grammar_capable,
            response_format=PM_NEXT_RESPONSE_FORMAT,
            grammar=GBNF_PM_NEXT,
        )
    except ValueError as exc:
        logger.error(f'PM next selection failed to return valid JSON: {exc}')
        queue = {}

    chosen_item: PMWorkItem | None = None
    queued_phase = ''
    try:
        pm_response = PMResponse.model_validate(queue)
        if len(pm_response.work_items) != 1:
            raise ValueError('pm_next must return exactly one work item')
        queued_phase = pm_response.phase.strip()
        chosen_item = pm_response.work_items[0]
    except Exception as exc:
        logger.warning(f'[pm_next] invalid_pm_response={exc}')
        chosen_item = None
        queued_phase = ''

    # Fallback: first open item
    fallback_choice = next(iter(open_items), None)
    if fallback_choice is None:
        logger.error('No open items available.')
        return 1

    # Initialise defaults for selected work item
    # Cast the fallback id to string to satisfy static type checking
    selected_id: str = str(fallback_choice.get('id') or '')
    selected_title = fallback_choice.get('title', '').strip()
    raw_acceptance: list[Any] = []
    invalid_reason = ''

    if not chosen_item:
        invalid_reason = 'missing_work_item'
    else:
        # Validate ID first
        if chosen_item.id not in open_items_by_id:
            invalid_reason = 'unknown_id'
        else:
            expected = open_items_by_id[chosen_item.id]
            if queued_phase != selected_phase.strip():
                invalid_reason = 'phase_mismatch'
            elif chosen_item.title.strip() != str(expected.get('title', '')).strip():
                invalid_reason = 'title_mismatch'
            else:
                selected_id = chosen_item.id
                selected_title = expected.get('title', '')
                raw_acceptance = chosen_item.acceptance

    if invalid_reason:
        logger.warning(f'[pm_next] invalid_selection={invalid_reason} fallback=true')
        raw_acceptance = [f'Complete PLAN work item: {selected_title}']

    # Fetch requirements for the final selected title
    selected_requirements = (
        str(
            open_items_by_id.get(selected_id, {}).get(
                'instructions', 'No specific requirements provided in PLAN.md.'
            )
        ).strip()
        or 'No specific requirements provided in PLAN.md.'
    )

    # Log selected task for human visibility
    logger.info('=' * 40)
    logger.info(f'TARGET TASK: {selected_title}')
    logger.info(f'PLAN SPECS: {selected_requirements}')
    logger.info('=' * 40)

    # Determine acceptance criteria and update state to in_progress
    acceptance = filter_acceptance_criteria(selected_title, raw_acceptance)
    update_state_item(
        state,
        str(selected_id),
        status='in_progress',
        notes='Execution started',
    )
    save_plan_state(state)

    # Resolve implementation role and alias
    plan_item = plan_items_by_id.get(selected_id)
    if plan_item is None or not plan_item.role:
        logger.error(f'No role found for selected work item id={selected_id!r}')
        return 1
    selected_role = plan_item.role
    try:
        impl_alias = resolve_role_alias(manifest_data, selected_role)
    except KeyError as exc:
        logger.error(f'Unable to resolve alias for role {selected_role!r}: {exc}')
        return 1

    impl_system = build_role_scoped_impl_system(
        manifest=manifest_data,
        role=selected_role,
        base_system=IMPL_SYSTEM,
    )

    # Implementation retry loop state
    max_retries: int = 3
    schema_repair_used: bool = False
    fix_prompt: str = ''
    verify_retry_notes: str = ''
    changed: list[str] = []
    skip_impl: bool = False
    gate_report = None
    parsed_verdict = PMVerdict.model_validate(
        {'status': 'fail', 'missing': [], 'notes': ''}
    )

    attempt = 0
    while attempt < max_retries:
        logger.info(f'--- Implementation attempt {attempt + 1}/{max_retries} ---')
        if skip_impl:
            logger.info('Physical gate passed - skipping impl, retrying PM verify only')
        else:
            impl_prompt = (
                'Implement this PLAN work item ONLY.\n\n'
                f'ID: {selected_id}\n'
                f'Title: {selected_title}\n\n'
                f'Plan Requirements: {selected_requirements}\n\n'
                'Acceptance criteria:\n'
                f'{json.dumps(acceptance, indent=2)}\n\n'
                'PRD excerpt (hard requirements):\n'
                f'{prd_summary}\n\n'
                'Constraints:\n'
                '- Do not implement other PLAN items yet.\n'
                '- Only touch files necessary for this work item.\n'
                '- Minimal diffs.\n'
                '- Write real, working logic only.\n'
                '- No placeholder code.\n'
            )
            if fix_prompt:
                impl_prompt += f'\nPREVIOUS ATTEMPT FAILED. FIX ISSUES:\n{fix_prompt}\n'

            model_alias = impl_alias
            if not _ctx_monitor.track_usage(
                model_alias,
                count_tokens(impl_prompt),
                16384,
            ):
                logger.warning(
                    f'[context] prompt near limit for {model_alias} - truncating'
                )
                # Clip PRD/PLAN summaries when near context window limit
                prd_summary = _clip(prd_summary, 4000)
                plan_summary = _clip(plan_summary, 4000)

            try:
                impl_payload = call_json_with_retry(
                    client=client,
                    stage=f'impl_{selected_role}',
                    model=model_alias,
                    system=impl_system,
                    user=impl_prompt,
                    schema_hint=SCHEMA_HINT_IMPL,
                    temperature=None,
                    grammar_capable=grammar_capable,
                    response_format=WRITES_RESPONSE_FORMAT,
                    grammar=GBNF_WRITES,
                )
            except ValueError as exc:
                # JSON parse failure is fatal; mark blocked
                logger.error(f'Implementation JSON parse failure: {exc}')
                update_state_item(
                    state,
                    str(selected_id),
                    status='blocked',
                    notes=f'impl_json_parse: {exc}',
                    missing=['json_parse_fail'],
                    evidence=changed,
                )
                save_plan_state(state)
                return 1

            # Attempt to repair schema issues once before consuming an attempt
            try:
                validate_writes_payload(impl_payload)
            except ValueError as exc:
                # If first time encountering a schema failure, try auto-repair
                failure_kind = classify_validate_error(exc)
                if not schema_repair_used:
                    repaired_payload, changed_flag = coerce_impl_payload(impl_payload)
                    if changed_flag:
                        schema_repair_used = True
                        try:
                            validate_writes_payload(repaired_payload)
                            impl_payload = repaired_payload
                        except ValueError:
                            # Repair unsuccessful, treat as schema failure
                            pass
                # After repair attempt, re-validate
                try:
                    validate_writes_payload(impl_payload)
                except ValueError as exc2:
                    failure_kind = classify_validate_error(exc2)
                    if attempt < max_retries - 1:
                        logger.warning(
                            f'Attempt {attempt + 1}: Invalid writes payload ({failure_kind}): {exc2}'
                        )
                        if failure_kind == 'writes_schema_fail':
                            fix_prompt = (
                                'Your JSON writes payload was rejected by schema validation.\n'
                                'Return a JSON object with exactly two top-level keys:\n'
                                '- "writes": array of {{"path": "...", "content": "..."}} entries\n'
                                '- "notes": REQUIRED string summarising the changes\n'
                                f'Error: {exc2}\n'
                                'Return corrected JSON writes only.'
                            )
                        else:
                            fix_prompt = (
                                'Your JSON writes payload contained invalid paths or forbidden locations.\n'
                                'Rules:\n'
                                f'- Allowed prefixes: {_HINT_PREFIXES}\n'
                                f'- Allowed root files: {_HINT_ROOT}\n'
                                f'- Forbidden paths: {_HINT_DENIED}\n'
                                f'- Forbidden placeholders: {_HINT_PLACEHOLDER}\n'
                                '- Use ONLY single-quoted docstrings with meaningful content.\n'
                                '- Do NOT write to src/plugins/*.\n'
                                f'Error: {exc2}\n'
                                'Return corrected JSON writes only.'
                            )
                        attempt += 1
                        continue
                    else:
                        logger.error(
                            f'Task Blocked: Invalid writes payload on final attempt ({failure_kind}).'
                        )
                        update_state_item(
                            state,
                            str(selected_id),
                            status='blocked',
                            notes=str(exc2),
                            missing=[failure_kind],
                            evidence=changed,
                        )
                        save_plan_state(state)
                        return 1

            # Apply writes and format changed files
            changed = apply_writes_relpaths(impl_payload)
            if changed:
                subprocess.run(
                    ['uv', 'run', 'ruff', 'format', *changed],
                    cwd=ROOT,
                    capture_output=True,
                )
            # Hard gate: ensure we wrote at least one file
            if not changed:
                no_write_msg = (
                    'Implementation returned no file writes. '
                    'Return real code, not stubs or comments.'
                )
                if attempt < max_retries - 1:
                    logger.warning(f'Attempt {attempt + 1}: {no_write_msg}')
                    fix_prompt = no_write_msg
                    attempt += 1
                    continue
                else:
                    logger.error('Task Blocked: No files written on final attempt.')
                    update_state_item(
                        state,
                        str(selected_id),
                        status='blocked',
                        notes=no_write_msg,
                        missing=['No files written'],
                        evidence=[],
                    )
                    save_plan_state(state)
                    return 1

            logger.info(
                f'Execution Summary | Phase: {selected_phase} | '
                f'Task: {selected_title} | Modified: {len(changed)}'
            )

            # Build assets (PowerShell)
            build_rc, build_out = run_ps('.cursor/workflows/build-assets.ps1')
            if build_rc != 0:
                if attempt < max_retries - 1:
                    logger.warning(f'Attempt {attempt + 1}: Build failed.')
                    fix_prompt = (
                        'Build assets failed. Fix the build errors:\n'
                        f'{_clip(build_out, 4000)}'
                    )
                    attempt += 1
                    continue
                else:
                    logger.error('Task Blocked: Build failed on final attempt.')
                    update_state_item(
                        state,
                        str(selected_id),
                        status='blocked',
                        notes='Build assets failed',
                        missing=['Build failed'],
                        evidence=changed,
                    )
                    save_plan_state(state)
                    return 1

            # Run quality gate
            quality_args = quality_scope_args(changed)
            rc, quality_out = run_ps(
                '.cursor/workflows/check-quality.ps1', quality_args
            )
            if rc != 0:
                q_out_exc = _clip(quality_out, 12000) if quality_out else ''
                q_fix_prompt = (
                    f'Fix failing quality gate for: {selected_title}\n\n'
                    'Constraints:\n'
                    '- Only modify files listed in Changed files.\n'
                    '- Keep diffs minimal.\n'
                    '- Return strict JSON only (no markdown, no prose).\n'
                    f'Quality command output:\n{q_out_exc}\n\n'
                    f'Changed files:\n{json.dumps(changed, indent=2)}\n\n'
                )
                quick_fix_alias = stage_to_alias.get('quick_fix', 'quick-fix')
                try:
                    fix_payload = call_json_with_retry(
                        client=client,
                        stage='quick_fix',
                        model=quick_fix_alias,
                        system=IMPL_SYSTEM,
                        user=q_fix_prompt,
                        schema_hint=SCHEMA_HINT_IMPL,
                        temperature=None,
                        grammar_capable=grammar_capable,
                        response_format=WRITES_RESPONSE_FORMAT,
                        grammar=GBNF_WRITES,
                    )
                except ValueError as exc:
                    if attempt < max_retries - 1:
                        logger.warning(f'Quick-fix invalid JSON: {exc}. Retrying.')
                        fix_prompt = 'Quick-fix invalid JSON. Rewrite code.'
                        attempt += 1
                        continue
                    else:
                        logger.error(f'Task Blocked: Bad JSON final attempt: {exc}')
                        update_state_item(
                            state,
                            str(selected_id),
                            status='blocked',
                            notes='Quick-fix invalid JSON',
                            missing=['json'],
                            evidence=changed,
                        )
                        save_plan_state(state)
                        return 1
                # Validate and apply quick fix
                validate_writes_payload(fix_payload)
                changed += apply_writes_relpaths(fix_payload)
                rc2, quality_out2 = run_ps(
                    '.cursor/workflows/check-quality.ps1', quality_scope_args(changed)
                )
                if rc2 != 0:
                    if attempt < max_retries - 1:
                        fix_prompt = (
                            'Quality failing after quick fix. Output:\n'
                            f'{_clip(quality_out2, 4000)}'
                        )
                        attempt += 1
                        continue
                    else:
                        logger.error('Task Blocked: Quality failing.')
                        update_state_item(
                            state,
                            str(selected_id),
                            status='blocked',
                            notes='Quality failing',
                            missing=['Quality'],
                            evidence=changed,
                        )
                        save_plan_state(state)
                        return 1

            # Run validation gate (layers 1+2)
            try:
                from tools.validation_gate import run_validation_gate
            except ModuleNotFoundError:
                from validation_gate import (
                    run_validation_gate,  # type: ignore[no-redef]
                )
            gate_report = run_validation_gate(
                repo_root=ROOT,
                instructions=selected_requirements,
                changed_files=changed,
            )
            if not gate_report.all_passed:
                gate_errors = '; '.join(
                    err for layer in gate_report.layers for err in layer.errors
                )
                if attempt < max_retries - 1:
                    logger.warning(
                        f'Physical gate failed (attempt {attempt + 1}): {gate_errors}'
                    )
                    fix_prompt = (
                        f'Physical validation gate failed. Errors:\n{gate_errors}\n\n'
                        'Ensure every Target File listed in the PLAN instructions exists '
                        'and the **Validation:** command passes.'
                    )
                    attempt += 1
                    continue
                else:
                    logger.error('Task Blocked: Physical gate failed on final attempt.')
                    # Persist structured gate evidence when blocking the task
                    update_state_item(
                        state,
                        str(selected_id),
                        status='blocked',
                        notes=gate_errors,
                        missing=gate_errors.split('; '),
                        evidence=_gather_gate_evidence(gate_report) or changed,
                    )
                    save_plan_state(state)
                    return 1
        # Physical gate already passed; skip implementation on further iterations
        skip_impl = True

        # LLM semantic review (layer 3)
        verify_payload = {
            'id': str(selected_id),
            'title': selected_title,
            'acceptance': acceptance,
            'changed_files': changed,
            'gate_layers': [layer.model_dump() for layer in gate_report.layers]
            if gate_report
            else [],
        }
        verify_prompt = (
            'The physical validation gate has PASSED (files exist, test command returned 0).\n'
            'Now evaluate semantic completeness only.\n\n'
            'Rules:\n'
            '- Evaluate ONLY listed acceptance criteria for this work item.\n'
            "- Status is 'pass' only if all criteria are fully met.\n"
            "- If 'fail', list missing items concisely.\n\n"
            f'{verify_retry_notes}'
            f'PRD excerpt:\n{prd_summary}\n\n'
            f'PLAN excerpt:\n{plan_summary}\n\n'
            f'Work item:\n{json.dumps(verify_payload, indent=2)}\n'
        )
        pm_verify_alias = stage_to_alias.get('pm_verify', 'pm')
        try:
            verdict = call_json_with_retry(
                client=client,
                stage='pm_verify',
                model=pm_verify_alias,
                system=SYSTEM_PM_VERIFY,
                user=verify_prompt,
                schema_hint=SCHEMA_PM_VERIFY,
                temperature=None,
                grammar_capable=grammar_capable,
                response_format=PM_VERIFY_RESPONSE_FORMAT,
                grammar=GBNF_PM_VERIFY,
            )
        except ValueError as exc:
            # Could not parse JSON at all; mark as schema fail and try once
            if attempt < max_retries - 1:
                logger.warning(f'Invalid PM verdict JSON: {exc}')
                verify_retry_notes = (
                    'Previous PM verification returned invalid JSON. Please return a JSON '
                    "object with keys 'status', 'missing', and 'notes'.\n\n"
                )
                attempt += 1
                continue
            else:
                logger.error(
                    'Task Partial: PM verify returned invalid JSON on final attempt.'
                )
                update_state_item(
                    state,
                    str(selected_id),
                    status='partial',
                    notes='PM verification invalid JSON',
                    missing=['pm_verify_schema_fail'],
                    evidence=changed,
                )
                save_plan_state(state)
                return 1

        # Attempt to parse verdict using strict schema
        try:
            parsed_verdict = PMVerdict.model_validate(verdict)
        except Exception:
            # Schema fail for verdict; attempt to coerce by stripping unknown keys
            if isinstance(verdict, dict):
                cleaned = {
                    'status': verdict.get('status', 'fail'),
                    'missing': verdict.get('missing', []),
                    'notes': verdict.get('notes', ''),
                }
                try:
                    parsed_verdict = PMVerdict.model_validate(cleaned)
                except Exception:
                    parsed_verdict = PMVerdict.model_validate(
                        {
                            'status': 'fail',
                            'missing': [],
                            'notes': 'Invalid verdict response',
                        }
                    )
            else:
                parsed_verdict = PMVerdict.model_validate(
                    {
                        'status': 'fail',
                        'missing': [],
                        'notes': 'Invalid verdict response',
                    }
                )

        # Evaluate verdict status
        if parsed_verdict.status != 'pass':
            missing_list = parsed_verdict.missing
            notes = parsed_verdict.notes
            if attempt < max_retries - 1:
                logger.warning(f'PM Verify Failed. Notes: {notes}')
                verify_retry_notes = (
                    'Previous PM verification returned fail.\n'
                    f'Notes: {notes}\n'
                    f'Missing:\n{"\n".join(missing_list)}\n\n'
                    'Re-evaluate the same changed files against only the listed '
                    'acceptance criteria.\n\n'
                )
                attempt += 1
                continue
            else:
                logger.error(
                    'Task Partial: PM verify failed after physical gate passed.'
                )
                update_state_item(
                    state,
                    str(selected_id),
                    status='partial',
                    notes=notes or 'PM verification failed',
                    missing=missing_list,
                    evidence=changed,
                )
                save_plan_state(state)
                return 1

        # All three layers passed; mark done
        break

    # Completed successfully
    logger.success(f'Task Verified: {selected_title} — all 3 layers passed.')
    update_state_item(
        state,
        str(selected_id),
        status='verified',
        notes=parsed_verdict.notes,
        missing=[],
        evidence=changed,
    )
    append_history(
        state,
        item_id=str(selected_id),
        phase=selected_phase,
        title=selected_title,
        status='verified',
        changed_files=changed,
        notes=parsed_verdict.notes,
    )
    save_plan_state(state)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
