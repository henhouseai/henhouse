"""
Install configuration helpers.

Handles loading, parsing, and validating install configuration files.
"""

import configparser
import json
from pathlib import Path
from typing import Dict, Any, Optional


def get_install_config_path(project_name: str) -> Path:
    """Get path to install config file for a project."""
    return Path(f"/root/.{project_name}-install.cnf")


def parse_manifest_users(section: configparser.SectionProxy) -> Dict[str, Dict[str, Any]]:
    """Parse manifest_users section from config file."""
    parsed: Dict[str, Dict[str, Any]] = {}
    for k, v in section.items():
        try:
            obj = json.loads(v)
            if isinstance(obj, dict):
                parsed[k] = obj
                continue
        except Exception:
            pass
        parsed[k] = {"uid": str(v)}
    return parsed


def load_install_config(project_name: str, section_name: str = "install") -> Optional[Dict[str, Any]]:
    """
    Load and parse install configuration file.

    Returns None if config file doesn't exist.
    Raises ValueError if config is invalid or missing required fields.
    """
    cfg_path = get_install_config_path(project_name)
    if not cfg_path.exists():
        return None

    parser = configparser.ConfigParser()
    parser.read(cfg_path)

    if section_name not in parser:
        raise ValueError(f"Missing [{section_name}] section in {cfg_path}")

    section = parser[section_name]

    def req(key: str) -> str:
        val = section.get(key, "").strip()
        if not val:
            raise ValueError(f"Missing required field {key} in {cfg_path}")
        return val

    # Parse entry point script name
    hen_value = section.get("entry_point_script_name", "hen")
    hen_value = hen_value.strip() if hen_value is not None else "hen"

    # Parse manifest users if present
    manifest_users: Dict[str, Dict[str, Any]] = {}
    if parser.has_section("manifest_users"):
        manifest_users = parse_manifest_users(parser["manifest_users"])

    # Parse flask_start_port
    flask_start_port_str = section.get("flask_start_port", "5001").strip()
    try:
        flask_start_port = int(flask_start_port_str)
    except ValueError:
        flask_start_port = 5001

    data: Dict[str, Any] = {
        "db_host": req("db_host"),
        "cache_host": req("cache_host"),
        "mysql_tls_enabled": section.get("mysql_tls_enabled", "0").strip(),
        "ssl_ca_path": req("ssl_ca_path"),
        "cache_ssl_ca_path": req("cache_ssl_ca_path"),
        "mysql_ssl_dir": section.get("mysql_ssl_dir", "/etc/mysql/ssl").strip(),
        "mysql_server_cert_path": section.get("mysql_server_cert_path", "/etc/mysql/ssl/server-cert.pem").strip(),
        "mysql_server_key_path": section.get("mysql_server_key_path", "/etc/mysql/ssl/server-key.pem").strip(),
        "mysql_config_path": section.get("mysql_config_path", "/etc/mysql/mysql.conf.d/mysqld.cnf").strip(),
        "entry_point_script_name": hen_value or "hen",
        "mysql_root_password_main": req("mysql_root_password_main"),
        "mysql_root_password_cache": req("mysql_root_password_cache"),
        "password_guest": req("password_guest"),
        "password_verified": req("password_verified"),
        "password_admin": req("password_admin"),
        "password_root": req("password_root"),
        "htaccess_guest_password": section.get("htaccess_guest_password", "").strip(),
        "htaccess_admin_password": req("htaccess_admin_password"),
        "htaccess_panel_password": req("htaccess_panel_password"),
        "flask_start_port": flask_start_port,
        "htpasswd_dir": section.get("htpasswd_dir", "/var/www").strip(),
    }

    # Pass every other key through as a stripped string.  Module install hooks read their own
    # settings from this dict (e.g. hh_nginx: domain, ssl_enabled; core: password_human_db), so the
    # loader must not drop keys it doesn't know about.
    for key, value in section.items():
        data.setdefault(key, value.strip())
    data["manifest_users"] = manifest_users

    return data


def validate_config_value(key: str, value: str) -> None:
    """
    Validate that a config value is set and not a placeholder.

    Raises ValueError if validation fails.
    """
    if value is None:
        raise ValueError(f"{key} is required")
    v = str(value).strip()
    if not v:
        raise ValueError(f"{key} is required")
    lower = v.lower()
    if "change_me" in lower or "yourdomain" in lower or "example.com" in lower:
        raise ValueError(f"{key} must be set to real values (placeholder detected)")


def validate_entry_point_script_name(name: str) -> None:
    """
    Validate entry point script name.

    Raises ValueError if name is invalid or conflicts with existing files.
    """
    if not name or any(c in name for c in ('/', '\\')):
        raise ValueError("entry_point_script_name must be a simple filename (no slashes)")
    candidate = Path("/root") / name
    if candidate.exists():
        raise ValueError(f"entry_point_script_name '{name}' already exists at {candidate}; choose a different name")
