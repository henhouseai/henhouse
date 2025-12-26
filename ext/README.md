# Extension Folder (ext/)

The `ext/` folder contains all user customizations and project-specific code. This folder is **never touched during framework upgrades**, making it safe for your customizations.

## Overview

- **Purpose**: User customizations and project-specific implementations
- **Location**: Project root, sibling to `hh/` folder
- **Upgrade Safety**: Never modified during framework upgrades
- **Registry Integration**: Henhouse automatically scans `ext/` for decorated modules

## Registry Scanning

Henhouse discovers code in `ext/` by scanning for decorators, just like it does for `hh/`. The registry system searches both folders when looking for registered handlers.

**Supported Decorators:**
- `@register_action` - Business logic handlers
- `@register_command` - Command registration
- `@register_mcp_tool` - MCP API tools
- `@register_http` - HTTP backend handlers
- `@register_maintenance_tool` - Maintenance daemon tools
- `@register_download` - Download backend handlers
- `@register_page_class` - Custom page classes

**Warning**: If you register something in `ext/` that already exists in `hh/` (and wasn't blacklisted), you'll get a warning. The `ext/` registration will take precedence.

## Directory Structure

You can organize `ext/` however you like for your custom Python modules. However, certain subdirectories have special meaning:

- **`ext/deploy/conf/`** - Configuration file overrides (whitelists, blacklists)
- **`ext/deploy/db/`** - Database schema extensions
- **Any structure** - For custom Python modules, page classes, actions, etc.

## Blacklist/Whitelist Pattern

The configuration system uses a three-step process for combining base and extension whitelists:

1. **Load base** from `hh/deploy/conf/{name}.py`
2. **Subtract blacklist** from `ext/deploy/conf/{name}_blacklist.py` (if exists)
3. **Add extension** from `ext/deploy/conf/{name}.py` (if exists)

**Naming Convention:**
- Whitelist files in `ext/` use the same name as in `hh/` (e.g., `css_whitelist.py`)
- Blacklist files match the whitelist name but say "blacklist" instead of "whitelist" (e.g., `css_blacklist.py`)
- Location indicates override: `ext/` files override `hh/` files

**Example - CSS Whitelist Extension:**

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

## Database Extensions

You can extend the database schema by creating `ext/deploy/db/schema_ext.sql`. This file is executed **after** the core schema (`hh/deploy/db/init.sql`) during database initialization.

**Requirements:**
- Must be idempotent (use `IF NOT EXISTS` clauses)
- Can reference core tables via foreign keys
- Runs in the same transaction as core schema

**Example:**

```sql
-- ext/deploy/db/schema_ext.sql
CREATE TABLE IF NOT EXISTS custom_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    page_id INT NOT NULL,
    custom_field VARCHAR(255),
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Preserving hh/ Customizations

If you've modified files in `hh/` directly (not recommended, but sometimes necessary), you can preserve them during upgrades using `ext/deploy/conf/upgrade_preserve.py`.

**Usage:**
- Paths are relative to project root (e.g., `"hh/gateway/custom.py"`)
- Use sparingly - preserved files may become incompatible with framework upgrades
- Only preserve files you've actually modified

**Example:**

```python
# ext/deploy/conf/upgrade_preserve.py
UPGRADE_PRESERVE = [
    'hh/gateway/custom.py',  # File you modified in hh/
]
```

**Warning**: Preserving files in `hh/` is risky. Prefer moving customizations to `ext/` instead.

## Example: Custom Page Class

Here's a complete example of creating a custom page class in `ext/`:

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

## Package Import Requirement

The `ext/` folder must be importable as a Python package, which requires an `ext/__init__.py` file. This file already exists and makes `ext/` importable for registry scanning.

## Best Practices

1. **Keep customizations in `ext/`**: Never modify `hh/` directly if you can avoid it
2. **Use blacklists sparingly**: Only blacklist items you truly don't need
3. **Document your extensions**: Add docstrings and comments explaining your customizations
4. **Test after upgrades**: Framework upgrades won't touch `ext/`, but you should verify compatibility
5. **Use meaningful names**: Make it clear what your customizations do

## Integration with Deployment

- `ext/` folder is deployed to `/srv/{project_name}/ext/` during deployment
- `ext/deploy/` is cleaned after deployment (preserving whitelisted items like `conf/`)
- Whitelist extensions control what gets deployed from `ext/`
- Registry scanning works in both development and production

For more information on deployment, see `deployment/file-deployment.md` and `context/deployment.md`.

