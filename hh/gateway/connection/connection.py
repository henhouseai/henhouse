import configparser
import json
import os
import pymysql
import getpass
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union, TypedDict, Tuple
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.utils import detect_project_context
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

_connection_counter = 0

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

class DatabaseRow(TypedDict, total=False):
    id: int
    name: str
    status: str
    created_at: str
    updated_at: str

class JsonResponse(TypedDict, total=False):
    status: str
    timestamp: str
    data: Union[Dict, List]
    error: str
    hint: str

def load_dsn_pair() -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
    trace_in()
    config = configparser.ConfigParser()
    
    # Load DSN from user's home directory config
    project_name, _ = detect_project_context()
    path = os.path.expanduser(f'~/.{project_name}.cnf')
    if os.path.exists(path):
        config.read(path)
        dsn = {
            'host': config.get('client', 'host', fallback='localhost'),
            'user': config.get('client', 'user', fallback='root'),
            'password': config.get('client', 'password', fallback=''),
            'database': config.get('client', 'database', fallback=project_name),
            'port': config.getint('client', 'port', fallback=3306)
        }
        log(f"DSN loaded from config: {path}, host={dsn['host']}, database={dsn['database']}")
        
        # Detect user tier level from DSN username and set in response
        _detect_and_set_user_tier_level(project_name, dsn['user'])
        
        cache_dsn = {
            'host': config.get('client', 'cache_host', fallback=dsn['host']),
            'user': config.get('client', 'cache_user', fallback=dsn['user']),
            'password': config.get('client', 'cache_password', fallback=dsn['password']),
            'database': config.get('client', 'cache_database', fallback=f"{dsn['database']}_cache"),
            'port': config.getint('client', 'cache_port', fallback=dsn['port'])
        }
        
        trace_out()
        return dsn, cache_dsn
    else:
        warn(f"Configuration file not found: {path}")
        trace_out()
        return None, None

def load_dsn() -> Optional[Dict[str, str]]:
    primary, _ = load_dsn_pair()
    return primary

def load_cache_dsn() -> Optional[Dict[str, str]]:
    _, cache = load_dsn_pair()
    return cache

class HenhouseConnection:
    """Wrapper that holds primary/secondary DB connections and proxies to primary."""
    def __init__(self, primary, secondary=None):
        global _connection_counter
        _connection_counter += 1
        conn_id = _connection_counter
        object.__setattr__(self, '_conn_id', conn_id)
        object.__setattr__(self, '_primary', primary)
        object.__setattr__(self, '_secondary', secondary or primary)
        if hasattr(primary, '__dict__'):
            primary._conn_id = conn_id
        if secondary and secondary is not primary and hasattr(secondary, '__dict__'):
            secondary._conn_id = conn_id

    @property
    def primary(self):
        return object.__getattribute__(self, '_primary')

    @property
    def secondary(self):
        return object.__getattribute__(self, '_secondary')

    def get_connection(self, use_secondary: bool = False):
        return self.secondary if use_secondary else self.primary

    def __getattr__(self, item):
        return getattr(self.primary, item)

    def __setattr__(self, key, value):
        setattr(self.primary, key, value)

    # Convenience helpers so callers can do self.conn.r_query(...) later if desired
    def r_query(self, sql: str, params=None, *, use_secondary: bool = False):
        return r_query(self, sql, params, use_secondary=use_secondary)

    def u_query(self, sql: str, params=None, *, use_secondary: bool = False):
        return u_query(self, sql, params, use_secondary=use_secondary)

    def c_query(self, sql: str, params=None, *, use_secondary: bool = False):
        return c_query(self, sql, params, use_secondary=use_secondary)

    def d_query(self, sql: str, params=None, *, use_secondary: bool = False):
        return d_query(self, sql, params, use_secondary=use_secondary)

    def close(self):
        """Close both primary and secondary connections."""
        trace_in()
        conn_id = getattr(self, '_conn_id', None)
        if self._secondary and self._secondary is not self._primary:
            try:
                if self._secondary.open:
                    self._secondary.close()
                    log(_format_log_with_conn_id(self, "Secondary connection closed successfully"))
            except Exception as e:
                # Only warn if it's not an "already closed" error
                if "Already closed" not in str(e) and "closed" not in str(e).lower():
                    warn(f"Failed to close secondary connection: {e}")
        try:
            if self._primary.open:
                self._primary.close()
                log(_format_log_with_conn_id(self, "Primary connection closed successfully"))
        except Exception as e:
            # Only warn if it's not an "already closed" error
            if "Already closed" not in str(e) and "closed" not in str(e).lower():
                warn(f"Failed to close primary connection: {e}")
        trace_out()

