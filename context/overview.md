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
- Multiple instances can run against same database/filesystem
- Each invocation maintains request/response/connection/filesystem state
- Instances coordinate through database transactions and file locking

**Implementation Status:**

- All core systems (Gateway, Page, Registry, Render, Debug, MCP, HTTP, Maintenance, Parser) are fully implemented and operational
- Deployment system is fully operational with comprehensive infrastructure for multi-tier web application deployment
- History database architecture exists (connection support, hooks) but is not yet actively used
- Transaction/Batch system has database tables and page classes partially implemented; execution engine pending
- Tier 2 verification system, daemon manager, and aggregator system are planned for future development

### **System Architecture Map**

The following diagram shows the core system relationships and dependencies:

#### **Gateway**: global singleton - core orchestrator

- *Request*: parses command-line arguments
- *Response*: collects output, backend-specific subclasses
- *Connection*: database access (main, cache, history*)
- *FileSystem*: scheduled file operations
- *ProcessManager*: cross-platform process management
- *CommandRegistry*: handler discovery and loading
- *Debug System*: always-on data capture

#### **Page System**: hierarchical content management

- *Page Registry*: hot cache for in-memory instances
- *Page Class Registry*: dynamic subclass loading
- *Comprehensive functionality*: validation, hierarchy, content, images, files, display, ajax, cache, maintenance
- *TextProcessor*: markup parsing for page content
- *Cache System*: two-tier caching (hot cache + cache database)

#### **Image and File Systems**: media and attachment management

- Follow same patterns as Page system (registry, cache)
- Multi-size image instances with automatic generation
- Usage tracking via image_groups/file_groups tables

#### **Render System**: output formatting

- *TableData*: structured data collection
- *FieldConfig*: field type styling rules
- *TableBuilder*: table construction pipeline
- Backend routing: CLI tables (Parser) or HTML tables (HTTP)

#### **TypeScript Client**: web UI interactivity

- *OverlayManager*: modal dialog management
- *PageData*: field management and form processing
- *RPCClient*: MCP JSON-RPC wrapper
- All API operations route through MCP backend

### **Key Dependency Notes**

- **Gateway is foundational**: All systems depend on Gateway for state management, database access, and request lifecycle. Deployment system uses Gateway for all deployment commands.
- **Page system is self-contained**: Uses Gateway but doesn't require other content systems. Pages are served via Flask applications in production.
- **Backends are independent**: Each backend can operate separately, but all route through Gateway dispatch. Flask applications in production route HTTP and MCP requests through Gateway.
- **Render system is shared**: Used by multiple backends but doesn't depend on them. Deployment commands use Render system for CLI table output.
- **MCP is the API layer**: HTTP backend uses MCP backend for all API operations (no separate API exists). Flask applications expose MCP protocol in production.
- **Deployment enables production**: All core systems can run in development, but deployment system provides production infrastructure (users, databases, web servers, daemons).

### **Gateway Architecture**

- Gateway is a global singleton class providing unified access point
- All modules use gateway to get and set information for single invocation
- Designed for single-shot command execution with complete cleanup after each request
- Manages request lifecycle through parse → execute → respond → cleanup flow
- Same business logic serves CLI, web, API, and maintenance interfaces

#### **Initialization and Dispatch Flow**
- Entry points call `init_gateway(raw_argv, backend)` to create and initialize Gateway
- `Gateway.__init__()` performs all initialization, guaranteeing `request`, `response`, `conn`, and `files` are non-None
- `dispatch()` method orchestrates execution (handlers, commit, cleanup) - initialization already complete
- Initialization sequence: request parsing → connection setup → handler loading
- Action execution followed by backend rendering
- Error processing and coordinated commit/rollback across file and database operations
- Debug output flushing and cleanup

#### **State Management**
- Gateway holds all system state for single invocation lifecycle
- Contains request, response, registry, connection, file system, process manager
- **Type Safety**: After initialization, `request`, `response`, `conn`, and `files` are guaranteed non-None
- Maintains handler references: action_handler, backend_handler, error_handler
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

#### **Registry System**

The registry system provides dynamic discovery and loading of action and backend handlers throughout the codebase. Gateway uses CommandRegistry during dispatch to locate and load the appropriate action handler (business logic) and backend handler (presentation logic) for each command. All action handlers register themselves via @register_action and @register_command decorators, while backend handlers register via @register_parser, @register_http, @register_mcp, or @register_maintenance decorators. The registry scans for these decorators across the codebase and caches discovery results in JSON files to avoid repeated filesystem scans. When Gateway needs to execute a command, it queries the registry to find the registered handlers, which are then dynamically loaded and validated before execution.

