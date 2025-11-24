# Image Module Connection System Refactoring

This document describes the refactoring of the `hh/image` module from the old connection system to the new gateway-owned connection system.

## Overview

The image module was refactored to use the new connection system (`hh.gateway.connection.conn.Connection` and `hh.gateway.connection.files.FileSystem`) instead of the legacy system that used decorators, explicit connection passing, and complex wrapper methods.

## Key Changes

### 1. Image Registry (`image_registry.py`)

**Removed:**
- `get_image_conn()` function - no longer needed since images manage their own gateway connection
- `invalidate_image_cache_entry()` function - hot cache invalidation not needed
- `@db_read` decorators
- Connection parameter passing
- Helper functions `_get_cache_row()` and `_hydrate_image_from_cache()` - logic moved into `Image.__init__()`

**Changed:**
- `get_image()` now uses `gateway.conn.read()` directly (via `get_gateway()`)
- Cache hydration moved into `Image.__init__()` - images hydrate from cache database during initialization
- Added `refresh_stale_image_caches()` function that iterates through hot cache and refreshes flagged images

**Key Decision:** Cache hydration happens during `Image.__init__()` rather than as a separate step, simplifying the flow.

### 2. Image Class (`image.py`)

**Removed:**
- `_create_wrapper_methods()` function and its decorator
- `init_helper_dec`, `init_helper_conn`, `_do_init`, and `reset_connection` methods
- `self.conn` and `_external_conn` attributes
- All wrapper method logic

**Changed:**
- `__init__()` simplified to a normal initialization:
  - Sets `self.gateway = get_gateway()` as the first action
  - Loads basic image data from main database using `gateway.conn.read()`
  - Attempts cache hydration inline (checks cache freshness, loads from cache database if available)
  - No connection juggling, no wrappers, no helpers

**Key Decision:** Images store `self.gateway` directly, allowing all mixin methods to access `self.gateway.conn` without needing connection parameters.

### 3. Mixin Method Registry System Removal

**Removed:**
- `image_method_registry.py` file entirely
- `@register_image_mixin_methods` decorators from all mixin files
- `get_image_method_registry()` function calls
- All registry registration functions

**Changed Method Names:**
- All methods that were registered in the mixin registry had their underscore prefixes removed (made public):
  - `_validate_caption` → `validate_caption`
  - `_modify_caption` → `modify_caption`
  - `_modify_visibility` → `modify_visibility`
  - `_update_view_count` → `update_view_count`
  - `_delete_from_database` → `delete_from_database`
  - `_get_image_data` → `get_image_data`
  - `_flag_image_modification` → `flag_image_modification`
  - `_load_instances` → `load_instances`
  - `_get_instances` → `get_instances`
  - `_get_instances_data` → `get_instances_data`
  - `_get_best_instance` → `get_best_instance`
  - `_add_image_instance` → `add_image_instance`
  - `_copy_instances` → `copy_instances`
  - `_process_upload` → `process_upload`
  - `_get_usage_count` → `get_usage_count`
  - `_get_used_by_pages` → `get_used_by_pages`
  - `_check_incoming_links` → `check_incoming_links`
  - `_show_image` → `show_image`

- Methods that were NOT registered kept their underscore prefixes (remain private):
  - `_get_usage_data()`
  - `_check_extra_actions()`
  - `_process_image()`
  - `_soft_delete_files()`
  - `_is_file_shared()`
  - `_flag_cache_refresh()`
  - `_refresh_cached_image()`
  - `_ensure_image_cache_entry()`

**Key Decision:** Public methods (those that were registered) are now directly callable without wrappers. Private methods (not registered) remain internal helpers.

### 4. Connection System Migration

**Removed from all mixin files:**
- Imports: `r_query`, `c_query`, `u_query`, `d_query`, `schedule_file_move`
- Imports: `@db_read`, `@db_write` decorators
- Imports: Database connection type hints
- All `self.conn` references
- All `conn` parameters from methods

