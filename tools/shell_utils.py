from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


def resolve_powershell_executable() -> str:
    """Resolve the available PowerShell executable for this machine.

    Returns:
        An absolute path to the first available PowerShell executable.

    Raises:
        FileNotFoundError: If neither Windows PowerShell nor PowerShell 7 is
            available.

    """
    candidates = [
        shutil.which('pwsh'),
        str(
            Path(os.environ.get('ProgramFiles', r'C:\Program Files'))
            / 'PowerShell'
            / '7'
            / 'pwsh.exe'
        ),
        shutil.which('powershell'),
        str(
            Path(os.environ.get('SystemRoot', r'C:\Windows'))
            / 'System32'
            / 'WindowsPowerShell'
            / 'v1.0'
            / 'powershell.exe'
        ),
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    raise FileNotFoundError('Neither powershell.exe nor pwsh.exe is available.')


def normalize_powershell_command(command: str) -> str:
    """Replace a leading PowerShell alias with the resolved executable path.

    Args:
        command: Shell command string that may start with ``powershell`` or
            ``pwsh``.

    Returns:
        The normalized command string. Commands that do not begin with a
        PowerShell alias are returned unchanged.

    """
    if not re.match(r'^\s*(powershell|pwsh)(?=\s|$)', command, re.IGNORECASE):
        return command

    executable = resolve_powershell_executable()
    return re.sub(
        r'^\s*(powershell|pwsh)(?=\s|$)',
        lambda _: f'"{executable}"',
        command,
        count=1,
        flags=re.IGNORECASE,
    )
