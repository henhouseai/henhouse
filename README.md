# Henhouse

A flexible content management framework designed for building custom applications with hierarchical content, image management, and powerful text processing capabilities.

## Status

**⚠️ Active Development**: Henhouse is currently under active development. Many of the features listed below are only partially implemented. The `context/` folder contains detailed architecture documentation and planning for upcoming features.

## Overview

Henhouse provides a comprehensive foundation for content-driven applications, featuring:

- **Gateway Architecture**: Command-based execution system with action/backend separation
- **MCP Integration**: Model Context Protocol support for AI agent interactions
- **Page Management**: Hierarchical content organization with parent-child relationships
- **Image System**: Multi-size image instance management with automatic processing
- **Text Processing**: Custom markup syntax with decorator-based parsing
- **Transaction System**: Batch operations with approval workflows and variable passing
- **Multi-Tier Authentication**: Flexible access control with guest, verified, admin, and root tiers
- **Debug System**: Sophisticated debugging capabilities with filtering and trace analysis
- **Rendering System**: Advanced table formatting and output generation

## Quick Start

### Installation

**System Requirements:**
- Python 3.8 or higher
- NGINX (for web server deployment)

**Local Development (Laptop/Desktop):**

```bash
# Clone the repository
git clone https://github.com/henhouseai/henhouse.git
cd henhouse

# Install Python dependencies
pip install -r requirements.txt

# Test that it works (should work immediately on Mac, Windows may have some limitations)
python hen.py command-list
```

**Server Deployment (Ubuntu):**

```bash
# Install system users and dependencies (requires 4 passwords for user creation)
sudo python hen.py install

# Deploy the application
sudo hen deploy
```

**Development Tools:**
- Cursor (recommended IDE for development)

### Basic Usage

The basic command format is:

```bash
python hen.py command-name -arg value
```

Examples:
```bash
# List available commands
python hen.py command-list

# List available actions
python hen.py action-list

# Show a page by ID
python hen.py show-page -id 1
```

**Example Output** - Running `hen command-list` shows a table of all available commands:

