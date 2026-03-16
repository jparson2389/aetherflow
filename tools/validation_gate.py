"""Three-layer completion gate for PLAN implementations.

This module provides a physical validation gate consisting of two layers:

1. **Filesystem existence (Layer 1):** Ensure that the files declared as
   target files in the plan instructions actually exist on disk after
   implementation.  If no explicit targets are declared then any changed
   file satisfies the gate.
2. **Validation command (Layer 2):** Execute an optional shell command
   specified in the plan instructions (via ``**Validation:**`` or
   ``**Command:**``) and treat a non-zero exit code as a hard failure.
3. **Semantic review (Layer 3):** The semantic layer is handled by the PM
   verification agent and is not implemented here.

Additionally this module normalises Python docstrings in file write entries.
Triple-double-quoted strings are converted to triple-single-quoted strings.
If any triple-double-quoted string remains after normalisation the payload
is rejected to avoid docstring churn across retries.

Changes from upstream:

* ``WriteEntry.normalize_py_docstrings`` now performs a deterministic
  normalisation of Python docstrings.  If triple-double-quoted strings
  remain after normalisation a ``ValueError`` is raised to indicate a
  hard failure.
"""

from __future__ import annotations

import io
import re
import shlex
import subprocess
import tokenize
from dataclasses import field
from pathlib import Path

from pydantic import BaseModel, model_validator

try:
    from tools.shell_utils import normalize_powershell_command
except ModuleNotFoundError:  # pragma: no cover
    from shell_utils import normalize_powershell_command  # type: ignore[no-redef]


def normalize_docstring_quotes(content: str) -> str:
    '''Convert triple-double-quoted STRING tokens to triple-single-quoted.

    Only transforms tokens delimited by ``"""``.  Never modifies existing
    triple-single-quoted strings or raw text.  Skips tokens whose inner
    content contains triple-single-quotes to avoid corruption.
    '''
    if '"""' not in content:
        return content
    lines = content.splitlines(keepends=True)
    if not lines:
        return content

    def offset(pos: tuple[int, int]) -> int:
        line, col = pos
        return sum(len(lines[i]) for i in range(line - 1)) + col

    result: list[str] = []
    last_end = 0
    try:
        for tok in tokenize.generate_tokens(io.StringIO(content).readline):
            start_off = offset(tok.start)
            end_off = offset(tok.end)
            if tok.type == tokenize.STRING and tok.string.startswith('"""'):
                inner = tok.string[3:-3]
                if "'''" in inner:
                    # Skip normalisation if the inner string already contains
                    # triple single quotes to avoid introducing syntax errors.
                    result.append(content[last_end:end_off])
                else:
                    result.append(content[last_end:start_off])
                    result.append("'''" + inner + "'''")
            else:
                result.append(content[last_end:end_off])
            last_end = end_off
        result.append(content[last_end:])
    except tokenize.TokenError:
        # If tokenisation fails return the original content unchanged.
        return content
    return ''.join(result)


class WriteEntry(BaseModel):
    """A single file write entry in a writes payload.

    Each entry contains a repository-relative path and the full file
    contents.  For Python files a normalisation pass converts triple
    double-quoted strings to triple single-quoted strings.  If any
    triple-double-quoted string remains after normalisation the entry is
    considered invalid and a ``ValueError`` is raised.
    """

    path: str
    content: str

    @model_validator(mode='after')
    def normalize_py_docstrings(self) -> WriteEntry:
        """Transform triple-double-quoted docstrings to triple-single.

        When writing Python files the content is normalised by converting
        triple-double-quoted strings to triple-single-quoted strings.  After
        normalisation, any remaining triple-double-quotes are considered a
        hard error.  This deterministic transform eliminates repeated
        docstring warnings from the validation gate.
        """
        if self.path.endswith('.py') and '"""' in self.content:
            # Perform the normalisation.
            new_content = normalize_docstring_quotes(self.content)
            # If triple-double quotes remain, hard fail.
            if '"""' in new_content:
                raise ValueError(
                    'Triple-double-quoted docstrings remain after normalisation'
                )
            self.content = new_content
        return self