**Replaced with:**
- `self.gateway.conn.read()` for SELECT queries
- `self.gateway.conn.read_cache()` for cache database SELECT queries
- `self.gateway.conn.create()` for INSERT queries
- `self.gateway.conn.create_cache()` for cache database INSERT queries
- `self.gateway.conn.update()` for UPDATE queries
- `self.gateway.conn.update_cache()` for cache database UPDATE queries
- `self.gateway.conn.delete()` for DELETE queries
- `self.gateway.files.schedule_move()` for file move operations

**Mapping:**
- `r_query(conn, query, params)` → `self.gateway.conn.read(query, params)`
- `r_query(conn, query, params, use_secondary=True)` → `self.gateway.conn.read_cache(query, params)`
- `c_query(conn, query, params)` → `self.gateway.conn.create(query, params)`
- `c_query(conn, query, params, use_secondary=True)` → `self.gateway.conn.create_cache(query, params)`
- `u_query(conn, query, params)` → `self.gateway.conn.update(query, params)`
- `u_query(conn, query, params, use_secondary=True)` → `self.gateway.conn.update_cache(query, params)`
- `d_query(conn, query, params)` → `self.gateway.conn.delete(query, params)`
- `schedule_file_move(conn, from_path, to_path)` → `self.gateway.files.schedule_move(from_path, to_path)`

**Key Decision:** All database operations now go through `self.gateway.conn`, eliminating the need for connection parameters and decorators.

### 5. Cache Refresh System

**Old System:**
- Wrapper methods would call `_refresh_cached_image(conn)` after method execution
- Required passing connection explicitly
- Used `@db_write` decorator to get write connection

**New System:**
- `_refresh_cached_image()` no longer takes a `conn` parameter
- Uses `self.gateway.conn` directly
- Called by `refresh_stale_image_caches()` in `image_registry.py`
- `refresh_stale_image_caches()` is called from `gateway._commit()` after file operations but before database commit
- Images set `_cache_needs_refresh = True` flag when they compute/derive expensive data
- Gateway iterates through hot cache and refreshes flagged images

**Key Decision:** Cache refresh is now centralized in the gateway commit process, eliminating per-method overhead and connection juggling.

### 6. Utility Functions

**Moved to `hh/gateway/connection/utils.py`:**
- `_deserialize_json_blob()` → `deserialize_json_blob()`
- `_normalize_dt()` → `normalize_datetime()`

**Key Decision:** Shared utility functions belong in the connection utilities module for reuse across modules.

### 7. Error Handling

**Added:**
- `CACHE_REFRESH = "cache_refresh"` to `ErrorType` enum in `error_store.py`

**Fixed:**
- Dictionary iteration bug in `refresh_stale_image_caches()` - changed `_image_cache.items()` to `list(_image_cache.items())` to prevent "dictionary changed size during iteration" error

### 8. Data Retrieval Bug Fix

**Issue:**
- `show_image()` method in `image_display.py` had data retrieval calls commented out during debugging
- This caused empty data (zeros) to be returned on first load
- Data was only populated after cache refresh wrote to cache database

**Fixed:**
- Uncommented the three data retrieval calls:
  - `image_data = self.get_image_data()`
  - `usage_data = self._get_usage_data()`
  - `instances_data = self.get_instances_data()`
- Now data is properly loaded on first call and stored in the object before building response

**Key Lesson:** Always verify that data retrieval methods are actually being called, not just stubbed out.

### 9. Connection System Isolation

**Issue:**
- The new `conn.py` was importing `load_dsn_pair()` from the old `connection.py`
- This caused duplicate calls to `detect_project_context()`:
  1. Once inside the old `load_dsn_pair()` function
  2. Once in `conn.py`'s `initialize()` method
- The old system's `load_dsn_pair()` also called `_detect_and_set_user_tier_level()` which added unnecessary complexity