```

  🏠 Henhouse:   Command List:

    ┌─────────────┬───────────────────────────┬─────────────────────────────────────────────────┬───────────────────────┬───────────────────────┐
    │ 81 commands │ name                      │ module                                          │ action_args           │ status                │
    ╞═════════════╪═══════════════════════════╪═════════════════════════════════════════════════╪═══════════════════════╪═══════════════════════╡
    │ ✅  Loaded: │ action_list               │ hh.gateway.registry.utils                       │                       │                       │
    │ ✅  Loaded: │ backend_list              │ hh.gateway.registry.utils                       │                       │                       │
    │ ✅  Loaded: │ command_list              │ hh.gateway.registry.utils                       │                       │                       │
    │ ✅  Loaded: │ http_list                 │ hh.gateway.registry.utils                       │                       │                       │
    │ ✅  Loaded: │ mcp_list                  │ hh.gateway.registry.utils                       │                       │                       │
    │ ✅  Loaded: │ parser_list               │ hh.gateway.registry.utils                       │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ agent_list                │ hh.agents.agent_list                            │                       │                       │
    │ 🔲  Found:  │ agent_purge               │ hh.agents.agent_purge                           │                       │                       │
    │ 🔲  Found:  │ agent_tree                │ hh.agents.agent_tree                            │                       │                       │
    │ 🔲  Found:  │ punch_in                  │ hh.agents.punch_in                              │                       │                       │
    │ 🔲  Found:  │ punch_out                 │ hh.agents.punch_out                             │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ gossip                    │ hh.agents.feed.gossip                           │                       │                       │
    │ 🔲  Found:  │ gulp                      │ hh.agents.feed.gulp                             │                       │                       │
    │ 🔲  Found:  │ peek                      │ hh.agents.feed.peek                             │                       │                       │
    │ 🔲  Found:  │ sip                       │ hh.agents.feed.sip                              │                       │                       │
    │ 🔲  Found:  │ subscribe_agent           │ hh.agents.feed.subscription_runner              │ agent, subscribe      │                       │
    │ 🔲  Found:  │ subscribe_ask             │ hh.agents.feed.subscription_runner              │ ask, subscribe        │                       │
    │ 🔲  Found:  │ subscribe_docket          │ hh.agents.feed.subscription_runner              │ docket, subscribe     │                       │
    │ 🔲  Found:  │ subscribe_keyword         │ hh.agents.feed.subscription_runner              │ keyword, subscribe    │                       │
    │ 🔲  Found:  │ subscribe_operator        │ hh.agents.feed.subscription_runner              │ operator, subscribe   │                       │
    │ 🔲  Found:  │ subscribe_sidecar         │ hh.agents.feed.subscription_runner              │ sidecar, subscribe    │                       │
    │ 🔲  Found:  │ subscribe_step            │ hh.agents.feed.subscription_runner              │ step, subscribe       │                       │
    │ 🔲  Found:  │ subscribe_task            │ hh.agents.feed.subscription_runner              │ task, subscribe       │                       │
    │ 🔲  Found:  │ unsubscribe_agent         │ hh.agents.feed.subscription_runner              │ agent, unsubscribe    │                       │
    │ 🔲  Found:  │ unsubscribe_ask           │ hh.agents.feed.subscription_runner              │ ask, unsubscribe      │                       │
    │ 🔲  Found:  │ unsubscribe_docket        │ hh.agents.feed.subscription_runner              │ docket, unsubscribe   │                       │
    │ 🔲  Found:  │ unsubscribe_keyword       │ hh.agents.feed.subscription_runner              │ keyword, unsubscribe  │                       │
    │ 🔲  Found:  │ unsubscribe_operator      │ hh.agents.feed.subscription_runner              │ operator, unsubscribe │                       │
    │ 🔲  Found:  │ unsubscribe_sidecar       │ hh.agents.feed.subscription_runner              │ sidecar, unsubscribe  │                       │
    │ 🔲  Found:  │ unsubscribe_step          │ hh.agents.feed.subscription_runner              │ step, unsubscribe     │                       │
    │ 🔲  Found:  │ unsubscribe_task          │ hh.agents.feed.subscription_runner              │ task, unsubscribe     │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ answer                    │ hh.agents.onboarding.answer                     │                       │                       │
    │ 🔲  Found:  │ onboard                   │ hh.agents.onboarding.onboard                    │                       │                       │
    │ 🔲  Found:  │ promote                   │ hh.agents.onboarding.promote                    │                       │                       │
    │ 🔲  Found:  │ status                    │ hh.agents.onboarding.status                     │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ clear_cache               │ hh.deploy.cache.clear_cache                     │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ add_db_users              │ hh.deploy.db.add_db_users                       │                       │                       │
    │ 🔲  Found:  │ check_db                  │ hh.deploy.db.check_db                           │                       │                       │
    │ 🔲  Found:  │ clean_db                  │ hh.deploy.db.clean_db                           │                       │                       │
    │ 🔲  Found:  │ export_db                 │ hh.deploy.db.export_db                          │                       │                       │
    │ 🔲  Found:  │ import_db                 │ hh.deploy.db.import_db                          │                       │                       │
    │ 🔲  Found:  │ init_db                   │ hh.deploy.db.init_db                            │                       │                       │
    │ 🔲  Found:  │ init_homepage             │ hh.deploy.db.init_homepage                      │                       │                       │
    │ 🔲  Found:  │ remove_db_users           │ hh.deploy.db.remove_db_users                    │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ flask_status              │ hh.deploy.flask.flask_status                    │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ pull_project              │ hh.deploy.git.pull_project                      │                       │                       │
    │ 🔲  Found:  │ push_project              │ hh.deploy.git.push_project                      │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ http_deploy_ssl           │ hh.deploy.http.http_deploy_ssl                  │                       │                       │
    │ 🔲  Found:  │ http_remove               │ hh.deploy.http.http_remove                      │                       │                       │
    │ 🔲  Found:  │ http_status               │ hh.deploy.http.http_status                      │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ help                      │ hh.help.help                                    │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ modify_caption            │ hh.image.modify_caption                         │                       │                       │
    │ 🔲  Found:  │ show_image                │ hh.image.show_image                             │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ modify_mcp_action_request │ hh.mcp_action_request.modify_mcp_action_request │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ modify_mcp_request        │ hh.mcp_request.modify_mcp_request               │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ add_image                 │ hh.page.add_image                               │                       │                       │
    │ 🔲  Found:  │ add_images                │ hh.page.add_images                              │                       │                       │
    │ 🔲  Found:  │ add_page                  │ hh.page.add_page                                │                       │                       │
    │ 🔲  Found:  │ copy_image                │ hh.page.copy_image                              │                       │                       │
    │ 🔲  Found:  │ copy_images               │ hh.page.copy_images                             │                       │                       │
    │ 🔲  Found:  │ copy_page                 │ hh.page.copy_page                               │                       │                       │
    │ 🔲  Found:  │ count_pages               │ hh.page.count_pages                             │                       │                       │
    │ 🔲  Found:  │ delete_page               │ hh.page.delete_page                             │                       │                       │
    │ 🔲  Found:  │ get_page                  │ hh.page.get_page                                │                       │                       │
    │ 🔲  Found:  │ modify_name               │ hh.page.modify_name                             │                       │                       │
    │ 🔲  Found:  │ modify_text               │ hh.page.modify_text                             │                       │                       │
    │ 🔲  Found:  │ move_image                │ hh.page.move_image                              │                       │                       │
    │ 🔲  Found:  │ move_images               │ hh.page.move_images                             │                       │                       │
    │ 🔲  Found:  │ move_page                 │ hh.page.move_page                               │                       │                       │
    │ 🔲  Found:  │ remove_image              │ hh.page.remove_image                            │                       │                       │
    │ 🔲  Found:  │ set_image_rank            │ hh.page.set_image_rank                          │                       │                       │
    │ 🔲  Found:  │ show_page                 │ hh.page.show_page                               │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ 🔲  Found:  │ modify_language           │ hh.source_code_file.modify_language             │                       │                       │
    │ 🔲  Found:  │ modify_path               │ hh.source_code_file.modify_path                 │                       │                       │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ ❌  Failed: │ flask_start               │ hh.deploy.flask.flask_start                     │                       │ No module named 'pwd' │
    │ ❌  Failed: │ flask_stop                │ hh.deploy.flask.flask_stop                      │                       │ No module named 'pwd' │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ ❌  Failed: │ http_deploy               │ hh.deploy.http.http_deploy                      │                       │ No module named 'pwd' │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ ❌  Failed: │ deploy                    │ hh.deploy.srv.deploy                            │                       │ No module named 'pwd' │
    ├─────────────┼───────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┼───────────────────────┤
    │ ❌  Failed: │ install                   │ hh.deploy.users.install                         │                       │ No module named 'pwd' │
    │ ❌  Failed: │ install_cursor            │ hh.deploy.users.install_cursor                  │                       │ No module named 'pwd' │
    │ ❌  Failed: │ uninstall                 │ hh.deploy.users.uninstall                       │                       │ No module named 'pwd' │
    └─────────────┴───────────────────────────┴─────────────────────────────────────────────────┴───────────────────────┴───────────────────────┘
```

