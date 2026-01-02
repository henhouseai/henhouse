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

def _build_ssl_dict(config: configparser.ConfigParser, prefix: str = '') -> Dict[str, Union[str, bool, int]]:
    """Build SSL dictionary from config file for PyMySQL.

    SSL is ALWAYS REQUIRED. verify_mode controls strictness:
    - 3: verify cert + hostname (VERIFY_IDENTITY - strictest)
    - 2: verify cert, hostname check disabled (VERIFY_CA)
    - 1: optional verify; hostname check disabled (CERT_OPTIONAL)
    - 0: no verify; hostname check disabled (least strict)
    """
    ssl_ca = config.get('client', f'{prefix}ssl_ca', fallback=None)
    ssl_cert = config.get('client', f'{prefix}ssl_cert', fallback=None)
    ssl_key = config.get('client', f'{prefix}ssl_key', fallback=None)
    ssl_verify_mode = config.get('client', f'{prefix}ssl_verify_mode', fallback='2')
    ssl_check_hostname = config.get('client', f'{prefix}ssl_check_hostname', fallback='true')

    # Determine verify_mode from config (defaults to 2 if not set or invalid)
    verify_mode = 2  # Default to strict
    try:
        verify_mode = int(ssl_verify_mode)
        if verify_mode not in (0, 1, 2, 3):
            verify_mode = 2
    except (ValueError, TypeError):
        verify_mode = 2

    # Enforce SSL always; only relax verification based on verify_mode
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
        
        # SSL is ALWAYS REQUIRED for main database
        dsn['ssl'] = _build_ssl_dict(config, '')
        
        log(f"DSN loaded from config: {path}, host={dsn['host']}, database={dsn['database']}")
        
        cache_dsn: Dict[str, Union[str, int, Dict[str, Union[str, bool, int]]]] = {
            'host': config.get('client', 'cache_host', fallback=dsn['host']),
            'user': config.get('client', 'cache_user', fallback=dsn['user']),
            'password': config.get('client', 'cache_password', fallback=dsn['password']),
            'database': config.get('client', 'cache_database', fallback=f"{dsn['database']}_cache"),
            'port': config.getint('client', 'cache_port', fallback=dsn['port'])
        }
        
        # SSL is ALWAYS REQUIRED for cache database
        # Try cache-specific SSL first, fallback to main SSL if cache_ssl_ca not present
        try:
            cache_dsn['ssl'] = _build_ssl_dict(config, 'cache_')
        except ValueError:
            # Fallback to main SSL config
            cache_dsn['ssl'] = _build_ssl_dict(config, '')
        
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
            # SSL is ALWAYS REQUIRED for history database
            # Try history-specific SSL first, fallback to main SSL if history_ssl_ca not present
            try:
                history_dsn['ssl'] = _build_ssl_dict(config, 'history_')
            except ValueError:
                # Fallback to main SSL config
                history_dsn['ssl'] = _build_ssl_dict(config, '')
        
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
        self._transaction_started: bool = False
        self._initialized: bool = False
        self._dry_run: bool = dry_run
    
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
            
            # Extract SSL dict from main_dsn and pass separately
            main_ssl = main_dsn.pop('ssl', None) if isinstance(main_dsn.get('ssl'), dict) else None
            self.main = pymysql.connect(**main_dsn, ssl=main_ssl, cursorclass=cursorclass)  # type: ignore[call-arg]
            log(f"Main database connection opened: host={main_dsn['host']}, database={main_dsn.get('database', 'None')}")
            
            # Open cache database connection
            if cache_dsn:
                cache_ssl = cache_dsn.pop('ssl', None) if isinstance(cache_dsn.get('ssl'), dict) else None
                self.cache = pymysql.connect(**cache_dsn, ssl=cache_ssl, cursorclass=cursorclass)  # type: ignore[call-arg]
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
        
        self._transaction_started = False
        self._initialized = False
        log("All database connections closed successfully")
        trace_out()
    
    def has_transaction(self) -> bool:
        """Check if a transaction is currently active."""
        return self._transaction_started
    
    def is_initialized(self) -> bool:
        """Check if connections have been initialized."""
        return self._initialized
    
    def commit(self) -> None:
        """Commit all active transactions on all databases. If dry_run is enabled, rolls back instead."""
        trace_in()
        if not self._transaction_started:
            log("No transaction to commit")
            trace_out()
            return
        
        if self._dry_run:
            log("Dry run mode enabled - rolling back transactions instead of committing")
            self.rollback()
            trace_out()
            return
        
        log("Committing transactions on all databases...")
        
        try:
            if self.history and self.history is not self.main and self.history is not self.cache:
                self.history.commit()
                log("Transaction committed on history database")
            
            if self.cache and self.cache is not self.main:
                self.cache.commit()
                log("Transaction committed on cache database")
            
            if self.main:
                self.main.commit()
                log("Transaction committed on main database")
            
            self._transaction_started = False
            log("All transactions committed successfully")
        except Exception as e:
            warn(f"Failed to commit transactions: {e}")
            raise
        finally:
            trace_out()
    
    def rollback(self) -> None:
        """Rollback all active transactions on all databases."""
        trace_in()
        if not self._transaction_started:
            log("No transaction to rollback")
            trace_out()
            return
        
        log("Rolling back transactions on all databases...")
        
        try:
            if self.history and self.history is not self.main and self.history is not self.cache:
                try:
                    self.history.rollback()
                    log("Transaction rolled back on history database")
                except Exception as e:
                    warn(f"Error rolling back history transaction: {e}")
            
            if self.cache and self.cache is not self.main:
                try:
                    self.cache.rollback()
                    log("Transaction rolled back on cache database")
                except Exception as e:
                    warn(f"Error rolling back cache transaction: {e}")
            
            if self.main:
                try:
                    self.main.rollback()
                    log("Transaction rolled back on main database")
                except Exception as e:
                    warn(f"Error rolling back main transaction: {e}")
            
            self._transaction_started = False
            log("All transactions rolled back")
        except Exception as e:
            warn(f"Error during transaction rollback: {e}")
        finally:
            trace_out()
    
    def _start_transaction(self) -> None:
        """Start a transaction on all active databases. Called automatically on first write."""
        if self._transaction_started:
            return
        
        trace_in()
        log("Starting transaction on all databases...")
        
        try:
            if self.main:
                with self.main.cursor() as cur:
                    cur.execute("START TRANSACTION")
                log("Transaction started on main database")
            
            if self.cache and self.cache is not self.main:
                with self.cache.cursor() as cur:
                    cur.execute("START TRANSACTION")
                log("Transaction started on cache database")
            
            if self.history and self.history is not self.main and self.history is not self.cache:
                with self.history.cursor() as cur:
                    cur.execute("START TRANSACTION")
                log("Transaction started on history database")
            
            self._transaction_started = True
            log("All transactions started successfully")
        except Exception as e:
            warn(f"Failed to start transactions: {e}")
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
        
        self._start_transaction()
        
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
        
        self._start_transaction()
        
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
        
        self._start_transaction()
        
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
    
    def create_cache(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
        """Execute an INSERT query on the cache database. Returns lastrowid."""
        trace_in()
        if not self._initialized or not self.cache:
            warn("Cache connection not initialized, returning 0")
            trace_out()
            return 0
        
        self._start_transaction()
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Cache DB CREATE: {sql_preview}, params={params}")
        
        try:
            with self.cache.cursor() as cur:
                cur.execute(sql, params or [])
                lastrowid = cur.lastrowid
                log(f"Cache DB CREATE executed successfully: lastrowid={lastrowid}")
                trace_out()
                return lastrowid
        except Exception as exc:
            warn(f"Cache DB CREATE execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.cache)
            trace_out()
            raise
    
    def update_cache(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
        """Execute an UPDATE query on the cache database. Returns rowcount."""
        trace_in()
        if not self._initialized or not self.cache:
            warn("Cache connection not initialized, returning 0")
            trace_out()
            return 0
        
        self._start_transaction()
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"Cache DB UPDATE: {sql_preview}, params={params}")
        
        try:
            with self.cache.cursor() as cur:
                cur.execute(sql, params or [])
                rowcount = cur.rowcount
                log(f"Cache DB UPDATE executed successfully: {rowcount} rows affected")
                trace_out()
                return rowcount
        except Exception as exc:
            warn(f"Cache DB UPDATE execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.cache)
            trace_out()
            raise
    
    # History database operations (no delete)
    def read_history(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> List[DatabaseRow]:
        """Execute a SELECT query on the history database. Returns list of dict rows."""
        trace_in()
        if not self._initialized or not self.history:
            warn("History connection not initialized, returning empty result")
            trace_out()
            return []
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"History DB READ: {sql_preview}, params={params}")
        
        try:
            with self.history.cursor() as cur:
                cur.execute(sql, params or [])
                rows = cur.fetchall()
                if isinstance(rows, list) and rows and not isinstance(rows[0], dict):
                    columns = [d[0] for d in cur.description]
                    result = [dict(zip(columns, r)) for r in rows]
                    log(f"History DB READ executed successfully: {len(result)} rows returned (converted to dict)")
                else:
                    result = list(rows)
                    log(f"History DB READ executed successfully: {len(result)} rows returned")
                trace_out()
                return cast(List[DatabaseRow], result)
        except Exception as exc:
            warn(f"History DB READ execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.history if self.history else self.main)
            trace_out()
            raise
    
    def create_history(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
        """Execute an INSERT query on the history database. Returns lastrowid."""
        trace_in()
        if not self._initialized or not self.history:
            warn("History connection not initialized, returning 0")
            trace_out()
            return 0
        
        self._start_transaction()
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"History DB CREATE: {sql_preview}, params={params}")
        
        try:
            with self.history.cursor() as cur:
                cur.execute(sql, params or [])
                lastrowid = cur.lastrowid
                log(f"History DB CREATE executed successfully: lastrowid={lastrowid}")
                trace_out()
                return lastrowid
        except Exception as exc:
            warn(f"History DB CREATE execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.history if self.history else self.main)
            trace_out()
            raise
    
    def update_history(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> int:
        """Execute an UPDATE query on the history database. Returns rowcount."""
        trace_in()
        if not self._initialized or not self.history:
            warn("History connection not initialized, returning 0")
            trace_out()
            return 0
        
        self._start_transaction()
        
        sql_preview = sql[:500] + ('...' if len(sql) > 500 else '')
        log(f"History DB UPDATE: {sql_preview}, params={params}")
        
        try:
            with self.history.cursor() as cur:
                cur.execute(sql, params or [])
                rowcount = cur.rowcount
                log(f"History DB UPDATE executed successfully: {rowcount} rows affected")
                trace_out()
                return rowcount
        except Exception as exc:
            warn(f"History DB UPDATE execution failed: {exc}")
            setattr(exc, 'sql', sql)
            setattr(exc, 'params', params or [])
            self._classify_and_attach_error(exc, self.history if self.history else self.main)
            trace_out()
            raise

