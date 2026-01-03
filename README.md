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

Henhouse is deployed in phases, with each phase enabling new features. By the end, you'll have a customizable MCP server running that you can use in Cursor - your agents can run MCP commands in chat windows to update database content and make changes to the system. The web browser becomes a live dashboard for interacting with the system, and you can also use the command line for testing and smoke checking.

For detailed step-by-step installation instructions, see the numbered chapters in the `README/` folder:

- **Chapter 1**: DNS, NGINX, and Domain Setup
- **Chapter 2**: MySQL Server Setup
- **Chapter 3**: SSL Certificates
- **Chapter 4**: Smoke Check
- **Chapter 5**: Installation
- **Chapter 6**: Git and Staging Workflows
- **Chapter 7**: Database Setup
- **Chapter 8**: Deployment
- **Chapter 9**: TBD
- **Chapter 10**: Flask and Maintenance Daemons
- **Chapter 11**: MCP Wrapper Setup in Cursor
- **Chapter 12**: Security Considerations
- **Chapter 13**: Web Interface and Subdomains
- **Chapter 14**: Work Page Modules for Project Planning
- **Chapter 15**: EXT Folder and Customizations
- **Chapter 16**: Upgrading the Framework
- **Chapter 17**: Uninstalling Henhouse

**Key Terms:**

- **Deployment Box**: Your Linux server (developed and tested on Ubuntu Server 24.x, but should work on most Linux distributions) that's accessible over the network (local-only or remote with static IP). This is where Henhouse runs in production, serving web requests and hosting your content. **Deployment boxes are designed to be part of a cluster** - you can start with a single box and expand to multiple boxes (4-5 or more) for optimization and load distribution. **Do NOT use your developer box (Mac laptop, etc.) as a deployment box** - while Macs can host NGINX, they are not suitable for full Henhouse deployment.

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
  - Can be renamed to anything you want
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
  - Can be customized to match your project name
  - Each project can have its own entry point name
  - You can run different entry points for different projects, all on the same deployment box
  - Changing the entry point name is easier than changing project name: uninstall and reinstall with new name
  - Throughout this documentation, we use "hen" as the default entry point name

- **Developer Box**: Your laptop, desktop, or development machine (Windows, Mac, or Linux) where you write code and use your IDE.
  - Developed and tested with Cursor as the agentic IDE, but other IDEs like GitHub Copilot should be compatible as well
  - **No Henhouse installation** - developer box does NOT run Henhouse deployment (system is designed with separate boxes in mind, though theoretically they could be the same machine on Linux - untested)
  - Just clone the repository and run Python code directly for testing
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

### Development Tools

Henhouse integrates with Cursor IDE through MCP (Model Context Protocol), allowing agents to run commands directly in chat windows. The MCP wrapper script bridges stdio MCP protocol to HTTP requests sent to your deployment server.

For detailed MCP setup instructions, see **Chapter 11: MCP Wrapper Setup in Cursor** in the `README/` folder.

**File Upload Support:**

The MCP wrapper supports automatic file uploads. Agents can include files in MCP tool calls using `_files` or `file_paths` parameters. Supported file types include images, audio (with streaming), video (with streaming), and documents. Files are automatically attached to requests as multipart/form-data.

For more details, see `mcp_wrapper.py` docstring and `context/mcp.md`.

### Basic Usage

**Commands That Work Without Installation:**

Many commands work immediately after cloning - no database or installation required. These "lister" commands explore the system:

```bash
# Check dependencies (shows what's installed and what's missing)
python3 hen.py dependency-list

# List available commands
python3 hen.py command-list

# List available actions
python3 hen.py action-list

# List available backends
python3 hen.py backend-list

# List available parsers
python3 hen.py parser-list

# List available MCP tools
python3 hen.py mcp-list

# List available maintenance tools
python3 hen.py maintenance-list

# List available page classes
python3 hen.py class-list
```

**Debugging**: Add `-log` to any command for debug output that traces the execution flow:

```bash
python3 hen.py dependency-list -log
```

**Quick Installation Sprint:**

Starting from a fresh Ubuntu Server installation, here's the complete installation flow:

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install all required system packages and Python dependencies
sudo apt install python3 python3-pip git default-libmysqlclient-dev nginx mysql-server apache2-utils python3-flask python3-pymysql python3-psutil python3-mutagen python3-pil ffmpeg -y

