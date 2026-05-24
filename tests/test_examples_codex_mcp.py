from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_codex_mcp_stdio_smoke_example_runs() -> None:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = (
        src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    )

    result = subprocess.run(  # noqa: S603
        [sys.executable, "examples/codex-mcp/stdio_smoke.py"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)

    assert payload["tool_count"] >= 17
    assert payload["raw_gdb_tool_exposed"] is False
    assert "reset_target" in payload["tools"]
    assert "probemcp://schema" in payload["resources"]
    assert payload["schema_has_json_schemas"] is True
    assert payload["missing_session_has_error"] is True
