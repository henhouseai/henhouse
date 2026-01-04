import os
import configparser
from typing import Any, Optional, Dict, List, Sequence, Union, Tuple, TypedDict, TYPE_CHECKING, cast
from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.system.dependency import register_dependency

if TYPE_CHECKING:
    import pymysql as pymysql_type  # type: ignore[import-untyped]

# Register pymysql as a dependency
pymysql = None  # type: ignore[assignment]

@register_dependency("pymysql")
def _load_pymysql():
    global pymysql
    try:
        import pymysql as _pymysql  # type: ignore[import-untyped]
        pymysql = _pymysql  # type: ignore[assignment]
        return True
    except ImportError:
        return False

_load_pymysql()

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

def _build_ssl_dict(config: configparser.ConfigParser, prefix: str = '') -> Optional[Dict[str, Union[str, bool, int]]]:
    """Build SSL dictionary from config file for PyMySQL.
    
    Returns None if no SSL/TLS configuration is present (plain text connection).
    If SSL config is present, returns SSL dict with verify_mode controlling strictness:
    - 3: verify cert + hostname (VERIFY_IDENTITY - strictest)
    - 2: verify cert, hostname check disabled (VERIFY_CA)
    - 1: optional verify; hostname check disabled (CERT_OPTIONAL)
    - 0: no verify; hostname check disabled (least strict)
    """
    ssl_ca = config.get('client', f'{prefix}ssl_ca', fallback=None)
    ssl_cert = config.get('client', f'{prefix}ssl_cert', fallback=None)
    ssl_key = config.get('client', f'{prefix}ssl_key', fallback=None)
    # For verify_mode, if prefixed version doesn't exist, fall back to main ssl_verify_mode
    if prefix and not config.has_option('client', f'{prefix}ssl_verify_mode'):
        ssl_verify_mode = config.get('client', 'ssl_verify_mode', fallback=None)
    else:
        ssl_verify_mode = config.get('client', f'{prefix}ssl_verify_mode', fallback=None)
    
    # If no SSL configuration is present at all, return None (plain text connection)
    if not ssl_ca and not ssl_cert and not ssl_key and not ssl_verify_mode:
        debug(f"No SSL/TLS configuration found for {prefix}, using plain text connection")
        return None
    
    ssl_check_hostname = config.get('client', f'{prefix}ssl_check_hostname', fallback='true')

    # Determine verify_mode from config (defaults to 2 if not set or invalid)
    verify_mode = 2  # Default to strict
    if ssl_verify_mode:
        try:
            verify_mode = int(ssl_verify_mode)
            if verify_mode not in (0, 1, 2, 3):
                verify_mode = 2
        except (ValueError, TypeError):
            verify_mode = 2
    
    debug(f"SSL config: ssl_verify_mode='{ssl_verify_mode}', verify_mode={verify_mode}, ssl_ca={ssl_ca}")

    # If verify_mode requires CA but CA is not present, raise error
    if verify_mode in (2, 3) and not ssl_ca:
        raise ValueError(f"SSL verify_mode={verify_mode} but {prefix}ssl_ca is not configured in config file")

    # Map verify_mode to Python SSL settings
    # Mode 3: verify_mode=2 (CERT_REQUIRED) + check_hostname=True
    # Mode 2: verify_mode=2 (CERT_REQUIRED) + check_hostname=False
    # Mode 1: verify_mode=1 (CERT_OPTIONAL) + check_hostname=False
    # Mode 0: verify_mode=0 (CERT_NONE) + check_hostname=False
    python_verify_mode = 2 if verify_mode in (2, 3) else (1 if verify_mode == 1 else 0)
    check_hostname = verify_mode == 3
    
    ssl_dict: Dict[str, Union[str, bool, int]] = {
        'verify_mode': python_verify_mode,
        'check_hostname': check_hostname
    }

    # Include CA when available (required for modes 2,3; optional for mode 1; NOT for mode 0)
    if ssl_ca and verify_mode > 0:
        ssl_dict['ca'] = ssl_ca

    if ssl_cert:
        ssl_dict['cert'] = ssl_cert
    if ssl_key:
        ssl_dict['key'] = ssl_key

    debug(f"SSL dict built: {ssl_dict}")
    return ssl_dict

