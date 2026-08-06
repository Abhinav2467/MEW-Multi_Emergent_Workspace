# MCP Removal Backup

This file documents the exact MCP-specific code and configuration that was removed from the standalone branch.

## Files changed

### `agent.py`
- Removed `from mcp.server.fastmcp import FastMCP`
- Removed `mcp = FastMCP("Aura-Email-Agent")`
- Removed all `@mcp.tool()` decorators from the following functions:
  - `get_registration_link`
  - `finalize_user_token`
  - `find_leads`
  - `send_outreach`
- Replaced the MCP runtime entrypoint:
  - removed `mcp.run()` and the associated `if __name__ == "__main__":` block
- Added a standalone CLI entrypoint with `python agent.py demo`
- Preserved all business logic inside the existing functions.

### `requirements.txt`
- Removed `mcp>=1.2.0`

### `readme.md`
- Replaced MCP and orchestrator-specific service explanation with standalone usage instructions.
- Removed the stdio/JSON-RPC integration section.
- Added direct function import guidance and `python agent.py demo` instructions.

## Restore notes

To restore MCP later:
1. Re-add `from mcp.server.fastmcp import FastMCP` to `agent.py`.
2. Recreate `mcp = FastMCP("Aura-Email-Agent")`.
3. Re-apply `@mcp.tool()` decorators to the four public functions.
4. Replace the standalone CLI block with `if __name__ == "__main__": mcp.run()`.
5. Restore `mcp>=1.2.0` to `requirements.txt`.
6. Reintroduce MCP/orchestrator documentation in `readme.md`.