def _unwrap_connection(conn, use_secondary: bool = False):
    if isinstance(conn, HenhouseConnection):
        return conn.get_connection(use_secondary=use_secondary)
    return conn

def _get_connection_id(conn) -> Optional[int]:
    """Get connection ID from either HenhouseConnection wrapper or raw connection."""
    if isinstance(conn, HenhouseConnection):
        return getattr(conn, '_conn_id', None)
    return getattr(conn, '_conn_id', None)

def _format_log_with_conn_id(conn, message: str) -> str:
    """Format log message with connection ID prefix if available."""
    conn_id = _get_connection_id(conn)
    if conn_id is not None:
        return f"[{conn_id}] {message}"
    return message

def _detect_and_set_user_tier_level(project_name: str, username: str) -> None:
    """Detect user tier level from DSN username and set it in Gateway response."""
    trace_in()
    tier_level = 0  # Default to unknown
    try:
        # Use username from DSN config file
        if not username:
            log("DSN username is empty, cannot detect tier")
        else:
            # Check if username matches pattern: {project_name}_{tier}
            expected_prefix = f"{project_name}_"
            if not username.startswith(expected_prefix):
                log(f"Username {username} does not match expected pattern {expected_prefix}*")
            else:
                # Extract tier suffix
                tier_suffix = username[len(expected_prefix):]
                if not tier_suffix:
                    log(f"Username {username} has no tier suffix")
                else:
                    # Look up tier in HENHOUSE_TIERS list
                    try:
                        tier_index = HENHOUSE_TIERS.index(tier_suffix)
                        # Convert 0-based index to 1-based level (index 0 → level 1, etc.)
                        tier_level = tier_index + 1
                        log(f"Detected tier: {tier_suffix} (index {tier_index} → level {tier_level})")
                    except ValueError:
                        log(f"Tier suffix '{tier_suffix}' not found in HENHOUSE_TIERS")
        
    except Exception as e:
        warn(f"Failed to detect user tier level: {e}")
    finally:
        # Always set tier level (0 if detection failed, or detected level if successful)
        from hh.gateway.gateway import get_gateway
        gateway = get_gateway()
        if gateway and gateway.response:
            gateway.response.set_user_tier_level(tier_level)
            log(f"Set user tier level {tier_level} in response")
        else:
            log("Gateway or response not available for setting tier level")
        trace_out()

def get_connection(dict_cursor: bool = True, dsn_override: Optional[Dict[str, Union[str, int]]] = None):
    trace_in()
    dsn = dsn_override or load_dsn()
    if not dsn:
        warn("Cannot create connection: DSN not available")
        trace_out()
        return None
    cursorclass = pymysql.cursors.DictCursor if dict_cursor else None
    try:
        if cursorclass:
            conn = pymysql.connect(**dsn, cursorclass=cursorclass)
            log(f"Database connection established with DictCursor: host={dsn['host']}, database={dsn['database']}")
        else:
            conn = pymysql.connect(**dsn)
            log(f"Database connection established: host={dsn['host']}, database={dsn['database']}")
        # Initialize file operation buffer
        conn._file_operations = []
        trace_out()
        return conn
    except Exception as e:
        warn(f"Failed to connect to database: {e}")
        trace_out()
        return None


def r_query(conn, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None, *, use_secondary: bool = False) -> List[DatabaseRow]:
    trace_in()
    target_conn = _unwrap_connection(conn, use_secondary=use_secondary)
    target_conn._last_sql = sql
    target_conn._last_params = list(params or [])
    log(_format_log_with_conn_id(conn, f"{sql[:500]}{'...' if len(sql) > 500 else ''}, params={params}"))
    try:
        with target_conn.cursor() as cur:
            cur.execute(sql, params or [])
            rows = cur.fetchall()
            if isinstance(rows, list) and rows and not isinstance(rows[0], dict):
                columns = [d[0] for d in cur.description]
                result = [dict(zip(columns, r)) for r in rows]
                log(_format_log_with_conn_id(conn, f"r_query executed successfully: {len(result)} rows returned (converted to dict)"))
            else:
                result = list(rows)
                log(_format_log_with_conn_id(conn, f"r_query executed successfully: {len(result)} rows returned"))
            trace_out()
            return result
    except Exception as exc:
        warn(f"r_query execution failed: {exc}")
        setattr(exc, 'sql', sql)
        setattr(exc, 'params', params or [])
        trace_out()
        raise
    finally:
        target_conn._last_sql = None
        target_conn._last_params = None

