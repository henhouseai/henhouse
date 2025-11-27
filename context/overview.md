# Henhouse System Overview

- Henhouse is a content management and automation platform
- built around a central *Gateway* single-shot *command* dispatch process
- provides a unified interface for various client backends:

## **Parser Backend**
- Command-line interface for system administration
- Direct access to all system functions
- Primary interface for developers and power users

## **HTTP Backend** 
- Web browser interface for general users
- Interactive forms and visual content management
- Real-time updates without page refreshes

## **MCP Backend**
- API for external tools and automation
- Programmatic access to all system functions
- Used by other applications and scripts

## **Maintenance Backend**
- Background processing system for automated maintenance tasks
- Handles cache refresh, cleanup, and system optimization
- Operates independently without user intervention

## **Current State of Codebase**

- In-development project with solid working foundation
- Current functionality works well, though not all features are complete
- Focus on building robust architecture for planned future capabilities
- Multi-process server architecture: multiple instances can run against same database/filesystem
- Request state management: each invocation maintains request/response/connection/filesystem state
- Designed for parallelism: instances coordinate through database transactions and file locking

### **Gateway Architecture**

- Gateway is a global singleton class providing unified access point
- All modules use gateway to get and set information for single invocation
- Designed for single-shot command execution with complete cleanup after each request
- Manages request lifecycle: parse → execute → respond → cleanup
- Same business logic serves CLI, web, API, and maintenance interfaces

#### **Dispatch Flow**
- Single entry point: dispatch() method orchestrates entire execution
- Sequential initialization: request parsing → connection setup → handler loading
- Action execution followed by backend rendering
- Error processing and coordinated commit/rollback across file and database operations
- Debug output flushing and cleanup

#### **State Management**
- Gateway holds all system state for single invocation lifecycle
- Core components: request, response, registry, connection, file system, process manager
- Handler references: action_handler, backend_handler, error_handler
- Debug system configuration and user tier level tracking
- Automatic cleanup and resource management after each request

#### **Request**
- Parses command-line arguments from various backend-specific client scripts
- Grammar-based parsing with fallback handling
- Structured data tokenization (commands, flags, string/int args, no-flags)
- Backend-specific command defaults when no command specified

#### **Response**
- Collects output from backends into buffers for final assembly
- Manages action results, error output, debug output separately
- User tier detection from environment or connection
- Backend-specific Response subclasses for different output formats

#### **Business Logic**
- CommandRegistry discovers and loads action handlers dynamically
- Caches handler metadata in JSON files to avoid filesystem scans
- Lazy loading with automatic rebuild on cache miss
- Dual registration pattern (@register_action + @register_command)

#### **Database Connection**
- Connection manager handles main/cache/history databases
- User tier detection from DSN usernames ({project}_{tier} pattern)
- Transaction coordination with commit/rollback support
- Coordinated commit/rollback across file and database operations
- Dry-run mode for testing without permanent changes
- All business logic accesses database through gateway.conn

#### **File System**
- Schedules file operations (move/delete) for commit-time execution
- OS abstraction layer with cross-platform support
- Rollback support for failed operations
- Soft deletes by moving files to temp locations

#### **Process Management**
- Cross-platform process management with graceful error handling
- Background process creation with user switching support
- Process listing and termination capabilities
- Deployment detection and privilege checking

#### **Error Handling**
- Centralized error store with extensible list of error types
- Thread-safe error collection across all system components
- Backend-specific error formatting (CLI tables vs HTML vs JSON-RPC)

#### **Debug System**
- Always available debug data capture via SharedDebugDataStore, enabled per-request via flags
- Multiple debug backends: table (tabular), trace (call stack), mcp (JSON), safe (base)
- Configurable filtering (whitelist/graylist/blacklist patterns) with wildcard matching
- Combination tracking to prevent spam from repeated calls
- Output limiting with configurable message counts per function combination
- Thread-safe capture with safe mode context to prevent recursive rendering
- Works across all backends (CLI, HTTP, MCP, maintenance) with backend-specific output formats

#### **Dynamic Subclassing**
- Page class registry with @register_page_class decorators
- Cold cache JSON file for class discovery
- Automatic loading of appropriate subclass based on page 'class' field

#### **Registry System**
- Command/backend discovery with JSON caching
- Automatic regeneration on cache miss
- Support for multiple backend types (parser, http, mcp, maintenance)

---

### **Content Management Architecture**

- Hierarchical content system with pages, images, and custom markup
- Multi-tier caching strategy for performance optimization
- Database abstraction supporting main, cache, and history databases (history not yet implemented)
- Background maintenance system for automated cleanup and optimization

#### **Page Hierarchy**
- 9-mixin architecture (validation, hierarchy, content, images, files, display, ajax, cache, maintenance)
- Parent-child relationships with automatic breadcrumb generation
- Built-in inheritance patterns for derived page classes