- CommandRegistry discovers and loads action handlers dynamically
- Caches handler metadata in JSON files to avoid filesystem scans
- Lazy loading with automatic rebuild on cache miss
- Dual registration pattern (@register_action + @register_command)

#### **Database Connection**

Gateway initializes the Connection manager during dispatch, which provides unified access to main, cache, and history databases. All business logic modules (Page, Image, File systems, and custom actions) access the database exclusively through gateway.conn methods (read, create, update, delete). The Connection manager handles transaction coordination, automatically starting transactions on first write operation and coordinating commit/rollback across both file and database operations during Gateway's commit process. User tier detection happens during connection initialization, reading the tier level from DSN username patterns. The Page system's cache refresh operations, TextProcessor's link resolution, and all CRUD operations throughout the system use gateway.conn as their single point of database access.

- Connection manager handles main/cache/history databases
- User tier detection from DSN usernames ({project}_{tier} pattern)
- Transaction coordination with commit/rollback support
- Coordinated commit/rollback across file and database operations
- Dry-run mode for testing without permanent changes

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
- Used by deployment system for Flask daemon and maintenance worker management

#### **Error Handling**
- Centralized error store with extensible list of error types
- Thread-safe error collection across all system components
- Backend-specific error formatting (CLI tables vs HTML vs JSON-RPC)

#### **Debug System**

The debug system provides always-on data capture that works across all backends, with each backend formatting debug output according to its interface. Parser backend includes debug output as formatted CLI tables, HTTP backend can include debug data in HTML responses, MCP backend includes debug output as a separate JSON content item in JSON-RPC responses, and Maintenance backend includes debug data in its JSON output format. All debug data is captured through the SharedDebugDataStore during request execution, regardless of which backend is active. The debug system integrates with Gateway to read debug flags from the request and applies filtering and output limits before formatting. When the Render system needs to display debug tables, it uses safe mode context to prevent recursive debug rendering during table construction.

- Always available debug data capture via SharedDebugDataStore, enabled per-request via flags
- Multiple debug backends available: table (tabular), trace (call stack), mcp (JSON), safe (base)
- Configurable filtering (whitelist/graylist/blacklist patterns) with wildcard matching
- Combination tracking to prevent spam from repeated calls
- Output limiting with configurable message counts per function combination
- Thread-safe capture with safe mode context to prevent recursive rendering

#### **Dynamic Subclassing**

- Page class registry with @register_page_class decorators
- Cold cache JSON file for class discovery (hh/page/cache/page-classes.json)
- Automatic loading of appropriate subclass based on page 'class' field
- Same `get_page(page_id)` call returns different subclasses based on database content
- Derived classes override validation functions, hooks, and display methods
- Examples: SourceCodeFile (simple derived), WorkPage (abstract intermediate), WorkDocket (concrete derived from WorkPage)

#### **Registry System**

The registry system manages discovery and loading of all command handlers across the system. Gateway creates a CommandRegistry instance during initialization to locate action handlers (business logic) and backend handlers (presentation logic) for each command. Action handlers throughout the codebase register themselves using @register_action and @register_command decorators, while backend handlers register using @register_parser, @register_http, @register_mcp, or @register_maintenance decorators. The registry system scans the codebase for these decorators, caches the results in JSON files, and provides Gateway with the handler information needed for command execution. All backends (Parser, HTTP, MCP, Maintenance) depend on the registry system to discover their handlers, and all action modules must register through this system to be accessible.

- CommandRegistry class manages command and backend handler discovery and loading
- Cache system provides JSON-based discovery to avoid repeated filesystem scans
- Automatic cache regeneration on miss with decorator scanning across codebase
- Five backend types supported: action (business logic), parser (CLI), mcp (API), http (web), maintenance (background)
- Dynamic handler loading via importlib with validation and error handling
- Backend handlers registered via @register_{type} decorators (e.g., @register_parser, @register_http)

#### **Render System**

The render system provides unified output formatting for structured data, transforming action response data into formatted tables and text. Parser and HTTP backends use the render system to produce CLI tables and HTML tables respectively, while the Debug system uses it for tabular debug output. The render system detects which backend is active through Gateway and routes to the appropriate renderer (CLI vs HTML). It also integrates with the Config Registry system to retrieve icons and labels for field types, and reads no-flag states from Gateway to conditionally show or hide content sections. The same TableData structure can be rendered as either CLI text tables or HTML tables depending on the active backend.

- Unified output formatting system for structured data transformation
- Modular design with backend routing: parser backend → CLI tables, HTTP backend → HTML tables
- HTML table output fully functional for web interface
- Not all backends require table output (MCP uses JSON format, not tables)
- Processing pipeline: TableData collection → FieldConfig styling → TableBuilder → backend-specific renderer
- Field-based configuration system matches row types to icons, labels, and colors

---

### **Content Management Architecture**

