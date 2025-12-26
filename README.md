# Henhouse

A flexible content management framework designed for building custom applications with hierarchical content, image management, and powerful text processing capabilities.

## Status

**⚠️ Active Development**: Henhouse is currently under active development. Many of the features listed below are only partially implemented. The `context/` folder contains detailed architecture documentation and planning for upcoming features.

## Overview

Henhouse is a flexible content management framework designed for building custom applications with hierarchical content, image management, and powerful text processing capabilities. It provides a comprehensive foundation for content-driven applications through a gateway-based architecture with multiple backend interfaces (CLI, HTTP, MCP).

For detailed architecture documentation, see the [Documentation](#documentation) section below.

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

First-time setup on a fresh server:

```bash
# 1. Clone the repository at server root
cd /
sudo git clone https://github.com/henhouseai/henhouse.git

# 2. (Optional) Rename to your project name (e.g., foxhouse, myproject)
# If you keep it as "henhouse", skip this step
sudo mv henhouse foxhouse
cd foxhouse

# 3. Install system users and infrastructure (requires 4 passwords)
# Use -hen flag to customize command name (e.g., "fox" instead of "hen")
sudo python hen.py install -hen fox

# 4. Deploy the application
sudo fox deploy

# 5. Initialize database (one-time setup)
sudo fox init-db --confirm -password <mysql_root_password>
sudo fox add-db-users -password <mysql_root_password>
fox init-homepage

# 6. Configure HTTP/NGINX (one-time setup)
sudo fox http-deploy -domain foxhouse.ai
# After SSL certificates are installed:
sudo fox http-deploy-ssl -domain foxhouse.ai
```

**Note**: The `install` command automatically copies SSH keys from the project owner's account (`~/.ssh/`) to all tier users, enabling passwordless access. Make sure your developer account has SSH keys set up before running install.

**Developer Laptop Setup** (after server setup):

Once the server is set up, clone from the bare repository on your server:

```bash
# Clone from your server's bare repository
git clone user@your-server:/srv/foxhouse/git/foxhouse.git
cd foxhouse

# Your origin will point to the server's bare repo
# Work locally, then push and deploy:
git push origin foxhouse
# On server: fox pull-project && sudo fox deploy
```

For detailed deployment documentation, see the `deployment/` folder.

**Development Tools:**
- Cursor (recommended IDE for development)

### Basic Usage

**Command Syntax**: The basic command format is:

```bash
python hen.py command-name -arg value
```

**Shorthand Command**: You can use the shorter `hen` command if the project folder is in your PATH. The PowerShell scripts (`.ps1` files) in the project folder provide wrapper scripts that enable this shorthand syntax. If the project folder is not in your PATH, you'll need to use the full `python hen.py` syntax or provide the full path to the `hen` script.

**Example Commands** (Windows PowerShell):

```powershell
# List all available commands
hen command-list

# List all actions (business logic handlers)
hen action-list

# List all backends (presentation handlers)
hen backend-list

# List MCP tools (API endpoints)
hen mcp-list

# List maintenance tools
hen maintenance-list

# List page classes
hen class-list

# Check system dependencies
hen dependency-list

# Show a page by ID
hen show-page -id 1

# Get help for a command
hen help
```

**Smoke Test**: Running `hen dependency-list` is a good way to verify the system is working correctly. If you see the dependency list output, it indicates that the Gateway, Registry, and command routing are functioning properly.

**Example Output** - Running `hen dependency-list` on Windows PowerShell:

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

**Debugging**: You can attach `-log` to any command to get thorough debugger output that traces the execution flow, helping you diagnose issues:

```powershell
hen dependency-list -log
hen show-page -id 1 -log
```

**Note**: Some commands (like `flask-start`, `http-deploy`, `install`) require Unix-specific modules and will show as "Failed" on Windows. These are deployment commands that should be run on the Ubuntu server.

Note: The `stage` script is also available for staging operations.

## Architecture

Henhouse follows a gateway-based architecture where commands are parsed and routed through the Gateway, actions execute business logic, and backends format data for different interfaces (CLI, HTTP, MCP).

For comprehensive architecture documentation, see the `context/` folder which contains detailed system documentation covering Gateway, Page System, Registry, Render, Debug, MCP, Maintenance, and other core components.

## Deployment

Henhouse is designed for deployment on Ubuntu servers, with desktop/laptop development tools (Cursor app and PowerShell scripts) working in conjunction with the server deployment.

For comprehensive deployment documentation, including installation procedures, user tier configuration, deployment commands, git workflows, and server setup, see the `deployment/` folder which contains detailed deployment guides.

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

Henhouse documentation is organized into three main folders:

### `context/` - System Architecture Documentation

Comprehensive system documentation covering all core components:

- **`overview.md`**: High-level system overview and architecture map
- **`gateway.md`**: Gateway system architecture, request lifecycle, and state management
- **`page.md`**: Page system architecture, mixins, validation functions, and extensibility
- **`deployment.md`**: Deployment system architecture and workflows
- **`maintenance.md`**: Maintenance system architecture and daemon management
- Additional documentation for Registry, Debug, MCP, Render, Text Processor, and TypeScript

These documents provide detailed implementation information, code-level details, file locations, function names, and architectural patterns for developers and AI agents working with the codebase.

### `deployment/` - Deployment Guides

Practical deployment documentation:

- **`overview.md`**: Deployment system overview and philosophy
- **`installation.md`**: Step-by-step installation procedures
- Additional deployment guides for server setup, configuration, and operations

### `planning/` - Future Development Plans

Planning documents for upcoming features and architectural expansions:

- **`daemon_manager.md`**: Auto-scaling daemon orchestration system (unified daemon manager, Nginx integration, auto-scaling meta-daemon)
- **`transaction.md`**: Batch operations system with approval workflows
- **`verification.md`**: Tier 2 verification system (magic link authentication)
- **`aggregator.md`**: Distributed knowledge architecture for federated content aggregation

**Note on Aggregator**: The aggregator system documented in `planning/aggregator.md` represents a separate enterprise project that will be built on top of Henhouse. While it helps explain some architectural decisions in Henhouse (particularly around distributed content management), the aggregator itself is planned as a commercial product that may not be open source. This is one reason Henhouse uses the Mozilla Public License 2.0 (MPL 2.0), which allows building proprietary products on top of the open source framework while ensuring improvements to the core framework remain open source.

## Support

For questions, issues, or contributions, please use the GitHub issue tracker.

