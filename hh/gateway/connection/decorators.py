import os
import sys
import time
import pymysql
from typing import Dict, List, Optional, Callable, Union, TypedDict
from functools import wraps
from hh.gateway.connection.connection import get_connection, validate_agent_identity
from hh.deploy.utils import detect_project_context
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.response.json_standard import (
    resolve_error, ERROR_CODES
)
from hh.render.config.config import cc, mc
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

def errno_to_code(errno: Optional[int], error_str: str) -> str:
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

def code_properties(code: str) -> tuple[bool, str]:
    trace_in()
    properties = {
        'db_conn': (True, 'db'),
        'db_dead': (True, 'db'),
        'db_constraint': (False, 'db'),
        'db_permission': (False, 'db'),
        'db_execution': (False, 'db'),
        'db_table_missing': (False, 'db'),
        'db_column_missing': (False, 'db'),
        'db_foreign_key': (False, 'db'),
        'db_syntax': (False, 'db'),
        'db_connection_lost': (True, 'db'),
        'val_required': (False, 'business'),
        'partial_success': (False, 'business'),
        'sys_unk': (False, 'system'),
    }
    result = properties.get(code, (False, 'system'))
    log(f"Code properties: code={code}, retryable={result[0]}, source={result[1]}")
    trace_out()
    return result

def classify_exception(exc: Exception, conn: object) -> tuple[str, bool, str, Dict[str, Union[str, int, bool]]]:
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
    sql = getattr(exc, 'sql', getattr(conn, '_last_sql', None))
    if sql:
        extras['query'] = sql
    params = getattr(exc, 'params', getattr(conn, '_last_params', None))
    if params:
        extras['params'] = params
    error_str = str(exc)
    code = errno_to_code(errno, error_str)
    retryable, source = code_properties(code)
    log(f"Exception classified: code={code}, retryable={retryable}, source={source}")
    result = code, retryable, source, {k: v for k, v in extras.items() if v is not None}
    trace_out()
    return result

def should_retry(code: str, retryable: bool, attempt: int, max_retries: int) -> bool:
    trace_in()
    if attempt >= max_retries:
        log(f"Retry decision: attempt={attempt}, max_retries={max_retries}, retry=False (max reached)")
        trace_out()
        return False
    result = retryable
    log(f"Retry decision: attempt={attempt}, max_retries={max_retries}, retryable={retryable}, result={result}")
    trace_out()
    return result

def get_config_defaults() -> Dict[str, Union[str, int, bool]]:
    trace_in()
    config = {
        "default_transaction": cc("config_db_default_transaction") or "auto", 
        "default_retries": mc("config_db_default_retries") or 2,
        "retry_delay_ms": mc("config_db_retry_delay"),
        "error_mode": cc("config_db_error_mode") or "structured",
        "log_level": cc("config_db_log_level") or "info"
    }
    log(f"Configuration defaults loaded: {config}")
    trace_out()
    return config


