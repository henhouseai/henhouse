# Henhouse Deployment Hook System

Agent documentation for the hookified deployment architecture.

---

## Overview

Henhouse uses a **hookification architecture** that distributes deployment logic across modules instead of concentrating it in monolithic scripts. Each module owns its deployment hooks, making the system modular, extensible, and maintainable.

**The Problem (Before Hookification):**
- Monolithic 500+ line scripts with hardcoded module logic
- Adding a module required editing multiple framework files
- High risk - one mistake breaks entire deployment
- Tight coupling between framework and modules
- Impossible to disable modules cleanly

**The Solution (After Hookification):**
- Each module owns its deployment logic in `deploy/` folder
- Framework scripts are thin orchestrators calling `run_hooks()`
- Modules can be added/removed without touching framework
- Module blacklist automatically prevents hooks from running
- Clear ownership - module code lives with module

---

## Hook Registry System

### Core Functions

Located in `hh/gateway/registry/module_hooks.py`:

```python
@register_module_hook(hook_name: str, priority: int = 100, description: str = "")
def my_hook_function():
    """Decorator registers a hook for a specific deployment phase."""
    pass

run_hooks(hook_name: str) -> List[Dict[str, Any]]
    """Execute all registered hooks for a name, ordered by priority.
    Returns list of results from each module's hook."""
```

**How It Works:**
1. Modules use `@register_module_hook()` to register functions
2. Framework calls `run_hooks('hook_name')` at appropriate times
3. Registry executes hooks in priority order (low number = runs first)
4. Within same priority, hooks execute alphabetically by module name
5. Each hook's return value is collected and returned
6. Module auto-discovery finds the module name from the function's file path

**Key Properties:**
- **Flexible**: Any hook name can be used (no predefined master list)
- **Non-blocking**: If no hooks registered, gracefully returns empty list
- **Priority-ordered**: Control execution sequence with priority numbers
- **Module-aware**: Each hook knows which module it belongs to
- **Blacklist-aware**: Blacklisted modules' hooks are never executed

### Example Hook Registration

```python
# hh_page/deploy/db_hooks.py
from hh.gateway.registry.module_hooks import register_module_hook

@register_module_hook('init_db_15_init_page_main', priority=100,
                      description="Initialize page and link tables")
def init_page_tables():
    """Create pages and links tables in main database."""
    # ... implementation ...
    return {"tables_created": ["pages", "links"]}
```

---

## Hook Naming Convention

All hooks follow the pattern: `{command}_{phase}_{description}`

### Components

1. **Command** - The deployment command (install, deploy, init_db, etc.)
2. **Phase** - Two-digit number controlling execution order (00, 05, 10, ...)
3. **Description** - Short snake_case description of what this phase does

### Phase Numbering Rules

**Increment by 5s:**
- Phases use: 00, 05, 10, 15, 20, 25, ...
- Gaps allow inserting new phases without renumbering
- Example: If you need a phase between 10 and 15, use 11, 12, or 13

**Standard Phase Ranges:**
- `00` - Pre-validation (always runs first)
- `05-85` - Primary work phases (command-specific)
- `90` - Cleanup (temp files, credentials)
- `95` - Rendering (always runs last)

**Fine-Grained Separation:**
- Similar operations use different phases for ordering
- Example: `init_db_15_init_page_main` vs `init_db_20_init_page_cache`
- Pages separate from media, main DB separate from cache DB

**Parallel Execution:**
- Multiple modules at SAME phase = run in parallel
- Example: All media modules at phase 25 for main DB tables
- Framework doesn't care about module count

### Examples

```
init_db_05_create_main_db       # Command: init_db, Phase: 05, Creates main database
install_55_media_dirs           # Command: install, Phase: 55, Creates media directories
deploy_95_render                # Command: deploy, Phase: 95, Rendering hooks
add_db_users_20_grant_media_main  # Command: add_db_users, Phase: 20, Grant permissions
```

---

## Current Hookified Commands