**Fixed:**
- Created new `_load_dsn()` function in `conn.py` that accepts `project_name` as a parameter
- Removed import of `load_dsn_pair` from old `connection.py`
- Updated `_get_main_dsn()` to accept `project_name` parameter
- Modified `initialize()` to call `detect_project_context()` once at the start, then pass `project_name` to all DSN loading calls

**Key Decision:** The new system must not import utility functions from the old system. Each system should have its own implementations to avoid coupling and duplicate work.

### 10. Logging Cleanup

**Removed:**
- "Arg not found, returning empty" log line from `request.py` - unnecessary noise in logs when arguments are not provided

## Files Modified

1. `hh/image/image_registry.py` - Removed connection juggling, simplified get_image, added cache refresh orchestration
2. `hh/image/image.py` - Simplified __init__, removed wrapper system, added self.gateway
3. `hh/image/image_validation.py` - Removed registry, renamed methods, updated to use gateway.conn
4. `hh/image/image_content.py` - Removed registry, renamed methods, updated all queries to use gateway.conn
5. `hh/image/image_instances.py` - Removed registry, renamed methods, updated all queries to use gateway.conn
6. `hh/image/image_usage.py` - Removed registry, renamed methods, updated all queries to use gateway.conn
7. `hh/image/image_display.py` - Removed registry, renamed methods, updated all queries to use gateway.conn, fixed commented-out data retrieval calls
8. `hh/image/image_cache.py` - Removed decorators, removed conn parameters, updated to use gateway.conn
9. `hh/gateway/gateway.py` - Added call to refresh_stale_image_caches() in _commit()
10. `hh/gateway/connection/utils.py` - Added deserialize_json_blob and normalize_datetime
11. `hh/gateway/connection/conn.py` - Created new `_load_dsn()` function, removed dependency on old system's `load_dsn_pair()`
12. `hh/gateway/error/error_store.py` - Added CACHE_REFRESH error type
13. `hh/gateway/request/request.py` - Removed unnecessary "Arg not found" log line

## Files Deleted

1. `hh/image/image_method_registry.py` - Registry system no longer needed

## Files Updated (External Dependencies)

1. `hh/page/page_images.py` - Updated to use `get_image()` instead of `get_image_conn()`
2. `hh/tp/tp.py` - Updated to use `get_image()` instead of `get_image_conn()`
3. `hh/deploy/maint/image_cache_refresh.py` - Updated to use `get_image()` instead of `get_image_conn()`

## Key Principles Applied

1. **Gateway-owned connections**: All database operations use `self.gateway.conn` directly
2. **No connection parameters**: Methods no longer accept `conn` parameters
3. **No decorators**: Removed all `@db_read`, `@db_write` decorators
4. **Simplified initialization**: `Image.__init__()` is a straightforward initialization
5. **Centralized cache refresh**: Cache refresh happens in gateway commit process
6. **Public vs private methods**: Registered methods become public (no underscore), unregistered remain private
7. **Hot cache preserved**: In-memory cache for Image objects remains for performance
8. **System isolation**: New system must not import utility functions from old system - each system should have its own implementations
9. **Avoid duplicate work**: When refactoring, ensure functions that are called multiple times don't repeat expensive operations (like `detect_project_context()`)

## Migration Pattern for Other Modules

This refactoring pattern can be applied to other modules (files, pages):

1. Remove registry system and decorators
2. Rename registered methods to remove underscore prefix
3. Add `self.gateway = get_gateway()` to class `__init__()`
4. Replace all `self.conn` with `self.gateway.conn`
5. Replace old connection functions with new gateway methods
6. Remove all `conn` parameters from methods
7. Move cache refresh logic to gateway commit process
8. Update utility functions to use shared connection utilities
9. **Ensure new system doesn't import from old system** - create new utility functions if needed
10. **Verify data retrieval methods are actually called** - check for commented-out code from debugging
11. **Eliminate duplicate expensive operations** - if a function is called multiple times, ensure expensive operations (like `detect_project_context()`) are done once and passed as parameters

