# Installation Steps

### Tier 1: Developer Box Smoke Check

Start on your developer box to get familiar with the system and train an agent helper.

**Developer box `. {project}.cnf` and SSL CA setup (for DB + MCP):**

1) Copy baseline config from server: fetch `/home/{project_owner}/.{project}.cnf` (created by install).  
2) On your dev box, save as `~/.{project}.cnf` and edit:
   - In `[client]`: set `host=db.yourdomain.tld`, keep user/password, and set `ssl_ca=/home/you/.henhouse/ssl/ca.pem` (or your chosen path).
   - Add an `[mcp]` section for MCP HTTP auth:
     ```
     [mcp]
     user=henhouse_root
     password=<htaccess_panel_password>
     host=panel.yourdomain.tld
     ```
     Use the htaccess panel password from the install config.
3) Copy the SSL CA bundle from the server:
   - On server, copy `/etc/mysql/ssl/ca.pem` (root+intermediate) to a readable location for your dev user (e.g., `~/ca.pem`) and then to your dev box (e.g., `~/.henhouse/ssl/ca.pem`).
   - Ensure perms on dev box: `chmod 600 ~/.henhouse/ssl/ca.pem`.
4) Update paths in `~/.{project}.cnf` to point to your local CA bundle. Do not reference server-only paths.

MCP wrapper uses `[mcp]` if present; otherwise falls back to `[client]`.

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

# (Optional) Rename your project folder if desired
# mv henhouse myproject

# move your project to a more central location (outside of your home folder)
sudo mv henhouse /

# Change into the project directory
cd /henhouse

# Check dependencies on deployment box, install packages as necessary
python hen.py dependency-list
pip install -r requirements.txt
```

**Step 2: Prerequisites Check**

Before installing, ensure you have:

- **DNS configured**: All required DNS records pointing to your server's static IP (see `deployment/dns.md`)
  - Main domain, www, admin, panel, db, and cache subdomains must all have A records
- **NGINX installed and running**: Web server must be set up (see `deployment/http-nginx.md`)
- **MySQL installed and running**: Database server must be set up (see `deployment/mysql.md`)
- **At least one top-level domain** that you own (ideally one per project)

**Step 3: Clean Git History (Required)**

Delete the `.git` folder so install creates a fresh repository instead of reusing the existing one. This is required to avoid conflicts during installation.

```bash
# Remove existing git history so install starts fresh
rm -rf .git
```

**Step 4: Install (config-driven)**

```bash
# Install system users and infrastructure
cd /henhouse
ls -la
# Verify: All files should be owned by your human user account (user:group should show your username)

# CRITICAL: Must run inside the project directory, as the owner, with passwordless SSH ready.
# SSH keys are copied from ~/.ssh/authorized_keys to all tier users.

# First run: creates /root/.{project}-install.cnf (mode 600, root) and exits.
sudo python hen.py install

# Edit the config file that was just created:
sudo vi /root/.henhouse-install.cnf
# (or use nano if you prefer: sudo nano /root/.henhouse-install.cnf)
#
# Required fields to set:
#
# Database hosts:
#   db_host: Database server hostname
#   cache_host: Cache database server hostname
#   - If this is your FIRST henhouse installation: use subdomains like db.{yourdomain} and cache.{yourdomain}
#     Example: db.henhouse.ai, cache.henhouse.ai
#   - If this is your SECOND+ henhouse: use the same database server as your first installation
#     All henhouse installations on the same server share the same database server
#   - IMPORTANT: DNS records must be set up BEFORE installing (see deployment/dns.md)
#     All subdomains (db, cache, admin, panel, www, main domain) must point to your server's static IP
#
# SSL CA paths (absolute paths to certificate files):
#   ssl_ca_path: Path to SSL CA certificate for main database (e.g., /etc/mysql/ssl/ca.pem)
#   cache_ssl_ca_path: Path to SSL CA certificate for cache database
#   - These certificates can be set up AFTER installation if needed
#   - The installer will accept these paths even if files don't exist yet
#   - See deployment/ssl.md and deployment/mysql.md for certificate setup details
#
# MySQL root passwords (one per database server):
#   mysql_root_password_main: Root password for main database server
#   mysql_root_password_cache: Root password for cache database server
#
# Database user passwords (used for both main and cache databases):
#   password_guest, password_verified, password_admin, password_root
#
# HTTP Basic Auth passwords:
#   htaccess_admin_password: For admin subdomain access
#   htaccess_panel_password: For panel subdomain access
#
# Entry script name:
#   hen_script_name: Name of the entry point script (defaults to "hen")
#
# Optional:
#   user_key: Additional SSH public key to copy to all tier users
#
# All passwords must be changed from "CHANGE_ME" - installer validates this.

# Re-run after editing. Installer fails if manifest_users has entries (previous install not cleared).
sudo python hen.py install
```

**Verify Installation and Permissions:**

```bash
# Check project directory ownership (group should now be henhouse)
ls -la
# Verify: Files are still owned by your user, but group is now "henhouse"

# Check /srv directory structure
ls /srv
# Should show: files/, audio/, video/, images/ folders
# Inside each folder, you'll see a subfolder for your project (e.g., henhouse/)

# Check that you cannot yet access /srv/henhouse (group permissions not active)
ls /srv/henhouse
# Should show "Permission denied" - this is expected until you log out and back in

# Check new user accounts were created
ls /home
# Should show four new accounts: {project}_guest, {project}_verified, {project}_admin, {project}_root

# Check install config file was created
sudo vi /root/.henhouse-install.cnf
# Should see the configuration with all passwords set (not "CHANGE_ME")

# IMPORTANT: Log out and log back in via SSH to activate group permissions
exit
# (Then SSH back in)