### Database Operations

**init_db** - Initialize database schema
- 00: Create credential files
- 05: Create main database
- 10: Create cache database
- 15-30: Create tables (pages, then media)
- 90: Remove credentials
- 95: Render summaries

**clean_db** - Drop all tables
- 00: Create credential files
- 05-20: Drop tables (cache first, then main; media first, then pages)
- 90: Remove credentials
- 95: Render summaries

**add_db_users** - Create database users and grant permissions
- 00: Create credential files
- 05: Create tier users
- 10-25: Grant permissions (pages, then media)
- 90: Remove credentials
- 95: Render summaries

**remove_db_users** - Revoke permissions and remove database users
- 00: Create credential files
- 05-20: Revoke permissions (reverse order: media, then pages)
- 25: Remove tier users
- 90: Remove credentials
- 95: Render summaries

**export_db** / **import_db** - Database backup/restore
- 00: Pre-validate and setup
- 05-10: Export/import operations (cache, then main)
- 90: Cleanup temp files
- 95: Render summaries

### Installation Operations

**install** - Install Henhouse on new system
- **Branching logic**: Mode detected in phase 00
- **Template mode** (00-02-95):
  - 00: Detect mode='template'
  - 01: Modules contribute config template sections
  - 02: Write template file, STOP (skip 05-70)
  - 95: Render template summary
- **Install mode** (00, 05-70, 95):
  - 00: Detect mode='install'
  - 05: Validate configuration
  - 10-70: Installation phases (users, git, directories, permissions, etc.)
  - 95: Render installation summary

**uninstall** - Remove Henhouse from system
- 00: Pre-validate
- 15-65: Removal phases (users, directories, groups, cleanup)
- 95: Render uninstall summary

### Deployment Operations

**deploy** - Deploy code to production
- 00: Pre-validate
- 05: Stop daemons
- 10-30: Git operations (preserve, sterilize, restore, deploy modules, cleanup)
- 35-75: Deployment operations (cache cleanup, Flask apps, client files, site, permissions)
- 80: Restart daemons
- 85-87: NGINX operations
- 90: Update manifest
- 95: Render deployment summary

**remove** - Remove deployed site
- 00: Pre-validate
- 05-15: NGINX cleanup
- 20-25: Stop daemons
- 30-35: Remove files and clear manifest
- 95: Render removal summary

---

## Module Ownership Patterns

### Framework Core (hh/)

**What belongs in hh core:**
- Fundamental operations (database creation, tier users)
- Gateway and entry point scripts
- Cross-cutting infrastructure (credentials, cache cleanup)
- Operations that MUST run exactly once per command

**Example hooks:**
- `init_db_05_create_main_db` - Core framework creates databases
- `add_db_users_05_create_users` - Core framework creates tier users
- `install_45_scripts` - Core framework creates gateway scripts

### Module-Specific Logic

**What belongs in modules:**
- Module-specific database tables/permissions
- Module-specific directories
- Module-specific configuration validation
- Module-specific rendering

**Example modules:**
- `hh_page/` - Page and link tables, page cache
- `hh_image/`, `hh_file/`, `audio/`, `video/` - Media tables, media directories
- `hh_git/` - Git repository operations
- `hh_flask/`, `maintenance/` - Daemon management
- `hh_nginx/` - Web server configuration
- `hh_srv/` - Server deployment infrastructure
- `hh_user_tiers/` - Tier user management

### Parallel Module Execution

When multiple modules run at the SAME phase number, they execute in parallel:

```
# All four media modules at phase 25 (main DB tables)
init_db_25_init_media_main:
  - audio module
  - hh_file module
  - hh_image module
  - video module

# All four again at phase 30 (cache DB tables)
init_db_30_init_media_cache:
  - audio module
  - hh_file module
  - hh_image module
  - video module
```

Order doesn't matter within a phase - they're independent operations.

---

## File Organization

### Standard Module Structure