The Page system provides hierarchical content management with pages, images, files, and custom markup processing. All Page operations access the database through Gateway.conn, using standard Connection methods (read, create, update, delete) for all CRUD operations. When actions modify page content, they set results via Gateway.response.set_action_response(), which backends then format for output. The Page system's cache refresh mechanism integrates with Gateway's commit process: when derived fields are computed during a request, pages are flagged for cache refresh, and during Gateway.commit(), the refresh_stale_page_caches() function writes all flagged cache updates to the cache database. This coordination ensures cache consistency while maintaining the single-shot request lifecycle. The same pattern applies to Image and File systems, which follow similar registry and cache patterns but with simpler structures.

- Hierarchical content system with pages, images, files, and custom markup
- Base Page class designed for inheritance and extension
- Standard action pattern uses `show_page()` as consistent output format for CRUD operations
- Multi-tier caching strategy for performance optimization
- Database abstraction supporting main, cache, and history databases (history not yet implemented)
- Background maintenance system for automated cleanup and optimization

#### **Page Hierarchy**

- Comprehensive functionality organized into focused areas (validation, hierarchy, content, images, files, display, ajax, cache, maintenance)
- Parent-child relationships with automatic breadcrumb generation
- Extensible infrastructure: Base Page class designed for inheritance with derived classes
- Five validation functions control page behavior and hierarchy constraints (allow_null_names, allow_duplicate_names, auto_link_name, allow_class_inside, allow_inside_of)
- Extension points include class hooks, display hooks, hierarchy hooks for customizing behavior
- Supports abstract intermediate classes (e.g., WorkPage) and concrete derived classes (e.g., WorkDocket, SourceCodeFile)
- Automatically extracts metadata JSON fields as object attributes
- Page class registry automatically loads appropriate subclass based on database 'class' field

#### **Text Processing**

TextProcessor provides custom markup parsing for page content, handling wiki-style syntax for links, images, and decorators. The system integrates into the Page system through Page.get_prepared_text(), which processes page text content and caches the result in the prepared_text field. During link and image resolution, TextProcessor uses Gateway.conn to query the page and image registries, resolving page names to IDs and finding primary images for pages. When page text is modified via Page.modify_text(), TextProcessor updates the links and image_links database tables to track page-to-page and page-to-image relationships. The processed text flows through a decorator pipeline that can produce different output formats (JSON, CLI tables, HTML) based on the final decorator, making it format-agnostic while maintaining the same parsing and resolution logic.

- Custom markup language similar to wiki syntax ([[links]], {{images}}, {{{direct_image_id}}})
- Recursive-descent parser architecture handles nested elements and decorator chains
- Two-phase processing flow: preprocessing (parse + resolve) → postprocessing (decorators + final format)
- Decorator pipeline architecture with right-to-left application (last decorator applied first)
- Format-agnostic design: same input produces different outputs (JSON, CLI tables, HTML) via final decorator
- Pure decorators: decorators can work without base elements (e.g., `@pi(5)`, `@echo('text')`)
- Automatic page/image lookup with error collection and graceful fallbacks
- Automatic discovery of custom decorators via `@register_tp_decorator` with JSON caching

#### **Two-Tier Caching**

- Hot cache (in-memory Page/Image/File instances) for request lifetime
- Cache database storing 5 derived fields (display_name, prepared_text, children_by_class, images, files) plus main DB metadata backup
- All main database fields (name, link, text, parent, class, last_modified, username, comments, visibility, displayStyle, viewCount, metadata) stored in cache for full hydration capability
- Lazy computation with automatic cache refresh during gateway commit
- On-demand resource loading with automatic invalidation
- Same caching pattern used for Images (instances, pages/usage) and Files (pages/usage)

#### **Image and File Processing**

- Multi-size image instances with automatic generation and management (huge, large, small, tn)
- Image groups with ranking system for primary image selection
- Automatic file path management and instance cleanup
- Simple file association management with ranking system
- Usage tracking via image_groups/file_groups tables
- Soft deletes (moved to deleted subdirectory, not permanently removed)
- Date-based file storage organization (/srv/images/{project}/{date}/, /srv/files/{project}/{date}/)
- Storage directories created during deployment installation with proper permissions and group ownership

#### **Database Structure**

- Relational structure for pages, images, files, links, users, image_groups, file_groups
- Flat document database for derived field storage plus metadata backup
- Cache tables store pages (5 derived fields + metadata), images (instances + pages + metadata), files (pages + metadata)
- Architecture supports history database (not yet implemented)

#### **Maintenance Backend**

- Passive database operations for cascading corrections
- Stale reference detection and cache rebuilds
- Priority system: User requests override passive maintenance
- Job queue system for background processing
- Maintenance worker daemon runs continuously in production, managed by deployment system