Status indicators:
- ✅ **Loaded**: Command is ready to use
- 🔲 **Found**: Command module found but not yet loaded
- ❌ **Failed**: Command failed to load (often due to platform-specific dependencies)

**Convenience Script**: Once the `hen` command is set up in your system path (via PowerShell script on Windows or Ubuntu server setup), you can use the shorter form:

```bash
hen command-list
hen action-list
hen show-page -id 1
```

Note: The `stage` script is also available for staging operations.

## Architecture

Henhouse follows a gateway-based architecture where:

1. **Commands** are parsed and routed through the Gateway
2. **Actions** execute business logic and return structured data
3. **Backends** format the data for different interfaces (CLI, HTTP, MCP)
4. **Registry** system discovers and loads handlers dynamically

### Key Components

- **Gateway** (`hh/gateway/`): Core orchestration and state management
- **Page System** (`hh/page/`): Hierarchical content management
- **Image System** (`hh/image/`): Media management with multi-size instances
- **Text Processor** (`hh/tp/`): Custom markup parsing with decorators
- **Render System** (`hh/render/`): Output formatting and table generation
- **MCP Integration** (`hh/deploy/flask/mcp_client.py`): AI agent protocol support

## Deployment

Henhouse is designed for deployment on Ubuntu servers, with desktop/laptop development tools (Cursor app and PowerShell scripts) working in conjunction with the server deployment.