```
my_module/
  __module__.py              # Module manifest
  __init__.py                # Module init
  deploy/
    db_hooks.py              # Database operation hooks
    db_user_hooks.py         # Database user permission hooks
    install_hooks.py         # Installation hooks
    {command}_hooks.py       # Other command-specific hooks
```

### Naming Conventions

**Hook files:**
- Pattern: `{command}_hooks.py`
- Examples: `install_hooks.py`, `deploy_hooks.py`, `db_hooks.py`

**Helper files:**
- Pattern: `{command}_helpers.py` or `{topic}_helpers.py`
- Examples: `db_helpers.py`, `db_user_helpers.py`, `install_helpers.py`
- Contain shared functions used by multiple hooks

**Configuration globals:**
- Live in framework hook files for cross-cutting state
- Example: `INSTALL_CONFIG` in `hh/deploy/install_hooks.py`
- Modules import: `from hh.deploy.install_hooks import INSTALL_CONFIG`

---

## The 95 Rendering Pattern

Every hookified command has a `{command}_95_render` hook that modules use to contribute output.

### Two Types of Rendering

**1. Summary Pieces (Aggregated)**

Modules return `{"table_data": TableData, "field_config": FieldConfig}`:

```python
@register_module_hook('init_db_95_render', priority=100,
                      description="Render image module summary")
def render_summary():
    table = TableData()
    table.add_row('image_tables', info='images, image_cache')

    config = FieldConfig()
    config.add_simple(['image_tables'])

    return {
        "table_data": table,
        "field_config": config
    }
```

The parser aggregates all pieces into ONE summary table.

**2. Full Tables (Separate)**

Modules return `{"render_block": "html_string"}`:

```python
@register_module_hook('deploy_95_render', priority=200,
                      description="Render Flask daemon detail table")
def render_flask_table():
    table = TableData()
    # ... build detailed table ...

    html = render_block(table, field_config, block_type='rows')

    return {"render_block": html}
```

The parser inserts full tables as separate sections.

### Parser Pattern

All hookified parsers follow this pattern:

```python
@register_parser('my_command')
def my_command_parser() -> bool:
    # Get action response
    json_data = gateway.response.get_action_response()
    source_data = get_data(json_data)

    lines = [render_header_block('l_my_command_header')]

    # Call 95_render hooks
    render_instructions = run_hooks('my_command_95_render')

    # Separate pieces vs full tables
    summary_table_data = TableData()
    summary_field_config = FieldConfig()
    full_tables = []

    for instruction in render_instructions:
        if 'render_block' in instruction:
            full_tables.append(instruction['render_block'])
        elif 'table_data' in instruction:
            # Merge into summary
            summary_table_data.rows.extend(instruction['table_data'].rows)
            summary_field_config.configs.extend(instruction['field_config'].configs)

    # Render summary table first
    if summary_table_data.num_rows() > 0:
        summary_field_config.add_header('my_command_summary')
        lines.append(render_block(summary_table_data, summary_field_config))
        break_section(lines)

    # Then render full tables
    for full_table in full_tables:
        lines.append(full_table)
        break_section(lines)

    gateway.response.add_output(finalize_output(lines))
    return True
```

**Key points:**
- Call `break_section(lines)` after EACH table
- Summary table shows aggregated data from all modules
- Full tables appear as separate sections
- Modules control what they contribute via return value

---

## Discovery Tools

### module_list Command

Shows all discovered modules with their hooks:

```bash
python hen.py module_list
```

**Output:**
- Module status (enabled/blacklisted)
- Hook count per module
- Per-module hook tables showing all hooks that module provides

**Use case:** "Which modules provide hooks? What hooks does module X have?"

### hook_list Command

Shows all hooks organized by command prefix:

```bash
python hen.py hook_list
```

**Output:**
- Separate table for each command (init_db, deploy, install, etc.)
- All hook registrations shown with module and description
- Section breaks between different hook names

**Use case:** "What's the full execution flow for command X? Which modules contribute to each phase?"

