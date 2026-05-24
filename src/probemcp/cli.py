"""Command-line entry point for ProbeMCP."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated, Literal, cast

import typer

from probemcp.config import ProbeMCPConfig, default_config, load_config
from probemcp.mcp_server.app import create_app
from probemcp.mcp_server.factory import create_tool_service_from_config

app = typer.Typer(help="ProbeMCP embedded debugging MCP server.", no_args_is_help=True)


@app.command()
def version() -> None:
    """Print the package version."""
    from probemcp import __version__

    typer.echo(__version__)


@app.command()
def serve(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to a local ProbeMCP TOML configuration file.",
        ),
    ] = None,
    transport: Annotated[
        str,
        typer.Option(
            "--transport",
            help="MCP transport: stdio, sse, or streamable-http.",
        ),
    ] = "stdio",
) -> None:
    """Run the MCP server."""

    if transport not in {"stdio", "sse", "streamable-http"}:
        raise typer.BadParameter("transport must be stdio, sse, or streamable-http")
    loaded = _load_or_default_config(config)
    service = create_tool_service_from_config(loaded)
    create_app(service=service).run(
        transport=cast(Literal["stdio", "sse", "streamable-http"], transport)
    )


@app.command()
def doctor(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to a local ProbeMCP TOML configuration file.",
        ),
    ] = None,
) -> None:
    """Check local ProbeMCP configuration and toolchain availability."""

    problems: list[str] = []
    try:
        loaded = _load_or_default_config(config)
    except Exception as exc:
        typer.echo(f"config: failed: {exc}")
        raise typer.Exit(1) from exc

    typer.echo(f"config: ok schema_version={loaded.schema_version}")
    selected_targets = loaded.targets
    if not selected_targets:
        typer.echo("targets: none configured")
    for name, target in selected_targets.items():
        typer.echo(f"target {name}: backend={target.backend.value} endpoint={target.endpoint}")
        if shutil.which(target.gdb_path) is None:
            problems.append(f"target {name}: gdb executable not found: {target.gdb_path}")

    if loaded.server.audit_log_path is not None:
        audit_parent = Path(loaded.server.audit_log_path).expanduser().parent
        if audit_parent.exists() and not audit_parent.is_dir():
            problems.append(f"audit path parent is not a directory: {audit_parent}")
        else:
            typer.echo(f"audit: ok path={loaded.server.audit_log_path}")

    if problems:
        for problem in problems:
            typer.echo(f"failed: {problem}")
        raise typer.Exit(1)

    typer.echo("doctor: ok")


def main() -> None:
    """Run the ProbeMCP CLI."""
    app()


def _load_or_default_config(config_path: Path | None) -> ProbeMCPConfig:
    if config_path is None:
        return default_config()
    return load_config(config_path)
