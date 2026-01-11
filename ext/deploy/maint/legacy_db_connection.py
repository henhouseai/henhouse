"""Legacy database connection helper for migration daemon."""

from __future__ import annotations
from typing import Optional, Dict, Any
import os
import configparser
from contextlib import contextmanager

try:
    import pymysql  # type: ignore[import-untyped]
except ImportError:
    pymysql = None

from hh.deploy.deploy_utils import detect_project_context


def get_legacy_database_name() -> Optional[str]:
    """Get legacy database name from environment variable or Python config.
    
    Returns:
        Legacy database name, or None if not configured
    """
    # First check environment variable
    legacy_db_name = os.getenv('LEGACY_DB_NAME')
    if legacy_db_name:
        return legacy_db_name
    
    # Otherwise, try to get from Python config file
    try:
        from ext.deploy.conf.migration_config import LEGACY_DB_NAME
        return LEGACY_DB_NAME
    except (ImportError, AttributeError):
        return None


def get_legacy_dsn(project_name: str) -> Optional[Dict[str, Any]]:
    """Get DSN for legacy database (same connection info, different database name).
    
    Args:
        project_name: Project name for config lookup
        
    Returns:
        DSN dictionary for legacy database, or None if not configured
    """
    if pymysql is None:
        return None
    
    # Get legacy database name
    legacy_db_name = get_legacy_database_name()
    if not legacy_db_name:
        return None
    
    # Load main DSN to get connection info (host, user, password, port, SSL)
    config = configparser.ConfigParser()
    path = os.path.expanduser(f'~/.{project_name}.cnf')
    if not os.path.exists(path):
        return None
    
    config.read(path)
    
    # Build DSN with same connection info but different database
    dsn: Dict[str, Any] = {
        'host': config.get('client', 'host', fallback='localhost'),
        'user': config.get('client', 'user', fallback='root'),
        'password': config.get('client', 'password', fallback=''),
        'database': legacy_db_name,  # Different database name
        'port': config.getint('client', 'port', fallback=3306)
    }
    
    # Build SSL dict (same as main database)
    ssl_dict: Dict[str, Any] = {}
    ssl_ca = config.get('client', 'ssl_ca', fallback=None)
    if ssl_ca:
        ssl_dict['ca'] = ssl_ca
        ssl_dict['verify_mode'] = 2
        ssl_dict['check_hostname'] = True
    
    if ssl_dict:
        dsn['ssl'] = ssl_dict
    
    return dsn


@contextmanager
def get_legacy_db_connection():
    """Context manager for legacy database connection.
    
    Yields:
        pymysql connection to legacy database
        
    Example:
        with get_legacy_db_connection() as legacy_conn:
            cursor = legacy_conn.cursor()
            cursor.execute("SELECT * FROM accounts")
            results = cursor.fetchall()
    """
    if pymysql is None:
        raise RuntimeError("pymysql not available")
    
    project_name, _ = detect_project_context()
    if not project_name:
        raise RuntimeError("Could not detect project context")
    
    dsn = get_legacy_dsn(project_name)
    if not dsn:
        raise RuntimeError("Legacy database not configured (set LEGACY_DB_NAME env var or configure in ext/deploy/conf/migration_config.py)")
    
    # Extract SSL dict if present
    ssl = dsn.pop('ssl', None) if isinstance(dsn.get('ssl'), dict) else None
    
    conn = None
    try:
        cursorclass = pymysql.cursors.DictCursor
        conn = pymysql.connect(**dsn, ssl=ssl, cursorclass=cursorclass)
        yield conn
    finally:
        if conn:
            conn.close()

