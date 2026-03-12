from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from loguru import logger
from openai import OpenAI

try:
    from tools.json_utils import WRITES_RESPONSE_FORMAT, parse_json_object
except ModuleNotFoundError:
    from json_utils import (  # type: ignore[no-redef]
        WRITES_RESPONSE_FORMAT,
        parse_json_object,
    )

try:
    from tools.prompts import IMPL_SYSTEM, SYSTEM_JSON_WRITES
except ModuleNotFoundError:
    from prompts import IMPL_SYSTEM, SYSTEM_JSON_WRITES  # type: ignore[no-redef]


def _read(path: str) -> str:
    """Read a UTF-8 text file, tolerating decode issues.

    Args:
        path: Filesystem path to read.

    Returns:
        The decoded file content.
    """
    return Path(path).read_text(encoding='utf-8', errors='ignore')


def _parse_json(s: str) -> dict[str, Any] | None:
    """Parse a JSON object from model output.

    Args:
        s: Raw model response text.

    Returns:
        The parsed JSON object when successful, otherwise ``None``.
    """
    try:
        return parse_json_object(s, stage='agent_call')
    except ValueError:
        return None


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


def _build_extra_body(*, model: str, use_local_backend: bool) -> dict[str, Any]:
    """Build backend-specific request fields for local llama.cpp calls.

    Args:
        model: Runtime alias requested from the router.
        use_local_backend: Whether llama.cpp-specific fields are safe to send.

    Returns:
        Extra request fields for the chat completions call.
    """
    if use_local_backend and model == 'pm':
        return {'reasoning_format': 'deepseek'}
    return {}


def main() -> int:
    """Run the ad-hoc agent caller CLI.

    Returns:
        Process exit code.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--agent', required=True, help='architect|pm|quick-fix|researcher|ui-ux'
    )
    ap.add_argument('--prompt', default=None)
    ap.add_argument('--prompt-file', default=None)
    ap.add_argument('--include', action='append', default=[])
    ap.add_argument('--base-url', default='http://127.0.0.1:8080/v1')
    ap.add_argument('--api-key', default='anything')
    ap.add_argument('--temperature', type=float, default=None)
    ap.add_argument('--json-writes', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--repo-root', default='.')

    args = ap.parse_args()

    if not args.prompt and not args.prompt_file:
        logger.error('Provide --prompt or --prompt-file')
        return 2

    prompt = args.prompt
    if prompt is None:
        prompt_file = args.prompt_file
        if prompt_file is None:
            logger.error('Provide --prompt or --prompt-file')
            return 2
        prompt = _read(prompt_file)

    if args.include:
        ctx: list[str] = []
        for inc in args.include:
            if Path(inc).exists():
                ctx.append(f'\n\n# FILE: {inc}\n{_read(inc)}')
            else:
                ctx.append(f'\n\n# FILE: {inc}\n<missing>')
        import subprocess

        try:
            tree = subprocess.getoutput("tree -I '__pycache__|venv|.git' .")
        except Exception:
            tree = 'tree command not available'

        prompt = f'DIRECTORY STRUCTURE:\n{tree}\n\n' + prompt + '\n' + '\n'.join(ctx)

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    system = IMPL_SYSTEM if (args.json_writes or args.apply) else SYSTEM_JSON_WRITES
    parsed_base_url = urlparse(args.base_url)
    use_local_overrides = parsed_base_url.hostname in {'127.0.0.1', 'localhost'}

    extra: dict[str, Any] = {}
    if args.json_writes or args.apply:
        extra['response_format'] = WRITES_RESPONSE_FORMAT
    extra_body = _build_extra_body(
        model=args.agent,
        use_local_backend=use_local_overrides,
    )
    if extra_body:
        extra['extra_body'] = extra_body

    kwargs: dict[str, Any] = {
        'model': args.agent,
        'temperature': args.temperature,
        'messages': _build_messages(system, prompt),
    }
    kwargs.update(extra)
    resp = client.chat.completions.create(**kwargs)

    content = (resp.choices[0].message.content or '').strip()

    if not args.apply:
        logger.info(content)
        return 0

    payload = _parse_json(content)
    if payload is None:
        logger.error('Expected JSON but could not parse model output: {}', content)
        return 3

    # Apply writes. Support both module invocation (`-m tools.agent_call`)
    # and direct script invocation (`python tools/agent_call.py`).
    try:
        from tools.apply_writes import apply_writes  # local import
    except ModuleNotFoundError:
        from apply_writes import apply_writes  # type: ignore[no-redef]

    repo_root = Path(args.repo_root).resolve()
    changed = apply_writes(repo_root, payload)

    notes = payload.get('notes', '')
    if isinstance(notes, str) and notes:
        logger.info(notes)

    for p in changed:
        logger.info(p.relative_to(repo_root))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
