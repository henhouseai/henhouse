# Chapter 15: EXT Folder and Customizations

## Overview

The `ext/` folder contains all user customizations and project-specific code. This folder is **never touched during framework upgrades**, making it safe for your customizations. The registry system automatically discovers code in `ext/` alongside code in `hh/`.

## Framework vs Extension Architecture

Henhouse uses a two-folder architecture to separate framework code from project-specific customizations:

- **`hh/` folder**: Core Henhouse framework code (reusable across all projects)
  - Contains all framework functionality: Gateway, Page system, deployment system, etc.
  - Framework upgrades happen in `hh/` folder
  - Shared across all projects using Henhouse
  - Located at project root: `{project_name}/hh/`

- **`ext/` folder**: Project-specific customizations (optional, per-project)
  - Contains project-specific modules, page classes, whitelist extensions, etc.
  - Project work happens in `ext/` folder
  - Unique to each project
  - Located at project root: `{project_name}/ext/`

**Key Distinction**:
- **Framework Work**: Changes to `hh/` affect all projects using Henhouse. These are framework upgrades.
- **Project Work**: Changes to `ext/` affect only the current project. These are project-specific implementations.

## Registry Scanning

Henhouse discovers code in `ext/` by scanning for decorators, just like it does for `hh/`. The registry system searches both folders when looking for registered handlers.

**Supported Decorators**:
- `@register_action` - Business logic handlers
- `@register_command` - Command registration
- `@register_mcp_tool` - MCP API tools
- `@register_http` - HTTP backend handlers
- `@register_maintenance_tool` - Maintenance daemon tools
- `@register_download` - Download backend handlers
- `@register_page_class` - Custom page classes
- `@register_tp_decorator` - Text processor decorators (for markup transformation)
- `@register_label` - Configuration labels (for render system)

