"""Regression test: check_ai.py must actually run and print something."""
import os
import pathlib
import subprocess
import sys

BACKEND = pathlib.Path(__file__).resolve().parents[1]


def test_check_ai_script_runs_and_reports_when_unconfigured():
    env = {**os.environ, "AI_PROVIDER": "none", "AI_API_KEY": ""}
    r = subprocess.run([sys.executable, "check_ai.py", "speed"], cwd=BACKEND, env=env,
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert "Settings seen by the app" in r.stdout
    assert "NOT CONFIGURED" in r.stdout