---

### **Parser Architecture**

The parser backend provides command-line access to all system functions, routing all commands through Gateway dispatch. When a CLI command is executed, Gateway loads the appropriate action handler (registered through the Registry system) to execute business logic, then loads the parser backend handler to format the action response as CLI table output using the Render system. The parser backend uses the same action handlers as other backends, ensuring consistent business logic across all interfaces. Debug flags and filtering options are fully supported, with debug output formatted through the Debug system's table renderer.

- Command-line backend for direct system access and administration
- Scriptable interface for automation and batch operations
- Primary interface for developers, debugging, and system maintenance
- Full access to all system functions with formatted output

#### **CLI Interface**

- Command-line tools for interactive system administration
- Direct gateway dispatch with argument parsing and validation
- Supports all debug flags and filtering options

#### **Table Rendering**

- Uses unified render system for structured output formatting
- Unicode-aware text manipulation and column alignment
- Configurable field types, labels, and icons via FieldConfig

---

### **HTTP Architecture**

The HTTP backend provides web-based interface for content management, combining server-rendered HTML with client-side TypeScript interactivity. Server-rendered pages route through Gateway dispatch, using the same action handlers as other backends, and format output using the Render system's HTML table renderer. The TypeScript client makes all API operations through the MCP backend using JSON-RPC calls - there is no separate API layer. This unified approach means all CRUD operations, whether initiated by humans through the web UI or by agents through MCP protocol, route through the same MCP backend and use the same business logic. The HTTP backend serves initial HTML with embedded seed data, then the TypeScript client takes over for interactive operations, making MCP calls and updating the DOM dynamically. In production, Flask applications serve the HTTP backend, with NGINX as a reverse proxy handling SSL, static files, and security headers.

- Web-based interface for general users and content management
- Combines server-rendered HTML with client-side JavaScript interactivity
- Bridges user interactions to backend systems through API calls
- Production deployment via Flask daemons (one per tier) with NGINX reverse proxy

#### **Web Interface**

- Web interface serving HTML with embedded TypeScript client
- Hybrid one-page app architecture with overlay system

#### **TypeScript Client**

- Overlay-based UI using Fetch API tied to MCP protocol
- Separate app action payload system integrated with MCP whitelist
- Build process coordination with Python backend
- Optimization logic for aggregate operations: minimizes MCP calls by selecting best combination of setters to mutate required data with minimum API calls (traveling salesman-like optimization)
- Component-based modal dialogs with array-based content structure, singleton OverlayManager for z-index stacking and focus management
- Field management system with automatic registration, change detection, and optimal MCP tool selection via weighted set cover algorithm
- MCP JSON-RPC wrapper with automatic debug option capture from overlay UI
- CRUD operation handlers live in PageData classes (base or derived), registered via app.ts from available_actions
- Debug options UI in overlay footer, automatic debug data extraction and display in separate overlay windows

---

### **MCP Architecture**

The MCP backend provides JSON-RPC 2.0 API access and serves as the unified API layer for the entire system - there is no separate API backend. All MCP tool calls route through Gateway dispatch, using action handlers registered through the Registry system. The MCPWhitelist system manages tier-based tool access, with separate whitelists for each user tier (guest, verified, admin, root) that are cached and automatically rebuilt when tools are added. The HTTP backend's TypeScript client makes all API calls through the MCP backend, ensuring that web UI operations and external MCP client operations use identical business logic. The application actions layer extends the MCP whitelist system to provide clickable action links in the web UI, with tools available as either MCP-only (for agents), app-action-only (for web UI aggregate operations), or dual-purpose (available through both interfaces). In production, Flask applications expose the MCP protocol endpoint (`/mcp`) for external tool integration.

- JSON-RPC 2.0 API backend for programmatic access and automation - **this IS the API layer** (no separate API backend exists)
- Tier-based security with tool whitelisting and permission management
- Used by external clients and internal web interface for all operations
- Production deployment via Flask applications with MCP endpoint routing

#### **MCP Protocol**

- JSON-RPC 2.0 API with tier-based tool whitelisting
- Auto-generated wrappers using exec() for all whitelisted tools
- Lazy loading with cache rebuild on miss by scanning mcp_utils.py files
- Decorator-based registration in module-specific mcp_utils.py files

#### **Application Actions**

- Custom layer built on MCP whitelist that makes MCP the unified API layer (no separate API backend)
- Eight-tier system combines 4 user tiers (guest, verified, admin, root) × 2 access methods (MCP protocol vs web UI app actions)
- Tools can be MCP-only (tiers 1-4), app-action-only (tiers 5-8), or dual-purpose (e.g., `[3, 4, 7, 8]` for admin/root)
- App actions provide clickable links in web UI; aggregate operations without direct MCP counterparts are built from individual MCP tools
- TypeScript client includes optimization logic to minimize MCP calls when executing aggregate operations