#### **Text Processing**
- Custom markup language similar to wiki syntax ([[links]], {{images}})
- Decorator pipeline architecture with right-to-left application
- Database integration for link tracking and resolution

#### **Two-Tier Caching**
- Hot cache (in-memory Page instances) for request lifetime
- Cache database storing 5 derived fields (display_name, prepared_text, children_by_class, images, files)
- Lazy computation with automatic cache refresh during gateway commit
- On-demand resource loading with automatic invalidation

#### **Image Processing**
- Multi-size instances with automatic generation and management
- Image groups with ranking system for primary image selection
- Automatic file path management and instance cleanup

#### **Database Structure**
- Main database: Relational structure for pages, images, links, users
- Cache database: Flat document database for derived field storage
- History database: Architecture supports history database (not yet implemented)

#### **Maintenance Backend**
- Passive database operations for cascading corrections
- Stale reference detection and cache rebuilds
- Priority system: User requests override passive maintenance
- Job queue system for background processing

---

### **Parser Architecture**

- Command-line backend for direct system access and administration
- Scriptable interface for automation and batch operations
- Primary interface for developers, debugging, and system maintenance
- Full access to all system functions with formatted output

#### **CLI Interface**
- Command-line tools for interactive system administration
- Direct gateway dispatch with argument parsing and validation
- Supports all debug flags and filtering options

#### **Table Rendering**
- Structured output formatting for CLI display
- Unicode-aware text manipulation and column alignment
- Configurable field types, labels, and icons

---

### **HTTP Architecture**

- Web-based interface for general users and content management
- Combines server-rendered HTML with client-side JavaScript interactivity
- Bridges user interactions to backend systems through API calls

#### **Web Interface**
- Web interface serving HTML with embedded TypeScript client
- Hybrid one-page app architecture with overlay system
- All API operations route through MCP backend (no separate API layer)

#### **TypeScript Client**
- Overlay-based UI using Fetch API tied to MCP protocol
- Separate app action payload system integrated with MCP whitelist
- Build process coordination with Python backend
- Optimization logic for aggregate operations: minimizes MCP calls by selecting best combination of setters to mutate required data with minimum API calls (traveling salesman-like optimization)

---

### **MCP Architecture**

- JSON-RPC 2.0 API backend for programmatic access and automation - **this IS the API layer** (no separate API backend exists)
- Tier-based security with tool whitelisting and permission management
- Used by external clients and internal web interface for all operations
- HTTP backend uses MCP backend - all API operations route through MCP protocol
- Application actions layer transforms MCP into the web interface API, with distinct availability per tier and access method

#### **MCP Protocol**
- JSON-RPC 2.0 API with tier-based tool whitelisting
- Auto-generated wrappers using exec() for all whitelisted tools
- Lazy loading with cache rebuild on miss by scanning mcp_utils.py files
- Decorator-based registration in module-specific mcp_utils.py files

#### **Application Actions**
- Custom layer built on MCP whitelist that makes MCP the unified API layer (no separate API backend)
- Eight-tier system: 4 user tiers (guest, verified, admin, root) × 2 access methods (MCP protocol vs web UI app actions)
- Tools can be MCP-only (tiers 1-4), app-action-only (tiers 5-8), or dual-purpose (e.g., `[3, 4, 7, 8]` for admin/root)
- App actions provide clickable links in web UI; aggregate operations without direct MCP counterparts are built from individual MCP tools
- TypeScript client includes optimization logic to minimize MCP calls when executing aggregate operations

---

### **Maintenance Architecture**

#### **Maintenance Backend**
- Custom ResponseMaintenance class outputs JSON format for machine consumption
- Auto-generated wrapper functions via exec() that unwrap MCP envelope: extracts flat data from `action_response["content"][0]["text"]` since operations are internal-only
- Simple decorator system: `register_maintenance_tool("tool_name")` at bottom of each tool file triggers wrapper generation
- Similar to MCP backend but simpler: no tier whitelisting (always root tier), single-purpose internal usage
- Entry point: `maintenance_client.py` calls `gateway.dispatch(argv, "maintenance")`
- Dual interface: Tools accessible via maintenance backend (daemon) and parser backend (CLI testing)

#### **Background Processing**
- Database-backed job queue system for task coordination
- Automatic cache refresh and stale reference cleanup
- Cross-platform daemon management and orchestration
- Priority system: User requests override passive maintenance

---

---

## **Future Development**

This section documents planned features and architectural decisions that explain current design choices but are not yet implemented.

### **API / MCP Integration**
- Help agents spawned from browser: The unified MCP interface allows all CRUD work to go through the same interface, whether humans or agents are performing the work. Future plans include allowing users to spawn help agents directly from their browser to assist with work. Input may come from both humans and agents simultaneously as they collaborate, all routing through the same MCP protocol. This unified approach is why HTTP and MCP architectures share the same backend layer.

### **Database**
- History database: Planned for audit trails and versioning. Architecture already supports history database connections, but implementation is pending.