**Reading the output:**
- Each hook name may have multiple rows (one per module)
- Hook name only shown on first row to reduce clutter
- Modules column shows which module provides that hook
- Description explains what that specific module's hook does

### Hook Cache

The hook registry is cached for performance:

**Cache Location:** `hh/gateway/registry/cache/module-hooks.json`

**What's Cached:**
- All discovered hooks with their module names
- Hook descriptions and priorities
- Updated during module discovery (cold cache rebuild)

**When to Rebuild:**
- After adding new hooks to modules
- After modifying hook decorators
- Automatically on first run if cache missing

---

## Implementation Examples

### Example 1: Database Table Creation

```python
# hh_page/deploy/db_hooks.py
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.db_config import DB_CONFIG

@register_module_hook('init_db_15_init_page_main', priority=100,
                      description="Initialize page and link tables")
def init_page_main_tables():
    """Create pages and links tables in main database."""
    trace_in()

    # Use credentials from DB_CONFIG (created by framework in phase 00)
    mysql_cmd = f"mysql --defaults-extra-file={DB_CONFIG['main_cred_file']}"

    sql = """
    CREATE TABLE IF NOT EXISTS pages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        parent INT,
        class VARCHAR(100),
        text TEXT
    );

    CREATE TABLE IF NOT EXISTS links (
        id INT AUTO_INCREMENT PRIMARY KEY,
        page_id INT,
        url VARCHAR(512)
    );
    """

    # Execute SQL
    result = subprocess.run(f"{mysql_cmd} -e {shlex.quote(sql)}",
                          shell=True, capture_output=True)

    if result.returncode != 0:
        warn(f"Failed to create page tables: {result.stderr}")
        return trace_out({"success": False})

    log("Page tables created successfully")
    return trace_out({"success": True, "tables": ["pages", "links"]})
```

### Example 2: Permission Grants

```python
# hh_page/deploy/db_user_hooks.py
from hh.gateway.registry.module_hooks import register_module_hook
from hh.deploy.db_config import DB_CONFIG

@register_module_hook('add_db_users_10_grant_page_main', priority=100,
                      description="Grant page permissions on main DB")
def grant_page_permissions():
    """Grant SELECT, INSERT, UPDATE, DELETE on page tables."""
    trace_in()

    # Get tier list from DB_CONFIG
    tiers = DB_CONFIG.get('tier_list', [])
    if not tiers:
        warn("No tier list found in DB_CONFIG")
        return trace_out({"success": False})

    grants_applied = []
    for tier_name in tiers:
        db_user = f"{DB_CONFIG['project_name']}_{tier_name}"

        sql = f"""
        GRANT SELECT, INSERT, UPDATE, DELETE
        ON {DB_CONFIG['main_db']}.pages
        TO '{db_user}'@'localhost';

        GRANT SELECT, INSERT, UPDATE, DELETE
        ON {DB_CONFIG['main_db']}.links
        TO '{db_user}'@'localhost';

        FLUSH PRIVILEGES;
        """

        # Execute grant
        # ... (similar to above example)

        grants_applied.append(tier_name)

    log(f"Granted page permissions to {len(grants_applied)} tier users")
    return trace_out({"success": True, "tiers": grants_applied})
```

### Example 3: Rendering Hook

```python
# hh_page/deploy/db_hooks.py (continued)

@register_module_hook('init_db_95_render', priority=100,
                      description="Render page module summary")
def render_page_summary():
    """Contribute page module summary to aggregated table."""
    trace_in()

    from hh.render.render import TableData, FieldConfig

    # Create summary piece
    table = TableData()
    table.add_row('page_tables', info='pages, links, page_cache')

    config = FieldConfig()
    config.add_simple(['page_tables'])

    # Return piece for aggregation
    return trace_out({
        "table_data": table,
        "field_config": config
    })
```

### Example 4: Branching Logic (Install)