---

### **Maintenance Architecture**

#### **Maintenance Backend**

The maintenance backend provides background task processing for automated system maintenance. All maintenance tools route through Gateway dispatch, using the same action handlers registered through the Registry system that other backends use. Maintenance tools access the database through Gateway.conn for cache refresh operations, stale reference detection, and job queue management. The maintenance backend uses auto-generated wrapper functions (similar to MCP backend) that unwrap the MCP response envelope since operations are internal-only. Tools are registered via `register_maintenance_tool()` decorators, which trigger wrapper generation during registry discovery. The maintenance worker daemon calls maintenance tools via `maintenance_client.py`, which routes through Gateway dispatch, while the same tools are also accessible via the parser backend for command-line testing.

- Custom ResponseMaintenance class outputs JSON format for machine consumption
- Auto-generated wrapper functions via exec() that unwrap MCP envelope: extracts flat data from `action_response["content"][0]["text"]` since operations are internal-only
- Simple decorator system: `register_maintenance_tool("tool_name")` at bottom of each tool file triggers wrapper generation
- Similar to MCP backend but simpler: no tier whitelisting (always root tier), single-purpose internal usage

#### **Background Processing**

- Database-backed job queue system for task coordination
- Automatic cache refresh and stale reference cleanup
- Cross-platform daemon management and orchestration
- User requests override passive maintenance
- Maintenance daemon deployed and managed via deployment system with start/stop/status commands

---

## **Additional Reading**

The following documents provide detailed implementation information beyond this overview. Each document focuses on specific subsystems with code-level details, file locations, function names, and architectural patterns. Below is what you'll learn from each document and why you might want to read it.

**Most important documents for general development work:**

- **gateway.md**: Essential reading for understanding how the system orchestrates requests, manages state, and coordinates all subsystems. Required for any work involving request handling, database connections, file operations, or extending Gateway functionality.
- **page.md**: Essential reading for content management work. Covers the extensible page system architecture, validation functions, and how to create new page types. Required for any work involving pages, images, files, or content processing.
- **deployment.md**: Essential reading for understanding the deployment system architecture, multi-tier infrastructure setup, and production deployment workflows. Required for any work involving server setup, deployment operations, or production environment management.

### **gateway.md**

- **Implementation Details**: Specific method signatures, initialization sequence details, connection management patterns, and file operation scheduling
- **Dispatch Flow**: Exact flow of `dispatch()`, how `_initialize()` sets up subsystems in order, and commit/rollback coordination mechanism
- **Request Parsing**: How Request parsing transforms raw arguments into structured data through the parsing pipeline
- **File Locations**: Specific file paths, function names, and code patterns for extending Gateway functionality

### **page.md**

- **Page Architecture**: The Page class functionality organized into focused areas with detailed breakdown
- **Extension Patterns**: How derived classes override validation functions with specific examples
- **Metadata Extraction**: Mechanics of automatic metadata extraction as object attributes
- **Database Access**: Database access patterns through `gateway.conn` and transaction handling
- **Page Registry**: Page class registry loading mechanism and dynamic subclass selection
- **Concrete Examples**: SourceCodeFile and WorkDocket implementations showing extension patterns

### **registry.md**

- **Handler Discovery**: How CommandRegistry validates and loads handlers dynamically with validation logic and error handling
- **Cache System**: Cache structure and regeneration algorithms that avoid filesystem scans
- **Backend Types**: Backend type definitions and decorator generation patterns
- **Data Structures**: Two-part data structure for action/backend handlers with specific class methods and cross-references

### **debug.md**

- **Debug Data Capture**: How SharedDebugDataStore captures data with thread-safe mechanisms
- **Debug Levels**: The five debug levels and their activation patterns
- **Filter Mechanics**: Filter pattern matching algorithms, combination tracking to prevent spam, and precise filter configuration
- **Safe Mode**: Safe mode context manager implementation to prevent recursive rendering
- **Debug Backends**: How each debug backend (table, trace, mcp) formats output differently
- **Integration**: How to integrate debug output into custom handlers effectively

### **mcp.md**

- **Tool Registration**: How `@register_mcp_tool` decorators work and file organization pattern (mcp_utils.py files)
- **Whitelist Management**: Tier-specific cache files and their structure, tier whitelisting mechanics
- **Wrapper Generation**: Auto-generated wrapper functions using exec() and response format construction
- **Cache Behavior**: Cache rebuild on miss behavior and discovery process
- **Gateway Integration**: Integration points with Gateway dispatch flow and how to add new tools

### **maintenance.md**

