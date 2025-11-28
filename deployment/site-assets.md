# Site Assets Deployment

The site folder contains all static web assets (CSS, JavaScript, favicons, etc.) that are deployed to `/srv/{project_name}/site/` and served by the web application.

## Prerequisites

Before using site assets deployment, you must have:
- Project folder with `hh/deploy/site/` directory structure
- Whitelist configuration files in place (see `configuration.md`)

The site assets deployment is handled automatically by the file deployment system (see `file-deployment.md`). All site assets are controlled by whitelist files in `hh/deploy/conf/` (see `configuration.md`).

## Directory Structure

**Directory**: `hh/deploy/site/`

**Subdirectories**:
- **`css/`**: Stylesheets (tier-specific color schemes, layout, syntax highlighting)
- **`js/`**: JavaScript files (compiled from TypeScript source)
- **`infographic/`**: Standalone infographic module (optional, project-specific)

**Top-level files**:
- Favicon files (`.ico`, `.png` variants)
- `site.webmanifest` (PWA manifest)
- `ajaxloading.gif` (loading animation)

## CSS Stylesheets

**Directory**: `hh/deploy/site/css/`

The CSS system uses a separation of concerns approach:

### Base Stylesheet

**File**: `site.css`
- **Purpose**: Layout, structure, and formatting (no colors)
- **Content**: Box model, typography, container structure, link base styles, component layouts
- **Philosophy**: Defines *how* things are laid out, not *what* they look like

### Tier-Specific Color Schemes

Each user tier has its own color theme stylesheet:

- **`site-guest.css`**: Dark theme with blue accents (public/guest tier)
- **`site-verified.css`**: Color scheme for verified tier
- **`site-admin.css`**: Orange/amber theme (admin tier)
- **`site-root.css`**: Color scheme for root tier

**Color Organization**:
- Colors are defined in tier-specific files, not hardcoded in base styles
- Each tier file defines CSS variables and color values for:
  - Body background and text colors
  - Link colors (normal, hover, visited)
  - Container backgrounds and borders
  - Heading colors
  - Status box colors
  - Button colors
  - Border colors
- This allows visual identification of which portal/tier you're logged into
- The tier system is defined by the installation system (see `installation.md`)

**Example Structure**:
```css
/* site-guest.css - Dark theme color scheme */
body {
    color: #d4d4d4;
    background: #0d1117;
}
a {
    color: #79c0ff;  /* Subdued blue theme */
}
.container {
    background: #161b22;
    border: 1px solid #30363d;
}
```

### Supporting Stylesheets

**Always Included** (via `CSS_ALWAYS_INCLUDE` from `configuration.md`):
- **`ansi-colors.css`**: ANSI terminal color codes for code output
- **`tables.css`**: Table styling and formatting
- **`pygments.css`**: Syntax highlighting for code blocks
- **`overlay.css`**: Overlay/modal dialog styling

**Whitelisting**: All CSS files are whitelisted in `hh/deploy/conf/css_whitelist.py` (see `configuration.md`):
- `CSS_ALWAYS_INCLUDE`: Files loaded on every page
- `CSS_WHITELIST`: All available CSS files (can be included via `gateway.add_css_link()`)

## JavaScript Files

**Directory**: `hh/deploy/site/js/`

**Note**: JavaScript files in this directory are compiled from TypeScript source. See TypeScript documentation in context files for development details.

**Structure**:
- Main application files (`app.js`, `page-manager.js`, `rpc-client.js`)
- Page data handlers (`work-page-data.js`, `mcp-request-page-data.js`, etc.)
- Overlay system (`overlay/` subdirectory)
- Utility files (`debug-helper.js`, `upload-handler.js`, `seed.js`)

**Whitelisting**: JavaScript files are whitelisted in `hh/deploy/conf/js_whitelist.py` (see `configuration.md`) and deployed to `/srv/{project_name}/site/js/` by file deployment (see `file-deployment.md`).

## Favicon and Web Assets

**Top-level files** in `hh/deploy/site/`:

- **`favicon.ico`**: Main favicon (15KB)
- **`favicon-16x16.png`**: 16x16 PNG favicon
- **`favicon-32x32.png`**: 32x32 PNG favicon
- **`apple-touch-icon.png`**: iOS home screen icon (9KB)
- **`android-chrome-192x192.png`**: Android icon 192x192 (10KB)
- **`android-chrome-512x512.png`**: Android icon 512x512 (35KB)
- **`site.webmanifest`**: PWA manifest file (defines icons, theme colors)
- **`ajaxloading.gif`**: Loading animation (404B)

