"""
tmux Wrapper Module for Post-Exploitation MCP Server.

Provides a thin async Python wrapper around tmux CLI commands.
All functions use asyncio.create_subprocess_exec for non-blocking I/O.
Command execution functions integrate with the guardrails module.
"""

import asyncio
from dataclasses import dataclass
from guardrails import validate_command
import re

#To wait untill the command gets finished.
PROMPT_RE = re.compile(r'(\$|#|>)\s*$', re.MULTILINE)


@dataclass
class TmuxResult:
    """Structured result from a tmux operation."""
    success: bool
    data: str = ""
    error: str = ""


async def _run_tmux(*args: str, capture: bool = True) -> TmuxResult:
    """Execute a tmux command asynchronously and return a structured result."""
    cmd = ["tmux"] + list(args)
    try:
        if capture:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return TmuxResult(success=True, data=stdout.decode().strip())
            else:
                return TmuxResult(
                    success=False,
                    error=stderr.decode().strip() or f"tmux exited with code {process.returncode}",
                )
        else:
            process = await asyncio.create_subprocess_exec(*cmd)
            await process.wait()
            if process.returncode == 0:
                return TmuxResult(success=True)
            else:
                return TmuxResult(
                    success=False,
                    error=f"tmux exited with code {process.returncode}",
                )
    except FileNotFoundError:
        return TmuxResult(success=False, error="tmux is not installed or not in PATH")
    except Exception as e:
        return TmuxResult(success=False, error=str(e))


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

async def create_session(name: str, window_name: str | None = None) -> TmuxResult:
    """Create a new tmux session (detached)."""
    args = ["new-session", "-d", "-s", name]
    if window_name:
        args.extend(["-n", window_name])
    return await _run_tmux(*args)


async def list_sessions() -> TmuxResult:
    """List all tmux sessions with details."""
    return await _run_tmux(
        "list-sessions",
        "-F", "#{session_id}|#{session_name}|#{session_windows}|#{session_created}|#{session_attached}",
    )


async def kill_session(name: str) -> TmuxResult:
    """Kill (destroy) a tmux session."""
    return await _run_tmux("kill-session", "-t", name)


# ============================================================================
# WINDOW MANAGEMENT
# ============================================================================

async def create_window(session: str, name: str | None = None) -> TmuxResult:
    """Create a new window in a session."""
    args = ["new-window", "-t", session]
    if name:
        args.extend(["-n", name])
    return await _run_tmux(*args)


async def list_windows(session: str) -> TmuxResult:
    """List all windows in a session with details."""
    return await _run_tmux(
        "list-windows",
        "-t", session,
        "-F", "#{window_index}|#{window_name}|#{window_active}|#{window_panes}",
    )


async def kill_window(session: str, index: int) -> TmuxResult:
    """Kill a window."""
    return await _run_tmux("kill-window", "-t", f"{session}:{index}")


# ============================================================================
# PANE MANAGEMENT
# ============================================================================

async def split_pane(session: str, window: int, direction: str = "vertical") -> TmuxResult:
    """
    Split a pane in the specified window.

    Args:
        session: Session name.
        window: Window index.
        direction: 'vertical' (left/right) or 'horizontal' (top/bottom).
    """
    flag = "-v" if direction == "horizontal" else "-h"
    return await _run_tmux("split-window", flag, "-t", f"{session}:{window}")


async def list_panes(session: str, window: int) -> TmuxResult:
    """List all panes in a window with details."""
    return await _run_tmux(
        "list-panes",
        "-t", f"{session}:{window}",
        "-F", "#{pane_index}|#{pane_active}|#{pane_current_command}|#{pane_pid}",
    )


async def kill_pane(session: str, window: int, pane: int) -> TmuxResult:
    """Kill a pane."""
    return await _run_tmux("kill-pane", "-t", f"{session}:{window}.{pane}")


# ============================================================================
# COMMAND EXECUTION (with guardrails)
# ============================================================================

async def send_keys(
    session: str, window: int, pane: int,
    keys: str, press_enter: bool = True,
    timeout: float = 30.0, stable_delay: float = 2.0,
) -> TmuxResult:
    """
    Send keystrokes to a pane. If press_enter is True:
     - guardrail check is applied first
     - waits for pane output to stabilize before returning
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

    # Capture baseline BEFORE sending
    baseline_r = await _run_tmux("capture-pane", "-t", target, "-p")
    baseline = baseline_r.data if baseline_r.success else ""

    # Fire the keystrokes — this returns as soon as tmux daemon ACKs
    send_r = await _run_tmux(*args)
    if not send_r.success or not press_enter:
        # No-enter sends (e.g. Ctrl+C) don't need to wait for output
        return send_r

    # Poll until output stabilizes (command finished) or timeout
    return await _wait_for_output(target, baseline, timeout, stable_delay)

async def execute_command(
    session: str, window: int, pane: int, command: str,
    timeout: float = 30.0, stable_delay: float = 2.0,
) -> TmuxResult:
    """
    Execute a command in a pane with guardrail validation.
    Waits for command output to stabilize before returning.
    """
    check = validate_command(command)
    if not check.is_safe:
        return TmuxResult(
            success=False,
            error=f"GUARDRAIL BLOCKED: {check.reason}",
        )

    target = f"{session}:{window}.{pane}"

    # Capture baseline BEFORE sending
    baseline_r = await _run_tmux("capture-pane", "-t", target, "-p")
    baseline = baseline_r.data if baseline_r.success else ""

    # Fire the command — returns when tmux ACKs, NOT when command finishes
    send_r = await _run_tmux("send-keys", "-t", target, command, "Enter")
    if not send_r.success:
        return send_r

    # Poll until output stabilizes
    return await _wait_for_output(target, baseline, timeout, stable_delay)


async def _wait_for_output(
    target: str,
    baseline: str,
    timeout: float = 30.0,
    poll_interval: float = 0.5,
) -> TmuxResult:
    """
    Poll `capture-pane` until a shell prompt reappears in the pane,
    indicating the command has finished executing.
    """
    elapsed = 0.0
    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
        cap = await _run_tmux("capture-pane", "-t", target, "-p")
        current = cap.data if cap.success else ""

        # Wait until output has changed from baseline first
        if current == baseline:
            continue

        # Then check if a prompt line has appeared — command is done
        if PROMPT_RE.search(current):
            return TmuxResult(
                success=True,
                data=_new_output(baseline, current),
            )

    # Timeout — return whatever we have
    cap = await _run_tmux("capture-pane", "-t", target, "-p")
    current = cap.data if cap.success else ""
    return TmuxResult(
        success=True,
        data=_new_output(baseline, current) or current,
        error=f"Timed out after {timeout}s — output may be incomplete",
    )


def _new_output(baseline: str, current: str) -> str:
    """Return only the lines in `current` that are new vs `baseline`."""
    b_lines = baseline.rstrip("\n").split("\n") if baseline.strip() else []
    c_lines = current.rstrip("\n").split("\n") if current.strip() else []
    i = 0
    while i < len(b_lines) and i < len(c_lines) and b_lines[i] == c_lines[i]:
        i += 1
    new = c_lines[i:]
    while new and not new[-1].strip():
        new.pop()
    return "\n".join(new)


async def capture_pane(
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
    result = await _run_tmux(*args)
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

async def kill_server() -> TmuxResult:
    """Kill the tmux server (destroys all sessions)."""
    return await _run_tmux("kill-server")