- **Daemon Implementation**: How the maintenance worker processes jobs and cross-platform daemon management (Windows vs Unix)
- **Job Queue**: Database-backed queue structure and priority system implementation
- **Cache Refresh**: Algorithms for detecting stale pages/images/files and refresh logic
- **Tool Differences**: How maintenance tools differ from MCP tools in structure and usage
- **Tool Creation**: How to create maintenance tools and understand job queue processing

### **render.md**

- **Table Building**: How TableBuilder constructs tables with layout calculations, column sizing algorithms, and border rendering
- **Field Configuration**: Field type matching to icons/labels/colors and FieldConfig API
- **Cell Formatting**: Cell formatting, Unicode width calculation, and text processing
- **Backend Renderers**: How backend-specific renderers (CLI vs HTML) transform the same TableData
- **Config Registry**: Decorator-based config registry and INI file configuration structure
- **Render Pipeline**: Step-by-step render pipeline from TableData to final output

### **text_processor.md**

- **Parser Internals**: Recursive-descent parser implementation details and how nested elements are handled
- **Decorator Mechanics**: Decorator pipeline execution order (right-to-left) and pure decorator support
- **Link Resolution**: Link resolution algorithms with error collection and graceful fallbacks
- **Database Integration**: Database link tracking during text modification and link table updates
- **Decorator Registry**: Decorator registry discovery and how to create custom decorators
- **Format Agnostic**: How format-agnostic design produces different outputs (JSON, CLI, HTML) from the same input

### **type_script.md**

- **Component Lifecycle**: Overlay class mount/unmount flow and OverlayManager z-index stacking logic
- **Field Management**: PageData field registration and change detection implementation
- **MCP Tool Selection**: Weighted set cover algorithm for optimal MCP tool selection
- **RPC Integration**: RPC error handling with multiple error extraction and debug option capture
- **Derived Classes**: How derived PageData classes extend base functionality with concrete examples
- **Action Handlers**: How to create new action handlers, implement form patterns, and understand overlay state management

### **patterns.md**

- **Code Examples**: Complete action-backend pairs showing the full pattern from start to finish
- **Error Handling**: Error handling strategies and error reporting patterns
- **Response Formatting**: Response formatting techniques and output structure
- **Command Structure**: How to structure new commands following established patterns
- **Integration Examples**: How to implement actions, create backend handlers, and integrate with Gateway system

### **deployment.md**

- **Deployment Architecture**: Comprehensive overview of the "set it up once, deploy repeatedly" deployment philosophy
- **Installation System**: One-time infrastructure setup with tier-based users, SSH keys, credential files, and git repositories
- **File Deployment**: Whitelist-based file copying, permission management, and service coordination
- **Service Management**: Flask daemon lifecycle (4 tier-based instances), maintenance worker, and NGINX configuration
- **Database Deployment**: MySQL initialization, tier-based user creation, and schema management
- **Git Operations**: Code synchronization via stage branch workflow with pull/push operations
- **Cache Management**: Registry-based cache cleanup system integrated with deployment
- **Configuration System**: Whitelist/blacklist management for file deployment and context files
- **Deployment Workflows**: Standard deployment, rollback procedures, and development-to-production sync
- **Integration Points**: How deployment system integrates with Gateway, Registry, Page System, and other core components

---

## **Future Development**

This section documents planned features and architectural expansions.

### **Database**

- History database planned for audit trails and versioning. Architecture already supports history database connections, but implementation is pending.
- Deployment system already supports database initialization and tier-based user management; history database integration will extend deployment capabilities.

### **TypeScript Client**

- Browser component for hierarchical page/image navigation with target, path, contents, and images sections
- Browser-dependent operations: copyPage, movePage, copyImages, moveImages, sortImages using browser for destination selection
- pageInfo handler for displaying incoming links, child counts, and read-only page information
- FormBuilder component for dynamic form generation from field configuration with validation
- ImageViewer component for full-screen image viewing with zoom, pan, touch gestures, and keyboard navigation
- TextEditor component with browser integration for inserting image references at cursor position
- Animation/transitions for overlay show/hide operations
- Accessibility improvements including ARIA labels and enhanced keyboard navigation

### **Tier 2 Verification System**

- Magic link authentication allowing guest users to elevate to verified status via email verification
- Database-backed session management with cookie-based session_id storage for dynamic tier elevation
- `magic_links` table for one-time verification tokens, `sessions` table for active user sessions
- Authentication flow: request link → email sent → token validation → session creation → tier elevation
- Session expiration, activity tracking, and automatic cleanup of expired sessions
- Session tier passed to Gateway for tier-specific credential loading and database permissions
- Cryptographically secure tokens, rate limiting, one-time use enforcement, minimal database permissions
- SMTP configuration, email templates, error handling, prevention of email enumeration attacks
- Future enhancements: password reset, email change verification, two-factor authentication, session management UI

