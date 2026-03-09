# 🖥️ Post-Exploitation tmux MCP Server

A **MCP** server that exposes essential [tmux](https://github.com/tmux/tmux) features as MCP tools — giving AI agents a terminal multiplexer for post-exploitation operations, with **built-in guardrails** that block destructive commands.

---

## ✨ Tools (14)

| Category | Tools | Description |
|---|---|---|
| **Sessions** | 3 | Create, list, kill |
| **Windows** | 3 | Create, list, kill |
| **Panes** | 3 | Split, list, kill |
| **Command Execution** | 3 | `execute_command`, `send_keys`, `capture_pane` — all guarded |
| **Utility** | 2 | `validate_command_safety`, `kill_server` |

---

## 🛡️ Guardrails

Every command sent through `execute_command` or `send_keys` is validated before execution. The guardrails block:

- **File destruction** — `rm -rf /`, `shred`, `wipefs`
- **Disk operations** — `mkfs`, `dd if=`, `fdisk`, `parted`
- **Fork bombs** — `:(){ :|:& };:`
- **System shutdown** — `shutdown`, `reboot`, `halt`, `init 0/6`
- **Critical process killing** — `kill -9 1`, `killall -9`
- **Permission bombs** — `chmod -R 777 /`
- **Dangerous redirects** — `> /etc/passwd`, `> /etc/shadow`
- **Network destruction** — `iptables -F`
- **Log tampering** — `> /var/log/`, `history -c`
- **Obfuscated execution** — `curl ... | sh`, `base64 -d | sh`

---

## 📦 Installation

```bash
cd Post-Exploitation
pip install -r requirements.txt
```

> **Prerequisite**: tmux must be installed on the target machine.

---

## 🚀 Usage

### Run the MCP server

```bash
python server.py
```

### Test with the interactive client

```bash
python client.py
```

The client connects to `server.py` via stdio, lists available tools, and gives you an interactive REPL to call them.

### Connect from an MCP client (e.g. AI agent)

```json
{
  "mcpServers": {
    "post-exploitation-tmux": {
      "command": "python3",
      "args": ["path/to/Post-Exploitation/server.py"]
    }
  }
}
```

---

## 🔧 Tool Reference

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

---

## 📂 Project Structure

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

---

## 🧪 Testing

### Run guardrail tests

```bash
python test_guardrails.py
```

### Test MCP tools interactively

```bash
python client.py
```

---

## ⚠️ Disclaimer

This tool is intended for **authorized penetration testing and security research only**. Unauthorized use against systems you do not own or have explicit permission to test is illegal.