def with_connection(
    transaction: Optional[bool] = None,
    retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    dict_cursor: bool = True,
    agent_validation: bool = False,
    log_scope: Optional[str] = None
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Union[str, int, bool]]:
            trace_in()
            gateway = get_gateway()
            if not gateway:
                warn("No gateway available")
                trace_out()
                return False
            config = get_config_defaults()
            if retries is None:
                actual_retries = config["default_retries"] if config["default_retries"] > 0 else 0
            else:
                actual_retries = retries
            if retry_delay is None:
                retry_delay_ms = config["retry_delay_ms"]
                actual_retry_delay = retry_delay_ms / 1000.0 if retry_delay_ms > 0 else 0.0
            else:
                actual_retry_delay = retry_delay
            
            # Buffer configuration details
            config_details = []
            config_details.append(f"retries={actual_retries}")
            config_details.append(f"delay={actual_retry_delay}")
            config_details.append(f"dict={dict_cursor}")
            config_details.append(f"agent={agent_validation}")
            
            if not args or not hasattr(args[0], 'cursor'):
                pass
            agent_id = None
            badge_ts = None
            if agent_validation:
                agent_id = kwargs.get('agent_id')
                badge_ts = kwargs.get('badge_ts')
                config_details.append(f"aid={agent_id}")
                config_details.append(f"ts={badge_ts}")
            
            auto_transaction = transaction
            if auto_transaction is None:
                if config["default_transaction"] == "auto":
                    func_name = func.__name__.lower()
                    auto_transaction = any(word in func_name for word in ['insert', 'update', 'delete', 'create', 'modify', 'sip', 'bulk'])
                elif config["default_transaction"] == "true":
                    auto_transaction = True
                else:
                    auto_transaction = False
            
            config_details.append(f"txn={auto_transaction}")
            last_exception = None
            start_time = time.time()
            for attempt in range(actual_retries + 1):
                conn = None
                log(f"{func.__name__}: Connection attempt {attempt + 1}/{actual_retries + 1} - {', '.join(config_details)}")
                try:
                    conn = get_connection(dict_cursor=dict_cursor)
                    if not conn:
                        report_error("connection", "Could not connect to database")
                        trace_out()
                        return False
                    if agent_validation and agent_id and badge_ts:
                        if not validate_agent_identity(conn, agent_id, badge_ts):
                            report_error("action", "Agent identity validation failed")
                            trace_out()
                            return False
                    if auto_transaction:
                        with conn.cursor() as cur:
                            cur.execute("START TRANSACTION")
                    
                    # Check if this is a class method by looking for 'self' parameter
                    import inspect
                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    
                    if params and params[0] == 'self':
                        # This is a class method, call with self as first arg, conn as second
                        result = func(args[0], conn, *args[1:], **kwargs)
                    else:
                        # This is a regular function, call with conn as first arg
                        result = func(conn, *args[1:], **kwargs)
                    
                    if auto_transaction:
                        if is_error():
                            conn.rollback()
                            log("Transaction rolled back due to errors")
                        else:
                            # Execute buffered file operations before committing DB
                            from hh.gateway.connection.connection import _execute_file_operations, _rollback_file_operations
                            if not _execute_file_operations(conn):
                                # File operations failed, rollback file ops and DB transaction
                                warn("File operations failed, rolling back")
                                _rollback_file_operations(conn)
                                conn.rollback()
                                log("Transaction rolled back due to file operation errors")
                            elif is_error():
                                # Check for errors after file operations
                                warn("Errors detected after file operations, rolling back")
                                _rollback_file_operations(conn)
                                conn.rollback()
                                log("Transaction rolled back due to errors after file operations")
                            else:
                                # All good, commit DB transaction
                                conn.commit()
                                log("Transaction committed successfully after file operations")
                    duration_ms = int((time.time() - start_time) * 1000)
                    log(f"{func.__name__}: Function execution successful, duration={duration_ms}ms")
                    trace_out()
                    return result
                except (pymysql.Error, pymysql.OperationalError, pymysql.ProgrammingError, 
                        pymysql.IntegrityError, pymysql.DataError, pymysql.NotSupportedError,
                        pymysql.InternalError, pymysql.InterfaceError) as exc:
                    last_exception = exc
                    if conn and auto_transaction:
                        # Rollback any file operations that were executed
                        try:
                            from hh.gateway.connection.connection import _rollback_file_operations
                            _rollback_file_operations(conn)
                        except:
                            pass
                        try:
                            conn.rollback()
                        except:
                            pass
                    code, retryable, source, extras = classify_exception(exc, conn)
                    message, _, _ = resolve_error(code)
                    if should_retry(code, retryable, attempt, actual_retries):
                        if log_scope:
                            print(f"[{log_scope}] Retry {attempt + 1}/{actual_retries}: {message}", file=sys.stderr)
                        time.sleep(actual_retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        break
                except Exception as exc:
                    # Re-raise non-database exceptions so they can be handled properly
                    raise
                        
                finally:
                    if conn:
                        try:
                            conn.close()
                        except:
                            pass
            duration_ms = int((time.time() - start_time) * 1000)
            code, retryable, source, extras = classify_exception(last_exception, conn)
            message, _, _ = resolve_error(code)
            trace_out()
            gateway = get_gateway()
            if gateway:
                report_error("connection", {
                    "message": message,
                    "code": code,
                    "retryable": retryable,
                    "source": source,
                    "info": extras
                })
            return False
        return wrapper
    return decorator

def db_read(func: Callable) -> Callable:
    trace_in()
    log(f"{func.__name__}")
    trace_out()
    return with_connection(transaction=False, retries=0)(func)

def db_write(func: Callable) -> Callable:
    trace_in()
    log(f"{func.__name__}")
    trace_out()
    return with_connection(transaction=True, retries=2)(func)

def root_read(func: Callable) -> Callable:
    trace_in()
    log(f"{func.__name__}")
    trace_out()
    return with_root_connection(transaction=False, retries=0)(func)

def root_write(func: Callable) -> Callable:
    trace_in()
    log(f"{func.__name__}")
    trace_out()
    return with_root_connection(transaction=True, retries=2)(func)

def with_mysql_connection(
    transaction: Optional[bool] = None,
    retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    dict_cursor: bool = True,
    log_scope: Optional[str] = None
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Union[str, int, bool]]:
            trace_in()
            gateway = get_gateway()
            if not gateway:
                warn("No gateway available")
                trace_out()
                return False
            
            # Get root password from command line args
            root_password = gateway.get_arg('password')
            if not root_password:
                warn("Root password required for MySQL system connection")
                report_error("action", "Root password required")
                trace_out()
                return False
            
            # Get DSN info but override user/password and set database to None
            from hh.gateway.connection.connection import load_dsn
            dsn = load_dsn()
            if dsn:
                # Override with root credentials and no specific database
                dsn['user'] = 'root'
                dsn['password'] = root_password
                dsn['database'] = None  # Connect to MySQL system, not project database
            else:
                warn("Cannot create MySQL system connection: DSN not available")
                trace_out()
                return False
            
            debug(f"MySQL system DSN configuration: {dsn}")
            
            config = get_config_defaults()
            if retries is None:
                actual_retries = config["default_retries"] if config["default_retries"] > 0 else 0
            else:
                actual_retries = retries
            if retry_delay is None:
                retry_delay_ms = config["retry_delay_ms"]
                actual_retry_delay = retry_delay_ms / 1000.0 if retry_delay_ms > 0 else 0.0
            else:
                actual_retry_delay = retry_delay
            
            log(f"MySQL system connection decorator config: retries={actual_retries}, retry_delay={actual_retry_delay}, dict_cursor={dict_cursor}")
            
            auto_transaction = transaction
            if auto_transaction is None:
                if config["default_transaction"] == "auto":
                    func_name = func.__name__.lower()
                    auto_transaction = any(word in func_name for word in ['insert', 'update', 'delete', 'create', 'modify', 'sip', 'bulk'])
                    log(f"Auto transaction determined by function name: {func_name} -> {auto_transaction}")
                elif config["default_transaction"] == "true":
                    auto_transaction = True
                else:
                    auto_transaction = False
            
            log(f"MySQL system transaction mode: {auto_transaction}")
            last_exception = None
            start_time = time.time()
            
            for attempt in range(actual_retries + 1):
                conn = None
                log(f"MySQL system connection attempt {attempt + 1}/{actual_retries + 1}")
                try:
                    # Create connection with root credentials to MySQL system
                    import pymysql
                    cursorclass = pymysql.cursors.DictCursor if dict_cursor else None
                    
                    debug(f"Attempting PyMySQL connection to MySQL system with: host={dsn['host']}, user={dsn['user']}")
                    
                    if cursorclass:
                        conn = pymysql.connect(**dsn, cursorclass=cursorclass)
                        log(f"MySQL system connection established with DictCursor: host={dsn['host']}")
                    else:
                        conn = pymysql.connect(**dsn)
                        log(f"MySQL system connection established: host={dsn['host']}")
                    
                    if not conn:
                        report_error("connection", "Could not connect to MySQL system as root")
                        trace_out()
                        return False
                    
                    if auto_transaction:
                        with conn.cursor() as cur:
                            cur.execute("START TRANSACTION")
                    
                    # Check if this is a class method by looking for 'self' parameter
                    import inspect
                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    
                    if params and params[0] == 'self':
                        # This is a class method, call with self as first arg, conn as second
                        result = func(args[0], conn, *args[1:], **kwargs)
                    else:
                        # This is a regular function, call with conn as first arg
                        result = func(conn, *args[1:], **kwargs)
                    
                    if auto_transaction:
                        if is_error():
                            conn.rollback()
                            log("MySQL system transaction rolled back due to errors")
                        else:
                            conn.commit()
                            log("MySQL system transaction committed successfully")
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    log(f"MySQL system function execution successful: {func.__name__}, duration={duration_ms}ms")
                    trace_out()
                    return result
                    
                except (pymysql.Error, pymysql.OperationalError, pymysql.ProgrammingError, 
                        pymysql.IntegrityError, pymysql.DataError, pymysql.NotSupportedError,
                        pymysql.InternalError, pymysql.InterfaceError) as exc:
                    last_exception = exc
                    if conn and auto_transaction:
                        try:
                            conn.rollback()
                        except:
                            pass
                    code, retryable, source, extras = classify_exception(exc, conn)
                    message, _, _ = resolve_error(code)
                    if should_retry(code, retryable, attempt, actual_retries):
                        if log_scope:
                            print(f"[{log_scope}] MySQL system retry {attempt + 1}/{actual_retries}: {message}", file=sys.stderr)
                        time.sleep(actual_retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        break
                except Exception as exc:
                    # Re-raise non-database exceptions so they can be handled properly
                    raise
                        
                finally:
                    if conn:
                        try:
                            conn.close()
                        except:
                            pass
            
            duration_ms = int((time.time() - start_time) * 1000)
            code, retryable, source, extras = classify_exception(last_exception, conn)
            message, _, _ = resolve_error(code)
            trace_out()
            gateway = get_gateway()
            if gateway:
                report_error("connection", {
                    "message": message,
                    "code": code,
                    "retryable": retryable,
                    "source": source,
                    "info": extras
                })
            return False
        return wrapper
    return decorator

def mysql_read(func: Callable) -> Callable:
    trace_in()
    log(f"{func.__name__}")
    trace_out()
    return with_mysql_connection(transaction=False, retries=0)(func)

def mysql_write(func: Callable) -> Callable:
    trace_in()
    log(f"{func.__name__}")
    trace_out()
    return with_mysql_connection(transaction=True, retries=2)(func)

def with_root_connection(
    transaction: Optional[bool] = None,
    retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
    dict_cursor: bool = True,
    log_scope: Optional[str] = None
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Union[str, int, bool]]:
            trace_in()
            gateway = get_gateway()
            if not gateway:
                warn("No gateway available")
                trace_out()
                return False
            
            # Get root password from command line args
            root_password = gateway.get_arg('password')
            if not root_password:
                warn("Root password required for root connection")
                report_error("action", "Root password required")
                trace_out()
                return False
            
            # Get DSN info but override user/password
            # When running as root, try to detect project owner and use their config
            dsn = None
            if os.geteuid() == 0:  # Running as root
                project_name, _ = detect_project_context()
                if project_name:
                    # Try to find project owner's config
                    import pwd
                    try:
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
                                }
                                log(f"Using project owner's config: {owner_config}")
                    except Exception as e:
                        warn(f"Failed to detect project owner config: {e}")
            
            # Fallback to standard DSN loading
            if not dsn:
                from hh.gateway.connection.connection import load_dsn
                dsn = load_dsn()
                if dsn:
                    # Override with root credentials
                    dsn['user'] = 'root'
                    dsn['password'] = root_password
            
            if not dsn:
                warn("Cannot create root connection: DSN not available")
                trace_out()
                return False
            
            # DSN already has root credentials set above
            root_dsn = dsn
            
            debug(f"Root DSN configuration: {root_dsn}")
            debug(f"Root DSN host: {root_dsn.get('host', 'Not set')}")
            debug(f"Root DSN user: {root_dsn.get('user', 'Not set')}")
            debug(f"Root DSN database: {root_dsn.get('database', 'Not set')}")
            debug(f"Root DSN password length: {len(root_dsn.get('password', '')) if root_dsn.get('password') else 'Not set'}")
            
            config = get_config_defaults()
            if retries is None:
                actual_retries = config["default_retries"] if config["default_retries"] > 0 else 0
            else:
                actual_retries = retries
            if retry_delay is None:
                retry_delay_ms = config["retry_delay_ms"]
                actual_retry_delay = retry_delay_ms / 1000.0 if retry_delay_ms > 0 else 0.0
            else:
                actual_retry_delay = retry_delay
            
            log(f"Root connection decorator config: retries={actual_retries}, retry_delay={actual_retry_delay}, dict_cursor={dict_cursor}")
            
            auto_transaction = transaction
            if auto_transaction is None:
                if config["default_transaction"] == "auto":
                    func_name = func.__name__.lower()
                    auto_transaction = any(word in func_name for word in ['insert', 'update', 'delete', 'create', 'modify', 'sip', 'bulk'])
                    log(f"Auto transaction determined by function name: {func_name} -> {auto_transaction}")
                elif config["default_transaction"] == "true":
                    auto_transaction = True
                else:
                    auto_transaction = False
            
            log(f"Root transaction mode: {auto_transaction}")
            last_exception = None
            start_time = time.time()
            
            for attempt in range(actual_retries + 1):
                conn = None
                log(f"Root connection attempt {attempt + 1}/{actual_retries + 1}")
                try:
                    # Create connection with root credentials
                    import pymysql
                    cursorclass = pymysql.cursors.DictCursor if dict_cursor else None
                    
                    debug(f"Attempting PyMySQL connection with: host={root_dsn['host']}, user={root_dsn['user']}, database={root_dsn['database']}")
                    debug(f"Connection parameters: {root_dsn}")
                    
                    if cursorclass:
                        conn = pymysql.connect(**root_dsn, cursorclass=cursorclass)
                        log(f"Root database connection established with DictCursor: host={root_dsn['host']}, database={root_dsn['database']}")
                    else:
                        conn = pymysql.connect(**root_dsn)
                        log(f"Root database connection established: host={root_dsn['host']}, database={root_dsn['database']}")
                    
                    debug(f"Connection object created: {type(conn)}")
                    debug(f"Connection host info: {getattr(conn, 'host', 'Not available')}")
                    
                    if not conn:
                        report_error("connection", "Could not connect to database as root")
                        trace_out()
                        return False
                    
                    if auto_transaction:
                        with conn.cursor() as cur:
                            cur.execute("START TRANSACTION")
                    
                    # Check if this is a class method by looking for 'self' parameter
                    import inspect
                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    
                    if params and params[0] == 'self':
                        # This is a class method, call with self as first arg, conn as second
                        result = func(args[0], conn, *args[1:], **kwargs)
                    else:
                        # This is a regular function, call with conn as first arg
                        result = func(conn, *args[1:], **kwargs)
                    
                    if auto_transaction:
                        if is_error():
                            conn.rollback()
                            log("Root transaction rolled back due to errors")
                        else:
                            conn.commit()
                            log("Root transaction committed successfully")
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    log(f"Root function execution successful: {func.__name__}, duration={duration_ms}ms")
                    trace_out()
                    return result
                    
                except (pymysql.Error, pymysql.OperationalError, pymysql.ProgrammingError, 
                        pymysql.IntegrityError, pymysql.DataError, pymysql.NotSupportedError,
                        pymysql.InternalError, pymysql.InterfaceError) as exc:
                    last_exception = exc
                    if conn and auto_transaction:
                        try:
                            conn.rollback()
                        except:
                            pass
                    code, retryable, source, extras = classify_exception(exc, conn)
                    message, _, _ = resolve_error(code)
                    if should_retry(code, retryable, attempt, actual_retries):
                        if log_scope:
                            print(f"[{log_scope}] Root retry {attempt + 1}/{actual_retries}: {message}", file=sys.stderr)
                        time.sleep(actual_retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        break
                except Exception as exc:
                    # Re-raise non-database exceptions so they can be handled properly
                    raise
                        
                finally:
                    if conn:
                        try:
                            conn.close()
                        except:
                            pass
            
            duration_ms = int((time.time() - start_time) * 1000)
            code, retryable, source, extras = classify_exception(last_exception, conn)
            message, _, _ = resolve_error(code)
            trace_out()
            gateway = get_gateway()
            if gateway:
                report_error("connection", {
                    "message": message,
                    "code": code,
                    "retryable": retryable,
                    "source": source,
                    "info": extras
                })
            return False
        return wrapper
    return decorator