### Prerequisites

**SSH Access**: Passwordless SSH access must already be configured between your laptop/desktop and the Ubuntu server. The install process will automatically transfer your SSH keys to the created system users, enabling passwordless connections.

**DNS Configuration**: Before deployment, configure DNS records for:
- Main domain (e.g., `example.com`)
- `admin.example.com` subdomain
- `panel.example.com` subdomain

All three domains must point to the same Ubuntu server. DNS setup is outside the scope of this project.

### Installation Process

**Step 1: Initial System Setup**

```bash
# On the Ubuntu server, run the install command from your project folder
# This requires 4 passwords (one for each user tier)
# You can use -pwd1/-p1, -pwd2/-p2, -pwd3/-p3, -pwd4/-p4 (all work)
sudo python hen.py install -pwd1 <pwd1> -pwd2 <pwd2> -pwd3 <pwd3> -pwd4 <pwd4>
```

**Project Name Detection**: The install command automatically detects:
- **Project name**: The name of the folder where the install command is run from
- **Project owner**: The user who owns that folder

These two values determine how the system configures file ownerships, permissions, and user access throughout the deployment.

The install command:
- Creates 4 system users (one per tier: guest, verified, admin, root)
- Sets up project groups and permissions
- Creates a bare git repository at `/srv/{project_name}/git/{project_name}.git`
- Auto-scans and transfers SSH keys from the project owner to all created users
- Creates credential files (`~/.{project_name}.cnf`) for each user in their home directories
- Sets up convenience scripts (`hen` command) for all users

**Step 2: Database Initialization**

```bash
# Initialize the database schema
sudo python hen.py init-db -password <root_db_password> -confirm

# Create database users for each tier
sudo python hen.py add-db-users

# Create the homepage (page ID 1) - run once when pages table is empty
sudo python hen.py init-homepage
```

**Step 3: Deploy Application**

```bash
# Deploy the application to /srv/{project_name}
# This copies files, sets permissions, and starts services
sudo hen deploy
```

The deploy command:
- Copies project files to `/srv/{project_name}`
- Creates `/srv/images/{project_name}` for image storage
- Creates `/srv/files/{project_name}` for file storage
- Sets proper ownership and permissions for all deployed files
- Starts Flask application services

**Important**: Only the **root tier** user can run Python directly and execute files from the project folder. The other three tiers (admin, verified, guest) access the Gateway system exclusively through the MCP (Model Context Protocol) interface provided by the deployed Flask server, not by running Python directly.

### User Tiers and Access Levels

The system creates four user tiers, each with specific database, filesystem, and execution access:

1. **Guest** (`{project}_guest`):
   - Database: Read-only access
   - Filesystem: No write access
   - Gateway Access: MCP protocol only (via Flask server)
   - Python Execution: Not allowed (cannot run Python directly)

2. **Verified** (`{project}_verified`):
   - Database: Read and moderate write access
   - Filesystem: No write access (Unix permissions)
   - Gateway Access: MCP protocol only (via Flask server)
   - Python Execution: Not allowed (cannot run Python directly)

3. **Admin** (`{project}_admin`):
   - Database: Full read/write access
   - Filesystem: Write access to project directories
   - Gateway Access: MCP protocol only (via Flask server)
   - Python Execution: Not allowed (cannot run Python directly)
   - Web Access: `admin.{domain}` subdomain with HTTP Basic Auth

4. **Root** (`{project}_root`):
   - Database: Full read/write access
   - Filesystem: Full write access
   - Gateway Access: Direct Python execution from `/srv/{project_name}`
   - Python Execution: Allowed (can run Python directly)
   - Web Access: `panel.{domain}` subdomain with HTTP Basic Auth

### Credential Files

Each user tier has a credential file stored in their home directory:
- Location: `~/.{project_name}.cnf`
- Format: INI-style configuration with database connection details
- Contains: username, password, host, and database name for that tier

### Deployment Commands

