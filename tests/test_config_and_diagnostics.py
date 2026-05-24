from pathlib import Path

import pytest
from typer.testing import CliRunner

from probemcp.cli import app
from probemcp.config import ProbeMCPConfig, default_config, load_config
from probemcp.mcp_server.factory import create_tool_service_from_config
from probemcp.mcp_server.schemas import BackendKind, PermissionLevel
from probemcp.safety.policy import TargetClass


def test_default_config_is_readonly_and_local_first() -> None:
    config = default_config()

    assert config.server.permission_mode == PermissionLevel.READONLY
    assert config.server.target_class == TargetClass.UNKNOWN
    assert config.targets == {}


def test_load_config_with_target_profile(tmp_path: Path) -> None:
    config_path = tmp_path / "probemcp.toml"
    config_path.write_text(
        """
schema_version = 1
default_target = "demo"

[server]
permission_mode = "confirm-required"
target_class = "emulator"
audit_log_path = "audit/probemcp.jsonl"
max_sessions = 2
max_memory_read_bytes = 64
max_memory_write_bytes = 16
max_snapshot_stack_bytes = 128
max_concurrent_tool_calls = 3
max_session_operations = 1
max_mi_command_queue = 8
hardware_operation_allowlist = ["halt", "resume"]

[targets.demo]
backend = "qemu"
endpoint = "localhost:3333"
gdb_path = "arm-none-eabi-gdb"
profile = "cortex-m"
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.get_target().backend == BackendKind.QEMU
    assert config.server.permission_mode == PermissionLevel.CONFIRM_REQUIRED
    assert config.server.max_memory_read_bytes == 64
    assert config.server.hardware_operation_allowlist[0].value == "halt"


def test_config_rejects_missing_default_target() -> None:
    with pytest.raises(ValueError, match="default_target not found"):
        ProbeMCPConfig.model_validate({"default_target": "missing"})


def test_create_tool_service_from_config_sets_limits_and_factory() -> None:
    service = create_tool_service_from_config(
        ProbeMCPConfig.model_validate(
            {
                "server": {
                    "permission_mode": "full-control",
                    "target_class": "development-hardware",
                    "max_sessions": 1,
                    "max_memory_read_bytes": 32,
                    "max_memory_write_bytes": 8,
                    "max_snapshot_stack_bytes": 256,
                    "max_concurrent_tool_calls": 2,
                    "max_session_operations": 1,
                    "confirmation_ttl_seconds": 10,
                    "hardware_operation_allowlist": ["reset_target"],
                }
            }
        )
    )

    assert service.session_factory is not None
    assert service.resource_limits.max_sessions == 1
    assert service.resource_limits.max_memory_read_bytes == 32
    assert service.resource_limits.max_memory_write_bytes == 8
    assert service.hardware_operation_allowlist
    assert service.permission_mode == PermissionLevel.FULL_CONTROL


def test_doctor_succeeds_with_default_config() -> None:
    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "doctor: ok" in result.stdout


def test_doctor_reports_invalid_config(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.toml"
    config_path.write_text("schema_version = 999\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["doctor", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "unsupported config schema_version" in result.stdout