class WritesPayload(BaseModel):
    """A JSON payload containing one or more file writes and optional notes."""

    writes: list[WriteEntry]
    notes: str


# ── Data models (Pydantic v2) ────────────────────────────────────────────────


class GateResult(BaseModel):
    """Result from a single validation gate layer.

    In addition to a binary pass/fail, each gate may emit structured
    evidence about what was checked.  Depending on the layer this may
    include the invoked command, its return code, captured output excerpts,
    target file paths, failing test identifiers, assertion excerpts, or
    exception excerpts.  Evidence and errors remain as lists of strings
    for backward compatibility, while the additional fields provide
    programmatic access to structured diagnostics.
    """

    layer: int
    passed: bool
    # User-facing evidence and error lists remain simple strings.
    evidence: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # Structured diagnostics (optional depending on the layer)
    command: str | None = None
    returncode: int | None = None
    stdout_excerpt: str | None = None
    stderr_excerpt: str | None = None
    target_files: list[str] | None = None
    failing_test: str | None = None
    assertion_excerpt: str | None = None
    exception_excerpt: str | None = None


class ValidationReport(BaseModel):
    """Aggregated result from all validation layers.

    This report collates the results of each gate and promotes
    structured diagnostics to the top level for convenience.  When
    available, ``command``, ``returncode``, ``stdout_excerpt``,
    ``stderr_excerpt``, ``target_files``, ``failing_test``,
    ``assertion_excerpt``, and ``exception_excerpt`` are surfaced from
    the deepest executed gate.  These fields are optional and remain
    ``None`` when not applicable.
    """

    all_passed: bool
    layers: list[GateResult]
    changed_files: list[str]
    validation_command: str | None = None
    # Promote structured diagnostics to the report level
    command: str | None = None
    returncode: int | None = None
    stdout_excerpt: str | None = None
    stderr_excerpt: str | None = None
    target_files: list[str] | None = None
    failing_test: str | None = None
    assertion_excerpt: str | None = None
    exception_excerpt: str | None = None


# ── Layer 1: Filesystem existence ────────────────────────────────────────────

_TARGET_FILE_RE = re.compile(
    r'\*\*Target Files?:\*\*\s*`([^`]+)`',
    re.IGNORECASE,
)


def extract_target_files(instructions: str) -> list[str]:
    """Parse all ``**Target File:**`` paths from a PLAN.md instruction block."""
    return _TARGET_FILE_RE.findall(instructions)


def check_filesystem_existence(
    repo_root: Path,
    instructions: str,
    changed_files: list[str],
) -> GateResult:
    """
    Layer 1 gate: verify every Target File listed in instructions physically
    exists on disk.  Also accepts any file present in ``changed_files``.
    Structured diagnostics record the list of target files seen and which
    were satisfied.
    """
    target_paths = extract_target_files(instructions)
    # If there are no explicit targets then any changed file counts.  We
    # record the changed files as evidence and treat that as the target list.
    if not target_paths:
        return GateResult(
            layer=1,
            passed=bool(changed_files),
            evidence=changed_files,
            errors=[]
            if changed_files
            else ['No files were written and no Target File declared.'],
            target_files=changed_files if changed_files else None,
        )

    changed_set = {Path(p).as_posix() for p in changed_files}
    errors: list[str] = []
    evidence: list[str] = []

    for rel in target_paths:
        abs_path = repo_root / rel
        if abs_path.exists():
            evidence.append(rel)
        elif Path(rel).as_posix() in changed_set:
            evidence.append(rel)  # was written this run
        else:
            errors.append(f'MISSING: {rel}')

    return GateResult(
        layer=1,
        passed=len(errors) == 0,
        evidence=evidence,
        errors=errors,
        target_files=target_paths,
    )


# ── Layer 2: Validation command ──────────────────────────────────────────────