# Set MySQL root password (required before installation)
sudo mysql
# In MySQL prompt, run:
# ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'your_secure_password';
# FLUSH PRIVILEGES;
# EXIT;

# Clone the repository
cd ~
git clone https://github.com/henhouseai/henhouse.git
sudo mv henhouse /
cd /henhouse

# Install system users and infrastructure (creates config template)
sudo python3 hen.py install

# Edit the config file with your settings (see Chapter 5 for required fields)
sudo vi /root/.henhouse-install.cnf
# Set all passwords, domain names, database hosts, etc.

# Run install again to complete setup
sudo python3 hen.py install

# Log out and log back in to refresh user groups (you can now use 'hen' instead of 'python3 hen.py')

# Set up database
sudo hen init-db -root --confirm
sudo hen add-db-users -root

# Test that db connection works
hen show-page -id 1

# Deploy code and configure NGINX (unified command)
sudo hen deploy

# For local deployments: configure /etc/hosts on client machines
# For public deployments: ensure DNS records are configured
```

**Setting Up a Second Site:**

To run multiple Henhouse installations on the same server:

```bash
# Clone and rename for second project
cd ~
git clone https://github.com/henhouseai/henhouse.git
sudo mv henhouse /foxhouse
cd /foxhouse

# Install with different project name
sudo python3 hen.py install
sudo vi /root/.foxhouse-install.cnf
# Set entry_point_script_name = fox (or your preferred name)
# Set different domain, passwords, etc.
sudo python3 hen.py install

# Log out and log back in

# Set up database (uses same MySQL server, creates separate databases)
sudo fox init-db -root --confirm
sudo fox add-db-users -root

# Test connection
fox show-page -id 1

