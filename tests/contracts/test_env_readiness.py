from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_verify_env_generates_report() -> None:
    report_path = PROJECT_ROOT / "logs" / "env_report.json"
    if report_path.exists():
        report_path.unlink()

    script_path = PROJECT_ROOT / "scripts" / "verify-env.ps1"
    assert script_path.exists()

    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["uv"]["available"] is True
    assert report["python"]["available"] is True
    assert report["powershell"]["available"] is True
    assert report["cl"]["available"] is True
