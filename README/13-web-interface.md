# Chapter 13: Web Interface and Subdomains

## Overview

Henhouse provides a web browser interface for interacting with your installation. The interface is accessible through different subdomains, each with different access levels and capabilities.

## Technical Details: Subdomain Routing Architecture

NGINX routes requests to Flask daemons based on subdomain:

| Subdomain          | Flask Instance | Port | Tier  | Database User      | HTTP Auth |
|--------------------|----------------|------|-------|--------------------|-----------|
| `example.com`      | Guest          | 5001 | guest | `{project}_guest`  | None      |
| `www.example.com`  | Guest          | 5001 | guest | `{project}_guest`  | None      |
| `admin.example.com`| Admin          | 5003 | admin | `{project}_admin`  | Required  |
| `panel.example.com`| Root           | 5004 | root  | `{project}_root`   | Required  |

**Routing Flow**:
1. **NGINX receives request**: Determines subdomain from `Host` header
2. **Selects server block**: Routes to appropriate Flask instance based on subdomain
3. **HTTP Basic Auth** (admin/panel only): Validates credentials before proxying
4. **Proxies to Flask**: Sends request to `http://127.0.0.1:{port}` with tier info
5. **Flask app processes**: Extracts tier from script name, sets `USER_TIER` environment variable
6. **Gateway receives request**: Uses tier for permission checks and database connections

**Tier Detection in Flask**:
- Flask app script name: `{project_name}_{tier}.py` (e.g., `myproject_guest.py`)
- Tier extracted from script name via regex: `{project_name}_(\w+)\.py`
- Falls back to environment variable or empty string
- Tier passed to Gateway via `USER_TIER` environment variable

## Subdomain Architecture

### Main Domain (Public Access)

**URL**: `https://yourdomain.com` or `https://www.yourdomain.com`

**Access Level**: Public (no authentication required)

**Capabilities**:
- **Read-only access**: View pages and content
- **No write access**: Cannot create, modify, or delete pages
- **No app actions**: App action buttons do not appear
- **Guest tier**: Runs as guest tier Flask daemon (port 5001)

**Use Cases**:
- Public-facing website
- Content viewing
- Information display

### Admin Subdomain

**URL**: `https://admin.yourdomain.com`

**Access Level**: Protected (HTTP Basic Auth required)

**Authentication**:
- Username: `{project}_admin`
- Password: `htaccess_admin_password` (from install config)
- Stored in: `/var/www/.htpasswd_admin`

**Capabilities**:
- **Full write access**: Create, modify, and delete pages
- **App actions available**: App action buttons appear for page management
- **Admin tier**: Runs as admin tier Flask daemon (port 5003)
- **Database credentials**: Uses admin tier database user

**Use Cases**:
- Content management
- Page creation and editing
- Administrative tasks

### Panel Subdomain

**URL**: `https://panel.yourdomain.com`

**Access Level**: Protected (HTTP Basic Auth required)

**Authentication**:
- Username: `{project}_root`
- Password: `htaccess_panel_password` (from install config)
- Stored in: `/var/www/.htpasswd_panel`

**Capabilities**:
- **Full write access**: Create, modify, and delete pages
- **App actions available**: App action buttons appear for page management
- **Root tier**: Runs as root tier Flask daemon (port 5004)
- **Database credentials**: Uses root tier database user
- **MCP server access**: Used for MCP client connections

**Use Cases**:
- Full system access
- MCP server endpoint
- Root-level operations

**Note**: Currently, admin and panel subdomains are functionally equivalent in terms of database credentials and write access. Planned splits for more granular permissions are planned for future releases.

## Accessing the Web Interface

### Public Domain

Simply open your domain in a web browser:

```
https://yourdomain.com
```

No authentication is required. You can browse pages and view content, but cannot make changes.

### Admin Subdomain

1. Open `https://admin.yourdomain.com` in your browser
2. Enter HTTP Basic Auth credentials when prompted:
   - Username: `{project}_admin`
   - Password: `htaccess_admin_password` (from install config)

After authentication, you'll have full write access and app actions will be available.

