# Working Notes for Henhouse Overview Document

## Files Already Read - Key Extraction

### gateway.md - Central Orchestration System
**Purpose**: Core dispatch and state management
**Key Terms**:
- Gateway: Singleton orchestrator (get_gateway()) with state management for request/response/registry/conn/files
- Request/Response: Parsed args → structured output with backend-specific Response subclasses
- 4-stage parsing: Grammar Parser (orchestrator) → Tokenizer (quote/token detection) → Parser (grammar structure) → Semantics (Request object)
- Debug system: Always-on warning system, toggleable trace/log/debug levels with white/gray/black filtering and debug-limit controls
- Error system: Centralized error_store with 12 error types (request, registry, action, backend, debug, connection, JSON, syntax, link_resolution, cache_refresh, dependency, deployment)
- Connection: Database access with user tier detection (Connection/MySQLConnection/RootConnection), transaction management, dry-run support
- FileSystem: File operations with rollback support, OS detection (Windows/macOS/Linux), scheduled vs immediate operations

**Integration Points**: Entry point for all system operations, provides gateway.conn for DB access, coordinates commit/rollback between files and database

### page.md - Hierarchical Content Management  
**Purpose**: Page/image CRUD with caching and text processing
**Key Terms**:
- Page class: 9 mixins for functionality (validation, hierarchy, content, images, files, display, ajax, cache, maintenance)
- Cache system: Two-tier - Hot cache (in-memory Page instances) + Cache database (5 derived fields: display_name, prepared_text, children_by_class, images, files)
- Page registry: get_page(id) for loading from hot cache or DB, refresh_stale_page_caches() during gateway commit
- Page class registry: Dynamic subclass loading via @register_page_class decorators, cold cache JSON file
- Mixin pattern: Direct gateway.conn access (self.gateway.conn.read/create/update/delete), no decorators
- Cache hydration: Lazy computation with _flag_cache_refresh() → gateway commit → _refresh_cached_page()
- Image module: Multi-size instance management with automatic processing
- TextProcessor: Custom markup parsing ([[links]], {{images}}) with decorator-based pipeline

**Integration Points**: Uses gateway.conn directly, integrates with TextProcessor for markup, cache refresh coordinated by gateway commit

