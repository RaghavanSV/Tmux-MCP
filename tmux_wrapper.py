"""
tmux Wrapper Module for Post-Exploitation MCP Server.

Provides a thin Python wrapper around tmux CLI commands.
All functions call subprocess and return structured results.
Command execution functions integrate with the guardrails module.
"""

import subprocess
from dataclasses import dataclass

from guardrails import validate_command


@dataclass
class TmuxResult:
    """Structured result from a tmux operation."""
    success: bool
    data: str = ""
    error: str = ""


def _run_tmux(*args: str, capture: bool = True) -> TmuxResult:
    """Execute a tmux command and return a structured result."""
    cmd = ["tmux"] + list(args)
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return TmuxResult(success=True, data=result.stdout.strip())
        else:
            return TmuxResult(
                success=False,
                error=result.stderr.strip() or f"tmux exited with code {result.returncode}",
            )
    except FileNotFoundError:
        return TmuxResult(success=False, error="tmux is not installed or not in PATH")
    except subprocess.TimeoutExpired:
        return TmuxResult(success=False, error="tmux command timed out after 30s")
    except Exception as e:
        return TmuxResult(success=False, error=str(e))


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def create_session(name: str, window_name: str | None = None) -> TmuxResult:
    """Create a new tmux session (detached)."""
    args = ["new-session", "-d", "-s", name]
    if window_name:
        args.extend(["-n", window_name])
    return _run_tmux(*args)


def list_sessions() -> TmuxResult:
    """List all tmux sessions with details."""
    return _run_tmux(
        "list-sessions",
        "-F", "#{session_id}|#{session_name}|#{session_windows}|#{session_created}|#{session_attached}",
    )


def kill_session(name: str) -> TmuxResult:
    """Kill (destroy) a tmux session."""
    return _run_tmux("kill-session", "-t", name)


# ============================================================================
# WINDOW MANAGEMENT
# ============================================================================

def create_window(session: str, name: str | None = None) -> TmuxResult:
    """Create a new window in a session."""
    args = ["new-window", "-t", session]
    if name:
        args.extend(["-n", name])
    return _run_tmux(*args)


def list_windows(session: str) -> TmuxResult:
    """List all windows in a session with details."""
    return _run_tmux(
        "list-windows",
        "-t", session,
        "-F", "#{window_index}|#{window_name}|#{window_active}|#{window_panes}",
    )


def kill_window(session: str, index: int) -> TmuxResult:
    """Kill a window."""
    return _run_tmux("kill-window", "-t", f"{session}:{index}")


# ============================================================================
# PANE MANAGEMENT
# ============================================================================

def split_pane(session: str, window: int, direction: str = "vertical") -> TmuxResult:
    """
    Split a pane in the specified window.

    Args:
        session: Session name.
        window: Window index.
        direction: 'vertical' (left/right) or 'horizontal' (top/bottom).
    """
    flag = "-v" if direction == "horizontal" else "-h"
    return _run_tmux("split-window", flag, "-t", f"{session}:{window}")


def list_panes(session: str, window: int) -> TmuxResult:
    """List all panes in a window with details."""
    return _run_tmux(
        "list-panes",
        "-t", f"{session}:{window}",
        "-F", "#{pane_index}|#{pane_active}|#{pane_current_command}|#{pane_pid}",
    )


def kill_pane(session: str, window: int, pane: int) -> TmuxResult:
    """Kill a pane."""
    return _run_tmux("kill-pane", "-t", f"{session}:{window}.{pane}")


# ============================================================================
# COMMAND EXECUTION (with guardrails)
# ============================================================================

def send_keys(
    session: str, window: int, pane: int,
    keys: str, press_enter: bool = True,
) -> TmuxResult:
    """
    Send keystrokes to a pane. If press_enter is True, the guardrail
    check is applied first.
    """
    if press_enter:
        check = validate_command(keys)
        if not check.is_safe:
            return TmuxResult(
                success=False,
                error=f"GUARDRAIL BLOCKED: {check.reason}",
            )

    target = f"{session}:{window}.{pane}"
    args = ["send-keys", "-t", target, keys]
    if press_enter:
        args.append("Enter")
    return _run_tmux(*args)


def execute_command(session: str, window: int, pane: int, command: str) -> TmuxResult:
    """
    Execute a command in a pane (send-keys + Enter) with guardrail validation.
    """
    check = validate_command(command)
    if not check.is_safe:
        return TmuxResult(
            success=False,
            error=f"GUARDRAIL BLOCKED: {check.reason}",
        )

    target = f"{session}:{window}.{pane}"
    return _run_tmux("send-keys", "-t", target, command, "Enter")


def capture_pane(
    session: str, window: int, pane: int,
    start_line: int | None = None, end_line: int | None = None,
) -> TmuxResult:
    """
    Capture the visible contents of a pane.

    Args:
        start_line: Start line (negative = scrollback). Default: visible top.
        end_line: End line. Default: visible bottom.
    """
    args = ["capture-pane", "-t", f"{session}:{window}.{pane}", "-p"]
    if start_line is not None:
        args.extend(["-S", str(start_line)])
    if end_line is not None:
        args.extend(["-E", str(end_line)])
    result = _run_tmux(*args)
    # Strip trailing blank lines for cleaner output
    if result.success and result.data:
        lines = result.data.rstrip("\n").split("\n")
        while lines and not lines[-1].strip():
            lines.pop()
        result.data = "\n".join(lines)
    return result


# ============================================================================
# SERVER
# ============================================================================

def kill_server() -> TmuxResult:
    """Kill the tmux server (destroys all sessions)."""
    return _run_tmux("kill-server")
