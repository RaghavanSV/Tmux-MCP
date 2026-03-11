<p align="center">
  <h1 align="center">Tmux-MCP</h1>
  <h4 align="center">MCP server exposing tmux as AI-agent tools with built-in safety guardrails</h4>
</p>

<p align="center">

  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/license-MIT-_red.svg">
  </a>

  <a href="https://github.com/Raghavan/Post-Exploitation-tmux-MCP">
    <img src="https://img.shields.io/badge/maintained%3F-yes-brightgreen.svg">
  </a>

  <a href="https://github.com/Raghavan/Post-Exploitation-tmux-MCP/issues">
    <img src="https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat">
  </a>

</p>

<p align="center">
  <a href="#introduction">Introduction</a> •
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#tool-reference">Tool Reference</a> •
  <a href="#testing">Testing</a> •
  <a href="#disclaimer">Disclaimer</a>
</p>

# Introduction

Post-Exploitation tmux MCP is a **Model Context Protocol** server that exposes essential [tmux](https://github.com/tmux/tmux) features as MCP tools — giving AI agents a fully-featured terminal multiplexer for post-exploitation operations. Every command is validated through **built-in guardrails** that block destructive system commands before they execute. Built with [FastMCP](https://github.com/jlowin/fastmcp), it lets any MCP-compatible client (AI agents, automation frameworks, etc.) create sessions, spawn windows, split panes, and run commands — all while preventing accidental or malicious system damage.

# Features

This server exposes **14 tools** across the following categories:

- Session management:
  - Create detached sessions
  - List all active sessions
  - Kill specific sessions

- Window management:
  - Create new windows in a session
  - List windows in a session
  - Kill specific windows

- Pane management:
  - Split panes vertically or horizontally
  - List panes with running command & PID info
  - Kill specific panes

- Command execution (all guarded):
  - `execute_command` — run a command with guardrail validation
  - `send_keys` — send keystrokes to a pane (guarded when Enter is pressed)
  - `capture_pane` — read pane output with trailing blanks stripped

- Utility:
  - `validate_command_safety` — pre-check a command without executing
  - `kill_server` — kill the entire tmux server

- Built-in guardrails that block:
  - File destruction — `rm -rf /`, `shred`, `wipefs`
  - Disk operations — `mkfs`, `dd if=`, `fdisk`, `parted`
  - Fork bombs — `:(){ :|:& };:`
  - System shutdown — `shutdown`, `reboot`, `halt`, `init 0/6`
  - Critical process killing — `kill -9 1`, `killall -9`
  - Permission bombs — `chmod -R 777 /`
  - Dangerous redirects — `> /etc/passwd`, `> /etc/shadow`
  - Network destruction — `iptables -F`
  - Log tampering — `> /var/log/`, `history -c`
  - Obfuscated execution — `curl ... | sh`, `base64 -d | sh`

# Installation

Just clone the repository and install the dependencies:

```sh
git clone https://github.com/RaghavanSV/Tmux-MCP.git
cd 'Tmux-MCP'
pip install -r requirements.txt
```

> **Prerequisite**: tmux must be installed on the target machine.

# Usage

> Run the MCP server
```sh
python server.py
```

> Test with the interactive client
```sh
python client.py
```

The client connects to `server.py` via stdio, lists available tools, and gives you an interactive REPL to call them.

> Connect from an MCP client (e.g. AI agent)
```json
{
  "mcpServers": {
    "post-exploitation-tmux": {
      "command": "python3",
      "args": ["path/to/Tmux-MCP/server.py"]
    }
  }
}
```

> Generate a session, create a window, and run a guarded command
```sh
# Using the interactive client
> create_session("pentest", "recon")
> execute_command("pentest", "recon", "0", "nmap -sV 192.168.1.1")
> capture_pane("pentest", "recon", "0")
```

# Tool Reference

### Sessions

| Tool | Description |
|---|---|
| `create_session(name, window_name?)` | Create a new detached session |
| `list_sessions()` | List all sessions |
| `kill_session(name)` | Destroy a session |

### Windows

| Tool | Description |
|---|---|
| `create_window(session, name?)` | Create a new window |
| `list_windows(session)` | List windows |
| `kill_window(session, index)` | Kill a window |

### Panes

| Tool | Description |
|---|---|
| `split_pane(session, window, direction?)` | Split pane vertically/horizontally |
| `list_panes(session, window)` | List panes with command & PID |
| `kill_pane(session, window, pane)` | Kill a pane |

### Command Execution (Guarded)

| Tool | Description |
|---|---|
| `execute_command(session, window, pane, command)` | Run a command (guardrail-checked) |
| `send_keys(session, window, pane, keys, press_enter?)` | Send keystrokes (guarded if Enter) |
| `capture_pane(session, window, pane, start?, end?)` | Read pane output (trailing blanks stripped) |

### Utility

| Tool | Description |
|---|---|
| `validate_command_safety(command)` | Pre-check a command without executing |
| `kill_server()` | Kill the tmux server (destroys all sessions) |

# Project Structure

```
Post-Exploitation/
├── server.py            # FastMCP server — 14 tools
├── tmux_wrapper.py      # Thin Python wrapper around tmux CLI
├── guardrails.py        # Command validation & safety checks
├── client.py            # Interactive MCP test client
├── test_guardrails.py   # Guardrails unit tests
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

# Testing

> Run guardrail tests
```sh
python test_guardrails.py
```

> Test MCP tools interactively
```sh
python client.py
```

# References

```
https://github.com/tmux/tmux
https://github.com/jlowin/fastmcp
https://modelcontextprotocol.io
https://github.com/tmux-python/libtmux
```

# Disclaimer

Use this project under your own responsibility! This tool is intended for **authorized penetration testing and security research only**. Unauthorized use against systems you do not own or have explicit permission to test is illegal. The author is not responsible for any misuse of this project.

# License

This project is under [MIT](https://opensource.org/licenses/MIT) license

Copyright © 2025, *RaghavanSV*