### mcp.md - Model Context Protocol Integration
**Purpose**: MCP backend with tool whitelisting and JSON-RPC responses
**Key Terms**:
- MCP backend: One of 4 backend types (parser/mcp/http/maintenance), not action (actions aren't backends)
- Tool whitelist: @register_mcp_tool decorators in module-specific mcp_utils.py files, tier-specific caches (mcp-whitelist-{tier}.json)
- Tier system: 1=guest, 2=verified, 3=admin, 4=root (MCP tools), 5-8=app actions (UI-only)
- Response flow: success_payload() → ResponseMCP → JSON-RPC 2.0 with request_id, debug output in content array
- mcp_wrapper.py: stdio→HTTP bridge with config from ~/.{project}.cnf, handles file uploads as multipart/form-data
- Auto-generated wrappers: mcp.py uses exec() to create @register_mcp wrappers for all whitelisted tools
- Lazy loading: Cache rebuild on cache miss by scanning all mcp_utils.py files for decorators
- Validation: MCPWhitelist.validate_tool() with JSON Schema validation and type coercion

**Integration Points**: Routes through Gateway dispatch, uses standard action handlers, shares config format with database connection

### registry.md - Command Discovery and Handler Loading
**Purpose**: Command/backend discovery with caching and database decorators
**Key Terms**:
- CommandRegistry: Dynamic handler loading and validation, holds action/backend/error cache data
- Cache system: JSON cache files in hh/gateway/registry/cache/ to avoid filesystem scans, automatic regeneration on cache miss
- Backend types: ['action', 'parser', 'mcp', 'http', 'maintenance'] with decorator/dictionary mappings
- Action pattern: Dual registration @register_action + @register_command + gateway.response.set_action_response()
- DB decorators: @db_read (no retry, SELECT) / @db_write (retry with exponential backoff, INSERT/UPDATE/DELETE)
- Connection system: DSN from ~/.henhouse.cnf, agent validation, TypedDict structures, JSON utilities
- Command variations: Automatic kebab-case ↔ snake_case conversion (command-list ↔ command_list)
- Backend handlers: Typically dual-registered @register_parser + @register_http for CLI/web support

**Integration Points**: Provides handlers to Gateway, manages database access patterns, coordinates with render system for output formatting

### TypeScript.md - Client-Side HTTP Interface
**Purpose**: Browser-based interactivity with overlay system and RPC integration
**Key Terms**:
- OverlayManager: Singleton modal system with array-based content structure, z-index stacking, keyboard shortcuts
- PageData classes: Field management with getField('name', 'form') registration, field mappings to MCP tools, priority-based tool selection
- PageManager: Change detection, optimal MCP tool selection via weighted set cover algorithm, field registry lifecycle
- RPCClient: MCP JSON-RPC wrapper with automatic debug option capture, RPCError handling, extractMCPData() parsing
- Field IDs: Standardized as #page-field-{fieldName}, required for automatic form value extraction
- processOperationsIncrementally(): Sequential MCP operations for UPDATE with incremental overlay feedback
- PageDataFactory: Creates appropriate PageData subclass (SourceCodeFilePageData, MCPRequestPageData, WorkDocketPageData, etc.)
- Debug integration: Always-present collapsible debug options, automatic debug overlay creation, debug table rendering
- Action handlers: CRUD operations in PageData classes, dual registration (persistent + hot-cache), handler lookup by action ID
- File upload: UploadHandler with multi-file support, progress tracking, sequential processing

**Integration Points**: Makes JSON-RPC calls to MCP backend, uses same MCP tools as CLI, integrates with Python HTTP seed data

### text_processor.md - Markup Parsing System
**Purpose**: Transform structured markup ([[links]], {{images}}) into formatted output
**Key Terms**:
- TextProcessor: Pipeline architecture with decorator chains, format-agnostic design via final decorators
- Syntax: [[page_links]], {{images}}, {{{direct_image_id}}}, @decorators with argument parsing
- Decorator pipeline: Input → Parse → JSON → User decorators (reversed order, right-to-left) → Final decorator → Output
- Final decorators: @mcp (JSON), @parser (CLI tables), @http (HTML) - convert dict to string
- Built-in decorators: @pi(precision), @echo(text), @repeat(count, separator), @precision(decimals)
- Database integration: Updates links/image_links tables, automatic cleanup, page/image resolution via registries
- Registry: @register_tp_decorator with hot/cold cache system, lazy loading, module validation
- Error handling: Parse error collection, graceful fallbacks, detailed error reporting via error_store
- Recursive-descent parser: Handles nested elements, decorator chaining with whitespace rules, argument extraction
- Caching: JSON-based decorator discovery cache, deployed decorator scanning (/srv/{project}/site/py)

**Integration Points**: Used by Page system for content processing, integrates with page/image registries, debug system, gateway database connections

## System Architecture Overview (Draft Notes)
- Gateway is central coordinator: hen.py → gateway.dispatch() → action → backend → response
- Registry provides command discovery and handler loading with JSON caching
- Page/Image use mixin architecture with direct database access via gateway.conn
- MCP integrates as backend type with tool whitelisting and JSON-RPC responses
- TypeScript provides client-side HTTP interface with overlay system
- TextProcessor handles markup parsing with decorator chains

## Files Read - Complete

### aggregator.md - Distributed Knowledge Architecture (READ)
**Purpose**: High-level planning for federated content curation system
**Key Terms**:
- Three-tier architecture: Authoritative (MySQL) → Cache (JSON) → Aggregator (federated nodes)
- Authority model: Domain experts maintain canonical datasets, aggregators selectively replicate
- Trust system: Four-tier access (Guest/Verified/Admin/Root), consensus detection, provenance tracking
- Distribution: Pull-based selective replication, reachability-based garbage collection
- Puzzle collection: Specific domain implementation with creator/collector/manufacturer roles

**Integration Points**: Builds on existing Henhouse infrastructure, extends cache system for external sources
**Status**: Planning document for future phases (Phase 1-5 development strategy)

### daemon_manager.md - Auto-Scaling Daemon Orchestration (READ)
**Purpose**: High-level planning for comprehensive daemon management system
**Key Terms**:
- Meta-daemon: Central daemon manager that monitors and scales all other daemons
- Horizontal scaling: Multiple workers per daemon type (Flask tiers + maintenance workers)
- Async handoff: Flask apps use fire-and-forget request delegation to sub-daemons
- JSON state management: Dynamic daemon configuration with rolling boxcar dampening
- Fixed Nginx: Four main Flask tiers stay on fixed ports, sub-daemons use dynamic ports
- Tempo signaling: Flask apps ping daemon manager with request frequency metrics

**Integration Points**: Builds on existing Flask/maintenance architecture, adds auto-scaling layer
**Status**: Planning document for Phase 2 implementation (10-week development strategy)

### debug.md - Comprehensive Debug System (READ)
**Purpose**: Nitty-gritty details of debug system architecture and usage
**Key Terms**:
- Debug levels: trace (1-2), log (3), debug (4), warn (5) - activated by CLI flags
- Filter system: Three-tier filtering (whitelist/graylist/blacklist) with combination counting
- Debug modules: Debug Safe (base), Debug Table (tabular), Debug Trace (call stack), Debug MCP (JSON)
- Error system: Structured error rendering with field configurations and backend-specific parsers
- Safe mode: Context manager to prevent recursive debug rendering
- MCP integration: All debug flags work in MCP requests, output returned as JSON

**Integration Points**: Used throughout system for debugging, integrates with Gateway/Registry/Response
**Status**: Implemented system with comprehensive usage guide

### maintenance.md - Automated Background Task System (READ)
**Purpose**: Specific details of maintenance worker daemon and job queue system
**Key Terms**:
- Maintenance worker: Single monolithic daemon that processes job queue and stale cache items
- Job queue: Database-backed queue (maintenance_jobs table) with priority-based processing
- Cache refresh: Automatic detection and refresh of stale pages, images, files
- Tool registration: @register_maintenance_tool decorator for command discovery
- Daemon control: Cross-platform start/stop/status with privilege detection
- Envelope unwrapping: Maintenance backend extracts flat data from success_payload() MCP wrapper

**Integration Points**: Routes through Gateway dispatch with "maintenance" backend, uses standard connection patterns
**Status**: Implemented system with cross-platform daemon management

### overlay.md - TypeScript Overlay System Planning (READ)
**Purpose**: Specific details of modern TypeScript-based overlay system design
**Key Terms**:
- Component hierarchy: OverlayManager (singleton) → Overlay → OverlayBackdrop/Window/Header/Content
- Content components: Browser (navigation), FormBuilder (dynamic forms), ImageViewer (full-screen), TextEditor (rich text)
- React-inspired patterns: Components, props, state, lifecycle hooks without React framework
- MCP integration: Built-in RPC client support, JSON-RPC 2.0 format via /mcp endpoint
- Progressive enhancement: Python HTTP renders HTML, TypeScript adds interactivity
- Implementation phases: 7 phases from core foundation to full integration

**Integration Points**: Replaces legacy jQuery overlay system, integrates with MCP backend and Python HTTP
**Status**: Planning document with detailed implementation roadmap and checklist

### patterns.md - System Architecture Patterns (READ)
**Purpose**: Nitty-gritty details of coding patterns used throughout Henhouse system
**Key Terms**:
- Basic patterns: Action functions (CRUD + JSON response) + Backend functions (format output)
- Decorators: @register_action + @register_command for actions, @register_parser + @register_http for backends
- Error handling: Three-layer approach (Gateway reporting, Warning logging, Boolean bubbling)
- Database access: gateway.conn.read/create/update/delete methods with transaction management
- Table rendering: TableData + FieldConfig system with registered labels/icons via @register_label
- Tracing: Always use trace_in()/trace_out() for debugging, consistent gateway checks

**Integration Points**: Used throughout system for consistent coding patterns, integrates with Gateway/Registry/Render
**Status**: Implemented patterns with detailed examples and best practices

### render.md - Comprehensive Output Formatting System (READ)
**Purpose**: Nitty-gritty details of render system architecture and table formatting
**Key Terms**:
- Render pipeline: TableData.add_row() → render_block() → backend router → render_flexible_table() → TableBuilder → Layout/Borders/Cells → Output
- Table data collection: TableData() with add_row(field_type, **columns) for row collection
- Field configuration: FieldConfig() with add_header()/add_simple()/add_simple_color() for styling rules
- Table builder: TableBuilder(class_name, table_id) with set_columns() → row() → render() for table construction
- Text processing: display_width(), wrap(), pad_*(), to_*_case() for Unicode-aware text manipulation
- Configuration access: ic(), dc(), mc(), tc(), cc(), out() for icons, labels, table config, parse settings
- Config registry: @register_label decorator system for icons/labels with hot/cold cache

**Integration Points**: Used by all backend handlers for output formatting, integrates with Gateway/Config/Text systems
**Status**: Implemented comprehensive system with Unicode support and flexible configuration

### transaction.md - Batch Operation and Approval System (READ)
**Purpose**: Specific details of transaction/batch system for MCP requests with approval workflow
**Key Terms**:
- Batch operations: batch_operations tool accepts transaction JSON, creates approval queue pages
- Register system: register[key].bucket - 2D associative arrays for variable passing between serial groups
- Transaction hierarchy: Transaction → Serial Groups → Individual Actions (parallelization via sibling actions)
- Multi-tier MCP: Guest (read-only), Admin (approval queue), Root (immediate execution)
- Approval workflow: Human reviews via web interface, can approve/reject/delete individual items
- Executed-once rule: Successfully executed actions never re-run, subsequent runs process remaining approved items
- Lazy extraction: Register extraction evaluated at use-time from producers' stored results

**Integration Points**: Extends MCP system with batch capabilities, uses Page system for approval queue organization
**Status**: Detailed specification with comprehensive design constraints and implementation details

### verification.md - Tier 2 Authentication System Planning (READ)
**Purpose**: High-level planning for Tier 2 (verified) authentication using magic links and sessions
**Key Terms**:
- Magic link system: Token generation, email sending, validation for tier elevation
- Session management: Database-backed sessions with cookie-based session_id
- Tier elevation: Dynamic tier switching from guest (Tier 1) to verified (Tier 2) via email verification
- Database tables: magic_links (tokens), sessions (session data) with proper permissions
- Flask integration: Session middleware, auth routes, Gateway integration for tier-specific credentials
- Security: Cryptographically secure tokens, rate limiting, one-time use, expiration handling

**Integration Points**: Integrates with Flask app, Gateway system, and database connection for tier-based access
**Status**: Comprehensive implementation plan with 7 phases, security considerations, and testing checklist

## Summary of All Files Read

I have now read all 12 context files as requested. Here's what I found:

### High-Level Overview Files (6 files)
These provide the foundational understanding needed to navigate the codebase:
- **gateway.md**: Central orchestration system with 4-stage parsing pipeline
- **page.md**: Hierarchical content management with mixin architecture and caching
- **mcp.md**: Model Context Protocol integration with tool whitelisting
- **registry.md**: Command discovery and handler loading with caching
- **TypeScript.md**: Client-side HTTP interface with overlay system
- **text_processor.md**: Markup parsing system with decorator chains

### High-Level Planning Files (3 files)
These guide future development and system evolution:
- **aggregator.md**: Distributed knowledge architecture for federated content curation
- **daemon_manager.md**: Auto-scaling daemon orchestration system planning
- **verification.md**: Tier 2 authentication system using magic links and sessions

### Nitty-Gritty Detail Files (3 files)
These provide specific implementation patterns and deep technical details:
- **debug.md**: Comprehensive debug system with filtering and MCP integration
- **patterns.md**: System architecture patterns and coding best practices
- **render.md**: Output formatting system with table rendering and Unicode support

### Specific System Detail Files (2 files)
These cover specific subsystems with implementation details:
- **maintenance.md**: Automated background task system with daemon management
- **overlay.md**: TypeScript overlay system planning with React-inspired patterns
- **transaction.md**: Batch operation and approval system for MCP requests

## Key Insights for Overview Document

### Core Architecture Flow
Gateway → Registry → Action/Backend → Response → Output (CLI/HTTP/MCP)

### Integration Patterns
- Everything routes through Gateway dispatch
- Registry provides command discovery and handler loading
- Database access via gateway.conn methods
- Error handling through three-layer approach
- Debug system used throughout for tracing

### Cross-Cutting Systems
- MCP integration as backend type
- Page system for hierarchical content
- Render system for all output formatting
- Text processor for markup parsing
- Config system for icons/labels/settings

## Ready for Final Planning
Now that I have comprehensive notes from all files, we can plan the high-level overview document structure together.
