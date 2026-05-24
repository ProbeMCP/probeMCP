# GitHub Triage Workflow

Use milestones to keep the backlog readable:

- `v0.1`: local MCP server, safe tools, QEMU demo, Cortex-M fault analysis
- `v0.2`: stronger analyzers, SVD tooling, client compatibility
- `future`: RTOS, multi-board, commercial/open-core work
- `research`: vendor backend investigations

Recommended labels:

- `type:bug`
- `type:feature`
- `type:research`
- `area:mcp`
- `area:backend`
- `area:safety`
- `area:analyzer`
- `area:docs`
- `area:tests`
- `needs-triage`
- `needs-hardware`
- `needs-transcript`
- `good-first-issue`

The canonical label definitions live in `.github/labels.yml`. Issue templates
reference these labels directly so new backlog items start in a sortable state.

Hardware-dependent issues should stay open until there is validation evidence:
device, backend version, GDB version, host OS, exact operation list, and
sanitized transcript or logs.
