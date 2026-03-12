"""
Post-Exploitation MCP Server — tmux Terminal Emulator

A FastMCP server that exposes essential tmux features as MCP tools with
command-execution guardrails to prevent destructive operations.
All tool() handlers are async for non-blocking subprocess execution.
"""

from fastmcp import FastMCP
import tmux_wrapper as tmux

mcp = FastMCP(
    "post-exploitation-tmux",
    instructions=(
        "Post-exploitation tmux terminal emulator. "
        "Provides session, window, and pane management plus guarded "
        "command execution. Destructive commands are auto-blocked. "
        "All operations are async and non-blocking."
    ),
)


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@mcp.tool()
async def create_session(name: str, window_name: str | None = None) -> dict:
    """
    Create a new detached tmux session.

    Args:
        name: Name for the new session.
        window_name: Optional name for the initial window.
    """
    r = await tmux.create_session(name, window_name)
    return {"success": r.success, "data": r.data, "error": r.error}


@mcp.tool()
async def list_sessions() -> dict:
    """List all active tmux sessions."""
    r = await tmux.list_sessions()
    if r.success and r.data:
        sessions = []
        for line in r.data.splitlines():
            parts = line.split("|")
            if len(parts) >= 5:
                sessions.append({
                    "id": parts[0], "name": parts[1], "windows": parts[2],
                    "created": parts[3], "attached": parts[4],
                })
        return {"success": True, "sessions": sessions}
    return {"success": r.success, "sessions": [], "error": r.error}


@mcp.tool()
async def kill_session(name: str) -> dict:
    """Kill (destroy) a tmux session and all its windows/panes."""
    r = await tmux.kill_session(name)
    return {"success": r.success, "data": r.data, "error": r.error}


# ============================================================================
# WINDOW MANAGEMENT
# ============================================================================

@mcp.tool()
async def create_window(session: str, name: str | None = None) -> dict:
    """Create a new window in a tmux session."""
    r = await tmux.create_window(session, name)
    return {"success": r.success, "data": r.data, "error": r.error}


@mcp.tool()
async def list_windows(session: str) -> dict:
    """List all windows in a tmux session."""
    r = await tmux.list_windows(session)
    if r.success and r.data:
        windows = []
        for line in r.data.splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                windows.append({
                    "index": parts[0], "name": parts[1],
                    "active": parts[2], "panes": parts[3],
                })
        return {"success": True, "windows": windows}
    return {"success": r.success, "windows": [], "error": r.error}


@mcp.tool()
async def kill_window(session: str, index: int) -> dict:
    """Kill a window and all its panes."""
    r = await tmux.kill_window(session, index)
    return {"success": r.success, "data": r.data, "error": r.error}


# ============================================================================
# PANE MANAGEMENT
# ============================================================================

@mcp.tool()
async def split_pane(session: str, window: int, direction: str = "vertical") -> dict:
    """
    Split the current pane in a window.

    Args:
        session: Session name.
        window: Window index.
        direction: 'vertical' (left/right) or 'horizontal' (top/bottom).
    """
    r = await tmux.split_pane(session, window, direction)
    return {"success": r.success, "data": r.data, "error": r.error}


@mcp.tool()
async def list_panes(session: str, window: int) -> dict:
    """List all panes in a window with index, active status, command, and PID."""
    r = await tmux.list_panes(session, window)
    if r.success and r.data:
        panes = []
        for line in r.data.splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                panes.append({
                    "index": parts[0], "active": parts[1],
                    "command": parts[2], "pid": parts[3],
                })
        return {"success": True, "panes": panes}
    return {"success": r.success, "panes": [], "error": r.error}


@mcp.tool()
async def kill_pane(session: str, window: int, pane: int) -> dict:
    """Kill a specific pane."""
    r = await tmux.kill_pane(session, window, pane)
    return {"success": r.success, "data": r.data, "error": r.error}


# ============================================================================
# COMMAND EXECUTION (GUARDED)
# ============================================================================

@mcp.tool()
async def execute_command(session: str, window: int, pane: int, command: str) -> dict:
    """
    Execute a shell command in a tmux pane (guardrail-checked).

    Destructive commands (rm -rf, mkfs, fork bombs, shutdown, etc.)
    are automatically blocked.
    """
    r = await tmux.execute_command(session, window, pane, command)
    return {"success": r.success, "data": r.data, "error": r.error}


@mcp.tool()
async def send_keys(session: str, window: int, pane: int, keys: str, press_enter: bool = True) -> dict:
    """
    Send keystrokes to a tmux pane (guardrail-checked if press_enter=True).

    Args:
        keys: Keys/text to send (e.g. 'ls -la', 'C-c' for Ctrl+C).
        press_enter: Whether to press Enter after sending (default True).
    """
    r = await tmux.send_keys(session, window, pane, keys, press_enter)
    return {"success": r.success, "data": r.data, "error": r.error}


@mcp.tool()
async def capture_pane(
    session: str, window: int, pane: int,
    start_line: int | None = None, end_line: int | None = None,
) -> dict:
    """
    Capture and return the visible text content of a tmux pane.
    Trailing blank lines are stripped for cleaner output.
    """
    r = await tmux.capture_pane(session, window, pane, start_line, end_line)
    return {"success": r.success, "output": r.data, "error": r.error}


# ============================================================================
# UTILITY
# ============================================================================

@mcp.tool()
async def validate_command_safety(command: str) -> dict:
    """
    Check if a command would pass the guardrail safety check WITHOUT executing it.
    Useful for pre-validating commands.
    """
    from guardrails import validate_command as _validate
    result = _validate(command)
    return {"is_safe": result.is_safe, "reason": result.reason}


@mcp.tool()
async def kill_server() -> dict:
    """Kill the tmux server (destroys ALL sessions). Use with caution."""
    r = await tmux.kill_server()
    return {"success": r.success, "data": r.data, "error": r.error}


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    mcp.run()
