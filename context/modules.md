# Henhouse Modular Architecture

## Overview

Henhouse implements a sophisticated modular architecture that enables distributed ownership of deployment logic while maintaining strict separation of concerns. This document explains how modules work together through whitelist systems, hook registries, and configuration management without creating cross-cutting dependencies.

## Module Discovery and Loading

### Module Structure
Each module is a directory under the project root with a required `__module__.py` manifest:

```
project/
├── hh/           # Core framework module
├── hh_srv/       # Server infrastructure module
├── hh_nginx/     # NGINX configuration module
├── hh_flask/     # Flask application module
└── ext/          # External modules container
```

### Module Manifest (`__module__.py`)
Every module must have a `__module__.py` file defining its metadata:

```python
MODULE = {
    "name": "hh_nginx",
    "version": "1.0.0",
    "description": "NGINX configuration and SSL management",
    "dependencies": ["hh_srv"]  # Optional: modules this one depends on
}
```

### Discovery Process
Modules are discovered through direct filesystem scanning (`hh/deploy/deploy_utils.py:get_active_modules()`):

1. **Framework Scan**: `hh/` directory scanned for subdirectories with `__module__.py`
2. **Module Scan**: Project root scanned for module directories with `__module__.py`
3. **Dependency Resolution**: Module dependencies validated via `get_module_paths()` in `hh/gateway/registry/module_discovery.py`
4. **Blacklist Filtering**: Blacklisted modules excluded during loading

**Note**: `scan_for_decorator()` is used for hook discovery, not module discovery. Module discovery uses direct filesystem enumeration for performance and reliability.

## Whitelist and Blacklist Systems

### Module Whitelisting
Modules are controlled through whitelist files that determine which modules are active:

**Location**: `hh/deploy/conf/deploy_whitelist.py` (and module-specific equivalents)

```python
# Example deploy_whitelist.py
DEPLOY_WHITELIST = [
    'hh_srv',      # Server infrastructure - always required
    'hh_nginx',    # NGINX configuration
    'hh_flask',    # Flask applications
    'users',       # User management
    'accounting',  # Accounting system
]

DEPLOY_BLACKLIST = [
    'broken_module',  # Exclude known broken modules
]
```

### Dynamic Module Loading
The whitelist system enables selective module loading (`hh/deploy/deploy_utils.py:load_whitelist_with_extensions()`):

```python
# Load only whitelisted modules
active_modules = load_whitelist_with_extensions(
    'deploy_whitelist',      # Base whitelist name
    DEPLOY_WHITELIST,        # Default whitelist
    DEPLOY_BLACKLIST         # Modules to exclude
)
```

### Configuration Extension
Modules can extend whitelists through their own config files:

```
hh_nginx/deploy/conf/deploy_whitelist.py  # NGINX-specific extensions
users/deploy/conf/deploy_whitelist.py     # User module extensions
```

## Hook System Architecture

### Hook Registry
Modules register lifecycle hooks through a decorator-based system (`hh/gateway/registry/module_hooks.py:register_module_hook()`):

```python
from hh.gateway.registry.module_hooks import register_module_hook

@register_module_hook('deploy_00_pre_validate', 'Validate deployment prerequisites')
def validate_deployment_config():
    """Pre-validate deployment configuration."""
    # Module-specific validation logic
    pass
```

### Hook Execution Flow
Hooks execute in alphabetical order by module name (`hh/gateway/registry/module_hooks.py:run_hooks()`):

```
deploy_00_pre_validate:
├── hh_flask.validate_flask_config()    # Executes first (alphabetical)
├── hh_nginx.validate_nginx_config()    # Executes second
└── hh_srv.validate_server_config()    # Executes third

deploy_05_stop_daemons:
├── hh_flask.stop_flask_daemons()       # Flask stops first
└── hh_nginx.stop_nginx_service()       # NGINX stops second
```

### Hook Result Aggregation
Hook results are collected and aggregated during execution (`hh/deploy/deploy.py:deploy()`):

```python
# Initialize hook results collection
hook_results: List[Dict[str, Any]] = []

# Execute hooks and collect results
results = run_hooks('deploy_00_pre_validate')
if results:
    hook_results.extend(results)

# Results contain structured data from each module
# Example result from nginx config hook:
{
    "module": "hh_nginx",
    "action": "deploy_nginx_config",
    "config_written": True,
    "deployment_mode": "https",
    "domain": "example.com"
}
```

Results are passed to rendering functions for display and can be used for status reporting and error aggregation.

### Hook Categories

