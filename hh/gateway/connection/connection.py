import configparser
import json
import os
import pymysql
import getpass
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union, TypedDict
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error, is_error
from hh.deploy.utils import detect_project_context
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

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

def load_dsn() -> Optional[Dict[str, str]]:
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
        }
        log(f"DSN loaded from config: {path}, host={dsn['host']}, database={dsn['database']}")
        
        # Detect user tier level from DSN username and set in response
        _detect_and_set_user_tier_level(project_name, dsn['user'])
        
        trace_out()
        return dsn
    else:
        warn(f"Configuration file not found: {path}")
        trace_out()
        return None

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

def get_connection(dict_cursor: bool = True):
    trace_in()
    dsn = load_dsn()
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


def r_query(conn, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> List[DatabaseRow]:
    trace_in()
    conn._last_sql = sql
    conn._last_params = list(params or [])
    log(f"{sql[:500]}{'...' if len(sql) > 500 else ''}, params={params}")
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            rows = cur.fetchall()
            if isinstance(rows, list) and rows and not isinstance(rows[0], dict):
                columns = [d[0] for d in cur.description]
                result = [dict(zip(columns, r)) for r in rows]
                log(f"r_query executed successfully: {len(result)} rows returned (converted to dict)")
            else:
                result = list(rows)
                log(f"r_query executed successfully: {len(result)} rows returned")
            trace_out()
            return result
    except Exception as exc:
        warn(f"r_query execution failed: {exc}")
        setattr(exc, 'sql', sql)
        setattr(exc, 'params', params or [])
        trace_out()
        raise
    finally:
        conn._last_sql = None
        conn._last_params = None

def c_query(conn, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
    trace_in()
    conn._last_sql = sql
    conn._last_params = list(params or [])
    log(f"{sql[:500]}{'...' if len(sql) > 500 else ''}, params={params}")
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            lastrowid = cur.lastrowid
            log(f"c_query executed successfully: lastrowid={lastrowid}")
            trace_out()
            return lastrowid
    except Exception as exc:
        warn(f"c_query execution failed: {exc}")
        setattr(exc, 'sql', sql)
        setattr(exc, 'params', params or [])
        trace_out()
        raise
    finally:
        conn._last_sql = None
        conn._last_params = None

def u_query(conn, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
    trace_in()
    conn._last_sql = sql
    conn._last_params = list(params or [])
    log(f"{sql[:500]}{'...' if len(sql) > 500 else ''}, params={params}")
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            rowcount = cur.rowcount
            log(f"u_query executed successfully: {rowcount} rows affected")
            trace_out()
            return rowcount
    except Exception as exc:
        warn(f"u_query execution failed: {exc}")
        setattr(exc, 'sql', sql)
        setattr(exc, 'params', params or [])
        trace_out()
        raise
    finally:
        conn._last_sql = None
        conn._last_params = None

def d_query(conn, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
    trace_in()
    conn._last_sql = sql
    conn._last_params = list(params or [])
    log(f"{sql[:500]}{'...' if len(sql) > 500 else ''}, params={params}")
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            rowcount = cur.rowcount
            log(f"d_query executed successfully: {rowcount} rows affected")
            trace_out()
            return rowcount
    except Exception as exc:
        warn(f"d_query execution failed: {exc}")
        setattr(exc, 'sql', sql)
        setattr(exc, 'params', params or [])
        trace_out()
        raise
    finally:
        conn._last_sql = None
        conn._last_params = None

def iso_now() -> str:
    trace_in()
    result = datetime.now().isoformat(sep=' ', timespec='microseconds')
    trace_out()
    return result

def json_out(obj: Union[Dict, List]) -> None:
    trace_in()
    json_str = json.dumps(obj, ensure_ascii=False)
    log(f"JSON output: {len(json_str)} characters")
    print(json_str)
    trace_out()

def json_success(data: Union[Dict, List]) -> JsonResponse:
    trace_in()
    result = {"status": "ok", "timestamp": iso_now(), "data": data}
    log(f"Success response created: data keys={list(data.keys()) if isinstance(data, dict) else 'not dict'}")
    trace_out()
    return result

def json_error(error: str, hint: Optional[str] = None) -> JsonResponse:
    trace_in()
    payload: JsonResponse = {"status": "error", "error": error, "timestamp": iso_now()}
    if hint is not None:
        payload["hint"] = hint
        log(f"Error response created: error={error}, hint={hint}")
    else:
        log(f"Error response created: error={error}")
    trace_out()
    return payload

def ensure_iso_timestamps(row: DatabaseRow, fields: Sequence[str]) -> None:
    trace_in()
    converted_count = 0
    for f in fields:
        v = row.get(f)
        if hasattr(v, 'isoformat'):
            row[f] = v.isoformat(sep=' ', timespec='microseconds')
            converted_count += 1
    log(f"Timestamp conversion completed: {converted_count} fields converted out of {len(fields)}")
    trace_out()

def normalize_meta(value: Union[str, int, float, bool, None]) -> Union[str, int, float, bool, None]:
    trace_in()
    # Currently just returns value as-is, but logged for future enhancement
    log(f"Meta normalization: value type={type(value)}")
    trace_out()
    return value

def count_json_chars(obj: Union[Dict, List]) -> int:
    trace_in()
    try:
        char_count = len(json.dumps(obj, ensure_ascii=False))
        log(f"JSON character count: {char_count}")
        trace_out()
        return char_count
    except Exception as e:
        warn(f"Failed to count JSON characters: {e}")
        trace_out()
        return 0

def validate_agent_identity(conn, agent_id: int, badge_ts: Optional[str]) -> bool:
    trace_in()
    if agent_id is None or badge_ts is None:
        warn("Agent validation failed: missing agent_id or badge_ts")
        trace_out()
        return False
    query = "SELECT COUNT(*) AS c FROM agents WHERE id=%s AND badge_ts=%s"
    results = r_query(conn, query, [int(agent_id), badge_ts])
    is_valid = bool(results and int(results[0].get("c") or 0) > 0)
    log(f"Agent identity validation: agent_id={agent_id}, badge_ts={badge_ts}, valid={is_valid}")
    trace_out()
    return is_valid


def schedule_file_move(conn, from_path: str, to_path: str) -> None:
    """Schedule a file move operation to be executed after DB commit."""
    trace_in()
    if not hasattr(conn, '_file_operations'):
        conn._file_operations = []
    operation = {
        'type': 'move',
        'from_path': from_path,
        'to_path': to_path,
        'status': 'scheduled',
        'temp_filename': None
    }
    conn._file_operations.append(operation)
    log(f"Scheduled file move: {from_path} -> {to_path}")
    trace_out()


def schedule_file_delete(conn, file_path: str) -> None:
    """Schedule a file delete operation (moves to /tmp) to be executed after DB commit."""
    trace_in()
    if not hasattr(conn, '_file_operations'):
        conn._file_operations = []
    # Generate unique temp filename
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
    conn._file_operations.append(operation)
    log(f"Scheduled file delete: {file_path} -> {temp_path}")
    trace_out()


def _execute_file_operations(conn) -> bool:
    """Execute all buffered file operations. Returns True if all succeed, False otherwise."""
    trace_in()
    if not hasattr(conn, '_file_operations') or not conn._file_operations:
        log("No file operations to execute")
        trace_out()
        return True
    
    log(f"Executing {len(conn._file_operations)} buffered file operations")
    
    # Execute all operations
    for operation in conn._file_operations:
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
                # Ensure destination directory exists
                to_path.parent.mkdir(parents=True, exist_ok=True)
                # Move file
                shutil.move(str(from_path), str(to_path))
                log(f"Moved file: {from_path} -> {to_path}")
                operation['status'] = 'completed'
                
            elif operation['type'] == 'delete':
                # Ensure /tmp directory exists
                to_path.parent.mkdir(parents=True, exist_ok=True)
                # Move file to temp
                shutil.move(str(from_path), str(to_path))
                log(f"Moved file to temp for deletion: {from_path} -> {to_path}")
                operation['status'] = 'completed'
                
        except Exception as e:
            warn(f"Failed to execute file operation {operation['type']}: {from_path} -> {to_path}: {str(e)}")
            report_error("file_operation", f"Failed to {operation['type']} file: {str(e)}")
            operation['status'] = 'failed'
            trace_out()
            return False
    
    log("All file operations executed successfully")
    trace_out()
    return True


def _rollback_file_operations(conn) -> bool:
    """Rollback all completed file operations. Returns True if all rollbacks succeed."""
    trace_in()
    if not hasattr(conn, '_file_operations') or not conn._file_operations:
        log("No file operations to rollback")
        trace_out()
        return True
    
    log(f"Rolling back {len(conn._file_operations)} file operations")
    
    # Rollback in reverse order
    for operation in reversed(conn._file_operations):
        if operation['status'] != 'completed':
            continue
        
        try:
            from_path = Path(operation['from_path'])
            to_path = Path(operation['to_path'])
            
            if operation['type'] == 'move':
                # Move back: to_path -> from_path
                if to_path.exists():
                    from_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(to_path), str(from_path))
                    log(f"Rolled back move: {to_path} -> {from_path}")
                else:
                    warn(f"Destination file does not exist for rollback: {to_path}")
                operation['status'] = 'rolled_back'
                
            elif operation['type'] == 'delete':
                # Move back from temp: to_path -> from_path
                if to_path.exists():
                    from_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(to_path), str(from_path))
                    log(f"Rolled back delete: {to_path} -> {from_path}")
                else:
                    warn(f"Temp file does not exist for rollback: {to_path}")
                operation['status'] = 'rolled_back'
                
        except Exception as e:
            warn(f"Failed to rollback file operation {operation['type']}: {str(e)}")
            report_error("file_operation", f"Failed to rollback {operation['type']}: {str(e)}")
            operation['status'] = 'rollback_failed'
            trace_out()
            return False
    
    log("All file operations rolled back successfully")
    trace_out()
    return True