```python
# hh/deploy/install.py (action function)

@register_action('install')
@register_command('install')
def install() -> bool:
    """Install with hookified architecture - branches on mode."""
    trace_in()
    gateway = get_gateway()

    hook_results = []

    # Phase 00: ALWAYS runs - determines mode
    if not is_error():
        results = run_hooks('install_00_pre_validate')
        hook_results.extend(results)

    # Get mode from INSTALL_CONFIG (set by phase 00 hook)
    from hh.deploy.install_hooks import INSTALL_CONFIG
    mode = INSTALL_CONFIG.get("mode")

    if mode == "template":
        # BRANCH A: Template generation only
        if not is_error():
            results = run_hooks('install_01_template_contribute')
            hook_results.extend(results)

        if not is_error():
            results = run_hooks('install_02_template_write')
            hook_results.extend(results)

        # STOP - skip 05-70 phases
        return trace_out(not is_error())

    elif mode == "install":
        # BRANCH B: Full installation
        phases = [
            'install_05_pre_validate',
            'install_10_conflict_check',
            # ... all phases 05-70 ...
        ]

        for phase in phases:
            if not is_error():
                results = run_hooks(phase)
                hook_results.extend(results)

        # Set response for parser
        if not is_error():
            gateway.response.set_action_response(
                success_payload({"hook_results": hook_results})
            )

        return trace_out(not is_error())
```

---

## Adding New Hooks

### Step-by-Step Guide

**1. Identify the command and phase**

Determine which hookified command you're extending (install, deploy, init_db, etc.) and where your hook fits in the sequence.

**2. Choose phase number**

Follow the increment-by-5s rule. Place your hook before or after existing phases:
- Need to run before phase 20? Use 15 or 17
- Need to run after phase 20? Use 25 or 22

**3. Create hook file if needed**

If your module doesn't have a hook file for this command yet:

```python
# my_module/deploy/{command}_hooks.py
from hh.gateway.registry.module_hooks import register_module_hook
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log

trace_in = lambda: None
trace_out = lambda arg: arg
log = lambda msg: None

def _initialize_debug():
    global trace_in, trace_out, log
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
```

**4. Register your hook**

```python
@register_module_hook('{command}_{phase}_{description}',
                      priority=100,  # Usually 100 unless ordering matters
                      description="Human-readable description")
def my_hook_function():
    """Docstring explaining what this hook does."""
    trace_in()

    # Your implementation here

    log("Operation completed successfully")
    return trace_out({"success": True, "details": "..."})
```

**5. Test the hook**

Run the command and verify your hook executes:

```bash
python hen.py {command} -log -debug
```

Look for log messages from your hook in the output.

**6. Add rendering hook (if applicable)**

If the command has a 95_render phase, contribute output:

```python
@register_module_hook('{command}_95_render',
                      priority=100,
                      description="Render my module summary")
def render_my_summary():
    """Contribute summary information."""
    trace_in()

    from hh.render.render import TableData, FieldConfig

    table = TableData()
    table.add_row('my_module_info', info='relevant details')

    config = FieldConfig()
    config.add_simple(['my_module_info'])

    return trace_out({
        "table_data": table,
        "field_config": config
    })
```

**7. Register labels (if needed)**

If you introduced new field types, register them:

```python
# my_module/deploy/config_labels.py
from hh.render.config.config_registry import register_label

@register_label("my_module_info", "My Module", "🔧")
def _register_labels():
    pass
```

**8. Verify with discovery tools**

Check that your hooks appear correctly:

```bash
python hen.py module_list  # Should show your module with new hook count
python hen.py hook_list    # Should show your hooks in the command table
```

---

## Common Patterns

### Pattern 1: Using Credentials

Framework creates credential files in phase 00, modules use them:

```python
from hh.deploy.db_config import DB_CONFIG

def my_db_operation():
    # Credential file created by framework in phase 00
    cred_file = DB_CONFIG['main_cred_file']
    mysql_cmd = f"mysql --defaults-extra-file={cred_file}"

    # Use it for operations
    subprocess.run(f"{mysql_cmd} -e '{sql}'", shell=True)
```

