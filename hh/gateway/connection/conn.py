import pymysql
import os
from typing import Any, Optional, Dict, List, Sequence, Union
from hh.gateway.connection.connection import load_dsn_pair, DatabaseRow
from hh.deploy.utils import detect_project_context
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS
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

class Connection:
    """Gateway-owned connection manager for main, cache, and history databases."""
    
    def __init__(self):
        self.main: Optional[Any] = None
        self.cache: Optional[Any] = None
        self.history: Optional[Any] = None
        self._transaction_started: bool = False
        self._initialized: bool = False
    
    def _get_main_dsn(self) -> Optional[Dict[str, Union[str, int]]]:
        """Get main database DSN. Override in subclasses for root/MySQL connections."""
        trace_in()
        main_dsn, _ = load_dsn_pair()
        trace_out()
        return main_dsn
    
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
            # Get main DSN (may be overridden by subclasses)
            main_dsn = self._get_main_dsn()
            
            if not main_dsn:
                warn("Cannot initialize connections: main DSN not available")
                trace_out()
                return 0
            
            # Detect user tier level from DSN username
            project_name, _ = detect_project_context()
            if project_name:
                tier_level = self._detect_user_tier_level(project_name, main_dsn.get('user', ''))
            
            # Load cache DSN (always uses standard loading)
            _, cache_dsn = load_dsn_pair()
            
            # Open main database connection
            cursorclass = pymysql.cursors.DictCursor
            self.main = pymysql.connect(**main_dsn, cursorclass=cursorclass)
            log(f"Main database connection opened: host={main_dsn['host']}, database={main_dsn.get('database', 'None')}")
            
            # Open cache database connection
            if cache_dsn:
                self.cache = pymysql.connect(**cache_dsn, cursorclass=cursorclass)
                log(f"Cache database connection opened: host={cache_dsn['host']}, database={cache_dsn['database']}")
            else:
                warn("Cache DSN not available, using main database for cache")
                self.cache = self.main
            
            # TODO: Open history database connection when DSN loading is implemented
            # For now, history is None
            log("History database connection skipped (not yet implemented)")
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
        """Commit all active transactions on all databases."""
        trace_in()
        if not self._transaction_started:
            log("No transaction to commit")
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
    def read(self, sql: str, params: Optional[Sequence[Union[str, int, float, bool, None]]] = None) -> List[DatabaseRow]:
        """Execute a SELECT query on the main database. Returns list of dict rows."""
        trace_in()
        if not self._initialized or not self.main:
            raise RuntimeError("Connection not initialized")
        
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
            raise RuntimeError("Connection not initialized")
        
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
            raise RuntimeError("Connection not initialized")
        
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
            raise RuntimeError("Connection not initialized")
        
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
            raise RuntimeError("Cache connection not initialized")
        
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
                return result
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
            raise RuntimeError("Cache connection not initialized")
        
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
            raise RuntimeError("Cache connection not initialized")
        
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
            raise RuntimeError("History connection not initialized")
        
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
                return result
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
            raise RuntimeError("History connection not initialized")
        
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
            raise RuntimeError("History connection not initialized")
        
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