_INLINE_VALIDATION_RE = re.compile(
    r'\*\*Validation:\*\*\s*`([^`]+)`',
    re.IGNORECASE,
)
_MULTILINE_VALIDATION_RE = re.compile(
    r'\*\*Validation:\*\*\s*\n\s*>?\s*`([^`]+)`',
    re.IGNORECASE,
)
_COMMAND_RE = re.compile(
    r'\*\*Command:\*\*\s*`([^`]+)`',
    re.IGNORECASE,
)


def extract_validation_command(instructions: str) -> str | None:
    """Parse the ``**Validation:**`` shell command from a PLAN.md instruction block."""
    inline_match = _INLINE_VALIDATION_RE.search(instructions)
    if inline_match:
        return inline_match.group(1).strip()

    multiline_match = _MULTILINE_VALIDATION_RE.search(instructions)
    if multiline_match:
        return multiline_match.group(1).strip()

    command_match = _COMMAND_RE.search(instructions)
    if command_match and re.search(r'\*\*Validation:\*\*\s*Exit\s+0', instructions):
        return command_match.group(1).strip()

    return None


def run_validation_command(
    repo_root: Path,
    command: str,
    timeout: int = 120,
) -> GateResult:
    """
    Layer 2 gate: execute the declared validation command in the repo root.
    A non-zero exit code is treated as a hard failure.  Structured
    diagnostics capture the invoked command, return code and
    excerpts of stdout/stderr.  When possible the output is parsed
    heuristically to extract failing test identifiers, assertion
    excerpts and exception excerpts.
    """
    try:
        argv = _parse_validation_command(command, repo_root=repo_root)
    except ValueError as exc:
        return GateResult(
            layer=2,
            passed=False,
            errors=[f'Disallowed command syntax: {exc}'],
            command=command,
        )
    try:
        result = subprocess.run(
            argv,
            shell=False,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        passed = result.returncode == 0
        # Capture separate stdout/stderr excerpts to aid diagnostics
        stdout_excerpt = (result.stdout or '')[:2000].strip() or None
        stderr_excerpt = (result.stderr or '')[:2000].strip() or None
        evidence: list[str] = []
        errors: list[str] = []
        if passed:
            # Provide a short combined excerpt as human evidence
            combined = ((result.stdout or '') + (result.stderr or '')).strip()
            if combined:
                evidence.append(combined[:2000])
        else:
            combined = ((result.stdout or '') + (result.stderr or '')).strip()
            if combined:
                errors.append(combined[:2000])

        # Heuristic extraction of failing test and assertion/exception excerpts
        failing_test = None
        assertion_excerpt = None
        exception_excerpt = None
        if not passed and combined:
            # Attempt to detect pytest failing test lines
            for line in combined.splitlines():
                line_strip = line.strip()
                if (
                    not failing_test
                    and '::' in line_strip
                    and line_strip.startswith('FAILED ')
                ):
                    # Example: FAILED tests/test_example.py::test_func - AssertionError: message
                    parts = line_strip.split(None, 1)
                    if len(parts) > 1:
                        failing_test = parts[1].split(' - ')[0].strip()
                # Detect assertion errors
                if 'AssertionError' in line_strip and not assertion_excerpt:
                    assertion_excerpt = line_strip
                # Detect exception tracebacks
                if (
                    'Traceback' in line_strip or 'Error:' in line_strip
                ) and not exception_excerpt:
                    exception_excerpt = line_strip
        return GateResult(
            layer=2,
            passed=passed,
            evidence=evidence,
            errors=errors,
            command=' '.join(argv),
            returncode=result.returncode,
            stdout_excerpt=stdout_excerpt,
            stderr_excerpt=stderr_excerpt,
            failing_test=failing_test,
            assertion_excerpt=assertion_excerpt,
            exception_excerpt=exception_excerpt,
        )
    except subprocess.TimeoutExpired:
        return GateResult(
            layer=2,
            passed=False,
            errors=[f'Validation command timed out after {timeout}s: {" ".join(argv)}'],
            command=' '.join(argv),
        )
    except Exception as exc:
        return GateResult(
            layer=2,
            passed=False,
            errors=[f'Validation command raised exception: {exc}'],
            command=' '.join(argv),
        )


_DISALLOWED_COMMAND_TOKENS = (';', '&&', '||', '|', '>', '<', '$(', '`')


def _parse_validation_command(command: str, *, repo_root: Path) -> list[str]:
    """Parse and allowlist supported validation commands.

    Args:
        command: Raw command string extracted from docs.
        repo_root: Repository root for path validation.

    Returns:
        Safe argv list for subprocess execution.

    Raises:
        ValueError: If the command contains disallowed syntax or is unsupported.

    """
    if any(token in command for token in _DISALLOWED_COMMAND_TOKENS):
        raise ValueError('command chaining and redirection are not allowed')
    argv = shlex.split(command, posix=False)
    if not argv:
        raise ValueError('empty command')
    head = argv[0].lower()
    if argv[:3] == ['uv', 'run', 'pytest']:
        return argv
    if argv[:4] == ['uv', 'run', 'ruff', 'check']:
        return argv
    if head in {'powershell', 'pwsh'}:
        normalized = list(argv)
        normalized[0] = normalize_powershell_command(head)
        if normalized[1:4] != ['-ExecutionPolicy', 'Bypass', '-File']:
            raise ValueError('only PowerShell -ExecutionPolicy Bypass -File is allowed')
        script_path = (repo_root / normalized[4]).resolve()
        if repo_root.resolve() not in script_path.parents:
            raise ValueError('PowerShell file must stay within repo root')
        normalized[4] = str(script_path)
        return normalized
    raise ValueError('command is not in the validation allowlist')


# ── Public entry point ───────────────────────────────────────────────────────


def run_validation_gate(
    repo_root: Path,
    instructions: str,
    changed_files: list[str],
) -> ValidationReport:
    """
    Run all physical validation layers.

    The caller receives a ``ValidationReport`` which aggregates results and
    surfaces structured diagnostics from the deepest executed layer.  If
    the filesystem check fails we return early; otherwise if a validation
    command is declared we execute it.  When a layer fails, the report
    includes the structured fields captured by that layer; on success the
    report may still expose diagnostics for informational purposes.
    """
    layers: list[GateResult] = []

    # Layer 1 - filesystem
    l1 = check_filesystem_existence(repo_root, instructions, changed_files)
    layers.append(l1)
    if not l1.passed:
        return ValidationReport(
            all_passed=False,
            layers=layers,
            changed_files=changed_files,
            target_files=l1.target_files,
        )

    # Layer 2 - validation command (optional: if not declared, skip gracefully)
    command = extract_validation_command(instructions)
    if command:
        l2 = run_validation_command(repo_root, command)
        layers.append(l2)
        if not l2.passed:
            return ValidationReport(
                all_passed=False,
                layers=layers,
                changed_files=changed_files,
                validation_command=command,
                command=l2.command,
                returncode=l2.returncode,
                stdout_excerpt=l2.stdout_excerpt,
                stderr_excerpt=l2.stderr_excerpt,
                target_files=l1.target_files,
                failing_test=l2.failing_test,
                assertion_excerpt=l2.assertion_excerpt,
                exception_excerpt=l2.exception_excerpt,
            )

    # All passed
    # Expose diagnostics for informational success: propagate l2 fields if present
    report_kwargs = {
        'all_passed': True,
        'layers': layers,
        'changed_files': changed_files,
        'validation_command': command,
    }
    # Prefer diagnostics from layer2 if executed, else from layer1
    src = layers[-1]
    report_kwargs.update(
        {
            'command': getattr(src, 'command', None),
            'returncode': getattr(src, 'returncode', None),
            'stdout_excerpt': getattr(src, 'stdout_excerpt', None),
            'stderr_excerpt': getattr(src, 'stderr_excerpt', None),
            'target_files': getattr(l1, 'target_files', None),
            'failing_test': getattr(src, 'failing_test', None),
            'assertion_excerpt': getattr(src, 'assertion_excerpt', None),
            'exception_excerpt': getattr(src, 'exception_excerpt', None),
        }
    )
    return ValidationReport(**report_kwargs)
