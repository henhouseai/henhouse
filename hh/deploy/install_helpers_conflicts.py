"""
Install conflict detection helpers.

Handles scanning for active installations and detecting conflicts.
"""

import configparser
from pathlib import Path
from typing import Dict, Optional
from hh.gateway.gateway import get_gateway
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.deploy.install_helpers_config import get_install_config_path


def scan_active_installations(exclude_project: Optional[str] = None) -> Dict[str, int]:
    """
    Scan /root for active installations and return their port ranges.

    An installation is considered active if its users still exist.
    Returns dict mapping project_name -> flask_start_port.
    """
    active_installations: Dict[str, int] = {}
    root_dir = Path("/root")

    if not root_dir.exists():
        return active_installations

    gateway = get_gateway()
    if not gateway or not gateway.os:
        return active_installations

    # Find all install config files
    for config_file in root_dir.glob(".*-install.cnf"):
        try:
            # Extract project name from filename (e.g., .henhouse-install.cnf -> henhouse)
            filename = config_file.stem  # e.g., ".henhouse-install"
            if not filename.startswith("."):
                continue
            project_name = filename[1:].replace("-install", "")

            if exclude_project and project_name == exclude_project:
                continue

            # Check if installation is active by verifying users exist
            is_active = False
            for tier in HENHOUSE_TIERS:
                user = f"{project_name}_{tier}"
                if gateway.os.user_exists(user):
                    is_active = True
                    break

            if not is_active:
                continue

            # Load the config to get flask_start_port
            try:
                parser = configparser.ConfigParser()
                parser.read(config_file)
                if "install" in parser:
                    port_str = parser["install"].get("flask_start_port", "5001").strip()
                    try:
                        port = int(port_str)
                        active_installations[project_name] = port
                    except ValueError:
                        # Invalid port, use default
                        active_installations[project_name] = 5001
            except Exception:
                # Can't read config, skip it
                pass
        except Exception:
            # Skip files we can't process
            continue

    return active_installations


def check_port_conflict(requested_port: int, project_name: str) -> Optional[str]:
    """
    Check if requested port range conflicts with active installations.

    Returns error message if conflict found, None otherwise.
    Port range is 100 ports: requested_port through requested_port+99.
    """
    active_installations = scan_active_installations(exclude_project=project_name)

    requested_range = set(range(requested_port, requested_port + 100))

    for other_project, other_port in active_installations.items():
        other_range = set(range(other_port, other_port + 100))
        if requested_range.intersection(other_range):
            conflict_msg = (
                f"Port conflict: {project_name} requested port {requested_port} "
                f"(reserves {requested_port}-{requested_port+99}), but {other_project} "
                f"is using port {other_port} (reserves {other_port}-{other_port+99})"
            )
            return conflict_msg

    return None