### Panel Subdomain

1. Open `https://panel.yourdomain.com` in your browser
2. Enter HTTP Basic Auth credentials when prompted:
   - Username: `{project}_root`
   - Password: `htaccess_panel_password` (from install config)

After authentication, you'll have full write access and app actions will be available.

## Web Interface Features

### Page Navigation

The web interface provides hierarchical page navigation:
- **Breadcrumb navigation**: Shows current page path
- **Page tree**: Navigate through page hierarchy
- **Page browser**: Browse and select pages

### App Actions

App actions are interactive buttons that appear on pages when accessed through admin or panel subdomains. These actions allow you to:

- **Create pages**: Add new pages to the hierarchy
- **Modify pages**: Edit page names, text, and properties
- **Delete pages**: Remove pages from the hierarchy
- **Manage content**: Upload images, files, audio, video
- **Work page operations**: Create and manage work dockets, asks, tasks, steps

**Note**: App actions do **not** appear on the public domain (main domain). They are only available on admin and panel subdomains.

### Real-Time Updates

The web interface supports real-time updates:
- **No page refresh needed**: Changes update dynamically
- **Live dashboard**: View changes as they happen
- **Synchronized with MCP**: Changes made via MCP commands appear in the browser

## Using the Web Interface

### Creating Pages

1. Navigate to the parent page where you want to create a child
2. Click the "Add Page" app action button
3. Enter page name and select page class
4. Click "Create"

### Editing Pages

1. Navigate to the page you want to edit
2. Click the "Modify" app action button
3. Edit page name, text, or properties
4. Click "Save"

### Managing Content

1. Navigate to the page where you want to add content
2. Use app action buttons to:
   - Upload images
   - Upload files
   - Upload audio
   - Upload video
3. Content is attached to the page and accessible through the interface

### Work Page Management

1. Navigate to a work docket, ask, task, or step
2. Use app actions to:
   - Change status (todo, doing, review, done)
   - Modify work metadata
   - Update sort order
   - Add log entries

## Workflow: Cursor + Browser

A powerful workflow combines Cursor IDE with the web browser:

1. **Cursor IDE**: Open your project in Cursor, configure MCP (see Chapter 11)
2. **Web Browser**: Open `https://panel.yourdomain.com` in a separate window
3. **Agent Collaboration**: 
   - Use Cursor chat to have agents create/modify pages via MCP
   - Refresh browser to see live updates
   - View all changes in the web interface
   - Continue planning and iterating

**Example Workflow**:
- Agent creates a work docket in Cursor chat using MCP
- You refresh the browser and see the new work docket
- Agent adds tasks to the work docket via MCP
- You refresh and see the tasks appear
- You can view the full hierarchy in the browser while the agent continues working

## Troubleshooting

### Cannot Access Admin/Panel Subdomains

**Problem**: HTTP Basic Auth prompt doesn't appear or authentication fails

**Solutions**:
1. Verify htaccess files exist: `ls -la /var/www/.htpasswd_admin` and `/var/www/.htpasswd_panel`
2. Check credentials match install config
3. Verify NGINX is configured for these subdomains (see Chapter 9)
4. Check Flask daemons are running (see Chapter 10)

### App Actions Not Appearing

**Problem**: App action buttons don't show up

**Solutions**:
1. Verify you're accessing via admin or panel subdomain (not main domain)
2. Check you're authenticated (HTTP Basic Auth)
3. Verify Flask daemons are running for admin/root tiers
4. Check browser console for JavaScript errors

### Changes Not Appearing

**Problem**: Changes made via MCP don't show in browser

**Solutions**:
1. Refresh the browser page
2. Verify database changes were actually made (check via command line)
3. Check Flask daemon logs for errors
4. Verify you're looking at the correct page

## Next Steps

After familiarizing yourself with the web interface:

1. **Work Page Planning**: Learn about work page modules for project planning (see Chapter 14)
2. **Customizations**: Add your own customizations via the EXT folder (see Chapter 15)
3. **Framework Upgrades**: Learn how to upgrade the framework (see Chapter 16)

