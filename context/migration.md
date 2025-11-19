# Database Architecture Migration Plan

## Overview

This document outlines the migration plan for restructuring the database architecture to support a hybrid document-relational model with a separate caching layer. The system is designed to start on a single box but scale to three separate boxes as needed.

## Architecture Goals

### Current State
- Single MySQL server handling all operations
- Multiple relational tables requiring joins
- Text parsing bottleneck when traversing deep hierarchies
- Wiki-style syntax parsing with complex link resolution

### Target State
- Hybrid document-relational database using JSON fields to flatten structure
- Separate cache layer for read-only operations
- Decorator-based connection management with dual-database access
- Lazy cache invalidation with priority queuing
- Scalable architecture supporting 1-3 box deployment

## Database Structure

### Main Database (MySQL)
- **Purpose**: Write operations, complex business logic, link resolution
- **Structure**: Hybrid relational-document model
  - Core page table with indexed columns (id, parent, name)
  - JSON fields for flexible, document-style data storage
  - Reduced table count by moving variant data into JSON fields
  - Links table tracking wiki-syntax references between pages
- **Benefits**: 
  - Eliminates need for many joins
  - Supports derived classes/variants without separate tables
  - Maintains relational integrity where needed

### Cache Database
- **Purpose**: Read-only access to pre-computed page data
- **Structure**: 
  - Separate table (or separate database/server) containing cached pages
  - Stores fully parsed text output (processed wiki syntax)
  - Flat document-style structure for fast retrieval
  - No complex joins or processing required
- **Deployment**: 
  - Initially: separate table in same MySQL instance
  - Later: separate database or NoSQL server (e.g., MongoDB) on separate box

## Connection Management

### Decorator System
Both `@db_read` and `@db_write` decorators will provide connection objects containing **two connections**:
- **Primary connection**: Based on decorator type (read → cache, write → main)
- **Secondary connection**: Access to the other database as needed

### Connection Object Structure
```python
connection = {
    'primary': <cache_or_main_db_connection>,
    'secondary': <other_db_connection>
}
```

### Connection Passing Mechanism
- Decorator inserts connection object as **first argument** to decorated function
- Functions use this connection variable for all database operations
- In transaction mode: connection passed down call chain via connection-aware functions
  - Use "getpage for connections" (not "getpage for decorators") to pass connection
  - Initial call uses decorator; subsequent calls use connection-aware version
- Select queries within write transaction use same connection (no separate decorator needed)
- All operations within transaction commit/rollback together

### Usage Patterns
- **@db_read**: Defaults to cache database, but can access main DB for stale reference checks
- **@db_write**: Defaults to main database, but can access cache for navigation/selection UI
- Functions receive single connection object with both connections available
- Page mixin methods continue using `self.conn` pattern (connection object passed via wrapper system)
- Query functions (`r_query`, `u_query`, etc.) will accept connection object and use `connection['primary']` by default

## Cache Invalidation Strategy

### Stale Reference Handling
- Pages are **never proactively deleted** from cache
- Most recently computed cache always available for serving reads
- Stale references are acceptable for read-only operations

### Invalidation Triggers
1. **Page text updates**: Queue recalculation of parsed text
2. **Page name changes**: Queue updates to all pages linking via name
3. **Link table changes**: Queue updates to affected pages

### Priority Queue System
- **Background daemon**: Processes queued updates lazily
- **Queue storage**: Database table in main database tracking pending updates
- **Queue implementation options**:
  - **Query-based**: Queue the query itself (e.g., "update all pages linking to page X by name")
  - **Item-based**: Queue individual page IDs that need updates
- **Daemon operation**:
  - Runs queued query to determine how many items need processing
  - Processes one item at a time from the list
  - Checks queue when Flask apps are idle
  - Continues until queue empty or new high-priority item arrives

### Priority Levels
- **High**: Admin/editor requests requiring fresh data (blocks user, synchronous rebuild)
- **Normal**: User-driven requests - **first access of stale cache bumps to queue head**
- **Low**: Background processing of large update sets

### Request-Driven Prioritization
- **Key concept**: Accessing a stale cache entry automatically bumps it to priority queue
- **Flow**: `@db_read` checks cache first, detects stale reference via secondary connection, serves stale cache immediately and queues rebuild
- Example: Changing "Rubik's Cube" name triggers million-page update cascade
  - Operation completes immediately by adding update task to queue
  - No blocking - first user accessing stale cache triggers priority rebuild
  - Subsequent users benefit from updated cache
- **Background fetch API**: Optional enhancement - can slip in changes after recalculation completes
- Most important: Stale cache serves immediately, but access triggers background update