def _load_dsn(project_name: str) -> Tuple[Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]], Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]], Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]]:
    """Load DSN triple (main, cache, history) from config file with SSL support.
    
    Returns:
        Tuple of (main_dsn, cache_dsn, history_dsn), each may be None
    """
    trace_in()
    config = configparser.ConfigParser()
    path = os.path.expanduser(f'~/.{project_name}.cnf')
    if os.path.exists(path):
        config.read(path)
        dsn: Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]] = {
            'host': config.get('client', 'host', fallback='localhost'),
            'user': config.get('client', 'user', fallback='root'),
            'password': config.get('client', 'password', fallback=''),
            'database': config.get('client', 'database', fallback=project_name),
            'port': config.getint('client', 'port', fallback=3306)
        }
        
        # SSL/TLS is optional - only include if configured
        ssl_dict = _build_ssl_dict(config, '')
        if ssl_dict is not None:
            dsn['ssl'] = ssl_dict
        
        log(f"DSN loaded from config: {path}, host={dsn['host']}, database={dsn['database']}")
        
        cache_dsn: Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]] = {
            'host': config.get('client', 'cache_host', fallback=dsn['host']),
            'user': config.get('client', 'cache_user', fallback=dsn['user']),
            'password': config.get('client', 'cache_password', fallback=dsn['password']),
            'database': config.get('client', 'cache_database', fallback=f"{dsn['database']}_cache"),
            'port': config.getint('client', 'cache_port', fallback=dsn['port'])
        }
        
        # SSL/TLS is optional for cache database - only include if configured
        # Try cache-specific SSL first, fallback to main SSL if cache_ssl_ca not present
        cache_ssl_dict = _build_ssl_dict(config, 'cache_')
        if cache_ssl_dict is None:
            # Fallback to main SSL config
            cache_ssl_dict = _build_ssl_dict(config, '')
        if cache_ssl_dict is not None:
            cache_dsn['ssl'] = cache_ssl_dict
        
        # History database - only create DSN if explicitly configured (database doesn't exist yet)
        history_dsn = None
        history_host = config.get('client', 'history_host', fallback=None)
        if history_host:
            history_dsn = {
                'host': history_host,
                'user': config.get('client', 'history_user', fallback=dsn['user']),
                'password': config.get('client', 'history_password', fallback=dsn['password']),
                'database': config.get('client', 'history_database', fallback=f"{dsn['database']}_history"),
                'port': config.getint('client', 'history_port', fallback=dsn['port'])
            }
            # SSL/TLS is optional for history database - only include if configured
            # Try history-specific SSL first, fallback to main SSL if history_ssl_ca not present
            history_ssl_dict = _build_ssl_dict(config, 'history_')
            if history_ssl_dict is None:
                # Fallback to main SSL config
                history_ssl_dict = _build_ssl_dict(config, '')
            if history_ssl_dict is not None:
                history_dsn['ssl'] = history_ssl_dict
        
        trace_out()
        return dsn, cache_dsn, history_dsn
    else:
        log(f"Configuration file not found: {path}")
        trace_out()
        return None, None, None

def _load_root_dsn(project_name: str) -> Tuple[Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]], Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]], Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]]:
    """Load root DSN triple (main, cache, history) from root config file.
    
    This function reads from /root/.{project_name}-install.cnf which contains
    root credentials and configuration for all three database servers.
    
    TODO: Full implementation pending ask 1211 (root config file system).
    Currently returns None for all DSNs as a stub.
    
    Returns:
        Tuple of (main_dsn, cache_dsn, history_dsn), each may be None
    """
    trace_in()
    # Stub implementation - will be fully implemented in ask 1211
    # Root config file will contain:
    # - MySQL root password for each database server (main, cache, history)
    # - Database hostnames
    # - SSL certificate paths
    # - All four user tier credentials (for installer use)
    log("Root DSN loading not yet implemented (stub - see ask 1211)")
    trace_out()
    return None, None, None

