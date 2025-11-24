import json
import datetime as dt
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union, TypedDict
from hh.gateway.connection.conn import DatabaseRow
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

class JsonResponse(TypedDict, total=False):
    status: str
    timestamp: str
    data: Union[Dict, List]
    error: str
    hint: str

def iso_now() -> str:
    """Get current timestamp in ISO format with microseconds."""
    trace_in()
    result = datetime.now().isoformat(sep=' ', timespec='microseconds')
    trace_out()
    return result

def json_out(obj: Union[Dict, List]) -> None:
    """Print JSON object to stdout."""
    trace_in()
    json_str = json.dumps(obj, ensure_ascii=False)
    log(f"JSON output: {len(json_str)} characters")
    print(json_str)
    trace_out()

def json_success(data: Union[Dict, List]) -> JsonResponse:
    """Create a success JSON response."""
    trace_in()
    result = {"status": "ok", "timestamp": iso_now(), "data": data}
    log(f"Success response created: data keys={list(data.keys()) if isinstance(data, dict) else 'not dict'}")
    trace_out()
    return result

def json_error(error: str, hint: Optional[str] = None) -> JsonResponse:
    """Create an error JSON response."""
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
    """Convert datetime fields in a row to ISO format strings."""
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
    """Normalize meta value. Currently just returns value as-is."""
    trace_in()
    log(f"Meta normalization: value type={type(value)}")
    trace_out()
    return value

def count_json_chars(obj: Union[Dict, List]) -> int:
    """Count the number of characters in JSON representation of an object."""
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

def errno_to_code(errno: Optional[int], error_str: str) -> str:
    """Map MySQL errno to error code, or classify by string if errno is None."""
    trace_in()
    if errno is None:
        result = classify_by_string(error_str)
        log(f"Error code from string classification: {result}")
    else:
        errno_map = {
            1146: 'db_table_missing',
            1054: 'db_column_missing',
            1062: 'db_constraint',
            1216: 'db_foreign_key',
            1217: 'db_foreign_key',
            1451: 'db_foreign_key',
            1452: 'db_foreign_key',
            1064: 'db_syntax',
            1205: 'db_dead',
            1213: 'db_dead',
            2006: 'db_connection_lost',
            2013: 'db_connection_lost',
        }
        result = errno_map.get(errno, classify_by_string(error_str))
        log(f"Error code from errno mapping: errno={errno}, code={result}")
    trace_out()
    return result

def classify_by_string(error_str: str) -> str:
    """Classify error by string content when errno is not available."""
    trace_in()
    if "MySQL server has gone away" in error_str or "Lost connection" in error_str:
        result = "db_conn"
    elif "Deadlock found" in error_str or "1213" in error_str:
        result = "db_dead"
    elif "Duplicate entry" in error_str or "1062" in error_str:
        result = "db_constraint"
    elif "Access denied" in error_str or "1045" in error_str:
        result = "db_permission"
    elif "MySQL" in error_str or "pymysql" in str(type(Exception)):
        result = "db_execution"
    else:
        result = "sys_unk"
    log(f"String classification result: error_str={error_str[:50]}..., code={result}")
    trace_out()
    return result

def code_properties(code: str) -> str:
    """Get source for an error code."""
    trace_in()
    properties = {
        'db_conn': 'db',
        'db_dead': 'db',
        'db_constraint': 'db',
        'db_permission': 'db',
        'db_execution': 'db',
        'db_table_missing': 'db',
        'db_column_missing': 'db',
        'db_foreign_key': 'db',
        'db_syntax': 'db',
        'db_connection_lost': 'db',
        'val_required': 'business',
        'partial_success': 'business',
        'sys_unk': 'system',
    }
    result = properties.get(code, 'system')
    log(f"Code properties: code={code}, source={result}")
    trace_out()
    return result

def deserialize_json_blob(blob: Any, default: Any) -> Any:
    """Deserialize a JSON blob from database (handles bytes, strings, or already-parsed objects)."""
    trace_in()
    if blob in (None, '', b''):
        trace_out()
        return default
    if isinstance(blob, (bytes, bytearray)):
        blob = blob.decode('utf-8')
    if isinstance(blob, str):
        try:
            result = json.loads(blob)
            trace_out()
            return result
        except json.JSONDecodeError:
            trace_out()
            return default
    if isinstance(blob, (dict, list)):
        trace_out()
        return blob
    trace_out()
    return default


def normalize_datetime(value: Any) -> Optional[dt.datetime]:
    """Normalize a value to datetime object, handling various input types."""
    trace_in()
    if value is None:
        trace_out()
        return None
    if isinstance(value, dt.datetime):
        trace_out()
        return value
    if isinstance(value, dt.date):
        result = dt.datetime.combine(value, dt.time.min)
        trace_out()
        return result
    if isinstance(value, str):
        try:
            result = dt.datetime.fromisoformat(value)
            trace_out()
            return result
        except ValueError:
            trace_out()
            return None
    trace_out()
    return None


def classify_exception(exc: Exception, conn: Any = None) -> tuple[str, str, Dict[str, Union[str, int, bool]]]:
    """Classify an exception and return (code, source, extras)."""
    trace_in()
    extras: Dict[str, Union[str, int, bool]] = {}
    errno = getattr(exc, 'errno', None)
    if errno is not None:
        extras['errno'] = errno
    sqlstate = getattr(exc, 'sqlstate', None)
    if sqlstate:
        extras['sqlstate'] = sqlstate
    if hasattr(exc, 'args') and exc.args:
        extras['mysql_message'] = exc.args[-1]
    sql = getattr(exc, 'sql', getattr(conn, '_last_sql', None) if conn else None)
    if sql:
        extras['query'] = sql
    params = getattr(exc, 'params', getattr(conn, '_last_params', None) if conn else None)
    if params:
        extras['params'] = params
    error_str = str(exc)
    code = errno_to_code(errno, error_str)
    source = code_properties(code)
    log(f"Exception classified: code={code}, source={source}")
    result = code, source, {k: v for k, v in extras.items() if v is not None}
    trace_out()
    return result

