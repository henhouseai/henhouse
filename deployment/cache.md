# Cache Management

The cache management system provides a centralized registry for cleaning various caches throughout the Henhouse system. It uses a decorator-based registration pattern that allows any module to register its own cache cleanup function.

## Prerequisites

Before using cache management, you must have:
- Project folder with `hh/` directory structure
- Cache directories may exist in both project root and `/srv/{project_name}` (if deployed)

The cache management system is used by:
- **File deployment** (`file-deployment.md`): Discovers cache directories and sets permissions. Clears all caches after deployment.
- **Git operations** (`git.md`): Clears all caches after pull operations to prevent stale state issues.
- **Installation system** (`installation.md`): Clears all caches after install/uninstall to prevent permission issues.
- **Database deployment** (`database.md`): Cache database stores cached data, but cache cleanup registry manages file-based caches.

## Cache Cleanup Registry

**File**: `hh/deploy/cache/cache_cleanup_registry.py`

The registry system scans the codebase for `@register_cache_cleanup` decorators and provides centralized cache cleanup functionality.

### Key Functions

- **`register_cache_cleanup(cache_name, cache_dir=None)`**: Decorator for registering cache cleanup methods
  - `cache_name`: Unique identifier for the cache (e.g., 'page_classes', 'tp_decorators')
  - `cache_dir`: Optional relative path to cache directory (e.g., 'hh/page/cache') - used for permission management
- **`discover_cache_cleanups()`**: Scans codebase and loads all registered cleanup functions
- **`clean_cache(cache_name)`**: Cleans a specific cache by name
- **`clean_all_caches()`**: Cleans all registered caches and aggregates results
- **`get_cache_directories()`**: Returns list of all cache directory paths (used by deployment for permission setting)
- **`get_deployment_paths()`**: Returns both project root and `/srv/{project_name}` paths for cleaning

### Registration Pattern

Modules register their cleanup functions using the decorator:

```python
from hh.deploy.cache.cache_cleanup_registry import register_cache_cleanup

@register_cache_cleanup('page_classes', cache_dir='hh/page/cache')
def cleanup_page_class_cache():
    # Clean up page class cache
    cache_file.unlink()
    _page_class_registry.clear()
    return {'success': True, 'cache_files': 1, 'cache_files_list': ['hh/page/cache/page-classes.json']}
```

### Discovery Process

1. Scans `hh/` directory tree for files containing `@register_cache_cleanup`
2. Imports those modules to trigger registration
3. Populates global `_cleanup_registry` dictionary
4. Tracks cache directories in `_cache_dir_registry` for permission management

## Clear Cache Command

**File**: `hh/deploy/cache/clear_cache.py`

The `clear_cache` command uses the registry to clean all registered caches:

- Calls `clean_all_caches()` to execute all registered cleanup functions
- Aggregates results (pycache_dirs, pyc_files, cache_files, cache_dirs)
- Returns detailed results including success/failure counts and item lists

**See also**: `hh/deploy/cache/clear_cache.py` function `clear_cache`

## Built-in Cleanups

The system includes a built-in cleanup for Python bytecode:
- **`cleanup_python_bytecode()`**: Removes all `__pycache__` directories and `.pyc` files
- Cleans both project root and `/srv/{project_name}` deployment paths
- Registered as `'python_bytecode'` cache (no cache_dir since it's system-wide)

## Integration with Deployment

- Cache directories are discovered via `get_cache_directories()` during file deployment (see `file-deployment.md`)
- Used to set proper permissions on cache directories in `/srv/{project_name}` (setgid bit for group write)
- Both project root and deployment paths are cleaned during cache operations
- The `cache/` folder is whitelisted in `DEPLOY_WHITELIST` (see `configuration.md`) to survive deployment cleanup

## Integration with Other Systems

The cache management system integrates with:

1. **File Deployment** (`file-deployment.md`): 
   - Discovers cache directories via `get_cache_directories()` and sets proper permissions (setgid bit for group write)
   - Clears all caches after deployment to prevent permission issues
   - The `cache/` folder is whitelisted to survive deployment cleanup

2. **Git Operations** (`git.md`): 
   - Automatically clears all caches after pull operations to prevent stale state issues
   - Ensures clean state when syncing code from remote

3. **Installation System** (`installation.md`): 
   - Clears all caches after install/uninstall to prevent permission issues
   - Cache directories use the deploy group created during installation for group write access

4. **Database Deployment** (`database.md`): 
   - The cache database stores cached data (JSON-encoded), but this is separate from file-based caches managed by the cache cleanup registry
   - Cache refresh tools (see `maintenance.md`) update cache database, but file-based caches are managed by the cleanup registry

5. **Maintenance Daemon** (`maintenance.md`): 
   - Maintenance daemon refreshes stale caches in the cache database
   - File-based caches are managed separately by the cache cleanup registry

6. **Configuration System** (`configuration.md`): 
   - The `cache/` folder is whitelisted in `DEPLOY_WHITELIST` to survive deployment cleanup

## Cache Directory Permissions

Cache directories discovered via the registry are configured with special permissions during file deployment (see `file-deployment.md`):

- **Permissions**: `0o2775` (setgid for group write, owner:rwx, group:rwx, others:r-x)
- **Ownership**: `{project_name}_root:{project_name}_deploy` (users/groups from `installation.md`)
- **Purpose**: Allows all tier users (in deploy group) to write cache files via group permissions

This enables the maintenance daemon (see `maintenance.md`) and Flask applications (see `flask.md`) to write cache files without requiring root access.

## Deployment Workflow

Cache management is automatically handled during deployment:

**During File Deployment**:
- Cache directories are discovered and permissions are set
- All caches are cleared after deployment

**During Git Pull**:
- All caches are automatically cleared after pull operations

**Manual Cache Clearing**:
```bash
hen clear-cache    # Clear all registered caches
```

See `workflows.md` for complete deployment workflow documentation.

