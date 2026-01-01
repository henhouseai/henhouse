import os
from typing import Optional, Dict, Union
import configparser
from pathlib import Path
from hh.gateway.connection.connection import Connection, _load_dsn
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.users.install import _install_config_path

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)


class RootConnection(Connection):
    """Connection with root credentials for the main database. Cache/history unchanged."""
    
    def _load_install_config(self, project_name: str) -> Optional[Dict[str, Union[str, int]]]:
        cfg_path = _install_config_path(project_name)
        if not cfg_path.exists():
            warn(f"Root install config not found: {cfg_path}")
            return None
        parser = configparser.ConfigParser()
        parser.read(cfg_path)
        if "install" not in parser:
            warn(f"Missing [install] section in {cfg_path}")
            return None
        sec = parser["install"]
        def req(key: str) -> str:
            val = sec.get(key, "").strip()
            if not val:
                raise ValueError(f"Missing required field {key} in {cfg_path}")
            return val
        data: Dict[str, Union[str, int]] = {
            "db_host": req("db_host"),
            "cache_host": req("cache_host"),
            "ssl_ca_path": req("ssl_ca_path"),
            "cache_ssl_ca_path": req("cache_ssl_ca_path"),
            "mysql_root_password_main": req("mysql_root_password_main"),
            "mysql_root_password_cache": req("mysql_root_password_cache"),
        }
        # ssl_verify_mode is optional (defaults to 2 if not set)
        data["ssl_verify_mode"] = int(sec.get("ssl_verify_mode", "2"))
        return data
    
    def _get_main_dsn(self, project_name: str) -> Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]:
        """Get main database DSN with root credentials."""
        trace_in()
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            warn("Root connection requires sudo/root privileges")
            trace_out()
            return None
        
        cfg = None
        try:
            cfg = self._load_install_config(project_name)
        except Exception as e:
            warn(f"Failed to load root install config: {e}")
            trace_out()
            return None
        if not cfg:
            trace_out()
            return None
        
        dsn: Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]] = {
            'host': cfg["db_host"],
            'user': 'root',
            'password': cfg["mysql_root_password_main"],
            'database': project_name,
            'port': 3306,
        }
        # include ssl_ca if present
        if cfg.get("ssl_ca_path"):
            verify_mode = int(cfg.get("ssl_verify_mode", 2))
            check_hostname = verify_mode == 2
            dsn['ssl'] = {'ca': cfg["ssl_ca_path"], 'verify_mode': verify_mode, 'check_hostname': check_hostname}
        
        log(f"Root connection DSN: host={dsn.get('host')}, user={dsn.get('user')}, database={dsn.get('database')}")
        trace_out()
        return dsn
    
    def _get_cache_dsn(self, project_name: str) -> Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]:
        """Get cache database DSN with root credentials."""
        trace_in()
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            warn("Root cache connection requires sudo/root privileges")
            trace_out()
            return None
        
        cfg = None
        try:
            cfg = self._load_install_config(project_name)
        except Exception as e:
            warn(f"Failed to load root install config: {e}")
            trace_out()
            return None
        if not cfg:
            trace_out()
            return None
        
        dsn: Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]] = {
            'host': cfg["cache_host"],
            'user': 'root',
            'password': cfg["mysql_root_password_cache"],
            'database': f"{project_name}_cache",
            'port': 3306,
        }
        if cfg.get("cache_ssl_ca_path"):
            verify_mode = int(cfg.get("ssl_verify_mode", 2))
            check_hostname = verify_mode == 2
            dsn['ssl'] = {'ca': cfg["cache_ssl_ca_path"], 'verify_mode': verify_mode, 'check_hostname': check_hostname}
        
        log(f"Root cache connection DSN: host={dsn.get('host')}, user={dsn.get('user')}, database={dsn.get('database')}")
        trace_out()
        return dsn
    
    def _get_history_dsn(self, project_name: str) -> Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]:
        """Get history database DSN with root credentials.
        
        TODO: Full implementation pending ask 1211 (root config file system).
        Currently uses fallback to standard DSN loading with root credentials override.
        """
        trace_in()
        if hasattr(os, "geteuid") and os.geteuid() != 0:
            warn("Root history connection requires sudo/root privileges")
            trace_out()
            return None
        cfg = None
        try:
            cfg = self._load_install_config(project_name)
        except Exception as e:
            warn(f"Failed to load root install config: {e}")
            trace_out()
            return None
        if not cfg:
            trace_out()
            return None
        _, _, history_dsn = _load_dsn(project_name) if project_name else (None, None, None)
        if history_dsn:
            dsn = history_dsn.copy()
            dsn['user'] = 'root'
            dsn['password'] = cfg["mysql_root_password_main"]
            if cfg.get("ssl_ca_path"):
                verify_mode = int(cfg.get("ssl_verify_mode", 2))
                check_hostname = verify_mode == 2
                dsn['ssl'] = {'ca': cfg["ssl_ca_path"], 'verify_mode': verify_mode, 'check_hostname': check_hostname}
            log(f"Root history connection DSN: host={dsn.get('host')}, user={dsn.get('user')}, database={dsn.get('database')}")
            trace_out()
            return dsn
        
        trace_out()
        return None