**Warning**: If you register something in `ext/` that already exists in `hh/` (and wasn't blacklisted), you'll get a warning. The `ext/` registration will take precedence.

## Directory Structure

You can organize `ext/` however you like for your custom Python modules. However, certain subdirectories have special meaning:

- **`ext/deploy/conf/`** - Configuration file overrides (whitelists, blacklists)
- **`ext/deploy/db/`** - Database schema extensions
- **Any structure** - For custom Python modules, page classes, actions, etc.

## Configuration System

The configuration system manages whitelists, blacklists, and application settings that control what gets deployed and how the system behaves. All configuration files are located in `hh/deploy/conf/` and can be extended in `ext/deploy/conf/`.

### Configuration Files Location

**Directory**: `hh/deploy/conf/`

All configuration files are whitelisted to survive deployment cleanup. The `conf/` folder is included in `DEPLOY_WHITELIST` so it remains in `/srv/{project_name}/hh/deploy/conf/` after deployment.

### File Type Whitelists

The system uses separate whitelist files for different file types:

**Python Whitelist** (`py_whitelist.py`):
- Defines `PY_WHITELIST`: Python files deployed to `/srv/{project_name}/site/py/`
- Currently includes: `hh/deploy/site/infographic/infographic.py`

**JavaScript Whitelist** (`js_whitelist.py`):
- `JS_ALWAYS_INCLUDE`: JavaScript files included on every page (`seed.js`, `rpc-client.js`, `app.js`)
- `JS_WHITELIST`: All JavaScript files that can be included via `gateway.add_js_link()`
- Includes overlay system files, page data files, infographic files
- Files deployed flat to `site/js/` (overlay subfolder files flattened)

**CSS Whitelist** (`css_whitelist.py`):
- `CSS_ALWAYS_INCLUDE`: CSS files included on every page (`site.css`, `ansi-colors.css`, `tables.css`, `pygments.css`, `overlay.css`)
- `CSS_WHITELIST`: All CSS files that can be included via `gateway.add_css_link()`
- Includes tier-specific CSS files (site-guest.css, site-verified.css, site-admin.css, site-root.css)
- Includes infographic CSS files

**Miscellaneous Whitelist** (`misc_whitelist.py`):
- Defines `MISC_WHITELIST`: Additional files and patterns for deployment
- Includes favicons, web manifests, and other static assets

### Context Whitelist/Blacklist

**Files**: `context_whitelist.py`, `context_blacklist.py`

Controls what gets deployed for agent visibility (context documentation, planning docs, source code):

- **`CONTEXT_WHITELIST`**: Folders/files included in deployment:
  - `'context'`, `'planning'`, `'hh'` - Documentation and source
  - Top-level scripts: `hen.py`, `hen.ps1`, `hen.sh`, `stage.py`, `stage.ps1`, `stage.sh`, `mcp_wrapper.py`
  - Project files: `README.md`, `LICENSE`, `requirements.txt`
- **`CONTEXT_BLACKLIST`**: Patterns excluded from deployment:
  - `.git`, `__pycache__`, `*.pyc`, `.pytest_cache`
  - `node_modules`, `.env`, `*.log`
  - Cache JSON files: `*-reg.json`, `*.cycle.json`, `cache.json`, `*.cache.json`

### Deploy Whitelist

**File**: `deploy_whitelist.py`

Defines what stays in the `hh/deploy/` folder after deployment cleanup:

- **`DEPLOY_WHITELIST`**: Items preserved in deploy folder:
  - `'cache'` - Cache cleanup registry and utilities
  - `'conf'` - Configuration whitelists (self-preserving)
  - `'maint'` - Maintenance helpers
  - `'utils.py'` - General deployment utilities
- **`EXTRA_DEPLOY_FILES`**: Additional files deployed to `/srv/{project_name}`:
  - `hh/deploy/flask/http_client.py`
  - `hh/deploy/flask/mcp_client.py`
  - `hh/deploy/maint/maintenance_client.py`

### Blacklist/Whitelist Pattern

The configuration system uses a three-step process for combining base and extension whitelists:

1. **Load base** from `hh/deploy/conf/{name}.py`
2. **Subtract blacklist** from `ext/deploy/conf/{name}_blacklist.py` (if exists)
3. **Add extension** from `ext/deploy/conf/{name}.py` (if exists)

**Naming Convention**:
- Whitelist files in `ext/` use the same name as in `hh/` (e.g., `css_whitelist.py`)
- Blacklist files match the whitelist name but say "blacklist" instead of "whitelist" (e.g., `css_blacklist.py`)
- Location indicates override: `ext/` files override `hh/` files

**Example - CSS Whitelist Extension**:

```python
# hh/deploy/conf/css_whitelist.py
CSS_WHITELIST = [
    'hh/deploy/site/css/site.css',
    'hh/deploy/site/css/site-guest.css',
]

# ext/deploy/conf/css_blacklist.py
CSS_WHITELIST = [
    'hh/deploy/site/css/site-guest.css',  # Remove guest CSS
]

# ext/deploy/conf/css_whitelist.py
CSS_WHITELIST = [
    'ext/infographic/infographic-viewer.css',  # Add custom CSS
]

# Final result: ['hh/deploy/site/css/site.css', 'ext/infographic/infographic-viewer.css']
```

**Warning**: If you add something to an extension whitelist that already exists in the base (and wasn't blacklisted), you'll get a warning. This helps catch accidental duplicates.

## Technical Details: Configuration System Architecture

The configuration system is used by:

- **File deployment**: Reads all whitelists to determine what gets deployed
- **HTTP/NGINX deployment**: Reads whitelists to configure static file serving
- **Site assets deployment**: Uses whitelists to determine which files are deployed
- **Installation system**: Uses `HENHOUSE_TIERS` from `user_account_suffixes.py` to determine user tiers

**Project Detection**: The system uses `detect_project_context()` from `hh/deploy/utils.py` to automatically find project name and repository root. This function walks up from the current working directory looking for an `hh/` folder. (See Chapter 5 for more details on project detection.)

**Tier Configuration**: The `HENHOUSE_TIERS` constant (`['guest', 'verified', 'admin', 'root']`) is defined in `hh/deploy/conf/user_account_suffixes.py` and used throughout the deployment system to determine which users, database users, and Flask instances to create.

**Configuration File Details**:

- **`user_account_suffixes.py`**: Defines `HENHOUSE_TIERS` constant used by installation system, database deployment, Flask application management, and HTTP/NGINX deployment to create tier-specific users, database users, and Flask instances.

- **`application_actions.py`**: Defines application action links for admin/root tier CRUD operations in the web interface. Actions are organized into groups with header labels, and each action has a DOM ID for JavaScript event handlers (no hrefs). Actions appear only on admin and panel subdomains (not on public domain).

- **`site_links.py`**: Defines the site navigation menu links that appear in the sidebar. Navigation links are organized into groups with header pages, and each link references a page by ID and displays custom text.

- **`user_info.py`**: User information configuration (used by various systems for user display and management).

**Whitelist Usage**: The configuration system uses a three-step process for combining base and extension whitelists:
1. Load base whitelist from `hh/deploy/conf/{name}.py`
2. Subtract blacklist items from `ext/deploy/conf/{name}_blacklist.py` (if exists)
3. Add extension items from `ext/deploy/conf/{name}.py` (if exists)

This allows projects to remove framework items via blacklists and add custom items via extension whitelists, while preserving the base framework whitelist.

## Database Extensions

You can extend the database schema by creating `ext/deploy/db/schema_ext.sql`. This file is executed **after** the core schema (`hh/deploy/db/init.sql`) during database initialization.

**Requirements**:
- Must be idempotent (use `IF NOT EXISTS` clauses)
- Can reference core tables via foreign keys
- Runs in the same transaction as core schema

**Example**:

```sql
-- ext/deploy/db/schema_ext.sql
CREATE TABLE IF NOT EXISTS custom_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    page_id INT NOT NULL,
    custom_field VARCHAR(255),
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Custom Page Classes

You can create custom page classes in `ext/` that extend the base `Page` class:

**Example**:

```python
# ext/my_module/my_page.py
from hh.page.page import Page
from hh.gateway.registry.page_class import register_page_class

@register_page_class('my_custom_page')
class MyCustomPage(Page):
    """Custom page class for project-specific functionality."""
    
    def allow_null_names(self) -> bool:
        """Allow pages of this class to have null names."""
        return False
    
    def allow_duplicate_names(self) -> bool:
        """Allow duplicate names within the same parent."""
        return True
    
    def get_display_name(self) -> str:
        """Custom display name logic."""
        if self.name:
            return f"Custom: {self.name}"
        return "Unnamed Custom Page"
```

The registry system will automatically discover this class and make it available when creating pages with `class='my_custom_page'`.

## Custom Actions and Commands

You can add custom actions and commands in `ext/`:

**Example - Custom Action**:

```python
# ext/my_module/my_actions.py
from hh.gateway.registry.registry import register_action, register_command
from hh.gateway.gateway import get_gateway

@register_action('my_custom_action')
@register_command('my-custom-action')
def my_custom_action() -> bool:
    """Custom action for project-specific functionality."""
    gateway = get_gateway()
    # Your custom logic here
    return True
```

## Custom MCP Tools

You can add custom MCP tools in `ext/`:

**Example**:

```python
# ext/my_module/my_mcp_tools.py
from hh.gateway.registry.mcp import register_mcp_tool

@register_mcp_tool('my_custom_tool')
def my_custom_tool(arg1: str, arg2: int) -> dict:
    """Custom MCP tool for project-specific functionality."""
    # Your custom logic here
    return {"result": "success"}
```

## Preserving hh/ Customizations

If you've modified files in `hh/` directly (not recommended, but sometimes necessary), you can preserve them during upgrades using `ext/deploy/conf/upgrade_preserve.py`.

**Usage**:
- Paths are relative to project root (e.g., `"hh/gateway/custom.py"`)
- Use sparingly - preserved files may become incompatible with framework upgrades
- Only preserve files you've actually modified

**Example**:

```python
# ext/deploy/conf/upgrade_preserve.py
UPGRADE_PRESERVE = [
    'hh/gateway/custom.py',  # File you modified in hh/
]
```

**Warning**: Preserving files in `hh/` is risky. Prefer moving customizations to `ext/` instead.

## Application Actions

**File**: `hh/deploy/conf/application_actions.py`

Defines application action links for admin/root tier CRUD operations in the web interface:

- **Groups**: Actions are organized into groups with header labels
- **Actions**: Each action has a DOM ID for JavaScript event handlers (no hrefs)
- **Tier Access**: Actions appear only on admin and panel subdomains (not on public domain)
- **Configuration**: Edit `APPLICATION_ACTIONS` list to add/modify action groups

**Example Structure**:
```python
APPLICATION_ACTIONS = [
    {
        'group': 'test',
        'group_label': 'TEST',
        'actions': [
            {'action_id': 'test_one', 'label': 'test one'},
            {'action_id': 'test_two', 'label': 'test two'},
        ]
    },
]
```

You can extend this in `ext/deploy/conf/application_actions.py` to add project-specific actions.

## Site Links

**File**: `hh/deploy/conf/site_links.py`

Defines the site navigation menu links that appear in the sidebar:

- **Groups**: Navigation links are organized into groups with header pages
- **Links**: Each link references a page by ID and displays custom text
- **Configuration**: Edit `SITE_LINKS` list to customize navigation menu

**Example Structure**:
```python
SITE_LINKS = [
    {
        'group': 'home',
        'header_page_id': 1,
        'header_text': 'HOME',
        'links': [
            {'page_id': 234, 'text': 'SOURCE CODE'},
            {'page_id': 28, 'text': 'about'},
        ]
    },
]
```

You can extend this in `ext/deploy/conf/site_links.py` to customize your site's navigation menu.

## Package Import Requirement

The `ext/` folder must be importable as a Python package, which requires an `ext/__init__.py` file. This file already exists and makes `ext/` importable for registry scanning.

## Best Practices

1. **Keep customizations in `ext/`**: Never modify `hh/` directly if you can avoid it
2. **Use blacklists sparingly**: Only blacklist items you truly don't need
3. **Extend, don't replace**: Prefer extending base functionality over replacing it
4. **Test after upgrades**: Verify customizations still work after framework upgrades
5. **Document customizations**: Keep notes on what you've customized and why

## Troubleshooting

### Custom Code Not Discovered

**Problem**: Registry doesn't find your custom code in `ext/`

**Solutions**:
1. Verify `ext/__init__.py` exists
2. Check decorators are correct (`@register_action`, `@register_page_class`, etc.)
3. Clear cache: `{hen_script_name} clear-cache`
4. Verify file structure matches expected patterns

### Conflicts with Framework Code

**Problem**: Warnings about duplicate registrations

**Solutions**:
1. Check if you're registering something that already exists in `hh/`
2. Use blacklists to remove base items if you're replacing them
3. Verify your custom code is actually needed (maybe framework already provides it)

## Technical Details: TypeScript Compilation

JavaScript files deployed to `/srv/{project_name}/site/js/` are compiled from TypeScript source files. The compilation process preserves directory structure and supports both framework (`hh/`) and extension (`ext/`) TypeScript files.

### Compilation Process

**Source Directories**:
- `hh/deploy/site/ts/` - Framework TypeScript source files
- `ext/deploy/site/ts/` - Extension TypeScript source files (project-specific)

**Compilation Command**: TypeScript files are compiled using `tsc` (TypeScript compiler) from the project root directory, using `tsconfig.json` for configuration.

**Output Structure**: Compiled output preserves the full directory structure:
- `hh/deploy/site/ts/**/*.ts` → `hh/deploy/site/js/hh/deploy/site/ts/**/*.js`
- `ext/deploy/site/ts/**/*.ts` → `hh/deploy/site/js/ext/deploy/site/ts/**/*.js`

**Key Point**: All compiled JavaScript files (from both `hh/` and `ext/`) are placed in the same `hh/deploy/site/js/` directory, maintaining their original path structure within that directory.

### Deployment Integration

**Whitelisting**: The entire `hh/deploy/site/js/` directory (containing both `hh/` and `ext/` compiled output) is whitelisted in `JS_WHITELIST`:
- Base whitelist: `JS_WHITELIST = ['hh/deploy/site/js']`
- Extension whitelist: `ext/deploy/conf/js_whitelist.py` can add individual files or additional directories

**Deployment Process**: During deployment, the deploy script recursively finds all `.js` files in whitelisted directories and copies them to `/srv/{project_name}/site/js/`, preserving the subfolder structure.

**Note**: TypeScript source files (`*.ts`) are not deployed - only the compiled JavaScript output is deployed to production.

## Next Steps

After learning about customizations:

1. **Framework Upgrades**: Learn how to upgrade the framework while preserving customizations (see Chapter 16)