### **Transaction/Batch System**

- Batch operations system for submitting multiple MCP operations as a single atomic transaction with approval workflow
- Multi-tier MCP server architecture: Guest (read-only), Admin (approval queue), Root (immediate execution)
- Hierarchical transaction structure with serial groups executed sequentially, parallel operations within groups executed simultaneously
- Register system using two-dimensional associative arrays (`register[key].bucket`) for variable passing between serial groups with lazy extraction
- `mcp_requests` table for aggregate records, `mcp_action_requests` table for individual operations with status tracking
- Page classes `mcp_request` and `mcp_action` exist (partially implemented), serial groups use existing `page` class
- Human review interface for approving/rejecting/deleting individual actions or entire requests before execution
- Parallel execution within serial groups, dependency resolution via register references, executed-once rule preventing re-execution
- JSON path navigation for extracting values from tool responses into registers for subsequent operations
- New `batch_operations` MCP tool, Gateway subprocess execution, page system integration for visual organization
- Implementation status: Page classes and database tables exist; transaction parser, execution engine, approval interface, and register system pending
- Future enhancements: color coding, dashboard views, edit operation arguments, database transactions for serial groups, automatic execution, conditional execution

### **Daemon Manager System**

- Auto-scaling orchestration system providing dynamic horizontal scaling for all daemon types based on load metrics
- Meta-daemon architecture with centralized monitoring, scaling decisions, and daemon lifecycle management
- **Unified Daemon Manager**: CLI action (project folder, not deployed) that can `start|stop|status` any daemon (Flask tiers + maintenance jobs) with optional job args, individual status reporting, cross-platform support (Windows/Mac/Linux), and hooks for cron/systemd auto-start on reboot
- Flask tier scaling with fixed main daemons on ports 5001-5004 and dynamic sub-daemons on ports 5011-5049 for horizontal scaling
- Maintenance worker pool with horizontal scaling based on job queue depth and processing rates
- Async handoff pattern for Flask request delegation to sub-daemons using fire-and-forget patterns
- JSON configuration system as single source of truth with atomic updates and configuration caching (JSON state/config file in project directory, registered via cache cleanup system)
- Rolling boxcar averaging for scaling decisions to prevent jitter and rapid oscillation
- Coordinated logging system for multiple daemons with log coordinator service or file locking
- Tempo signaling from Flask tiers to meta-daemon for request frequency and response time metrics
- Cross-platform process management supporting Windows, macOS, and Linux with platform-specific abstractions
- **Deployment Integration**: Deploy scripts accept desired counts per Flask tier, emit Nginx upstream config, coordinate daemon restarts with Nginx reload, support SSL/non-SSL flows, and provide auto-start on reboot via cron/systemd
- Implementation phases: foundation (unified daemon manager, JSON config, logging), multi-worker support, auto-scaling, async handoff, production hardening, deployment + Nginx integration

### **Distributed Knowledge Architecture (Aggregator System)**

- Three-tier distributed knowledge management platform enabling federated content curation and aggregation
- Hybrid centralized-decentralized model where domain authorities maintain canonical datasets while aggregator nodes selectively replicate and extend content
- Tier 1 authoritative layer using MySQL with full relational schema (current implementation)
- Tier 2 cache layer using flat JSON store for fast browsing performance (current implementation)
- Tier 3 aggregator layer with independent nodes that selectively replicate from multiple authorities (planned)
- Selective replication similar to BitTorrent piece selection, pull-based distribution model
- Local autonomy allowing nodes to layer local modifications without affecting upstream sources
- Reachability-based garbage collection for automatic content mirroring and redundancy
- Authority emergence through natural authority (creators establishing domains) and surrogate authority (collectors filling voids)
- Consensus detection through pattern recognition when multiple nodes make similar modifications
- Namespace and identity management with global unique IDs combining namespace and local ID
- Human-in-the-loop design with passive curation model and implicit consensus through usage patterns
- Development phases: external source ingestion, local override and merge proposals, consensus detection, agent-driven curation, peer discovery
- Help agents spawned from browser: The unified MCP interface allows all CRUD work to go through the same interface, whether humans or agents are performing the work. Future plans include allowing users to spawn help agents directly from their browser to assist with work. Input may come from both humans and agents simultaneously as they collaborate, all routing through the same MCP protocol. This unified approach is why HTTP and MCP architectures share the same backend layer.


---

## **Additional Reading (Planning Documents)**

The following planning documents provide detailed specifications for future system features. These documents outline architectural designs, implementation plans, and design constraints for features that are partially implemented or planned for future development.

### **verification.md**

