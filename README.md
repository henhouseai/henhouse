# What Is This?

Henhouse is a content management framework written in Python for building applications with hierarchical content, multimedia management (images, audio, video), file serving, and text processing.

- Gateway-based architecture
- Multiple backend interfaces (CLI, HTTP, MCP)
- Gateway loads minimum modules needed per request
- Gateway is single-shot dispatch - users make multiple requests by invoking multiple gateway instances
- Long-running processes are daemons (Flask daemons and maintenance daemon)
- MySQL two-database architecture - main database for application data, cache database for derived fields and metadata backup
- NGINX reverse proxy with SSL/TLS support, serves static files directly and proxies dynamic requests to Flask applications
- Four tier levels (guest, verified, admin, root) with different restrictions and permissions for each tier
- Tier permissions apply to both file system access and database access
- Four Flask daemons run, each as the appropriate tier user, letting Linux handle permissions enforcement for HTTP and MCP protocol requests

For detailed architecture documentation, see the [Documentation](#documentation) section below.

## Quick Start

This guide walks you through setting up Henhouse in phases, with each phase enabling new features. By the end, you'll have a customizable MCP server running that you can use in Cursor - your agents can run MCP commands in chat windows to update database content and make changes to the system. The web browser becomes a live dashboard for interacting with the system, and you can also use the command line for testing and smoke checking.

**Roadmap:**

- **Tier 1: Developer Box Smoke Check** - Quick peek on your developer box. Clone the repository, have an agent read the context documentation, and try running Python commands and the debugger in your terminal (Windows PowerShell, Mac Terminal, or Linux shell) without installing anything. Enables: Agent helper trained on the system, ability to explore commands and debug output locally.

- **Tier 2: Server Installation and Git Sync** - Quick peek on your deployment box. Clone on server, install system users and infrastructure, verify what was created, then set up git sync between developer box and deployment box. Test push/pull workflow and push-project recovery features. Enables: Git repository on server, tier-based Unix users, ability to sync code between boxes, recovery mechanisms via stage branches.

- **Tier 3: Database Setup** - Initialize database and create tier-based users. Enables: Database access, ability to create and manage pages, work pages for project planning, full CRUD operations via command line.

- **Tier 4: Deploy to /srv** - Deploy code to production location. This populates `/srv` with the code that will run for web requests, MCP commands, and daemons. Automatically starts Flask applications and maintenance daemon. Enables: Production code deployment, ability to test commands using entry points (`hen` instead of `python hen.py`), running Flask apps and maintenance daemon.

- **Tier 5: HTTP/NGINX Configuration** - Configure web server. Phase A: HTTP-only configuration for initial setup and SSL certificate verification. Phase B: HTTPS configuration with SSL certificates. Enables: Web browser interface as live dashboard, MCP server accessible via HTTP, ability to use MCP commands in Cursor chat windows.

- **Tier 6: Flask and Maintenance Daemons** - Verify and manage background services. Enables: Full system operation with web interface, MCP server, and automated maintenance tasks.

**Key Terms:**

- **Deployment Box**: Your Linux server (developed and tested on Ubuntu, but should work on most Linux distributions) that's accessible over the internet. This is where Henhouse runs in production, serving web requests and hosting your content.

- **Henhouse**: A Henhouse Framework-enabled project.
  - The Henhouse Framework is an extensible and upgradable framework (via the `ext/` folder)
  - Lets you develop on top of it with your own project code
  - Can be used as a bare install for project management with built-in work page management system
  - Coordinates with agents via the MCP server
  - Provides interface for agents and humans to view project status and plan
  - Supports attaching multimedia (images, audio, video) and files
  - Works for project management without modification
  - Can be extended into a content management system by adding customizations to the `ext/` folder
  - MCP interface lets agents connect to a Henhouse for project management independently of other code
  - Throughout this documentation, "Henhouse" (capital H) means a Henhouse Framework-enabled project

- **Project Name**: The project name is determined by the folder name where your Henhouse is located.
  - Set before you run install
  - Default is "henhouse" (lowercase, the folder name)
  - Can be renamed to anything you want (e.g., "foxhouse", "myproject")
  - Affects naming conventions throughout the system, including:
    - Unix users it creates
    - Database names it creates
    - Database usernames
    - Log file names
    - Many other file names and system identifiers
  - Allows running multiple Henhouse projects on the same server
  - Changing the project name after installation requires uninstalling, renaming the folder, and reinstalling (may also require manual database work)
  - Throughout this documentation, "henhouse" (lowercase) refers to the default project folder name

- **Entry Point**: The command you use to run Henhouse operations (e.g., `hen deploy`, `hen show-page`).
  - Default name is "hen"
  - Can be customized (e.g., "fox") to match your project name
  - Each project can have its own entry point name
  - You can run `hen deploy` for one project and `fox deploy` for another, all on the same deployment box
  - Changing the entry point name is easier than changing project name: uninstall and reinstall with new name
  - Throughout this documentation, we use "hen" as the default entry point name

- **Developer Box**: Your laptop, desktop, or development machine where you write code and use your IDE.
  - Developed and tested with Cursor as the agentic IDE, but other IDEs like GitHub Copilot should be compatible as well
  - No install process - just clone the repository and run Python code directly
  - Wrapper scripts available (`.sh` for Mac/Linux, `.ps1` for Windows) - add project folder to PATH to use `hen` and `stage` commands
  - Entry points provide CLI interface to test features before pushing to server
  - Once deployment box is fully set up with database and MCP server running, developer box can connect to it
  - Smoke testing Python code in terminal on developer box accesses database on deployed server and makes live changes
  - MCP: stdio to HTTP MCP wrapper script (custom MCP client) configured in `mcp.json`
  - MCP wrapper script sends requests to deployment box - agents run commands on deployed server, not developer box
  
**Additional Notes:**

- All code is written as individual Python modules (not a package)
- Web interface API programmed in TypeScript
- TypeScript compiled from root directory with `tsc` (requires TypeScript compiler installed)
- TypeScript requires complete installation and deployment to function (depends on database, Flask applications, MCP server)
- HTML served through HTTP backend with Fetch API for browser interactions
- All Fetch API interactions route through MCP backend for processing
- Lazy loading registry scans both `hh/` and `ext/` folders for decorators and handlers
- Add code to `ext/` folder and registry discovers it automatically
- Registry generates cache files during scanning
- Cache files (along with Python bytecode caches) cleared with `clear-cache` command

### Tier 1: Developer Box Smoke Check

Start on your developer box to get familiar with the system and train an agent helper.

**Step 1: Clone and Open in Cursor**

```bash
# Clone the repository
git clone https://github.com/henhouseai/henhouse.git
cd henhouse

# Open this folder in Cursor app as a new project
```

**Step 2: Train Your Agent First**

Before running any commands, have your agent read the core documentation so it can help explain what you're doing in more depth, and can also help with debugging if necessary:

1. Open an agent chat window in Cursor
2. Have the agent read these this `README.md` document and also these files from `context/`:
   - `overview.md`
   - `gateway.md`
   - `page.md`
   - `debug.md`
   - `deployment.md`
   - `registry.md`

This gives the agent enough context to help you use debug flags, understand what commands do, and troubleshoot issues.

**Step 3: Smoke Test**

Open a terminal in Cursor (PowerShell on Windows, Terminal on Mac, or shell on Linux) and try:

```bash
# Check dependencies (shows what's installed and what's missing)
python hen.py dependency-list

# Try other listers to explore the system:
python hen.py command-list
python hen.py action-list
python hen.py backend-list
python hen.py parser-list
python hen.py http-list
python hen.py mcp-list
python hen.py maintenance-list
python hen.py class-list
```

**Debug Flags:**

You can use debug flags if something isn't working or you want to see what's happening:

```bash
# enable the debugger to show log entries
python hen.py dependency-list -log

# Debug filtering: show unlimited number of entries  (default limit is 10 per unique function name)
python hen.py dependency-list -log -debug-limit 0

# Debug filtering: whitelist only modules in the gateway path
python hen.py dependency-list -log -white "*gateway*"

# Debug filtering: graylist only gateway.py file
python hen.py dependency-list -log -gray "gateway.py"
```

These commands work without installation - you're just running Python code.

**Installing Dependencies:**

Install Python dependencies as needed:

```bash
pip install -r requirements.txt
```

The `dependency-list` command identifies which requirements are needed. Some commands (like `flask-start`, `http-deploy`, `install`) require Unix-specific modules and will show as "Failed" on Windows - these are deployment commands meant for Linux servers (developed and tested on Ubuntu, but should work on most Linux distributions).

**Try It Out:**

- Train your agent by having it read the context documentation files - this gives it the knowledge to explain commands, help with debugging, and guide you through the system
- Explore available commands using listers - try `command-list`, `action-list`, `backend-list`, `mcp-list`, `class-list`, and others to see what's available
- Experiment with debug flags - use `-log`, `-debug`, `-trace` to see what's happening under the hood
- Use debug filtering - try `-white`, `-gray`, `-black` to focus debug output on specific modules, files, or functions
- Control debug output volume with `-debug-limit` - by default each function shows up to 10 debug/log messages before being quieted, use `-debug-limit 0` for unlimited output
- Test commands locally without installation - all of this works by just running Python code directly

### Tier 2: Server Installation and Git Sync

Once you've verified it works on your developer box, set it up on your deployment box.

**Prerequisites:**

- **Passwordless SSH**: You must be able to SSH from your developer box to your deployment box using passwordless authentication (SSH key pairs). The installer will copy these SSH keys to all tier users it creates.
- **MySQL Server**: MySQL must already be running on your deployment box (for later tiers).
- **Python**: Python 3.8 or higher must be installed on your deployment box.
- **NGINX**: NGINX must be installed on your deployment box (for later tiers).

**Step 1: Clone on Deployment Box**

```bash
# On your deployment box, clone into your home directory
cd ~
git clone https://github.com/henhouseai/henhouse.git

# (Optional) Rename your project folder, example "foxhouse"
# mv henhouse foxhouse

# move your project to a more central location (outside of your home folder)
sudo mv henhouse /

# Change into the project directory
cd /henhouse

# Check dependencies on deployment box, install packages as necessary
python hen.py dependency-list
pip install -r requirements.txt
```

**Step 2: Clean Git History (Recommended)**

Delete the `.git` folder so install creates a fresh repository instead of reusing the existing one.

```bash
# Remove existing git history so install starts fresh
rm -rf .git
```

**Step 3: Install (config-driven)**

```bash
# Install system users and infrastructure
cd /henhouse
ls -la

# CRITICAL: Must run inside the project directory, as the owner, with passwordless SSH ready.
# SSH keys are copied from ~/.ssh/authorized_keys to all tier users.

# First run: creates /root/.{project}-install.cnf (mode 600, root) and exits.
# Edit that file with:
#   db_host, cache_host, ssl_ca_path, cache_ssl_ca_path
#   mysql_root_password_main/cache, four DB user passwords, two htaccess passwords
#   hen_script_name (entry point), optional user_key
# Re-run after editing. Installer fails if manifest_users has entries (previous install not cleared).
sudo python hen.py install
```

**Step 4: Verify Installation**

After installation, check what was created:

```bash
# Check the main project directory
ls -la /srv/henhouse
# ls -la /srv/foxhouse  # If using custom project name

# Check media directories
ls -la /srv/images/henhouse
ls -la /srv/files/henhouse
ls -la /srv/audio/henhouse
ls -la /srv/video/henhouse

# Check users created
id henhouse_guest
id henhouse_verified
id henhouse_admin
id henhouse_root

# If reinstalling: ensure /root/.{project}-install.cnf [manifest_users] is empty
# and no leftover users remain, or install will refuse to run.

# Check git repository
ls -la /srv/henhouse/git/henhouse.git
```

**Step 5: Smoke Test on Server**

You can test commands on the server before deploying (just use `python hen.py` instead of `hen`):

```bash
# Test without install (use python explicitly)
python hen.py dependency-list

# After install, you can use the entry point
# (but first log out and log back in to refresh SSH group permissions)
```

**Step 6: Developer Box Setup from Server**

Once your server has a valid domain you can connect to, clone from the server instead of GitHub:

```bash
# On your developer box, clone from your server's bare repository
git clone user@your-server:/srv/henhouse/git/henhouse.git
# git clone user@your-server:/srv/foxhouse/git/foxhouse.git  # If using custom project name
cd henhouse
# cd foxhouse  # If using custom project name

# Open this folder in Cursor as a new project
# Your origin will point to the server's bare repo
```

You can add GitHub as an additional remote if you want:

```bash
# Add GitHub as additional remote (optional)
git remote add github https://github.com/henhouseai/henhouse.git
```

**Step 7: Test Push/Pull Cycle**

Test the git sync workflow before deploying:

```bash
# On developer box: make a change and push
# (use Cursor's git features or command line)
git add .
git commit -m "test change"
git push origin henhouse  # or foxhouse, myproject, etc. (not main/master)

# On deployment box: pull (no sudo needed, as your Unix user)
hen pull-project
# fox pull-project  # If using custom script name
```

This syncs the project directory with the head of your project branch. The `pull-project` command automatically clears caches.

**Step 8: Test Push-Project Feature**

The `push-project` feature creates side branches for recovery:

```bash
# On deployment box: create a stage branch
hen push-project --message "test stage branch"
# fox push-project --message "test stage branch"  # If using custom script name

# On developer box: pull the stage branch
stage pull
```

This gives you a recovery mechanism. You can also manually reset to previous commits:

```bash
# On deployment box: reset to previous commit
cd /path/to/project
git reset --hard <commit_hash>
sudo hen deploy  # Redeploy that version

# Then push-project to create recovery point
hen push-project --message "revert to working version"
```

All of this git sync workflow can be tested before running `deploy`. The only thing in `/srv` at this point is the git repository.

**What This Enables:**

- Git repository on server - bare repo at `/srv/{project_name}/git/{project_name}.git`
- Tier-based Unix users - four users (guest, verified, admin, root) with proper permissions
- Media directories - `/srv/images/`, `/srv/files/`, `/srv/audio/`, `/srv/video/` with proper permissions
- Code sync workflow - push from developer box, pull on server, test changes before deploying
- Recovery mechanisms - push-project creates stage branches, manual git reset for rollbacks
- Developer box connected - your Cursor project now points to server as origin

**Try It Out:**

Make a small change on your developer box (edit a file, add a comment), commit it, and push to the server. Then on the server, run `hen pull-project` to sync. Try the push-project feature to create a stage branch, then use `stage pull` on your developer box to retrieve it. Test the recovery workflow by making a change, pushing it, then using git reset to roll back and push-project to create a recovery point.

### Tier 3: Database Setup

Set up the database before deploying to avoid maintenance daemon errors:

```bash
# Initialize database (one-time setup)
sudo hen init-db --confirm -password <mysql_root_password>
# sudo fox init-db --confirm -password <mysql_root_password>  # If using custom script name

# Create tier-based database users
sudo hen add-db-users -password <mysql_root_password>
# sudo fox add-db-users -password <mysql_root_password>  # If using custom script name

# Create homepage
hen init-homepage
# fox init-homepage  # If using custom script name
```

**What This Enables:**

- Database access - main database and cache database initialized
- Tier-based database users - four MySQL users with appropriate permissions
- Homepage created - page ID 1 ready to use
- Full CRUD operations - create, read, update, delete pages via command line
- Work page system - project planning and management features
- Page management - hierarchical content, images, files, audio, video

**Try It Out:**

Test page operations from the command line: `hen show-page -id 1` to see your homepage. Try creating a page: `hen add-page -target-page 1 -name "Test Page"`. Create a work docket for project planning: `hen add-page -target-page 1 -name "My Project" -class work_docket`. Explore the work page system for organizing tasks and tracking progress. All of this works from the command line - perfect for testing before exposing via web interface.

### Tier 4: Deploy to /srv

Deploying populates `/srv` with the code that will run for web requests, MCP commands, and daemons. This automatically starts Flask applications and the maintenance daemon.

**Step 1: Deploy**

After installation completes, **log out and log back in** to refresh SSH group permissions, then:

```bash
# Deploy the application
sudo hen deploy
# sudo fox deploy  # If using custom script name
```

This copies whitelisted files to `/srv/{project_name}`, sets permissions, and prepares the production environment. The deploy process automatically stops and restarts Flask applications and the maintenance daemon. You can't do NGINX deployment until code is deployed to `/srv` first, because NGINX configuration is generated from the deployed code.

**Step 2: Verify Daemons**

Check that Flask apps and maintenance daemon are running:

```bash
# Check Flask daemon status (4 instances, one per tier)
hen flask-status
# fox flask-status  # If using custom script name

# Check maintenance daemon status
hen maintenance-status
# fox maintenance-status  # If using custom script name
```

You should see four Flask daemons running (ports 5001-5004) and one maintenance daemon. If you need to stop them, use `hen flask-stop` and `hen maintenance-stop`, but note that they will automatically restart the next time you run `sudo hen deploy`.

**Note**: Auto-start on server reboot is not yet enabled. If your server reboots, you'll need to manually start the daemons using `sudo hen flask-start` and `sudo hen maintenance-start`.

**Step 3: Test Push/Pull/Deploy Cycle**

Now test the full workflow:

```bash
# On developer box: make changes, commit, push
git push origin henhouse

# On deployment box: pull and deploy
hen pull-project && sudo hen deploy
```

**What This Enables:**

- Production code deployment - all whitelisted files copied to `/srv/{project_name}`
- Entry points - can use `hen` command instead of `python hen.py` on server
- Full deployment workflow - make changes locally, push, pull, and deploy in one cycle
- Running Flask applications - four tier-based Flask daemons serving web and MCP requests
- Maintenance daemon - background worker for cache refresh and job processing
- Code ready for web requests, MCP commands, and daemons

**Try It Out:**

Make a change to any Python file in your project, commit and push from developer box, then on server run `hen pull-project && sudo hen deploy`. Verify your changes are in `/srv/{project_name}`. Check that daemons are running with `hen flask-status` and `hen maintenance-status`. Try using the entry point: `hen command-list` or `hen dependency-list` to see it work without typing `python hen.py`.

### Tier 5: HTTP/NGINX Configuration

Configure the web server. This is a two-phase process: HTTP-only first (for SSL certificate verification), then HTTPS with SSL.

**Phase A: HTTP-Only Configuration**

If you're setting up a new domain, start with HTTP-only to allow SSL certificate verification:

```bash
# Configure HTTP/NGINX (HTTP-only, for SSL certificate setup)
sudo hen http-deploy -domain yourdomain.com
# sudo fox http-deploy -domain yourdomain.com  # If using custom script name
```

This allows the SSL certificate authority to verify your domain by uploading a file and checking it. Once your SSL certificate is issued, proceed to Phase B.

**Phase B: HTTPS Configuration**

After SSL certificates are installed (typically via Let's Encrypt):

```bash
# Configure HTTPS/NGINX with SSL certificates
sudo hen http-deploy-ssl -domain yourdomain.com
# sudo fox http-deploy-ssl -domain yourdomain.com  # If using custom script name
```

This configures NGINX with SSL certificates and sets up HTTP-to-HTTPS redirects.

**What This Enables:**

- Web browser interface - live dashboard for interacting with the system
- MCP server accessible via HTTP/HTTPS - your customizable MCP server is now accessible
- Secure connections - HTTPS with SSL certificates
- Multiple interfaces - use web browser, command line, or MCP chat windows - all access the same system

**Try It Out:**

Open your domain in a web browser - you now have a live dashboard. After configuring the MCP wrapper in Cursor (see Development Tools section below) and restarting Cursor, you can use MCP commands in chat windows. Test that HTTPS redirects work and that your site is accessible.

### Tier 6: Flask and Maintenance Daemons

Verify and manage the background services that power your Henhouse installation.

**Verify Daemon Status**

Check that all services are running properly:

```bash
# Check Flask daemon status (4 instances, one per tier)
hen flask-status
# fox flask-status  # If using custom script name

# Check maintenance daemon status
hen maintenance-status
# fox maintenance-status  # If using custom script name
```

You should see:
- Four Flask daemons running (ports 5001-5004), one for each tier (guest, verified, admin, root)
- One maintenance daemon running for cache refresh and job processing

**Daemon Management**

If you need to stop daemons:

```bash
# Stop Flask daemons
sudo hen flask-stop
# sudo fox flask-stop  # If using custom script name

# Stop maintenance daemon
sudo hen maintenance-stop
# fox maintenance-stop  # If using custom script name
```

**Important**: Every time you run `sudo hen deploy`, the daemons are automatically stopped before deployment and restarted after deployment. You don't need to manually manage them during normal deployment cycles.

**Auto-Start on Reboot**

Auto-start on server reboot is not yet enabled. If your server reboots, you'll need to manually start the daemons:

```bash
# Start Flask daemons
sudo hen flask-start
# sudo fox flask-start  # If using custom script name

# Start maintenance daemon
sudo hen maintenance-start
# fox maintenance-start  # If using custom script name
```

**What This Enables:**

- Full system operation - web interface, MCP server, and automated maintenance all running
- MCP commands in Cursor chat - agents can run MCP tools to update database content and make changes
- Automated maintenance - cache refresh and job processing happen in the background
- Customizable MCP server - you can extend it with your own MCP commands in the `ext/` folder

**Try It Out:**

Configure the MCP wrapper in Cursor (see Development Tools section below) and restart Cursor. In a Cursor chat window, ask your agent to use MCP tools like `show_page` or `add_page` - your agent can now directly interact with your Henhouse database. Try creating pages, work dockets, and managing content all through chat. You can also test from the command line: `hen show-page -id 1` works the same whether you're in a terminal (PowerShell, Terminal, or shell), a web browser, or a chat window. This is your customizable MCP server - you can add your own commands by creating MCP tool registrations in your `ext/` folder.

For detailed deployment documentation, see the `deployment/` folder.

### Development Tools

**Cursor IDE:**

To enable MCP (Model Context Protocol) access in Cursor IDE, configure the MCP wrapper script:

1. **Create or edit** `~/.cursor/mcp.json` (on Windows: `C:\Users\{username}\.cursor\mcp.json`)

2. **Add MCP server configuration**:
   ```json
   {
     "mcpServers": {
       "henhouse-root": {
         "command": "python",
         "args": ["/absolute/path/to/mcp_wrapper.py"]
       }
     }
   }
   ```

   **Example for Windows:**
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

   **Example for Linux/Mac:**
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

3. **Ensure credentials are configured**: The wrapper reads from `~/.henhouse.cnf` (same file as database config). Make sure it contains:
   ```ini
   [client]
   user=your_username
   password=your_password
   host=panel.yourdomain.com
   ```

4. **Restart Cursor** to load the MCP server configuration.

**File Upload Support:**

The MCP wrapper supports automatic file uploads. Agents can include files in MCP tool calls using `_files` or `file_paths` parameters. Supported file types include images, audio (with streaming), video (with streaming), and documents. Files are automatically attached to requests as multipart/form-data.

For more details, see `mcp_wrapper.py` docstring and `context/mcp.md`.

### Basic Usage

**Command Syntax**: The basic command format is:

```bash
python hen.py command-name -arg value
```

**Shorthand Command**: You can use the shorter `hen` command if the project folder is in your PATH. The project includes wrapper scripts for all major operating systems:

- **Windows**: `hen.ps1` and `stage.ps1` (PowerShell scripts)
- **Mac/Linux**: `hen.sh` and `stage.sh` (bash scripts)

To use them:

1. **Add project folder to PATH**:
   - **Windows**: Add `C:\path\to\henhouse` to your user PATH environment variable
   - **Mac/Linux**: Add the project path to `~/.bashrc`, `~/.zshrc`, or `~/.profile`: `export PATH="/path/to/henhouse:$PATH"`

2. **Make scripts executable** (Mac/Linux only):
   ```bash
   chmod +x hen.sh stage.sh
   ```

3. **Optional: Remove extensions** (Mac/Linux only):
   ```bash
   mv hen.sh hen
   mv stage.sh stage
   ```
   This lets you type `hen` instead of `hen.sh`. On Windows, PowerShell automatically recognizes `.ps1` files.

After setup, you can use `hen` and `stage` commands from anywhere. If the project folder is not in your PATH, you'll need to use the full `python hen.py` syntax or provide the full path to the script.

**Example Commands**:

```bash
# Show a page by ID
hen show-page -id 1

# Get help for a command
hen help
```

**Example Output** - Running `hen dependency-list`:

```
  🏠 Henhouse:   Dependency List:

    ┌──────────────────────────┬────────────────┬──────────────────────────────┐
    │ 📦  Dependencies         │ 6 dependencies │ required by                  │
    ╞══════════════════════════╪════════════════╪══════════════════════════════╡
    │ ❌  Dependency Missing   │ grp            │ process_manager              │
    │ ✅  Dependency Installed │ pillow         │ utils                        │
    │ ✅  Dependency Installed │ psutil         │ process_manager              │
    │ ❌  Dependency Missing   │ pwd            │ file_system, process_manager │
    │ ✅  Dependency Installed │ pygments       │ source_code_file_content     │
    │ ✅  Dependency Installed │ pymysql        │ connection                   │
    └──────────────────────────┴────────────────┴──────────────────────────────┘
```

For more example output from various commands, see [`smoke_check.md`](smoke_check.md) which contains a complete smoke test session run on Windows.

**Debugging**: Add `-log` to any command for debug output that traces the execution flow:

```bash
hen dependency-list -log
hen show-page -id 1 -log
```

**Git Workflows**: The `push-project` and `pull-project` commands help sync code between your developer box and deployment box. The `stage` script is also available for staging operations. See `deployment/workflows.md` for details on syncing changes.

## Architecture

The Henhouse Framework follows a gateway-based architecture where commands are parsed and routed through the Gateway, actions execute business logic, and backends format data for different interfaces (CLI, HTTP, MCP).

For architecture documentation, see the `context/` folder which contains system documentation covering Gateway, Page System, Registry, Render, Debug, MCP, Maintenance, and other core components.

## Deployment

The Henhouse Framework is designed for deployment on Linux servers (developed and tested on Ubuntu, but should work on most Linux distributions), with desktop/laptop development tools (Cursor app on Windows/Mac/Linux) working in conjunction with the server deployment.

For deployment documentation, including installation procedures, user tier configuration, deployment commands, git workflows, and server setup, see the `deployment/` folder.

## License

This project is licensed under the Mozilla Public License 2.0 (MPL 2.0). See the [LICENSE](LICENSE) file for details.

The MPL 2.0 is a file-level copyleft license that:
- Allows you to use the Henhouse Framework in proprietary projects
- Requires that modifications to MPL-licensed files remain open source
- Permits mixing open and closed source code in the same project

This license keeps the framework open while allowing proprietary use.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Documentation

Henhouse Framework documentation is organized into two main folders. The overview documents in each folder should be enough to guide agents through the rest of the documentation.

### `context/` - System Architecture Documentation

Training documents for agents to learn how to extend and customize the Henhouse Framework. These documents contain implementation information, code-level details, file locations, function names, and architectural patterns.

- **`overview.md`**: High-level system overview and architecture map
- **`gateway.md`**: Gateway system architecture, request lifecycle, and state management
- **`page.md`**: Page system architecture, validation functions, and extensibility
- **`registry.md`**: Registry system for handler discovery and loading
- **`render.md`**: Render system for output formatting
- **`debug.md`**: Debug system for data capture and troubleshooting
- **`mcp.md`**: MCP (Model Context Protocol) integration system
- **`deployment.md`**: Deployment system architecture and workflows
- **`maintenance.md`**: Maintenance system architecture and daemon management
- **`text_processor.md`**: Text processor for custom markup parsing
- **`type_script.md`**: TypeScript client architecture
- **`patterns.md`**: Code patterns and examples
- **`work-page-protocol.md`**: Work page protocol documentation

### `deployment/` - Deployment Guides

Training documents for humans (or agents helping humans) to deploy the Henhouse Framework. These documents provide step-by-step procedures and operational guides.

- **`overview.md`**: Deployment system overview and philosophy
- **`installation.md`**: Step-by-step installation procedures
- **`database.md`**: Database initialization and management
- **`file-deployment.md`**: File deployment process and whitelisting
- **`flask.md`**: Flask application management
- **`http-nginx.md`**: HTTP/NGINX configuration
- **`maintenance.md`**: Maintenance daemon management
- **`git.md`**: Git operations and workflows
- **`cache.md`**: Cache management system
- **`configuration.md`**: Configuration and whitelist management
- **`user-management.md`**: User infrastructure management
- **`site-assets.md`**: Site assets deployment
- **`workflows.md`**: Deployment workflows and procedures

## Support

For questions, issues, or contributions, please use the GitHub issue tracker.

