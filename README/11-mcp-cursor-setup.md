# Chapter 11: MCP Wrapper Setup in Cursor

## Overview

Configure the MCP (Model Context Protocol) wrapper script in Cursor IDE to enable agents to run MCP commands directly in chat windows. This allows agents to interact with your Henhouse database and make changes through the Cursor interface.

## Prerequisites

Before setting up MCP in Cursor, ensure you have:

1. **Chapter 9**: HTTP/NGINX configuration completed (HTTPS must be configured)
2. **Chapter 10**: Flask and maintenance daemons running
3. **Developer box**: Cursor IDE installed on your development machine
4. **Project cloned**: Henhouse project cloned on your developer box

## Developer Box Configuration

### Step 1: Copy Config File from Server

Copy the baseline config file from your deployment server:

```bash
# On your developer box, copy from server
scp user@your-server:/home/{project_owner}/.{project}.cnf ~/.{project}.cnf
```

This config file was created during installation and contains database credentials.

### Step 2: Edit Config File

Edit the config file on your developer box:

```bash
# Edit the config file
vi ~/.{project}.cnf
# or
nano ~/.{project}.cnf
```

**Update the `[client]` section**:
- Set `host=db.yourdomain.tld` (your database host)
- Keep `user` and `password` (from server config)
- Set `ssl_ca=/home/you/.{project}/ssl/ca.pem` (or your chosen path)

**Add an `[mcp]` section** for MCP HTTP authentication:
```ini
[mcp]
user={project}_root
password=<htaccess_panel_password>
host=panel.yourdomain.tld
```

Use the `htaccess_panel_password` from your install config (`/root/.{project}-install.cnf` on the server).

**Note**: The MCP wrapper uses `[mcp]` section if present; otherwise falls back to `[client]` section.

### Step 3: Copy SSL CA Certificate

Copy the SSL CA certificate bundle from your server:

```bash
# On server, copy to a readable location
scp user@your-server:/etc/mysql/ssl/ca.pem ~/ca.pem

# On developer box, create directory and copy
mkdir -p ~/.{project}/ssl
# Copy the file you just downloaded
cp ~/ca.pem ~/.{project}/ssl/ca.pem

# Set proper permissions
chmod 600 ~/.{project}/ssl/ca.pem
```

**Important**: Update paths in `~/.{project}.cnf` to point to your local CA bundle. Do not reference server-only paths.

### Step 4: Set Up Developer Box Wrapper Scripts

The project includes wrapper scripts for developer boxes (laptops/desktops) on all major operating systems:

- **Windows**: `hen.ps1` and `stage.ps1` (PowerShell scripts)
- **Mac/Linux**: `hen.sh` and `stage.sh` (bash scripts)

These scripts change to the project directory and run the Python scripts, allowing you to use `hen` and `stage` commands from anywhere.

#### Add Project Folder to PATH

**Windows**:
1. Open System Properties → Environment Variables
2. Add the project folder (e.g., `C:\Users\username\Desktop\henhouse`) to your user PATH environment variable

**Mac/Linux**:
Add to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):

```bash
export PATH="/path/to/henhouse:$PATH"
```

#### Make Scripts Executable (Mac/Linux Only)

```bash
chmod +x hen.sh stage.sh
```

#### Optional: Remove Extensions (Mac/Linux Only)

For cleaner commands, you can remove the `.sh` extension:

```bash
mv hen.sh hen
mv stage.sh stage
```

This lets you type `hen` instead of `hen.sh`. On Windows, PowerShell automatically recognizes `.ps1` files.

After setup, you can use `hen` and `stage` commands from any directory. The scripts are already marked as executable in git (for Mac/Linux), so they'll be executable when cloned.

## Technical Details: Developer Box Wrapper Scripts

The wrapper scripts provide convenience by:

- **Automatic directory change**: Scripts `cd` to the project directory before running Python
- **Cross-platform support**: Windows PowerShell scripts and Unix bash scripts
- **PATH integration**: Once added to PATH, commands work from anywhere
- **Project detection**: Scripts automatically find the project root

**File locations**:
- `hen.sh` / `hen.ps1`: Wrapper for `hen.py` (main command script)
- `stage.sh` / `stage.ps1`: Wrapper for `stage.py` (stage branch management)

These scripts are part of the project repository and are deployed with the code. They're designed to work on developer boxes where the project is cloned, not on the deployment server (which uses the entry scripts created during installation).

## Cursor IDE Configuration

### Step 1: Create or Edit MCP Config

Create or edit the Cursor MCP configuration file:

**Windows**: `C:\Users\{username}\.cursor\mcp.json`

**Mac/Linux**: `~/.cursor/mcp.json`

### Step 2: Add MCP Server Configuration

Add the MCP server configuration to `mcp.json`:

```json
{
  "mcpServers": {
    "{project_name}-root": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_wrapper.py"]
    }
  }
}
```

**Replace placeholders**:
- `{project_name}-root`: Use your actual project name (e.g., `henhouse-root`, `myproject-root`)
- `/absolute/path/to/mcp_wrapper.py`: Use the absolute path to `mcp_wrapper.py` in your project directory