#### Deployment Hooks
- `deploy_00_pre_validate`: Configuration validation
- `deploy_05_stop_daemons`: Stop existing services
- `deploy_10_git_ops`: Git operations (preserve/restore)
- `deploy_25_module_deploy`: Module-specific deployment
- `deploy_40_service_config`: Service configuration
- `deploy_95_render`: Status rendering

#### Removal Hooks
- `remove_00_pre_validate`: Removal validation
- `remove_05_nginx_configs`: NGINX config removal
- `remove_20_stop_flask`: Flask daemon stop
- `remove_30_remove_files`: File cleanup
- `remove_95_render`: Removal status rendering

## Cross-Cutting Prevention

### The Cross-Cutting Anti-Pattern
❌ **Wrong**: Modules importing each other's internal state

```python
# hh_nginx/deploy/hooks.py
from hh_srv.deploy.hooks import srv_config  # ❌ Cross-cutting import
```

### Correct Module Isolation
✅ **Right**: Each module owns its own state and configuration

```python
# hh_nginx/deploy/remove_hooks.py
pre_validated_config = None  # Module-owned global

@register_module_hook('remove_00_pre_validate')
def validate_nginx_config():
    global pre_validated_config
    pre_validated_config = load_nginx_config()  # Load own config
    return {"status": "configured"}

@register_module_hook('remove_05_nginx_configs')
def remove_nginx_configs():
    # Use module's own pre_validated_config
    domains = pre_validated_config['domains']
    # ... remove configs
```

### Hook Result Pattern
Hooks communicate status through return values, not shared state:

```python
# hh_nginx/deploy/remove_hooks.py:remove_nginx_configs()
@register_module_hook('remove_05_nginx_configs')
def remove_nginx_configs():
    return {
        "component": "nginx_configs",
        "domains_removed": ["example.com"],
        "status": "completed"
    }

# hh_nginx/deploy/remove_hooks.py:render_nginx_removal()
@register_module_hook('remove_95_render')
def render_nginx_status():
    # Read from hook_results, not global state
    hook_results = gateway.response.get_action_response()
    nginx_data = [r for r in hook_results if r.get('component') == 'nginx_configs']
    # Render nginx-specific status
}
```

### Hook Result Aggregation in Deployment
In the deployment system (`hh/deploy/deploy.py`), hook results are systematically collected:

```python
@register_action('deploy')
def deploy() -> bool:
    # Initialize hook results collection
    hook_results: List[Dict[str, Any]] = []

    # Execute phases and collect results
    for hook_name, description in deployment_phases:
        if not is_error():
            log(f"Running {description} hooks")
            results = run_hooks(hook_name)
            if results:
                hook_results.extend(results)  # Aggregate all results

    # Results passed to action response for rendering
    result_data = {"hook_results": hook_results}
    gateway.response.set_action_response(result_data)
```

This aggregation enables comprehensive deployment status reporting and error tracking across all modules.

## Configuration Labels

Each module maintains its own `config_labels.py` files in folders sibling to the code that uses them:

```python
# hh/gateway/registry/config_labels.py
@register_label('module_list_header', 'Module List:', '📦')
@register_label('deploy_header', 'Deployment Status', '🚀')
```

The config registry system automatically discovers labels (`hh/render/config/config_registry.py:discover_config_registrations()`) and caches them from all active modules.

## Refactoring Legacy Monoliths

### Step 1: Identify Monolithic Functions
Find functions that handle multiple module concerns:

```python
# OLD: Monolithic deploy.py
def deploy():
    # Load config (server concern)
    # Stop nginx (nginx concern)
    # Stop flask (flask concern)
    # Remove files (server concern)
    # Clear manifest (server concern)
    pass
```

### Step 2: Extract Module-Specific Hooks
Break down into module-owned hooks:

```python
# NEW: hh_nginx/deploy/deploy_hooks.py
@register_module_hook('deploy_05_stop_daemons')
def stop_nginx_service():
    """NGINX owns nginx service management."""
    subprocess.run(['systemctl', 'stop', 'nginx'])

# NEW: hh_flask/deploy/deploy_hooks.py
@register_module_hook('deploy_05_stop_daemons')
def stop_flask_daemons():
    """Flask owns flask daemon management."""
    stop_flask_processes()

# NEW: hh_srv/deploy/deploy_hooks.py
@register_module_hook('deploy_30_remove_files')
def remove_deployment_files():
    """Server owns file operations."""
    shutil.rmtree('/srv/deployment')
```

