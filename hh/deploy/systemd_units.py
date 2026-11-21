"""
systemd boot units for Henhouse daemons.

Deploy starts the Flask daemons and the maintenance daemon itself (sudo -u <tier user> nohup ...).
Nothing brought them back after a reboot, so each daemon module also writes a small oneshot unit
that runs its existing `hen.py <module>-start` command at boot.  Reusing the start command keeps
one code path for starting daemons: deploy, a manual `flask-start` and a boot all do the same thing.

The units are `Type=oneshot` with `RemainAfterExit=yes`: the start command forks the daemons and
exits, the daemons stay in the unit's cgroup, and `systemctl stop` runs the matching stop command.

Deploy only enables the units; it does not start them, because the daemons were just started by
the deploy itself and the start commands restart running daemons.

Without systemd (containers, the sandbox) the unit file is still written when /etc/systemd/system
exists, and enabling is skipped with status "systemd_not_running".
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda arg=None: arg
log = lambda message: None
warn = lambda message: None


@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    warn = get_warn(True)


SYSTEMD_UNIT_DIR = Path("/etc/systemd/system")

# Ordering only: After= on a unit that does not exist is ignored by systemd.
DEFAULT_AFTER = ["network-online.target", "mysql.service", "mariadb.service"]


def systemd_running() -> bool:
    """True when systemd is PID 1 and systemctl is available."""
    return Path("/run/systemd/system").is_dir() and shutil.which("systemctl") is not None


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", *args], capture_output=True, text=True, check=False)


def daemon_unit_name(project_name: str, daemon: str) -> str:
    return f"{project_name}-{daemon}.service"


def build_daemon_unit(description: str, project_root: Path, start_command: str, stop_command: str,
                      after: Optional[List[str]] = None, python: Optional[str] = None) -> str:
    """Render a oneshot unit that runs `hen.py <start_command>` from the project checkout."""
    python = python or sys.executable or "/usr/bin/python3"
    hen = project_root / "hen.py"
    after_units = " ".join(after if after is not None else DEFAULT_AFTER)
    return "\n".join([
        "# Written by Henhouse deploy. Edits are overwritten on the next deploy.",
        "[Unit]",
        f"Description={description}",
        "Wants=network-online.target",
        f"After={after_units}",
        "",
        "[Service]",
        "Type=oneshot",
        "RemainAfterExit=yes",
        f"WorkingDirectory={project_root}",
        f"ExecStart={python} {hen} {start_command}",
        f"ExecStop={python} {hen} {stop_command}",
        "TimeoutStartSec=300",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ])


def install_daemon_unit(project_name: str, daemon: str, description: str, project_root: Path,
                        start_command: str, stop_command: str,
                        after: Optional[List[str]] = None) -> Dict[str, Any]:
    """Write /etc/systemd/system/<project>-<daemon>.service and enable it (without starting it)."""
    trace_in()
    unit = daemon_unit_name(project_name, daemon)
    result: Dict[str, Any] = {"unit": unit, "written": False, "enabled": False}
    try:
        if not SYSTEMD_UNIT_DIR.is_dir():
            result["status"] = "no_systemd"
            log(f"{SYSTEMD_UNIT_DIR} not found; skipping boot unit {unit}")
            return trace_out(result)

        unit_path = SYSTEMD_UNIT_DIR / unit
        content = build_daemon_unit(description, project_root, start_command, stop_command, after)
        changed = not unit_path.exists() or unit_path.read_text() != content
        if changed:
            unit_path.write_text(content)
            unit_path.chmod(0o644)
        result["written"] = True
        result["path"] = str(unit_path)

        if not systemd_running():
            result["status"] = "systemd_not_running"
            log(f"Wrote {unit_path}; systemd is not running so it was not enabled")
            return trace_out(result)

        if changed:
            _systemctl("daemon-reload")
        enable = _systemctl("enable", unit)
        if enable.returncode != 0:
            warn(f"systemctl enable {unit} failed: {enable.stderr.strip()}")
            result["status"] = "enable_failed"
            result["error"] = enable.stderr.strip()
            return trace_out(result)

        result["enabled"] = True
        result["status"] = "enabled"
        log(f"Boot unit {unit} written and enabled")
        return trace_out(result)

    except Exception as e:
        warn(f"Failed to install boot unit {unit}: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return trace_out(result)


def remove_daemon_unit(project_name: str, daemon: str) -> Dict[str, Any]:
    """Disable and delete a unit written by install_daemon_unit.  Does not stop the daemons."""
    trace_in()
    unit = daemon_unit_name(project_name, daemon)
    unit_path = SYSTEMD_UNIT_DIR / unit
    result: Dict[str, Any] = {"unit": unit, "removed": False}
    try:
        if systemd_running():
            _systemctl("disable", unit)
        if unit_path.exists():
            unit_path.unlink()
            result["removed"] = True
            if systemd_running():
                _systemctl("daemon-reload")
        return trace_out(result)
    except Exception as e:
        warn(f"Failed to remove boot unit {unit}: {e}")
        result["error"] = str(e)
        return trace_out(result)


def enable_existing_service(service: str) -> Dict[str, Any]:
    """Enable a distro service (nginx, mysql) at boot if it is installed and not enabled yet."""
    trace_in()
    result: Dict[str, Any] = {"service": service, "enabled": False}
    if not systemd_running():
        result["status"] = "systemd_not_running"
        return trace_out(result)
    state = _systemctl("is-enabled", service)
    current = state.stdout.strip()
    if current in ("enabled", "enabled-runtime", "static", "alias", "indirect", "generated"):
        result["enabled"] = True
        result["status"] = "already_enabled"
        return trace_out(result)
    if current in ("", "not-found") or "not-found" in state.stderr or "No such file" in state.stderr:
        result["status"] = "not_installed"
        return trace_out(result)
    enable = _systemctl("enable", service)
    if enable.returncode == 0:
        result["enabled"] = True
        result["status"] = "enabled"
        log(f"Enabled {service} at boot")
    else:
        result["status"] = "enable_failed"
        result["error"] = enable.stderr.strip()
        warn(f"systemctl enable {service} failed: {result['error']}")
    return trace_out(result)