**Whitelisting**: All misc files are whitelisted in `hh/deploy/conf/misc_whitelist.py` (see `configuration.md`) and deployed to `/srv/{project_name}/site/` (top level) by file deployment (see `file-deployment.md`).

## Infographic Module

**Directory**: `hh/deploy/site/infographic/`

**Note**: This is a standalone, project-specific module for creating flowcharts and diagrams. It's currently used for Henhouse's self-documentation but is not part of the core system.

**Purpose**: Demonstrates how to add custom modules to the site deployment:
1. Add files to `hh/deploy/site/infographic/`
2. Whitelist CSS/JS files in respective whitelists (see `configuration.md`)
3. Files are automatically deployed with the rest of the site by file deployment (see `file-deployment.md`)

**Status**: Not documented in detail - project-specific customization example.

## Deployment Integration

**Deploy Script Integration** (`hh/deploy/srv/deploy.py` - see `file-deployment.md`):

The deploy script handles site folder deployment:

1. **Site Directory Setup**:
   - Creates `/srv/{project_name}/site/` directory
   - Clears existing site directory if present

2. **JavaScript Deployment**:
   - Reads `JS_WHITELIST` from `hh/deploy/conf/js_whitelist.py` (see `configuration.md`)
   - Copies whitelisted JS files to `site/js/`
   - Preserves subdirectory structure (e.g., `overlay/`)

3. **CSS Deployment**:
   - Reads `CSS_WHITELIST` from `hh/deploy/conf/css_whitelist.py` (see `configuration.md`)
   - Copies whitelisted CSS files to `site/css/`

4. **Python File Deployment**:
   - Reads `PY_WHITELIST` from `hh/deploy/conf/py_whitelist.py` (see `configuration.md`)
   - Copies whitelisted Python files to `site/py/` (if any)

5. **Miscellaneous File Deployment**:
   - Reads `MISC_WHITELIST` from `hh/deploy/conf/misc_whitelist.py` (see `configuration.md`)
   - Copies whitelisted files to `site/` (top level)
   - Handles both files and directories

**Deployment Statistics**: The deploy script logs counts of deployed items (JS, CSS, PY, MISC) for verification.

## File Whitelisting System

All site assets are controlled by whitelist files in `hh/deploy/conf/` (see `configuration.md`):

- **`css_whitelist.py`**: Defines `CSS_ALWAYS_INCLUDE` and `CSS_WHITELIST`
- **`js_whitelist.py`**: Defines `JS_WHITELIST` and `JS_ALWAYS_INCLUDE`
- **`py_whitelist.py`**: Defines `PY_WHITELIST` (if Python files are needed)
- **`misc_whitelist.py`**: Defines `MISC_WHITELIST` for top-level files

**Path Format**: All paths in whitelists are relative to project root (above `hh/` folder).

## Integration with Other Systems

The site assets deployment integrates with:

1. **File Deployment** (`file-deployment.md`): 
   - Site assets are deployed to `/srv/{project_name}/site/` during file deployment
   - All whitelists are read to determine which files to deploy

2. **HTTP/NGINX Deployment** (`http-nginx.md`): 
   - NGINX serves static files from `/srv/{project_name}/site/` directly
   - NGINX reads whitelists to generate location blocks for static file serving
   - Static files are served with no-cache headers to prevent stale content

3. **Flask Application Management** (`flask.md`): 
   - Flask applications reference site assets via URLs (e.g., `/site/css/site.css`)
   - Flask doesn't serve static files directly - NGINX handles static file serving

4. **Configuration System** (`configuration.md`): 
   - All site assets are controlled by whitelist files
   - Whitelists determine which files are deployed and served

5. **Installation System** (`installation.md`): 
   - Tier-specific CSS files correspond to user tiers created during installation
   - Site assets use the tier system for visual identification

## Deployment Workflow

Site assets are automatically deployed during file deployment:

**During File Deployment**:
- All whitelisted site assets are copied to `/srv/{project_name}/site/`
- Files are served by NGINX (see `http-nginx.md`) with no-cache headers

**Modifying Site Assets**:
- Edit files in `hh/deploy/site/`
- Add new files to appropriate whitelists in `hh/deploy/conf/` (see `configuration.md`)
- Run `sudo hen deploy` to deploy changes (see `file-deployment.md`)

See `workflows.md` for complete deployment workflow documentation.

