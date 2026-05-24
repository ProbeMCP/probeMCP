"""Debug session factory for real GDB/MI sessions."""

from __future__ import annotations

from probemcp.backends.factory import create_backend
from probemcp.debug.session import DebugSession
from probemcp.mcp_server.schemas import ConnectTargetRequest
from probemcp.mi.controller import MIController, SubprocessMITransport


async def create_gdb_debug_session(request: ConnectTargetRequest) -> DebugSession:
    """Create a debug session backed by a spawned GDB/MI subprocess."""

    transport = await SubprocessMITransport.spawn_gdb(
        gdb_path=request.gdb_path,
        elf_path=request.elf_path,
    )
    return DebugSession(
        controller=MIController(transport),
        backend=create_backend(request.backend),
    )
