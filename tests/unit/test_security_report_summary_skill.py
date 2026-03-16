from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path


def _write_bandit_report(tmp_path: Path, html_body: str) -> Path:
    report_path = tmp_path / 'security_report.html'
    report_path.write_text(textwrap.dedent(html_body), encoding='utf-8')
    return report_path


def _run_summary_script(report_path: Path) -> subprocess.CompletedProcess[str]:
    script_path = (
        Path(__file__).resolve().parents[2]
        / '.codex'
        / 'skills'
        / 'security-report-summary'
        / 'scripts'
        / 'summarize_security_report.py'
    )
    return subprocess.run(
        [sys.executable, str(script_path), str(report_path)],
        capture_output=True,
        text=True,
        check=True,
    )


def test_summary_script_highlights_in_repo_findings(tmp_path: Path) -> None:
    report_path = _write_bandit_report(
        tmp_path,
        """
        <!DOCTYPE html>
        <html>
        <body>
        <div id="metrics">
            Total lines of code: <span id="loc">120</span><br>
            Total lines skipped (#nosec): <span id="nosec">2</span>
        </div>
        <div id="results">
            <div id="issue-0">
                <div class="issue-block issue-sev-high">
                    <b>subprocess_popen_with_shell_equals_true: </b>
                    subprocess call with shell=True identified, security issue.<br>
                    <b>Test ID:</b> B602<br>
                    <b>Severity: </b>HIGH<br>
                    <b>Confidence: </b>HIGH<br>
                    <b>File: </b><a href="./src/app.py">src/app.py</a><br>
                    <b>Line number: </b>42<br>
                </div>
            </div>
            <div id="issue-1">
                <div class="issue-block issue-sev-medium">
                    <b>hardcoded_password_string: </b>
                    Possible hardcoded password.<br>
                    <b>Test ID:</b> B105<br>
                    <b>Severity: </b>MEDIUM<br>
                    <b>Confidence: </b>MEDIUM<br>
                    <b>File: </b><a href="./scripts/bootstrap.py">scripts/bootstrap.py</a><br>
                    <b>Line number: </b>10<br>
                </div>
            </div>
            <div id="issue-2">
                <div class="issue-block issue-sev-low">
                    <b>blacklist: </b>
                    Consider possible security implications associated with
                    the subprocess module.<br>
                    <b>Test ID:</b> B404<br>
                    <b>Severity: </b>LOW<br>
                    <b>Confidence: </b>HIGH<br>
                    <b>File: </b><a href="./.venv/Lib/site-packages/pkg/mod.py">
                    ./.venv/Lib/site-packages/pkg/mod.py</a><br>
                    <b>Line number: </b>6<br>
                </div>
            </div>
        </div>
        </body>
        </html>
        """,
    )

    result = _run_summary_script(report_path)
    summary = result.stdout

    assert 'Bandit report summary' in summary
    assert 'Lines of code: 120' in summary
    assert 'Suppressed with #nosec: 2' in summary
    assert 'Total issues: 3' in summary
    assert 'In-repo findings: 2' in summary
    assert 'Third-party findings: 1' in summary
    assert 'HIGH 1 | MEDIUM 1 | LOW 1' in summary
    assert 'B602' in summary
    assert 'src/app.py:42' in summary
    assert 'scripts/bootstrap.py:10' in summary


def test_summary_script_calls_out_third_party_heavy_reports(
    tmp_path: Path,
) -> None:
    report_path = _write_bandit_report(
        tmp_path,
        """
        <!DOCTYPE html>
        <html>
        <body>
        <div id="metrics">
            Total lines of code: <span id="loc">80</span><br>
            Total lines skipped (#nosec): <span id="nosec">0</span>
        </div>
        <div id="results">
            <div id="issue-0">
                <div class="issue-block issue-sev-high">
                    <b>subprocess_popen_with_shell_equals_true: </b>
                    subprocess call with shell=True identified, security issue.<br>
                    <b>Test ID:</b> B602<br>
                    <b>Severity: </b>HIGH<br>
                    <b>Confidence: </b>HIGH<br>
                    <b>File: </b><a href="./.venv/Lib/site-packages/a.py">
                    ./.venv/Lib/site-packages/a.py</a><br>
                    <b>Line number: </b>8<br>
                </div>
            </div>
            <div id="issue-1">
                <div class="issue-block issue-sev-medium">
                    <b>request_with_no_cert_validation: </b>
                    Requests call without certificate validation.<br>
                    <b>Test ID:</b> B501<br>
                    <b>Severity: </b>MEDIUM<br>
                    <b>Confidence: </b>HIGH<br>
                    <b>File: </b><a href="./.venv/Lib/site-packages/b.py">
                    ./.venv/Lib/site-packages/b.py</a><br>
                    <b>Line number: </b>12<br>
                </div>
            </div>
            <div id="issue-2">
                <div class="issue-block issue-sev-low">
                    <b>blacklist: </b>
                    Consider possible security implications associated with
                    the subprocess module.<br>
                    <b>Test ID:</b> B404<br>
                    <b>Severity: </b>LOW<br>
                    <b>Confidence: </b>HIGH<br>
                    <b>File: </b><a href="./.venv/Lib/site-packages/c.py">
                    ./.venv/Lib/site-packages/c.py</a><br>
                    <b>Line number: </b>3<br>
                </div>
            </div>
            <div id="issue-3">
                <div class="issue-block issue-sev-medium">
                    <b>hardcoded_password_string: </b>
                    Possible hardcoded password.<br>
                    <b>Test ID:</b> B105<br>
                    <b>Severity: </b>MEDIUM<br>
                    <b>Confidence: </b>MEDIUM<br>
                    <b>File: </b><a href="./src/config.py">src/config.py</a><br>
                    <b>Line number: </b>5<br>
                </div>
            </div>
        </div>
        </body>
        </html>
        """,
    )

    result = _run_summary_script(report_path)

    assert 'Most findings come from third-party or virtualenv paths.' in result.stdout