# After logging back in, verify group permissions are active
ls /srv/henhouse
# Should now work! You can see the git/ folder inside
# This confirms your account now has the henhouse group permissions

# Verify /srv/henhouse permissions
ls -la /srv/henhouse
# Should show: owned by henhouse:henhouse (project group - human user + root tier only)

# Verify git folder permissions
ls -la /srv/henhouse/git
# Should show: owned by henhouse:henhouse (project group)
# Note: /srv/henhouse itself uses henhouse_deployed group (all tier users can access)
#       but git/ uses henhouse group (only human user + root tier)
```

**Note: Database Connection Warnings**

After installation, when you run hen commands (like `hen command-list` or `hen dependency-list`), you may see warnings like:
```
Failed to initialize database connection. Access denied for user {project}_root at {ip_address} using password: YES
```

This is **expected and temporary**. The installer creates the DSN configuration files (`~/.{project}.cnf`) that point to your database servers, but the databases themselves don't exist yet on those servers. The system is trying to load these DSN files and connect, but the databases haven't been created.

You can safely ignore these warnings until you set up the databases. See **Tier 3: Database Setup** below for instructions on creating the databases and database users.

Until then, the connection failures are harmless - the system is just trying to connect to databases that haven't been created yet.

**Step 5: Verify Installation**

After installation, check what was created:

```bash
# Check the main project directory
ls -la /srv/henhouse
# ls -la /srv/myproject  # If using custom project name

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
# git clone user@your-server:/srv/myproject/git/myproject.git  # If using custom project name
cd henhouse
# cd myproject  # If using custom project name

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
git push origin henhouse  # or your project name (not main/master)

# On deployment box: pull (no sudo needed, as your Unix user)
hen pull-project
# myproject pull-project  # If using custom script name
```

This syncs the project directory with the head of your project branch. The `pull-project` command automatically clears caches.

**Step 8: Test Push-Project Feature**

The `push-project` feature creates side branches for recovery:

```bash
# On deployment box: create a stage branch
hen push-project --message "test stage branch"
# myproject push-project --message "test stage branch"  # If using custom script name

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
# Creates databases and schema, automatically creates homepage if pages table is empty
sudo hen init-db -root --confirm

# Create tier-based database users
sudo hen add-db-users -root
```

**What This Enables:**

- Database access - main database and cache database initialized
- Tier-based database users - four MySQL users with appropriate permissions
- Homepage created - page ID 1 ready to use
- Full CRUD operations - create, read, update, delete pages via command line
- Work page system - project planning and management features
- Page management - hierarchical content, images, files, audio, video

**Try It Out:**

Test page operations from the command line:

```bash
# View the homepage
hen show-page -id 1

# Create a test page (will be page ID 2)
hen add-page -target-page 1 -name "Test Page"

# Set the page text (assuming it's page ID 2)
hen modify-text -page-id 2 -text "The quick red fox jumped over the lazy brown dog"

# View the updated page
hen show-page -id 2
```

This demonstrates basic page creation and text modification from the command line.

### Tier 4: Deploy to /srv

Deploying populates `/srv` with the code that will run for web requests, MCP commands, and daemons. This automatically starts Flask applications and the maintenance daemon.

**Step 1: Deploy**

After installation completes, **log out and log back in** to refresh SSH group permissions, then:

```bash
# Deploy the application
sudo hen deploy
# sudo myproject deploy  # If using custom script name
```

This copies whitelisted files to `/srv/{project_name}`, sets permissions, and prepares the production environment. The deploy process automatically stops and restarts Flask applications and the maintenance daemon. You can't do NGINX deployment until code is deployed to `/srv` first, because NGINX configuration is generated from the deployed code.

**Step 2: Verify Daemons**

Check that Flask apps and maintenance daemon are running:

```bash
# Check Flask daemon status (4 instances, one per tier)
hen flask-status
# myproject flask-status  # If using custom script name

# Check maintenance daemon status
hen maintenance-status
# myproject maintenance-status  # If using custom script name
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
# sudo myproject http-deploy -domain yourdomain.com  # If using custom script name
```

This allows the SSL certificate authority to verify your domain by uploading a file and checking it. Once your SSL certificate is issued, proceed to Phase B.

**Phase B: HTTPS Configuration**

After SSL certificates are installed (typically via Let's Encrypt):

```bash
# Configure HTTPS/NGINX with SSL certificates
sudo hen http-deploy-ssl -domain yourdomain.com
# sudo myproject http-deploy-ssl -domain yourdomain.com  # If using custom script name
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
# myproject flask-status  # If using custom script name

# Check maintenance daemon status
hen maintenance-status
# myproject maintenance-status  # If using custom script name
```

You should see:
- Four Flask daemons running (ports 5001-5004), one for each tier (guest, verified, admin, root)
- One maintenance daemon running for cache refresh and job processing

**Daemon Management**

If you need to stop daemons:

```bash
# Stop Flask daemons
sudo hen flask-stop
# sudo myproject flask-stop  # If using custom script name

# Stop maintenance daemon
sudo hen maintenance-stop
# myproject maintenance-stop  # If using custom script name
```

**Important**: Every time you run `sudo hen deploy`, the daemons are automatically stopped before deployment and restarted after deployment. You don't need to manually manage them during normal deployment cycles.

**Auto-Start on Reboot**

Auto-start on server reboot is not yet enabled. If your server reboots, you'll need to manually start the daemons:

```bash
# Start Flask daemons
sudo hen flask-start
# sudo myproject flask-start  # If using custom script name

# Start maintenance daemon
sudo hen maintenance-start
# myproject maintenance-start  # If using custom script name
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