- **System Architecture**: Magic link authentication flow from guest to verified tier with email-based verification
- **Database Schema**: `magic_links` table for one-time tokens, `sessions` table for active user sessions with tier information
- **Authentication Flow**: Request magic link → email sent → token validation → session creation → tier elevation sequence
- **Session Management**: Database-backed sessions with cookie-based session_id, expiration handling, and activity tracking
- **Gateway Integration**: How session tier is passed to Gateway for tier-specific credential loading and database permission management
- **Security Features**: Cryptographically secure tokens, rate limiting, one-time use enforcement, minimal database permissions
- **Email System**: SMTP configuration, email templates, error handling, prevention of email enumeration attacks
- **Implementation Phases**: Database setup, token system, email system, session setup, magic link routes, Gateway integration, testing and security audit

### **transaction.md**

- **System Architecture**: Multi-tier MCP server architecture (Guest, Admin, Root) with different execution behaviors and tool exposure
- **Transaction Structure**: Hierarchical JSON structure with serial groups containing parallel operations, parallelization keys, and extraction specifications
- **Register System**: Two-dimensional associative arrays for variable passing between serial groups using lazy extraction evaluated at use-time
- **Database Schema**: `mcp_requests` table for aggregate records, `mcp_action_requests` table for individual operations with status tracking
- **Approval Workflow**: Human review interface for approving/rejecting/deleting actions, hierarchical page-based organization, dependency readiness checking
- **Execution Model**: Parallel execution within serial groups, dependency resolution via register references, executed-once rule, failure barrier handling
- **Extraction System**: JSON path navigation for extracting values from tool responses into registers for subsequent operations
- **Integration Points**: `batch_operations` MCP tool, Gateway subprocess execution, page system integration, database transaction safety
- **Implementation Details**: Transaction parser responsibilities, register system data structures, execution engine flow, approval interface features
- **Design Constraints**: Explicit extraction, lazy resolution, associative keys, flexible group sizes, parallel failure handling, executed-once rule

### **daemon_manager.md**

- **System Architecture**: Auto-scaling orchestration system with meta-daemon managing all daemon lifecycle decisions and horizontal scaling
- **Current State Analysis**: Existing Flask architecture with fixed tiers, single maintenance worker, and scaling limitations
- **Auto-Scaling Architecture**: Meta-daemon monitoring load metrics, making scaling decisions with rolling boxcar averaging, managing daemon lifecycle
- **Meta-Daemon Design**: Central orchestrator with load monitoring, scaling decisions, configuration management, and process lifecycle control
- **Flask Tier Scaling**: Fixed main daemons on ports 5001-5004, dynamic sub-daemons on ports 5011-5049, async handoff pattern for request delegation
- **Maintenance Worker Scaling**: Horizontal worker pool with database-level job coordination, atomic job claiming, heartbeat monitoring
- **JSON Configuration System**: Single source of truth for daemon states with atomic updates, configuration caching, backup and rollback
- **Coordinated Logging**: Log coordinator service or file locking for multi-daemon logging, preventing log interleaving and race conditions
- **Implementation Strategy**: Five-phase approach from foundation through multi-worker support, auto-scaling, async handoff, to production hardening
- **Technical Challenges**: Race conditions in job claiming, configuration file consistency, port allocation conflicts, graceful shutdown, cross-platform compatibility, scaling decision jitter

### **aggregator.md**

- **System Architecture**: Three-tier distributed knowledge management platform with hybrid centralized-decentralized model for federated content curation
- **Tier 1 Authoritative Layer**: MySQL core with full relational schema, ACID transactions, four-tier access control, MCP integration (current implementation)
- **Tier 2 Cache Layer**: Flat JSON store for denormalized snapshots, timestamp-based cache invalidation, separates read performance from write operations (current implementation)
- **Tier 3 Aggregator Layer**: Independent nodes with selective replication, local override capabilities, pull-based distribution, reachability-based garbage collection (planned)
- **Authority and Trust Model**: Four-tier access control system, Unix-level security integration, trust token system for provenance tracking and consensus detection
- **Distribution and Redundancy**: Selective replication patterns, authority succession mechanisms, data reconstruction from cached replicas, namespace and identity management
- **Human-in-the-Loop Design**: Passive curation model with implicit consensus, automated consensus detection, pattern recognition for convergent editing, threshold-based acceptance
- **Puzzle Collection Application**: Domain-specific implementation demonstrating natural authority emergence, surrogate authority patterns, multi-domain aggregation, privacy and anonymity options
- **Workflow Patterns**: Top-down designer-initiated, middle-out manufacturer-initiated, bottom-up collector-initiated workflows with data stability and authority evolution
- **Implementation Strategy**: Five-phase development approach building on existing Henhouse infrastructure, MCP integration, page system extensibility
- **Licensing Strategy**: Open source core framework with premium extensions for guild management, aggregation layer, and transaction facilitation