**Database Management:**
- `init-db`: Initialize database schema
- `add-db-users`: Create database users for all tiers
- `init-homepage`: Create homepage (page ID 1) - run once when pages table is empty
- `remove-db-users`: Remove database users
- `check-db`: Verify database connectivity
- `export-db`: Export database to SQL file
- `import-db`: Import database from SQL file
- `clean-db`: Clean database (removes all data)

**Flask Application Management:**
- `flask-start`: Start Flask application services
- `flask-stop`: Stop Flask application services
- `flask-status`: Check status of Flask services

**HTTP Deployment:**
- `http-deploy`: Deploy HTTP configuration (main domain maps to guest tier)
- `http-deploy-ssl`: Deploy HTTPS configuration with SSL certificates
- `http-status`: Check HTTP deployment status
- `http-remove`: Remove HTTP deployment configuration

**Development Tools:**
- `install-cursor`: Install Cursor IDE configuration for all project users
- `uninstall`: Remove all project users, groups, and deployment files

**Git Operations:**
- `pull-project`: Pull latest code from git repository (on server)
- `push-project`: Push code to git repository, creates timestamped side branch if run on server

**Other:**
- `deploy`: Main deployment command (copies files, sets permissions, manages services)
- `clear-cache`: Clear system caches

### Subdomain Configuration

When HTTP is deployed:
- **Main domain** (e.g., `example.com`): Maps to guest tier Flask application
- **`admin.{domain}`**: Maps to admin tier with HTTP Basic Auth
- **`panel.{domain}`**: Maps to root tier with HTTP Basic Auth

All three domains must be configured in DNS to point to the same Ubuntu server.

### Git Workflow

The system supports bidirectional code synchronization between development and deployment environments. Root tier CLI agents can modify files in the project folder on the server (the git repository). The human user's convenience script (`hen`) points to the project folder, allowing them to test agent-modified experimental code via command line separately from the deployed production code that's live on the website and accessible through NGINX. Once satisfied with the code's behavior, the human user can deploy it to production. After agents make changes, the code can either be deployed to `/srv/{project_name}` to go live, or pushed to the staging process for human review and integration through the IDE's git staging tools.

**Development → Deployment:**
1. Make changes in Cursor on your laptop/desktop
2. Commit changes using Cursor's sidebar Git panel
3. Push to the git remote repository
4. On the server, run `hen pull-project` to get the latest version from the head of the branch
5. On the server, run `sudo hen deploy` to move all whitelisted files to `/srv/{project_name}` where NGINX can serve them

**Deployment → Development:**
When changes exist on the server that need to be brought back to the development environment:

1. **On the server**: Run `hen push-project` to create a timestamped branch with the server's current code
2. **On your laptop**: Run `stage pull` to fetch that branch into a `stage/` subfolder
   - You can search for specific branches by commit messages
3. **On your laptop**: Run `stage push -message "<commit message>"` to interactively move files from `stage/` back to your main codebase
4. Use Cursor's diff tools to review changes before committing
5. Commit and push the integrated changes

**Rollbacks:**
To recover a previous server state:

1. **On the server**: Use `git reset --hard <commit-hash>` to restore a previous commit
2. **On the server**: Run `hen push-project` from that commit to create a branch
3. **On your laptop**: Run `stage pull` to fetch that version into `stage/`
4. Use the deployment-to-development workflow above to selectively integrate the code

### Local Development Integration

The desktop/laptop development environment (using Cursor app and PowerShell scripts) is designed to work in conjunction with the server deployment:

- SSH keys are automatically transferred during install, enabling passwordless server access
- The `hen` convenience script can be used both locally and on the server
- The `stage` script provides interactive staging tools for bidirectional code synchronization

## License

This project is licensed under the Mozilla Public License 2.0 (MPL 2.0). See the [LICENSE](LICENSE) file for details.

The MPL 2.0 is a file-level copyleft license that:
- Allows you to use Henhouse in proprietary projects
- Requires that modifications to MPL-licensed files remain open source
- Permits mixing open and closed source code in the same project

This license is designed to foster adoption while keeping the framework itself open.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Documentation

For detailed architecture documentation and development planning, see the `context/` folder. This folder contains comprehensive system documentation intended for agent training and development, as well as planning documents for upcoming features.

## Support

For questions, issues, or contributions, please use the GitHub issue tracker.