def c_query(conn, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None, *, use_secondary: bool = False) -> int:
    trace_in()
    target_conn = _unwrap_connection(conn, use_secondary=use_secondary)
    target_conn._last_sql = sql
    target_conn._last_params = list(params or [])
    log(_format_log_with_conn_id(conn, f"{sql[:500]}{'...' if len(sql) > 500 else ''}, params={params}"))
    try:
        with target_conn.cursor() as cur:
            cur.execute(sql, params or [])
            lastrowid = cur.lastrowid
            log(_format_log_with_conn_id(conn, f"c_query executed successfully: lastrowid={lastrowid}"))
            trace_out()
            return lastrowid
    except Exception as exc:
        warn(f"c_query execution failed: {exc}")
        setattr(exc, 'sql', sql)
        setattr(exc, 'params', params or [])
        trace_out()
        raise
    finally:
        target_conn._last_sql = None
        target_conn._last_params = None

def u_query(conn, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None, *, use_secondary: bool = False) -> int:
    trace_in()
    target_conn = _unwrap_connection(conn, use_secondary=use_secondary)
    target_conn._last_sql = sql
    target_conn._last_params = list(params or [])
    log(_format_log_with_conn_id(conn, f"{sql[:500]}{'...' if len(sql) > 500 else ''}, params={params}"))
    try:
        with target_conn.cursor() as cur:
            cur.execute(sql, params or [])
            rowcount = cur.rowcount
            log(_format_log_with_conn_id(conn, f"u_query executed successfully: {rowcount} rows affected"))
            trace_out()
            return rowcount
    except Exception as exc:
        warn(f"u_query execution failed: {exc}")
        setattr(exc, 'sql', sql)
        setattr(exc, 'params', params or [])
        trace_out()
        raise
    finally:
        target_conn._last_sql = None
        target_conn._last_params = None

def d_query(conn, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None, *, use_secondary: bool = False) -> int:
    trace_in()
    target_conn = _unwrap_connection(conn, use_secondary=use_secondary)
    target_conn._last_sql = sql
    target_conn._last_params = list(params or [])
    log(_format_log_with_conn_id(conn, f"{sql[:500]}{'...' if len(sql) > 500 else ''}, params={params}"))
    try:
        with target_conn.cursor() as cur:
            cur.execute(sql, params or [])
            rowcount = cur.rowcount
            log(_format_log_with_conn_id(conn, f"d_query executed successfully: {rowcount} rows affected"))
            trace_out()
            return rowcount
    except Exception as exc:
        warn(f"d_query execution failed: {exc}")
        setattr(exc, 'sql', sql)
        setattr(exc, 'params', params or [])
        trace_out()
        raise
    finally:
        target_conn._last_sql = None
        target_conn._last_params = None

# Utility functions moved to hh.gateway.connection.utils
# Import them from there for backward compatibility
from hh.gateway.connection.utils import (
    iso_now,
    json_out,
    json_success,
    json_error,
    ensure_iso_timestamps,
    normalize_meta,
    count_json_chars
)

def validate_agent_identity(conn, agent_id: int, badge_ts: Optional[str]) -> bool:
    trace_in()
    if agent_id is None or badge_ts is None:
        warn("Agent validation failed: missing agent_id or badge_ts")
        trace_out()
        return False
    query = "SELECT COUNT(*) AS c FROM agents WHERE id=%s AND badge_ts=%s"
    results = r_query(conn, query, [int(agent_id), badge_ts])
    is_valid = bool(results and int(results[0].get("c") or 0) > 0)
    log(_format_log_with_conn_id(conn, f"Agent identity validation: agent_id={agent_id}, badge_ts={badge_ts}, valid={is_valid}"))
    trace_out()
    return is_valid


def schedule_file_move(conn, from_path: str, to_path: str) -> None:
    """Schedule a file move operation to be executed after DB commit."""
    trace_in()
    unwrapped_conn = _unwrap_connection(conn)
    if not hasattr(unwrapped_conn, '_file_operations'):
        unwrapped_conn._file_operations = []
    operation = {
        'type': 'move',
        'from_path': from_path,
        'to_path': to_path,
        'status': 'scheduled',
        'temp_filename': None
    }
    unwrapped_conn._file_operations.append(operation)
    log(_format_log_with_conn_id(conn, f"Scheduled file move: {from_path} -> {to_path}"))
    trace_out()


