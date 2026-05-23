"""Command-line entry point for early ProbeMCP development."""

from __future__ import annotations

import typer

app = typer.Typer(help="ProbeMCP embedded debugging MCP server.")


@app.command()
def version() -> None:
    """Print the package version."""
    from probemcp import __version__

    typer.echo(__version__)


def main() -> None:
    """Run the ProbeMCP CLI."""
    app()
