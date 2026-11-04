"""
Database configuration for init_db and clean_db operations.

This module contains the global DB_CONFIG that hook modules import to access
database connection parameters, passwords, and TLS settings.

Pattern: Similar to install_hooks.py INSTALL_CONFIG, this provides a cross-cutting
global that init_db.py/clean_db.py populate before running hooks.
"""

from typing import Dict, Any

# INTENTIONALLY CROSS-CUTTABLE GLOBAL
# Modules import and read this during db initialization/cleanup
DB_CONFIG: Dict[str, Any] = {
    "project_name": "",
    "project_path": "",
    "main_db": "",              # Database name (e.g., "henhouse")
    "cache_db": "",             # Cache database name (e.g., "henhouse_cache")
    "root_password_main": "",
    "root_password_cache": "",
    "mysql_tls_enabled": False,
    "ssl_ca_path": "",
    "cache_ssl_ca_path": "",
    "ssl_verify_mode": 2,       # 0=none, 1=optional, 2=required, 3=verify_identity
    "db_host": "",
}