class Connection:
    """Gateway-owned connection manager for main, cache, and history databases."""
    
    def __init__(self, dry_run: bool = False):
        self.main: Optional[Any] = None
        self.cache: Optional[Any] = None
        self.history: Optional[Any] = None
        self._main_transaction_started: bool = False
        self._cache_transaction_started: bool = False
        self._initialized: bool = False
        self._dry_run: bool = dry_run
        self._cache_buffer: List[Tuple[str, str, Optional[Sequence[Union[str, int, float, bool, None]]]]] = []
    
    def _get_main_dsn(self, project_name: str) -> Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]:
        """Get main database DSN. Override in subclasses for root/MySQL connections."""
        trace_in()
        main_dsn, _, _ = _load_dsn(project_name)
        trace_out()
        return main_dsn
    
    def _get_cache_dsn(self, project_name: str) -> Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]:
        """Get cache database DSN. Override in subclasses for root connections.
        Returns None to use default from _load_dsn()."""
        trace_in()
        trace_out()
        return None
    
    def _get_history_dsn(self, project_name: str) -> Optional[Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]]]:
        """Get history database DSN. Override in subclasses for root connections.
        Returns None to use default from _load_dsn()."""
        trace_in()
        trace_out()
        return None
    
    def _detect_user_tier_level(self, project_name: str, username: str) -> int:
        """Detect user tier level from DSN username. Returns tier level (0 if unknown)."""
        trace_in()
        tier_level = 0  # Default to unknown
        try:
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
        log(f"User tier level: {tier_level}")
        trace_out()
        return tier_level
    
    def initialize(self) -> int:
        """Open connections to all databases. Returns user tier level (0 if unknown)."""
        trace_in()
        if self._initialized:
            log("Connection already initialized")
            trace_out()
            return 0
        
        tier_level = 0
        try:
            # Detect project context once at the start
            project_name, _ = detect_project_context()
            
            # Get main DSN (may be overridden by subclasses)
            main_dsn = self._get_main_dsn(project_name)
            
            if not main_dsn:
                log("Cannot initialize connections: main DSN not available. Connection methods will be no-op.")
                trace_out()
                return 0
            
            # Detect user tier level from DSN username
            if project_name:
                tier_level = self._detect_user_tier_level(project_name, str(main_dsn.get('user', '') or ''))
            
            # Get cache DSN (may be overridden by subclasses, otherwise use standard loading)
            cache_dsn = self._get_cache_dsn(project_name)
            if not cache_dsn:
                _, cache_dsn, _ = _load_dsn(project_name)
            
            # History database - skip entirely (database doesn't exist yet)
            history_dsn = None
            
            # Open main database connection
            assert pymysql is not None
            cursorclass = pymysql.cursors.DictCursor  # type: ignore[attr-defined]
            if pymysql is None:
                warn("pymysql is None")
                trace_out()
                return 0
            
            # Extract SSL dict from main_dsn and pass separately (only if present)
            main_ssl = main_dsn.pop('ssl', None) if isinstance(main_dsn.get('ssl'), dict) else None
            if main_ssl is not None:
                self.main = pymysql.connect(**main_dsn, ssl=main_ssl, cursorclass=cursorclass)  # type: ignore[call-arg]
            else:
                self.main = pymysql.connect(**main_dsn, cursorclass=cursorclass)  # type: ignore[call-arg]
            log(f"Main database connection opened: host={main_dsn['host']}, database={main_dsn.get('database', 'None')}")
            
            # Open cache database connection
            if cache_dsn:
                cache_ssl = cache_dsn.pop('ssl', None) if isinstance(cache_dsn.get('ssl'), dict) else None
                if cache_ssl is not None:
                    self.cache = pymysql.connect(**cache_dsn, ssl=cache_ssl, cursorclass=cursorclass)  # type: ignore[call-arg]
                else:
                    self.cache = pymysql.connect(**cache_dsn, cursorclass=cursorclass)  # type: ignore[call-arg]
                log(f"Cache database connection opened: host={cache_dsn['host']}, database={cache_dsn['database']}")
            else:
                warn("Cache DSN not available, using main database for cache")
                self.cache = self.main
            
            # History database connection - only attempt if explicitly configured
            # (History database doesn't exist yet, so skip unless history_host is set)
            self.history = None
            
            self._initialized = True
            log("All database connections initialized successfully")
            trace_out()
            return tier_level
            
        except Exception as e:
            warn(f"Failed to initialize database connections: {e}")
            # Clean up any partial connections
            self.close()
            trace_out()
            return 0
    
    def close(self) -> None:
        """Close all database connections."""
        trace_in()
        
        if not self._initialized:
            log("No connections to close (not initialized)")
            trace_out()
            return
        
        log("Starting connection cleanup...")
        
        if self.history and self.history is not self.main and self.history is not self.cache:
            try:
                if hasattr(self.history, 'open') and self.history.open:
                    self.history.close()
                    log("History database connection closed")
            except Exception as e:
                warn(f"Error closing history connection: {e}")
            self.history = None
        
        if self.cache and self.cache is not self.main:
            try:
                if hasattr(self.cache, 'open') and self.cache.open:
                    self.cache.close()
                    log("Cache database connection closed")
            except Exception as e:
                warn(f"Error closing cache connection: {e}")
            self.cache = None
        
        if self.main:
            try:
                if hasattr(self.main, 'open') and self.main.open:
                    self.main.close()
                    log("Main database connection closed")
            except Exception as e:
                warn(f"Error closing main connection: {e}")
            self.main = None
        
        self._main_transaction_started = False
        self._cache_transaction_started = False
        self._cache_buffer.clear()
        self._initialized = False
        log("All database connections closed successfully")
        trace_out()
    
    def is_initialized(self) -> bool:
        """Check if connections have been initialized."""
        return self._initialized
    
    def commit(self) -> None:
        """Commit the main database transaction. If dry_run is enabled, rolls back instead.
        Cache transactions are handled independently by write_cache()."""
        trace_in()
        if not self._main_transaction_started:
            log("No main transaction to commit")
            trace_out()
            return
        
        if self._dry_run:
            log("Dry run mode enabled - rolling back main transaction instead of committing")
            self.rollback()
            trace_out()
            return
        
        log("Committing main database transaction...")
        
        try:
            if self.main:
                self.main.commit()
                log("Transaction committed on main database")
            
            self._main_transaction_started = False
            log("Main transaction committed successfully")
        except Exception as e:
            warn(f"Failed to commit main transaction: {e}")
            raise
        finally:
            trace_out()
    
    def rollback(self) -> None:
        """Rollback the main database transaction.
        Cache transactions are handled independently by write_cache()."""
        trace_in()
        if not self._main_transaction_started:
            log("No main transaction to rollback")
            trace_out()
            return
        
        log("Rolling back main database transaction...")
        
        try:
            if self.main:
                try:
                    self.main.rollback()
                    log("Transaction rolled back on main database")
                except Exception as e:
                    warn(f"Error rolling back main transaction: {e}")
            
            self._main_transaction_started = False
            log("Main transaction rolled back")
        except Exception as e:
            warn(f"Error during main transaction rollback: {e}")
        finally:
            trace_out()
    
    def _start_main_transaction(self) -> None:
        """Start a transaction on the main database only. Called automatically on first write.
        Cache transactions are handled independently by write_cache()."""
        if self._main_transaction_started:
            return
        
        trace_in()
        log("Starting transaction on main database...")
        
        try:
            if self.main:
                with self.main.cursor() as cur:
                    cur.execute("START TRANSACTION")
                log("Transaction started on main database")
            
            # Cache database transactions are handled independently by write_cache()
            # Do not start cache transaction here
            
            self._main_transaction_started = True
            log("Main transaction started successfully")
        except Exception as e:
            warn(f"Failed to start main transaction: {e}")
            raise
        finally:
            trace_out()
    
    def _classify_and_attach_error(self, exc: Exception, conn: Any) -> None:
        """Classify exception and attach structured error info to it."""
        from hh.gateway.connection.utils import classify_exception
        code, source, extras = classify_exception(exc, conn)
        setattr(exc, '_error_code', code)
        setattr(exc, '_error_source', source)
        setattr(exc, '_error_extras', extras)
    
    # Main database CRUD operations
    def read(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query on the main database. Returns list of dict rows."""
        trace_in()
        if not self._initialized or not self.main:
            warn("Connection not initialized, returning empty result")
            trace_out()
            return []
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Main DB READ: {sql_preview}, params={params}")
        
        try:
            with self.main.cursor() as cur:
                cur.execute(sql, params or [])
                rows = cur.fetchall()
                if isinstance(rows, list) and rows and not isinstance(rows[0], dict):
                    columns = [d[0] for d in cur.description]
                    result = [dict(zip(columns, r)) for r in rows]
                    log(f"Main DB READ executed successfully: {len(result)} rows returned (converted to dict)")
                else:
                    result = list(rows)
                    log(f"Main DB READ executed successfully: {len(result)} rows returned")
                trace_out()
                return result
        except Exception as exc:
            warn(f"Main DB READ execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.main)
            trace_out()
            raise
    
    def create(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
        """Execute an INSERT query on the main database. Returns lastrowid."""
        trace_in()
        if not self._initialized or not self.main:
            warn("Connection not initialized, returning 0")
            trace_out()
            return 0
        
        self._start_main_transaction()
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Main DB CREATE: {sql_preview}, params={params}")
        
        try:
            with self.main.cursor() as cur:
                cur.execute(sql, params or [])
                lastrowid = cur.lastrowid
                log(f"Main DB CREATE executed successfully: lastrowid={lastrowid}")
                trace_out()
                return lastrowid
        except Exception as exc:
            warn(f"Main DB CREATE execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.main)
            trace_out()
            raise
    
    def update(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
        """Execute an UPDATE query on the main database. Returns rowcount."""
        trace_in()
        if not self._initialized or not self.main:
            warn("Connection not initialized, returning 0")
            trace_out()
            return 0
        
        self._start_main_transaction()
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Main DB UPDATE: {sql_preview}, params={params}")
        
        try:
            with self.main.cursor() as cur:
                cur.execute(sql, params or [])
                rowcount = cur.rowcount
                log(f"Main DB UPDATE executed successfully: {rowcount} rows affected")
                trace_out()
                return rowcount
        except Exception as exc:
            warn(f"Main DB UPDATE execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.main)
            trace_out()
            raise
    
    def delete(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
        """Execute a DELETE query on the main database. Returns rowcount."""
        trace_in()
        if not self._initialized or not self.main:
            warn("Connection not initialized, returning 0")
            trace_out()
            return 0
        
        self._start_main_transaction()
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Main DB DELETE: {sql_preview}, params={params}")
        
        try:
            with self.main.cursor() as cur:
                cur.execute(sql, params or [])
                rowcount = cur.rowcount
                log(f"Main DB DELETE executed successfully: {rowcount} rows affected")
                trace_out()
                return rowcount
        except Exception as exc:
            warn(f"Main DB DELETE execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.main)
            trace_out()
            raise
    
    def upsert_main(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
        """Execute an INSERT ... ON DUPLICATE KEY UPDATE query on the main database. Returns lastrowid (0 if updated, non-zero if inserted)."""
        trace_in()
        if not self._initialized or not self.main:
            warn("Connection not initialized, returning 0")
            trace_out()
            return 0
        
        self._start_main_transaction()
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Main DB UPSERT: {sql_preview}, params={params}")
        
        try:
            with self.main.cursor() as cur:
                cur.execute(sql, params or [])
                lastrowid = cur.lastrowid
                log(f"Main DB UPSERT executed successfully: lastrowid={lastrowid}")
                trace_out()
                return lastrowid
        except Exception as exc:
            warn(f"Main DB UPSERT execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.main)
            trace_out()
            raise
    
    # Cache database operations (no delete)
    def read_cache(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> List[DatabaseRow]:
        """Execute a SELECT query on the cache database. Returns list of dict rows."""
        trace_in()
        if not self._initialized or not self.cache:
            warn("Cache connection not initialized, returning empty result")
            trace_out()
            return []
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Cache DB READ: {sql_preview}, params={params}")
        
        try:
            with self.cache.cursor() as cur:
                cur.execute(sql, params or [])
                rows = cur.fetchall()
                if isinstance(rows, list) and rows and not isinstance(rows[0], dict):
                    columns = [d[0] for d in cur.description]
                    result = [dict(zip(columns, r)) for r in rows]
                    log(f"Cache DB READ executed successfully: {len(result)} rows returned (converted to dict)")
                else:
                    result = list(rows)
                    log(f"Cache DB READ executed successfully: {len(result)} rows returned")
                trace_out()
                return cast(List[DatabaseRow], result)
        except Exception as exc:
            warn(f"Cache DB READ execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.cache)
            trace_out()
            raise
    
    def upsert_cache(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
        """Execute an INSERT ... ON DUPLICATE KEY UPDATE query on the cache database. Returns lastrowid (0 if updated, non-zero if inserted).
        Note: This method assumes a cache transaction is already started. Use buffer_cache() + write_cache() for buffered writes."""
        trace_in()
        if not self._initialized or not self.cache:
            warn("Cache connection not initialized, returning 0")
            trace_out()
            return 0
        
        if not self._cache_transaction_started:
            warn("Cache transaction not started - call write_cache() instead of upsert_cache() directly")
            trace_out()
            return 0
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Cache DB UPSERT: {sql_preview}, params={params}")
        
        try:
            with self.cache.cursor() as cur:
                cur.execute(sql, params or [])
                lastrowid = cur.lastrowid
                log(f"Cache DB UPSERT executed successfully: lastrowid={lastrowid}")
                trace_out()
                return lastrowid
        except Exception as exc:
            warn(f"Cache DB UPSERT execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.cache)
            trace_out()
            raise
    
    def buffer_cache(self, table_name: str, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> None:
        """Buffer a cache database write for later execution. Does not execute immediately."""
        trace_in()
        if not self._initialized or not self.cache:
            warn("Cache connection not initialized, buffering skipped")
            trace_out()
            return
        
        self._cache_buffer.append((table_name, sql, params))
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Cache DB BUFFER: table={table_name}, sql={sql_preview}, params={params} (buffered, {len(self._cache_buffer)} items in buffer)")
        trace_out()
    
    def write_cache(self) -> None:
        """Execute all buffered cache writes in a single independent transaction. Clears buffer after execution."""
        trace_in()
        if not self._initialized or not self.cache:
            warn("Cache connection not initialized, cannot write buffer")
            trace_out()
            return
        
        if not self._cache_buffer:
            log("Cache buffer is empty, nothing to write")
            trace_out()
            return
        
        log(f"Writing {len(self._cache_buffer)} buffered cache operations...")
        
        # Start independent cache transaction
        try:
            if self.cache and self.cache is not self.main:
                with self.cache.cursor() as cur:
                    cur.execute("START TRANSACTION")
                log("Cache transaction started")
                self._cache_transaction_started = True
        except Exception as e:
            warn(f"Failed to start cache transaction: {e}")
            self._cache_buffer.clear()
            trace_out()
            return
        
        # Execute all buffered writes
        failed_count = 0
        try:
            for table_name, sql, params in self._cache_buffer:
                try:
                    self.upsert_cache(sql, params)
                except Exception as exc:
                    failed_count += 1
                    warn(f"Failed to write buffered cache operation for table {table_name}: {exc}")
                    # Continue with remaining items
                    continue
            
            if failed_count > 0:
                warn(f"Some cache writes failed ({failed_count} of {len(self._cache_buffer)}), rolling back cache transaction")
                if self.cache and self.cache is not self.main:
                    self.cache.rollback()
                    log("Cache transaction rolled back due to failures")
                self._cache_transaction_started = False
            else:
                # Commit cache transaction
                if self.cache and self.cache is not self.main:
                    self.cache.commit()
                    log(f"Cache transaction committed successfully ({len(self._cache_buffer)} operations)")
                self._cache_transaction_started = False
        except Exception as e:
            warn(f"Fatal error during cache write: {e}, rolling back")
            if self.cache and self.cache is not self.main:
                try:
                    self.cache.rollback()
                    log("Cache transaction rolled back due to fatal error")
                except Exception as rollback_exc:
                    warn(f"Error during cache rollback: {rollback_exc}")
            self._cache_transaction_started = False
        finally:
            # Clear buffer
            self._cache_buffer.clear()
            trace_out()
    