## Scalability Path

### Phase 1: Single Box (Current)
- Single MySQL instance
- Two databases: `main_db` and `cache_db`
- Configuration file points decorators to appropriate databases
- All Flask/NGINX on same box

### Phase 2: Two Boxes
- **Box 1**: NGINX + Flask applications
- **Box 2**: MySQL server (both main and cache databases)
- Configuration update: Point to remote MySQL server

### Phase 3: Three Boxes
- **Box 1**: NGINX + Flask applications
- **Box 2**: Main MySQL database (writes, business logic)
- **Box 3**: Cache server (NoSQL or optimized read-only MySQL)
- Configuration update: Point decorators to separate servers
- **No code changes required** - only configuration file updates

## Transaction Handling

### Write Transactions
- `@db_write` decorator creates transaction context
- Transaction applies to primary connection (main DB)
- Connection passed down call chain via connection-aware functions
- Select queries within write transaction use same connection
- All operations within transaction commit/rollback together
- Read operations within write transaction don't require separate decorator
- Can read from secondary (cache) connection for reference data without affecting transaction

### Read Operations
- `@db_read` decorator provides read-only access
- Primary connection is cache DB, secondary is main DB
- Can perform select queries on either database via connection object
- Stale reference detection automatically checks secondary connection when needed
- No transaction locking concerns for read operations

## Data Normalization Status

### JSON Field Migration (Completed)
- Variant-specific data for all current page subclasses now lives directly in `pages.metadata`.
- Legacy tables removed: `work_dockets` still exists for historical reasons, but `source_code_files`, `mcp_requests`, and `mcp_action_requests` have been fully retired.
- Page helpers (`get_metadata_value`, `set_metadata_value`, `_write_metadata_dict`) are the single interface for derived classes.
- Existing subclasses migrated:
  - WorkPage hierarchy (dockets/asks/tasks/steps)
  - SourceCodeFile
  - MCP Request
  - MCP Action Request
- Benefits realized:
  - Fewer tables to manage and no join overhead for derived fields
  - Easier to add future subclasses without schema changes
  - JSON keys updated in-place via MySQL’s JSON operators

Future derived classes should follow the same pattern; no additional schema work is required for metadata storage.

## Cache Database Rollout

- A dedicated cache schema now exists alongside the primary database. Deployment scripts (`init_db`, `add_db_users`, `import_db`, `export_db`) were updated to create and manage both `<project>` and `<project>_cache`.
- New SQL file: `hh/deploy/db/init_cache.sql` defines the flattened cache tables (`pages`, `images`, `files`) that will eventually serve read traffic. Running `init_db` now executes both init scripts.
- Database credentials support optional `cache_*` overrides (host, user, password, database). When unspecified, the system falls back to the primary DSN and automatically targets `<database>_cache` for the secondary connection.
- Connection decorators hand out a wrapper containing both primary (main DB) and secondary (cache DB) connections so future read paths can switch to the cache transparently.

## Application Stack

### Current Architecture
- **NGINX**: Routes requests to different Flask daemons
- **Flask daemons**: Multiple instances running, handling requests
- **Gateway script**: Flask daemons make sub-process calls to gateway Python script (one-shot affair)
- **Python code layer**: Gateway script calls into system Python code with pyMySQL database connections
- **Scaling**: Multiple Flask apps can run on multiple ports/cores
  - NGINX distributes load across Flask instances
  - All Flask instances point to same MySQL server (potential bottleneck)

### Production Considerations
- **Future migration**: Consider switching from Flask daemons to Gunicorn or similar production WSGI server
- This would occur between current development setup and full production scaling

### Cache Rebuild Logic
- When cache miss occurs:
  1. Check main database for page
  2. Process text parsing (if needed)
  3. Queue cache rebuild (high priority if user-requested)
  4. Return stale cache or trigger synchronous rebuild for admin requests
- Background daemon handles non-blocking rebuilds

### Link Resolution
- Links table tracks: source page ID, link text, target page ID
- Name changes trigger cascade: find all links using old name, queue updates
- Updates processed lazily unless high-priority request

## Performance Considerations

### Read Patterns
1. **Single page + direct children**: Indexed parent lookup
2. **Deep hierarchy traversal**: Limited depth (2-3 levels) with guardrails
3. **Individual page lookups**: By ID or unique name field

### Optimization
- Cache eliminates parsing overhead for reads
- JSON fields eliminate join overhead
- Separate cache server reduces load on main database
- Lazy updates prevent blocking on large cascades (e.g., million-node trees)