### Step 3: Replace Monolithic Logic
Update main deployment script to orchestrate hooks (`hh/deploy/deploy.py:deploy()`):

```python
# hh/deploy/deploy.py:deploy()
def deploy():
    # Pre-validation - each module validates its own config
    run_hooks('deploy_00_pre_validate')

    # Service shutdown - each module stops its own services
    run_hooks('deploy_05_stop_daemons')

    # File operations - server module handles shared file operations
    run_hooks('deploy_30_remove_files')

    # Rendering - each module renders its own status
    render_results = run_hooks('deploy_95_render')
    # Aggregate render results into final output
```

### Step 4: Implement Rendering Separation
Each module renders its own status (`hh/deploy/deploy.py:render_deploy_hookified()`):

```python
# hh_nginx/deploy/deploy_hooks.py
@register_module_hook('deploy_95_render')
def render_nginx_status():
    """NGINX renders nginx-specific deployment status."""
    return {
        "table_data": nginx_status_table,
        "field_config": nginx_field_config
    }

# hh/deploy/deploy.py aggregates all module render results
render_instructions = run_hooks('deploy_95_render')  # Collect all module status
# Process and combine into final deployment summary table
```

## Best Practices

### Module Development
1. **Single Responsibility**: Each module owns one concern (nginx, flask, database, etc.)
2. **Self-Contained Config**: Load your own configuration in pre-validate hooks
3. **Return Structured Data**: Hooks return status objects for rendering
4. **No Cross-Module Imports**: Never import another module's internal state

### Hook Design
1. **Idempotent**: Hooks should be safe to run multiple times
2. **Error Handling**: Use exceptions for critical failures, structured returns for status
3. **Clear Naming**: `module_XX_operation` format (XX = priority number)
4. **Documentation**: Each hook should have clear docstrings

### Configuration Management
1. **Register Labels**: Always register UI labels and icons your module uses
2. **Version Dependencies**: Use `__module__.py` dependencies for required modules
3. **Config Extension**: Extend base whitelists through module-specific configs

### Testing
1. **Isolate Modules**: Test hooks independently without full deployment
2. **Mock Dependencies**: Mock external services and file operations
3. **Validate Rendering**: Test that hook results render correctly

## Common Patterns

### Configuration Loading
```python
# Each module loads its own config
@register_module_hook('deploy_00_pre_validate')
def load_module_config():
    global module_config
    module_config = load_config_from_install_file()
    return {"status": "configured", "config_version": "1.0"}
```

### Status Rendering
```python
@register_module_hook('deploy_95_render')
def render_module_status():
    # Get results from hook execution
    hook_results = get_hook_results()

    # Build module-specific table
    table = TableData()
    table.add_row('module_status', value="Module deployed successfully")

    return {
        "table_data": table,
        "field_config": FieldConfig().add_simple(['module_status'])
    }
```

### Error Handling
Hooks use exceptions for critical failures (`hh/gateway/registry/module_hooks.py:run_hooks()`):

```python
# Any hook can raise exceptions for critical failures
@register_module_hook('deploy_10_validate')
def validate_prerequisites():
    if critical_check_fails():
        raise ValueError("Critical prerequisite missing")  # Caught by run_hooks()

    return {"status": "validated", "warnings": ["minor issue"]}

# run_hooks() catches exceptions and stops execution:
# except Exception as e:
#     report_error("deployment", f"Hook failed: {module}.{func}")
#     return []  # Empty result stops remaining hooks
```

## Complete System Integration

The deploy script (`hh/deploy/deploy.py`) demonstrates the complete integration:

```python
# 1. Load whitelisted modules
# hh/deploy/deploy.py:deploy()
active_modules = load_whitelist_with_extensions('deploy_whitelist', ...)

# 2. Execute hook phases and aggregate results
hook_results: List[Dict[str, Any]] = []
results = run_hooks('deploy_00_pre_validate')    # Each module validates
if results:
    hook_results.extend(results)

results = run_hooks('deploy_05_stop_daemons')    # Each module stops services
if results:
    hook_results.extend(results)

results = run_hooks('deploy_30_remove_files')    # Server handles files
if results:
    hook_results.extend(results)

# 3. Render phase collects final status from all modules
render_instructions = run_hooks('deploy_95_render')
if render_instructions:
    hook_results.extend(render_instructions)

# 4. Results aggregated into final deployment response
result_data = {"hook_results": hook_results}
gateway.response.set_action_response(result_data)
```

This modular architecture enables scalable, maintainable deployment systems where each module owns its concerns while working together through well-defined hook interfaces and configuration systems.