def schedule_file_delete(conn, file_path: str) -> None:
    """Schedule a file delete operation (moves to /tmp) to be executed after DB commit."""
    trace_in()
    unwrapped_conn = _unwrap_connection(conn)
    if not hasattr(unwrapped_conn, '_file_operations'):
        unwrapped_conn._file_operations = []
    file_path_obj = Path(file_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    temp_filename = f"henhouse_deleted_{timestamp}_{unique_id}_{file_path_obj.name}"
    temp_path = f"/tmp/{temp_filename}"
    operation = {
        'type': 'delete',
        'from_path': file_path,
        'to_path': temp_path,
        'status': 'scheduled',
        'temp_filename': temp_filename
    }
    unwrapped_conn._file_operations.append(operation)
    log(_format_log_with_conn_id(conn, f"Scheduled file delete: {file_path} -> {temp_path}"))
    trace_out()


def _execute_file_operations(conn) -> bool:
    """Execute all buffered file operations. Returns True if all succeed, False otherwise."""
    trace_in()
    unwrapped_conn = _unwrap_connection(conn)
    if not hasattr(unwrapped_conn, '_file_operations') or not unwrapped_conn._file_operations:
        log(_format_log_with_conn_id(conn, "No file operations to execute"))
        trace_out()
        return True
    
    log(_format_log_with_conn_id(conn, f"Executing {len(unwrapped_conn._file_operations)} buffered file operations"))
    
    for operation in unwrapped_conn._file_operations:
        if operation['status'] != 'scheduled':
            continue
        
        try:
            from_path = Path(operation['from_path'])
            to_path = Path(operation['to_path'])
            
            if not from_path.exists():
                warn(f"Source file does not exist: {from_path}")
                report_error("file_operation", f"Source file does not exist: {from_path}")
                operation['status'] = 'failed'
                trace_out()
                return False
            
            if operation['type'] == 'move':
                to_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(from_path), str(to_path))
                log(_format_log_with_conn_id(conn, f"Moved file: {from_path} -> {to_path}"))
                operation['status'] = 'completed'
                
            elif operation['type'] == 'delete':
                to_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(from_path), str(to_path))
                log(_format_log_with_conn_id(conn, f"Moved file to temp for deletion: {from_path} -> {to_path}"))
                operation['status'] = 'completed'
                
        except Exception as e:
            warn(f"Failed to execute file operation {operation['type']}: {from_path} -> {to_path}: {str(e)}")
            report_error("file_operation", f"Failed to {operation['type']} file: {str(e)}")
            operation['status'] = 'failed'
            trace_out()
            return False
    
    log(_format_log_with_conn_id(conn, "All file operations executed successfully"))
    trace_out()
    return True


def _rollback_file_operations(conn) -> bool:
    """Rollback all completed file operations. Returns True if all rollbacks succeed."""
    trace_in()
    unwrapped_conn = _unwrap_connection(conn)
    if not hasattr(unwrapped_conn, '_file_operations') or not unwrapped_conn._file_operations:
        log(_format_log_with_conn_id(conn, "No file operations to rollback"))
        trace_out()
        return True
    
    log(_format_log_with_conn_id(conn, f"Rolling back {len(unwrapped_conn._file_operations)} file operations"))
    
    completed_count = sum(1 for op in unwrapped_conn._file_operations if op.get('status') == 'completed')
    log(_format_log_with_conn_id(conn, f"Found {completed_count} completed operations to rollback"))
    
    if completed_count == 0:
        log(_format_log_with_conn_id(conn, "No completed operations to rollback"))
        trace_out()
        return True
    
    rolled_back_count = 0
    for operation in reversed(unwrapped_conn._file_operations):
        if operation['status'] != 'completed':
            continue
        
        log(_format_log_with_conn_id(conn, f"Rolling back operation: {operation['type']} from {operation['from_path']} to {operation['to_path']}"))
        
        try:
            from_path = Path(operation['from_path'])
            to_path = Path(operation['to_path'])
            
            if operation['type'] == 'move':
                if to_path.exists():
                    from_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(to_path), str(from_path))
                    log(_format_log_with_conn_id(conn, f"Rolled back move: {to_path} -> {from_path}"))
                    operation['status'] = 'rolled_back'
                    rolled_back_count += 1
                else:
                    warn(f"Destination file does not exist for rollback: {to_path}")
                    report_error("file_operation", f"Destination file does not exist for rollback: {to_path}")
                    operation['status'] = 'rollback_failed'
                    trace_out()
                    return False
                
            elif operation['type'] == 'delete':
                if to_path.exists():
                    from_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(to_path), str(from_path))
                    log(_format_log_with_conn_id(conn, f"Rolled back delete: {to_path} -> {from_path}"))
                    operation['status'] = 'rolled_back'
                    rolled_back_count += 1
                else:
                    warn(f"Temp file does not exist for rollback: {to_path}")
                    report_error("file_operation", f"Temp file does not exist for rollback: {to_path}")
                    operation['status'] = 'rollback_failed'
                    trace_out()
                    return False
                
        except Exception as e:
            warn(f"Failed to rollback file operation {operation['type']}: {str(e)}")
            report_error("file_operation", f"Failed to rollback {operation['type']}: {str(e)}")
            operation['status'] = 'rollback_failed'
            trace_out()
            return False
    
    log(_format_log_with_conn_id(conn, f"All {rolled_back_count} file operations rolled back successfully"))
    trace_out()
    return True