### Pattern 2: Parallel Media Operations

All media modules run at same phase - keep operations independent:

```python
# ALL four modules register this hook at priority 100
@register_module_hook('init_db_25_init_media_main', priority=100,
                      description="Initialize {media_type} tables")
def init_my_media_tables():
    # Create my media tables
    # No dependencies on other media modules
    pass
```

### Pattern 3: Conditional Execution

Use `is_error()` to stop on errors:

```python
# In action function
if not is_error():
    results = run_hooks('phase_10_operation')
    hook_results.extend(results)

if not is_error():
    results = run_hooks('phase_15_operation')
    hook_results.extend(results)

# If phase_10 fails, phase_15 won't run
```

### Pattern 4: Cross-Cutting State

For global state that multiple modules need:

```python
# In framework hook file (e.g., hh/deploy/install_hooks.py)
INSTALL_CONFIG = {}

@register_module_hook('install_00_pre_validate', priority=100,
                      description="Detect installation mode")
def pre_validate():
    global INSTALL_CONFIG
    # Set global that other modules can import
    INSTALL_CONFIG["mode"] = "install"  # or "template"
    return {"mode": INSTALL_CONFIG["mode"]}

# In module hook file
from hh.deploy.install_hooks import INSTALL_CONFIG

@register_module_hook('install_01_template_contribute', priority=100,
                      description="Contribute template sections")
def contribute_template():
    mode = INSTALL_CONFIG["mode"]  # Access cross-cutting state
    # ...
```

---

## Best Practices

### Do:
- ✅ Use phase numbering with 5s increments
- ✅ Provide clear, descriptive hook names
- ✅ Include meaningful description in decorator
- ✅ Use trace_in() and trace_out() for debugging
- ✅ Log significant operations with log()
- ✅ Return structured data from hooks
- ✅ Keep hooks focused on single responsibility
- ✅ Register labels for new field types
- ✅ Call break_section() after each table in parsers

### Don't:
- ❌ Don't hardcode module logic in framework
- ❌ Don't create dependencies between parallel modules
- ❌ Don't use phase numbers arbitrarily (follow the pattern)
- ❌ Don't skip error handling
- ❌ Don't forget to import DB_CONFIG or other globals
- ❌ Don't mix summary pieces with full tables in 95_render
- ❌ Don't skip trace_in()/trace_out()
- ❌ Don't commit temporary credential files

---

## Troubleshooting

### Hook Not Executing

**Check:**
1. Is module blacklisted? (`python hen.py module_list`)
2. Is hook registered? (`python hen.py hook_list`)
3. Does command call run_hooks() for this phase?
4. Any errors in previous phases? (use `-log -debug`)

### Wrong Execution Order

**Check:**
1. Phase numbers - are they in correct sequence?
2. Priority numbers - lower runs first
3. Module discovery - is module being found?

### Import Errors

**Common issues:**
- Missing `from hh.deploy.{command}_hooks import SOME_CONFIG`
- Circular imports between hook files
- Missing module `__init__.py` files

### Rendering Issues

**Check:**
1. Did you return correct structure? (`table_data` + `field_config` OR `render_block`)
2. Did parser call `break_section(lines)` after each table?
3. Are field types registered in config_labels.py?
4. Did you add header to field config? (`.add_header()`)

---

## Summary

The hookification architecture transforms Henhouse deployment from monolithic scripts into a modular, extensible system:

- **Modules own their deployment logic** via decorator-based hooks
- **Framework orchestrates** via phase-based `run_hooks()` calls
- **Consistent patterns** across all deployment commands
- **Discovery tools** (module_list, hook_list) visualize the system
- **95 rendering pattern** aggregates output from all modules
- **Easy to extend** - just register new hooks, no framework changes needed

For agents: When working on deployment operations, check existing hooks with `hen hook_list`, follow the established patterns, and add your hooks to appropriate module files. The system handles discovery, ordering, and execution automatically.
