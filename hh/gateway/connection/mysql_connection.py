from typing import Optional, Dict, Union
from hh.gateway.connection.root_connection import RootConnection
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


class MySQLConnection(RootConnection):
    """Connection with root credentials to MySQL system database (database=None)."""
    
    def _get_main_dsn(self) -> Optional[Dict[str, Union[str, int]]]:
        """Get MySQL system DSN with root credentials and database=None."""
        trace_in()
        # Get root DSN from parent class
        dsn = super()._get_main_dsn()
        
        if dsn:
            # Override database to None (connect to MySQL system, not project database)
            dsn['database'] = None
            log(f"MySQL system connection DSN: host={dsn.get('host')}, user={dsn.get('user')}, database=None")
        
        trace_out()
        return dsn

