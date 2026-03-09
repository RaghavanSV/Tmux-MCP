"""
Guardrails Module for Post-Exploitation MCP Server.

Validates commands before execution to prevent destructive operations
on the host machine. Every command sent through tmux send-keys or
execute_command passes through these checks first.
"""

import re
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    is_safe: bool
    reason: str


# ---------------------------------------------------------------------------
# Dangerous command patterns (regex)
# ---------------------------------------------------------------------------
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    # File destruction
    (r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|-[a-zA-Z]*r[a-zA-Z]*\s+)*\s*(/|~|\*|\.\.|/\*)",
     "Recursive/forced deletion of critical paths"),
    (r"\brm\s+--no-preserve-root", "Removing root protection on rm"),
    (r"\bshred\b", "Secure file destruction (shred)"),
    (r"\bwipefs\b", "Filesystem signature wiping"),

    # Disk / filesystem destruction
    (r"\bmkfs\b", "Filesystem creation (mkfs) can destroy data"),
    (r"\bdd\s+if=", "Raw disk copy (dd) can destroy partitions"),
    (r">\s*/dev/sd[a-z]", "Direct write to block device"),
    (r">\s*/dev/nvme", "Direct write to NVMe device"),
    (r"\bfdisk\b", "Partition table manipulation (fdisk)"),
    (r"\bparted\b", "Partition table manipulation (parted)"),
    (r"\bmkswap\b", "Swap creation can destroy data"),
    (r"\bformat\s+[a-zA-Z]:", "Windows format command"),

    # Fork bomb / resource exhaustion
    (r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;?\s*:", "Fork bomb detected"),
    (r"\bfork\s*bomb", "Fork bomb reference"),

    # System shutdown / reboot
    (r"\bshutdown\b", "System shutdown"),
    (r"\breboot\b", "System reboot"),
    (r"\bhalt\b", "System halt"),
    (r"\bpoweroff\b", "System poweroff"),
    (r"\binit\s+[06]\b", "System runlevel change (shutdown/reboot)"),
    (r"\bsystemctl\s+(poweroff|reboot|halt)", "Systemctl power management"),
    (r"\btelinit\s+[06]\b", "Telinit shutdown/reboot"),

    # Critical process killing
    (r"\bkill\s+(-9\s+)?1\b", "Killing PID 1 (init/systemd)"),
    (r"\bkillall\s+-9\s+", "Mass process killing"),
    (r"\bpkill\s+-9\s+", "Mass process killing"),

    # Permission bombs
    (r"\bchmod\s+(-R\s+)?[0-7]*777\s+/\s*$", "Recursive chmod 777 on root"),
    (r"\bchmod\s+-R\s+[0-7]*777\s+/", "Recursive chmod 777 on system paths"),
    (r"\bchown\s+-R\s+.*\s+/\s*$", "Recursive chown on root"),

    # Dangerous redirects / overwrites
    (r">\s*/etc/passwd", "Overwriting passwd file"),
    (r">\s*/etc/shadow", "Overwriting shadow file"),
    (r">\s*/etc/sudoers", "Overwriting sudoers file"),
    (r">\s*/boot/", "Overwriting boot files"),
    (r"\bcat\s+/dev/(u?random|zero)\s*>\s*/dev/sd", "Overwriting disk with random/zero data"),

    # Network destruction
    (r"\biptables\s+-F", "Flushing all iptables rules"),
    (r"\biptables\s+-X", "Deleting all iptables chains"),
    (r"\bnft\s+flush\s+ruleset", "Flushing nftables ruleset"),

    # History / log tampering on self
    (r"\bhistory\s+-c\b", "Clearing shell history"),
    (r">\s*/var/log/", "Overwriting system logs"),
    (r"\btruncate\s+.*\s+/var/log/", "Truncating system logs"),

    # Encoded / obfuscated command execution
    (r"\bbase64\s+-d\s*\|.*\bsh\b", "Base64 decoded pipe to shell"),
    (r"\bcurl\s+.*\|\s*(ba)?sh\b", "Curl pipe to shell"),
    (r"\bwget\s+.*\|\s*(ba)?sh\b", "Wget pipe to shell"),

    # Python / Perl inline destruction
    (r"python[23]?\s+-c\s+.*os\.(remove|unlink|rmdir|system.*rm)", "Python inline file deletion"),
    (r"perl\s+-e\s+.*unlink", "Perl inline file deletion"),
]

# Compiled patterns for performance
_COMPILED_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern, re.IGNORECASE), reason)
    for pattern, reason in DANGEROUS_PATTERNS
]

# ---------------------------------------------------------------------------
# Protected system paths
# ---------------------------------------------------------------------------
PROTECTED_PATHS: list[str] = [
    "/",
    "/etc",
    "/boot",
    "/usr",
    "/var",
    "/sys",
    "/proc",
    "/dev",
    "/sbin",
    "/bin",
    "/lib",
    "/lib64",
    "/root",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
]

# Operations that are dangerous when targeting protected paths
DESTRUCTIVE_OPS: list[str] = [
    "rm", "rmdir", "del", "rd", "format", "shred",
    "wipefs", "truncate", "mv", "move",
]


def _check_protected_paths(command: str) -> GuardrailResult | None:
    """Check if a destructive operation targets a protected system path."""
    cmd_lower = command.lower().strip()
    for op in DESTRUCTIVE_OPS:
        if cmd_lower.startswith(op) or f" {op} " in f" {cmd_lower} ":
            for path in PROTECTED_PATHS:
                if path.lower() in cmd_lower:
                    return GuardrailResult(
                        is_safe=False,
                        reason=f"Destructive operation '{op}' targets protected path '{path}'",
                    )
    return None


def _check_patterns(command: str) -> GuardrailResult | None:
    """Check command against all dangerous regex patterns."""
    for pattern, reason in _COMPILED_PATTERNS:
        if pattern.search(command):
            return GuardrailResult(is_safe=False, reason=reason)
    return None


def validate_command(command: str) -> GuardrailResult:
    """
    Validate a command for safety before execution.

    Args:
        command: The shell command string to validate.

    Returns:
        GuardrailResult with is_safe=True if the command is safe,
        or is_safe=False with a reason string if it is blocked.
    """
    if not command or not command.strip():
        return GuardrailResult(is_safe=True, reason="Empty command")

    # Check regex patterns first
    result = _check_patterns(command)
    if result:
        return result

    # Check protected paths
    result = _check_protected_paths(command)
    if result:
        return result

    return GuardrailResult(is_safe=True, reason="Command passed all guardrail checks")
