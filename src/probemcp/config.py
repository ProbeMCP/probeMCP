"""Local ProbeMCP configuration models and loader."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator

from probemcp.mcp_server.schemas import BackendKind, PermissionLevel, SchemaModel
from probemcp.safety.policy import DebugOperation, TargetClass

CONFIG_SCHEMA_VERSION = 1


class ServerConfig(SchemaModel):
    """Local MCP server defaults."""

    permission_mode: PermissionLevel = PermissionLevel.READONLY
    target_class: TargetClass = TargetClass.UNKNOWN
    audit_log_path: str | None = None
    max_sessions: int = Field(default=4, ge=1, le=64)
    max_memory_read_bytes: int = Field(default=4096, ge=1, le=1_048_576)
    max_memory_write_bytes: int = Field(default=256, ge=1, le=65_536)
    max_snapshot_stack_bytes: int = Field(default=4096, ge=0, le=65_536)
    max_concurrent_tool_calls: int = Field(default=8, ge=1, le=128)
    max_session_operations: int = Field(default=1, ge=1, le=16)
    max_mi_command_queue: int = Field(default=32, ge=1, le=1024)
    confirmation_ttl_seconds: int = Field(default=300, ge=1, le=86_400)
    memory_write_enabled: bool = False
    hardware_operation_allowlist: list[DebugOperation] = Field(default_factory=list)


class TargetProfile(SchemaModel):
    """Named debugger target profile."""

    backend: BackendKind
    endpoint: str | None = None
    gdb_path: str = Field(default="arm-none-eabi-gdb", min_length=1)
    elf_path: str | None = None
    profile: str = Field(default="cortex-m", min_length=1)
    target_class: TargetClass | None = None
    timeout_ms: int = Field(default=30_000, ge=1, le=120_000)
    memory_write_enabled: bool | None = None

    @model_validator(mode="after")
    def require_endpoint_for_attach_backends(self) -> Self:
        """Attach-style backends need an explicit endpoint."""

        if self.backend in {
            BackendKind.GENERIC_REMOTE,
            BackendKind.QEMU,
            BackendKind.OPENOCD,
            BackendKind.JLINK,
            BackendKind.PYOCD,
        } and not self.endpoint:
            raise ValueError(f"{self.backend.value} target profile requires endpoint")
        return self


class ProbeMCPConfig(SchemaModel):
    """Versioned local configuration root."""

    schema_version: int = CONFIG_SCHEMA_VERSION
    default_target: str | None = None
    server: ServerConfig = Field(default_factory=ServerConfig)
    targets: dict[str, TargetProfile] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_default_target(self) -> Self:
        """Ensure the selected default target exists."""

        if self.schema_version != CONFIG_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported config schema_version {self.schema_version}; "
                f"expected {CONFIG_SCHEMA_VERSION}"
            )
        if self.default_target is not None and self.default_target not in self.targets:
            raise ValueError(f"default_target not found: {self.default_target}")
        return self

    def get_target(self, name: str | None = None) -> TargetProfile:
        """Return a named or default target profile."""

        target_name = name or self.default_target
        if target_name is None:
            raise KeyError("no target profile selected")
        try:
            return self.targets[target_name]
        except KeyError as exc:
            raise KeyError(f"target profile not found: {target_name}") from exc


def load_config(path: Path) -> ProbeMCPConfig:
    """Load a ProbeMCP TOML config file."""

    with path.open("rb") as config_file:
        data = tomllib.load(config_file)
    return ProbeMCPConfig.model_validate(data)


def default_config() -> ProbeMCPConfig:
    """Return a safe default config."""

    return ProbeMCPConfig()
