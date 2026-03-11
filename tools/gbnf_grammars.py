"""GBNF grammar definitions for token-level JSON enforcement on local backends.

llama.cpp's OpenAI-compatible ``/v1/chat/completions`` endpoint silently
ignores ``response_format`` with ``type: "json_schema"``.  These GBNF
grammars are passed via ``extra_body={"grammar": ...}`` so that the
model is constrained at the token level and *cannot* produce
non-conforming output.

Three grammars are provided, one per JSON-producing call type:

* ``GBNF_WRITES`` — implementation writes payload
* ``GBNF_PM_NEXT`` — PM next-item selector response
* ``GBNF_PM_VERIFY`` — PM verification verdict
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

_GBNF_JSON_PRIMITIVES = r"""
space    ::= [ \t\n\r]*
string   ::= "\"" ([^"\\] | "\\" .)* "\""
"""

# ---------------------------------------------------------------------------
# GBNF_WRITES
#
# Enforces: {"writes": [<1+ write entries>], "notes": "<string>"}
# Each write entry: {"path": "<string>", "content": "<string>"}
# ---------------------------------------------------------------------------

GBNF_WRITES: str = (
    r"""
root     ::= "{" space writes-key space ":" space writes-arr space "," space notes-key space ":" space string space "}"

writes-key ::= "\"writes\""
notes-key  ::= "\"notes\""
path-key   ::= "\"path\""
content-key ::= "\"content\""

writes-arr ::= "[" space write-entry ( space "," space write-entry )* space "]"
write-entry ::= "{" space path-key space ":" space string space "," space content-key space ":" space string space "}"
"""
    + _GBNF_JSON_PRIMITIVES
)

# ---------------------------------------------------------------------------
# GBNF_PM_NEXT
#
# Enforces: {"phase": "<str>", "work_items": [<1 item>]}
# Item: {"id": "<str>", "title": "<str>", "agent": "architect"|"ui-ux",
#         "acceptance": [<1+ strings>], "notes": "<str>"}
# ---------------------------------------------------------------------------

GBNF_PM_NEXT: str = (
    r"""
root     ::= "{" space phase-key space ":" space string space "," space wi-key space ":" space wi-arr space "}"

phase-key ::= "\"phase\""
wi-key    ::= "\"work_items\""
id-key    ::= "\"id\""
title-key ::= "\"title\""
agent-key ::= "\"agent\""
acc-key   ::= "\"acceptance\""
notes-key ::= "\"notes\""

agent-val ::= "\"architect\"" | "\"ui-ux\""

wi-arr    ::= "[" space wi-item space "]"
wi-item   ::= "{" space id-key space ":" space string space "," space title-key space ":" space string space "," space agent-key space ":" space agent-val space "," space acc-key space ":" space str-arr space "," space notes-key space ":" space string space "}"

str-arr   ::= "[" space string ( space "," space string )* space "]"
"""
    + _GBNF_JSON_PRIMITIVES
)

# ---------------------------------------------------------------------------
# GBNF_PM_VERIFY
#
# Enforces: {"status": "pass"|"fail", "missing": [<0+ strings>], "notes": "<str>"}
# ---------------------------------------------------------------------------

GBNF_PM_VERIFY: str = (
    r"""
root     ::= "{" space status-key space ":" space status-val space "," space missing-key space ":" space str-arr space "," space notes-key space ":" space string space "}"

status-key  ::= "\"status\""
missing-key ::= "\"missing\""
notes-key   ::= "\"notes\""

status-val  ::= "\"pass\"" | "\"fail\""

str-arr     ::= "[" space "]" | "[" space string ( space "," space string )* space "]"
"""
    + _GBNF_JSON_PRIMITIVES
)


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------


def is_local_backend(base_url: str) -> bool:
    """Detect local llama.cpp / vLLM backends by URL.

    Args:
        base_url: The base URL of the LLM backend (e.g. from agent_manifest).

    Returns:
        True if the URL points to a local server.
    """
    url = str(base_url).lower()
    return any(host in url for host in ('127.0.0.1', 'localhost', '0.0.0.0'))
