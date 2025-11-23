import os
from typing import Optional, Dict, Union
from hh.gateway.connection.conn import Connection
from hh.gateway.connection.connection import load_dsn_pair
from hh.deploy.utils import detect_project_context
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
    
    def _get_main_dsn(self) -> Optional[Dict[str, Union[str, int]]]:
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
        # When running as root, try to detect project owner and use their config
        dsn = None
        if os.geteuid() == 0:  # Running as root
            project_name, _ = detect_project_context()
            if project_name:
                # Try to find project owner's config
                try:
                    import pwd
                    # Look for project owner by checking /srv/{project_name} ownership
                    srv_path = f'/srv/{project_name}'
                    if os.path.exists(srv_path):
                        stat_info = os.stat(srv_path)
                        owner_uid = stat_info.st_uid
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
            main_dsn, _ = load_dsn_pair()
            if main_dsn:
                # Override with root credentials
                dsn = main_dsn.copy()
                dsn['user'] = 'root'
                dsn['password'] = root_password
        
        if dsn:
            log(f"Root connection DSN: host={dsn.get('host')}, user={dsn.get('user')}, database={dsn.get('database')}")
        
        trace_out()
        return dsn

