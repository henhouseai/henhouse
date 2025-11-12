import configparser
import json
import os
import pymysql
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union, TypedDict
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.deploy.utils import detect_project_context

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
    
    # Check if we're in deployed mode (IPC context)
    tier = os.environ.get('HH_TIER')
    if tier:
        # Deployed mode: use tier-based DSN from secrets directory
        project_name, _ = detect_project_context()
        if project_name:
            secrets_path = f'/srv/{project_name}/secrets/dsn_{tier}.cnf'
            if os.path.exists(secrets_path):
                config.read(secrets_path)
                dsn = {
                    'host': config.get('client', 'host', fallback='localhost'),
                    'user': config.get('client', 'user', fallback='root'),
                    'password': config.get('client', 'password', fallback=''),
                    'database': config.get('client', 'database', fallback=project_name),
                }
                log(f"DSN loaded from secrets: {secrets_path}, tier={tier}, host={dsn['host']}, database={dsn['database']}")
                trace_out()
                return dsn
            else:
                warn(f"Secrets DSN file not found: {secrets_path}")
                trace_out()
                return None
        else:
            warn("Could not detect project name for tier-based DSN")
            trace_out()
            return None
    
    # Dev mode: fall back to user's home directory config
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
        log(f"DSN loaded from dev config: {path}, host={dsn['host']}, database={dsn['database']}")
        trace_out()
        return dsn
    else:
        warn(f"Configuration file not found: {path}")
        trace_out()
        return None

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