**Example for Windows**:
```json
{
  "mcpServers": {
    "henhouse-root": {
      "command": "python",
      "args": ["C:\\Users\\lee\\Desktop\\henhouse\\mcp_wrapper.py"]
    }
  }
}
```

**Example for Linux/Mac**:
```json
{
  "mcpServers": {
    "henhouse-root": {
      "command": "python",
      "args": ["/home/user/henhouse/mcp_wrapper.py"]
    }
  }
}
```

**Windows path notes**: You can use either:
- Escaped backslashes: `"C:\\Users\\username\\project\\mcp_wrapper.py"`
- Forward slashes: `"C:/Users/username/project/mcp_wrapper.py"`

### Step 3: Restart Cursor

**Important**: Restart Cursor IDE to load the MCP server configuration.

After restarting, Cursor will connect to your MCP server and agents will be able to use MCP tools in chat windows.

## What This Enables

- **MCP commands in Cursor chat**: Agents can run MCP tools to update database content and make changes
- **Direct database interaction**: Agents can create pages, work dockets, and manage content through chat
- **File uploads**: Agents can upload images, audio, video, and documents via MCP
- **Unified interface**: Same commands work in terminal, web browser, and Cursor chat windows

## Testing MCP Setup

After configuring and restarting Cursor, test MCP commands:

1. **Open a Cursor chat window**
2. **Ask your agent to use MCP tools**:
   - "Use the MCP tool `show_page` to show page ID 1"
   - "Create a new page using the `add_page` MCP tool"
   - "List available MCP tools"

3. **Verify commands work**: The agent should be able to interact with your Henhouse database directly

## File Upload Support

The MCP wrapper supports automatic file uploads. Agents can include files in MCP tool calls using:

- **`_files` parameter**: Array of file paths (e.g., `["image1.jpg", "audio.mp3"]`)
- **`file_paths` parameter**: Alternative parameter name (same format)

**Supported file types**:
- Images (jpg, png, gif, etc.)
- Audio (with streaming support)
- Video (with streaming support)
- Documents

Files are automatically attached to HTTP requests as multipart/form-data. File paths can be:
- **Relative**: To project root (e.g., `"image.jpg"`)
- **Absolute**: Must be within project directory

The wrapper validates file paths to prevent path traversal attacks.

## Troubleshooting

### MCP Server Not Found

**Problem**: Cursor can't find the MCP server

**Solutions**:
1. Verify `mcp.json` file is in the correct location:
   - Windows: `C:\Users\{username}\.cursor\mcp.json`
   - Mac/Linux: `~/.cursor/mcp.json`
2. Check JSON syntax is valid (no trailing commas, proper quotes)
3. Verify the path to `mcp_wrapper.py` is correct and absolute
4. Ensure Python is in your PATH

### Configuration File Not Found

**Problem**: MCP wrapper reports "Configuration file not found"

**Solutions**:
1. Verify config file exists: `ls -la ~/.{project}.cnf`
2. Check project name detection: The wrapper auto-detects project name by finding `hh/` directory
3. Ensure config file has `[client]` or `[mcp]` section with required fields

### Authentication Failures

**Problem**: MCP requests fail with authentication errors

**Solutions**:
1. Verify `[mcp]` section in config file has correct credentials:
   - `user={project}_root`
   - `password=<htaccess_panel_password>` (from install config)
   - `host=panel.yourdomain.tld`
2. Check that HTTPS is configured (see Chapter 9)
3. Verify Flask daemons are running (see Chapter 10)
4. Test panel subdomain access: `curl https://panel.yourdomain.tld`

### Connection Refused

**Problem**: MCP wrapper can't connect to server

**Solutions**:
1. Verify HTTPS is configured and working (see Chapter 9)
2. Check Flask daemons are running: `{hen_script_name} flask-status`
3. Test panel subdomain: Open `https://panel.yourdomain.tld` in browser
4. Verify firewall allows HTTPS connections (port 443)

### File Upload Failures

**Problem**: File uploads fail in MCP tool calls

**Solutions**:
1. Verify file paths are correct (relative to project root or absolute within project)
2. Check file permissions: Files must be readable
3. Verify file types are supported
4. Check wrapper logs for specific error messages

## How MCP Works

The MCP wrapper script (`mcp_wrapper.py`):
- **Reads JSON-RPC from stdin**: Receives MCP protocol messages from Cursor
- **Bridges to HTTP**: Converts stdio MCP to HTTP requests
- **Sends to deployment box**: POSTs to `https://{host}/mcp` with Basic Auth
- **Handles file uploads**: Extracts `_files` or `file_paths` and sends as multipart/form-data
- **Returns responses**: Outputs JSON-RPC responses to stdout

The wrapper:
- Auto-detects project name by finding `hh/` directory
- Loads credentials from `~/.{project}.cnf` (prefers `[mcp]` section)
- Validates file paths to prevent security issues
- Handles multiple requests in a loop until EOF

## Next Steps

After MCP setup is complete:

1. **Test MCP commands**: Try using MCP tools in Cursor chat windows
2. **Customize MCP server**: Add your own MCP commands in the `ext/` folder
3. **Use in development**: Agents can now help with database operations through chat

For more details, see:
- `mcp_wrapper.py` docstring for wrapper details
- `context/mcp.md` for MCP system architecture
- README Development Tools section for additional information

