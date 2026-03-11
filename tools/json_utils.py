# tools/json_utils.py
"""Shared JSON extraction utilities. Single source of truth for both
plan_exec.py and agent_call.py."""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

WRITES_RESPONSE_FORMAT: dict = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'writes_response',
        'strict': True,
        'schema': {
            'type': 'object',
            'required': ['writes', 'notes'],
            'additionalProperties': False,
            'properties': {
                'writes': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'required': ['path', 'content'],
                        'additionalProperties': False,
                        'properties': {
                            'path': {'type': 'string'},
                            'content': {'type': 'string'},
                        },
                    },
                },
                'notes': {'type': 'string'},
            },
        },
    },
}


PM_NEXT_RESPONSE_FORMAT: dict = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'pm_next_response',
        'strict': True,
        'schema': {
            'type': 'object',
            'required': ['phase', 'work_items'],
            'additionalProperties': False,
            'properties': {
                'phase': {'type': 'string'},
                'work_items': {
                    'type': 'array',
                    'minItems': 1,
                    'maxItems': 1,
                    'items': {
                        'type': 'object',
                        'required': ['id', 'title', 'agent', 'acceptance', 'notes'],
                        'additionalProperties': False,
                        'properties': {
                            'id': {'type': 'string'},
                            'title': {'type': 'string'},
                            'agent': {
                                'type': 'string',
                                'enum': ['architect', 'ui-ux'],
                            },
                            'acceptance': {
                                'type': 'array',
                                'minItems': 1,
                                'items': {'type': 'string'},
                            },
                            'notes': {'type': 'string'},
                        },
                    },
                },
            },
        },
    },
}


PM_VERIFY_RESPONSE_FORMAT: dict = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'pm_verify_response',
        'strict': True,
        'schema': {
            'type': 'object',
            'required': ['status', 'missing', 'notes'],
            'additionalProperties': False,
            'properties': {
                'status': {'type': 'string', 'enum': ['pass', 'fail']},
                'missing': {
                    'type': 'array',
                    'items': {'type': 'string'},
                },
                'notes': {'type': 'string'},
            },
        },
    },
}


def _extract_fenced_json(text: str) -> str | None:
    """Return the content of the first ```json...``` fence, if any."""
    match = re.search(
        r'```(?:json)?\s*(\{.*?\})\s*```', text, re.IGNORECASE | re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_first_json_object(text: str) -> str | None:
    """Return the first balanced JSON object found via brace-counting."""
    start = -1
    depth = 0
    in_string = False
    escape = False

    for idx, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == '{':
            if depth == 0:
                start = idx
            depth += 1
        elif ch == '}' and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start : idx + 1].strip()

    return None


def parse_json_object(
    raw: str,
    *,
    stage: str = 'unknown',
    dump_on_failure: str | None = None,
) -> dict[str, Any]:
    """Try to parse a JSON object from raw text using three strategies:
    direct parse, fenced code block extraction, and brace-counting.

    Args:
        raw: Raw text from an LLM response.
        stage: Label used in log output and error messages.
        dump_on_failure: If provided, write the raw text to this path on failure.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If no valid JSON object is found.
    """
    text = raw.strip()
    candidates: list[tuple[str, str]] = []
    if text:
        candidates.append(('direct', text))
    fenced = _extract_fenced_json(text)
    if fenced:
        candidates.append(('fenced', fenced))
    first_obj = _extract_first_json_object(text)
    if first_obj:
        candidates.append(('first_object', first_obj))
    for strategy, candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            logger.debug(f'[parse] stage={stage} status=ok strategy={strategy}')
            return payload

    logger.debug(f'[parse] stage={stage} status=failed')
    raise ValueError(f"Could not parse valid JSON object for stage '{stage}'.")


def safe_json_from_model(stage: str, raw_text: str) -> dict[str, Any]:
    """Backwards-compatible wrapper around parse_json_object.

    Args:
        stage: Label used in log output and error messages.
        raw_text: Raw LLM response text.

    Returns:
        Parsed dict.

    Raises:
        ValueError: If no valid JSON object is found.
    """
    return parse_json_object(raw_text, stage=stage)


# Canonical system prompt for JSON writes: tools.prompts.SYSTEM_JSON_WRITES
