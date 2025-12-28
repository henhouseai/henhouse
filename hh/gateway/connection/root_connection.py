import os
from typing import Optional, Dict, Union
from hh.gateway.connection.connection import Connection, _load_dsn
from hh.deploy.deploy_utils import detect_project_context
from hh.gateway.gateway import get_gateway
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

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
    
    def _get_main_dsn(self, project_name: str) -> Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]:
        """Get main database DSN with root credentials."""
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for root connection")
            trace_out()
            return None
        
        # Get root password from command line args
        root_password = gateway.get_arg('password')
        if not root_password:
            warn("Root password required for root connection")
            trace_out()
            return None
        
        # Get DSN info but override user/password
        # project_name is passed from initialize() to avoid redundant detection
        
        # When running as root, try to detect project owner and use their config
        dsn = None
        if hasattr(os, "geteuid") and os.geteuid() == 0 and project_name:  # Running as root
            # Try to find project owner's config
            try:
                import pwd
                # Look for project owner by checking /srv/{project_name} ownership
                srv_path = f'/srv/{project_name}'
                if os.path.exists(srv_path):
                    stat_info = os.stat(srv_path)
                    owner_uid = stat_info.st_uid
                    if not hasattr(pwd, "getpwuid"):
                        warn("pwd.getpwuid is not available")
                        trace_out()
                        return None
                    owner_info = pwd.getpwuid(owner_uid)
                    owner_home = owner_info.pw_dir
                    owner_config = f'{owner_home}/.henhouse.cnf'
                    
                    if os.path.exists(owner_config):
                        import configparser
                        config = configparser.ConfigParser()
                        config.read(owner_config)
                        dsn = {
                            'host': config.get('client', 'host', fallback='localhost'),
                            'user': 'root',  # Override with root
                            'password': root_password,  # Use command line password
                            'database': config.get('client', 'database', fallback=project_name),
                            'port': config.getint('client', 'port', fallback=3306)
                        }
                        log(f"Using project owner's config: {owner_config}")
            except Exception as e:
                warn(f"Failed to detect project owner config: {e}")
        
        # Fallback to standard DSN loading
        if not dsn:
            main_dsn, _, _ = _load_dsn(project_name) if project_name else (None, None, None)
            if main_dsn:
                # Override with root credentials
                dsn = main_dsn.copy()
                dsn['user'] = 'root'
                dsn['password'] = root_password
        
        if dsn:
            log(f"Root connection DSN: host={dsn.get('host')}, user={dsn.get('user')}, database={dsn.get('database')}")
        
        trace_out()
        return dsn
    
    def _get_cache_dsn(self, project_name: str) -> Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]:
        """Get cache database DSN with root credentials."""
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for root cache connection")
            trace_out()
            return None
        
        # Get root password from command line args
        root_password = gateway.get_arg('password')
        if not root_password:
            warn("Root password required for root cache connection")
            trace_out()
            return None
        
        # Get cache DSN info but override user/password
        dsn = None
        if hasattr(os, "geteuid") and os.geteuid() == 0 and project_name:  # Running as root
            # Try to find project owner's config for cache database name
            try:
                import pwd
                srv_path = f'/srv/{project_name}'
                if os.path.exists(srv_path):
                    stat_info = os.stat(srv_path)
                    owner_uid = stat_info.st_uid
                    if not hasattr(pwd, "getpwuid"):
                        warn("pwd.getpwuid is not available")
                        trace_out()
                        return None
                    owner_info = pwd.getpwuid(owner_uid)
                    owner_home = owner_info.pw_dir
                    owner_config = f'{owner_home}/.henhouse.cnf'
                    
                    if os.path.exists(owner_config):
                        import configparser
                        config = configparser.ConfigParser()
                        config.read(owner_config)
                        # Cache database is typically main_database + '_cache'
                        main_db = config.get('client', 'database', fallback=project_name)
                        cache_db = f"{main_db}_cache"
                        dsn = {
                            'host': config.get('client', 'host', fallback='localhost'),
                            'user': 'root',
                            'password': root_password,
                            'database': cache_db,
                            'port': config.getint('client', 'port', fallback=3306)
                        }
                        log(f"Using project owner's config for cache: {owner_config}")
            except Exception as e:
                warn(f"Failed to detect project owner config for cache: {e}")
        
        # Fallback to standard DSN loading
        if not dsn:
            _, cache_dsn, _ = _load_dsn(project_name) if project_name else (None, None, None)
            if cache_dsn:
                dsn = cache_dsn.copy()
                dsn['user'] = 'root'
                dsn['password'] = root_password
        
        if dsn:
            log(f"Root cache connection DSN: host={dsn.get('host')}, user={dsn.get('user')}, database={dsn.get('database')}")
        
        trace_out()
        return dsn
    
    def _get_history_dsn(self, project_name: str) -> Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]:
        """Get history database DSN with root credentials.
        
        TODO: Full implementation pending ask 1211 (root config file system).
        Currently uses fallback to standard DSN loading with root credentials override.
        """
        trace_in()
        gateway = get_gateway()
        if not gateway:
            warn("No gateway available for root history connection")
            trace_out()
            return None
        
        # Get root password from command line args
        root_password = gateway.get_arg('password')
        if not root_password:
            warn("Root password required for root history connection")
            trace_out()
            return None
        
        # Fallback to standard DSN loading
        _, _, history_dsn = _load_dsn(project_name) if project_name else (None, None, None)
        if history_dsn:
            dsn = history_dsn.copy()
            dsn['user'] = 'root'
            dsn['password'] = root_password
            log(f"Root history connection DSN: host={dsn.get('host')}, user={dsn.get('user')}, database={dsn.get('database')}")
            trace_out()
            return dsn
        
        trace_out()
        return None