# Deploy
sudo fox deploy
```

**Note**: The key to running multiple installations is renaming the project folder (e.g., `/foxhouse` instead of `/henhouse`) and setting `entry_point_script_name` in the install config file. This allows you to use different command names (e.g., `fox` instead of `hen`) for each installation.

**Git Workflows**: The `push-project` and `pull-project` commands are optional convenience tools for syncing code between your developer box and deployment box. The `stage` script is also available for staging operations. These are not required - you're free to use standard git push/pull commands or any git workflow you prefer. You don't have to use the git repository created during installation; you can use GitHub or any other git hosting service instead. See **Chapter 6: Git and Staging Workflows** in the `README/` folder for details.

## Architecture

The Henhouse Framework follows a gateway-based architecture where commands are parsed and routed through the Gateway, actions execute business logic, and backends format data for different interfaces (CLI, HTTP, MCP).

**Tier-Based Architecture**: The system uses a four-tier user model with complete isolation:

- **Guest Tier**: Public access, read-only permissions. Runs as `{project_name}_guest` Unix user with SELECT-only database access.
- **Verified Tier**: Authenticated users, moderate permissions (SELECT + INSERT). Runs as `{project_name}_verified` Unix user.
- **Admin Tier**: Administrative access, full CRUD permissions. Runs as `{project_name}_admin` Unix user. Protected by HTTP Basic Auth on admin subdomain.
- **Root Tier**: Full system access, highest permissions. Runs as `{project_name}_root` Unix user. Protected by HTTP Basic Auth on panel subdomain.

Each tier has separate Unix user accounts, database credentials, Flask application instances (different ports), and distinct visual themes for the web interface.

**Security Model**: 
- **File Permissions**: Tier-based ownership with deploy group for shared access
- **Database Access**: Tier-based MySQL users with appropriate permissions
- **Process Isolation**: Each Flask instance runs as its corresponding Unix user
- **Network Security**: Flask apps listen on localhost only, proxied by NGINX
- **HTTP Basic Auth**: Admin and panel subdomains protected with `.htpasswd` files
- **SSL/TLS**: HTTPS deployment with Let's Encrypt certificates

**Key Design Principles**:
- **Separation of Concerns**: Each component has a single, well-defined responsibility
- **Idempotency**: Deployment operations can be run multiple times safely
- **Reversibility**: All operations can be rolled back or undone
- **Traceability**: Stage branches and logs provide audit trail
- **Automation**: Minimal manual intervention required after initial setup
- **Safety**: Extensive validation and error checking at every step
- **Modularity**: Components can be used independently or together

**System Dependencies**: The deployment system follows a clear dependency chain where each component builds upon the previous:
- **Gateway is foundational**: All deployment commands use Gateway for dispatch, error handling, and response management
- **Installation is prerequisite**: User infrastructure must exist before database, deployment, or service management
- **Database setup is independent**: Can be initialized separately from file deployment, but requires credential files from installation
- **File deployment coordinates services**: Automatically stops and restarts Flask and maintenance daemons during deployment
- **Git operations are independent**: Can sync code without affecting running services, with automatic cache clearing
- **Configuration drives deployment**: Whitelists determine what gets deployed, with extension support via `ext/` folder
- **Services depend on deployment**: Flask and maintenance daemons require deployed code to function
- **HTTP/NGINX depends on installation and deployment**: Uses authentication files from installation, serves files from deployment

For architecture documentation, see the `context/` folder which contains system documentation covering Gateway, Page System, Registry, Render, Debug, MCP, and other core components.

## Deployment

The Henhouse Framework is designed for deployment on Linux servers (developed and tested on Ubuntu Server 24.x on B-Link mini S hardware with Intel N150 processor, 16GB RAM, 512GB SSD, but should work on most Linux distributions and hardware configurations), with desktop/laptop development tools (Cursor app on Windows/Mac/Linux) working in conjunction with the server deployment.

**Hardware Testing**: Henhouse is tested on B-Link mini S mini PCs (Intel N150, 16GB RAM, 512GB SSD) running Ubuntu Server 24.x. The system is designed to scale from a single deployment box to a cluster of 4-5 boxes (or more) for optimization and load distribution.

**Deployment Philosophy**: Henhouse follows a **"set it up once, deploy repeatedly"** philosophy. After initial one-time setup (installation, database initialization, HTTP configuration), subsequent deployments are simple: pull the latest code and run `sudo hen deploy`. The deployment system automatically manages services, permissions, and file copying.

**File Whitelisting**: Only explicitly whitelisted files are deployed to production. Everything else is excluded by default. This ensures only approved code reaches production and prevents accidental deployment of development files.

**Development-to-Production Workflow**: After initial setup, the standard workflow is:
1. **Development** (on laptop): Make changes, test locally
2. **Sync** (on server): `hen pull-project` pulls latest code from git
3. **Deploy** (on server): `sudo hen deploy` copies files and restarts services
4. **Verify**: Check web interface, logs, functionality

That's it - just two commands (`hen pull-project` and `sudo hen deploy`) to push a new version of your code to production.

**Rollback Capability**: Easy recovery to any previous commit via git reset and redeploy. Stage branches provide recovery points for referencing previous working states.

**Deployment Target**: All deployment operations target `/srv/{project_name}/` as the production root:
- **Code**: `hh/` and `ext/` folder structures deployed to `/srv/{project_name}/hh/` and `/srv/{project_name}/ext/`
- **Site Assets**: Static files (CSS, JavaScript, favicons) deployed to `/srv/{project_name}/site/`
- **Logs**: Application logs in `/srv/{project_name}/logs/`
- **Cache**: Cache directories in `/srv/{project_name}/` (various locations)
- **Git Repository**: Bare repo at `/srv/{project_name}/git/{project_name}.git`

For deployment documentation, including installation procedures, user tier configuration, deployment commands, git workflows, and server setup, see the numbered chapters in the `README/` folder.

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

Henhouse Framework documentation is organized into the `context/` folder for system architecture documentation, and the `README/` folder for deployment guides. The overview documents should be enough to guide agents through the rest of the documentation.

### `context/` - System Architecture Documentation

Training documents for agents to learn how to extend and customize the Henhouse Framework. These documents contain implementation information, code-level details, file locations, function names, and architectural patterns.

- **`overview.md`**: High-level system overview and architecture map
- **`gateway.md`**: Gateway system architecture, request lifecycle, and state management
- **`page.md`**: Page system architecture, validation functions, and extensibility
- **`registry.md`**: Registry system for handler discovery and loading
- **`render.md`**: Render system for output formatting
- **`debug.md`**: Debug system for data capture and troubleshooting
- **`mcp.md`**: MCP (Model Context Protocol) integration system
- **`text_processor.md`**: Text processor for custom markup parsing
- **`type_script.md`**: TypeScript client architecture
- **`patterns.md`**: Code patterns and examples
- **`work-page-protocol.md`**: Work page protocol documentation


## Support

For questions, issues, or contributions, please use the GitHub issue tracker.

