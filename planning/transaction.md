# Henhouse Transaction/Batch System Architecture

This document covers the comprehensive transaction and batch operation system for MCP requests, including the approval queue, register-based variable passing, and multi-tier MCP server architecture.

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Multi-Tier MCP Server Architecture](#2-multi-tier-mcp-server-architecture)
3. [Transaction Structure](#3-transaction-structure)
4. [Register System](#4-register-system)
5. [Database Schema](#5-database-schema)
6. [Approval Workflow](#6-approval-workflow)
7. [Execution Model](#7-execution-model)
8. [Extraction System](#8-extraction-system)
9. [Integration Points](#9-integration-points)
10. [Implementation Details](#10-implementation-details)

## Agent Quick Reference

- **Batch Tool**: `batch_operations` or `execute_transaction` - accepts transaction JSON, creates approval queue pages
- **Register Syntax**: `register[key].bucket` - 2D associative arrays for variable passing between serial groups
- **Transaction Hierarchy**: Transaction → Serial Groups → Individual Actions (parallelization via sibling actions)
- **Approval**: Human reviews via web interface, can approve/reject/delete individual items or entire request
- **MCP Server Tiers**: Guest (read-only), Admin (approval queue), Root (immediate execution)
- **Executed-once**: Once an action executes successfully, it is never re-run; subsequent runs only process remaining approved-but-unrun items
- **Lazy extraction**: Register extraction is evaluated at use-time by consumers, from producers’ stored results

## Agent Training Notes

### Transaction Creation
- Use `batch_operations` tool with transaction JSON structure
- Specify serial groups, parallelization keys, and extraction paths
- Tool returns immediately with page ID for monitoring
- All operations go into approval queue (for admin tier) or execute immediately (for root tier)

### Register System
- Use associative keys (strings or numbers) for parallelization
- Extract values using JSON path navigation
- Reference registers in subsequent operations: `register[key].bucket`
- Registers persist across entire transaction, can be modified/added to

### Approval Process
- Human reviews via web interface (panel/admin tier)
- Can approve/reject/delete individual actions
- Can run entire request or parts of it
- Execution stores results, populates registers, aggregates final report

---

## 1. System Overview

The transaction/batch system enables agents to submit multiple MCP operations as a single atomic request with approval workflow, variable passing between operations, and comprehensive result tracking. The system supports parallel execution within serial groups, register-based variable extraction and reference, and human-in-the-loop approval for safety.

### Key Features

- **Batch Operations**: Submit hundreds of operations in a single transaction
- **Approval Queue**: Human review before execution (admin tier) or immediate execution (root tier)
- **Variable Passing**: Extract values from responses and use them in subsequent operations
- **Parallel Execution**: Run independent operations simultaneously within serial groups
- **Result Tracking**: Comprehensive reporting of requested vs. executed CRUD operations
- **Hierarchical Organization**: Use page system for visual organization of transaction structure

### Architecture Flow

```
Agent (Admin Tier)
    ↓
batch_operations MCP tool call
    ↓
Transaction Parser
    ↓
Database: Create pages in approval queue
    ↓
Human Review (Web Interface)
    ↓
Approval/Rejection/Modification
    ↓
Execution Engine
    ↓
Register Population
    ↓
Result Aggregation
    ↓
Final MCP Request Record
```

---

## 2. Multi-Tier MCP Server Architecture

The system uses three distinct MCP server tiers, each exposing different tools with different execution behaviors.

### Guest Tier MCP Server

**Purpose**: Read-only access, equivalent to web browsing

**Exposed Tools**:
- Listers: `command_list`, `parser_list`, `http_list`, `action_list`, `backend_list`, `mcp_list`
- Getters: `get_page`, `show_page`, `show_image`, `count_pages`
- Help: `help`
- Agent queries: `agent_list`, `agent_tree`, `peek`, `status`

**Behavior**:
- No write operations exposed
- No approval needed
- Immediate execution
- No batch operations tool

### Admin Tier MCP Server

**Purpose**: Write access with human approval workflow

**Exposed Tools**:
- All Guest tier tools (read operations)
- Write operations: `add_page`, `modify_text`, `modify_name`, `delete_page`, `copy_page`, `move_page`, etc.
- Image operations: `add_image`, `modify_caption`, `remove_image`, etc.
- Source code file operations: `modify_path`, `modify_language`
- Batch operations: `batch_operations` (approval queue required)
- Agent operations: `gossip`, `gulp`, `sip`, subscriptions, onboarding, etc.

**Behavior**:
- All write operations go through approval queue
- Creates pages in approval queue folder
- Returns immediately with page ID for monitoring
- Human must approve via web interface before execution
- Individual operations can be approved/rejected/deleted

### Root Tier MCP Server

**Purpose**: Immediate execution, no approval needed

**Exposed Tools**:
- All Admin tier tools
- Same tool set, different behavior

**Behavior**:
- All operations execute immediately
- No approval queue
- No page creation for review
- Direct execution via gateway subprocess calls
- Used for trusted agents or automated systems

### Whitelist System Enhancement

**Status**: ✅ **IMPLEMENTED**

The MCP whitelist system has been refactored to a decorator-based, lazy-loading system:

**Implementation**:
- **Core System**: `hh/gateway/registry/mcp_whitelist.py` - `MCPWhitelist` class with lazy loading
- **Registration Files**: Module-specific `mcp_utils.py` files using `@register_mcp_tool` decorators
- **Tier-Specific Caches**: `hh/gateway/registry/cache/mcp-whitelist-{tier}.json` for each tier
- **Tier Levels**: Uses numeric levels `[1, 2, 3, 4]` (1=guest, 2=verified, 3=admin, 4=root) instead of tier names

**Per-Tool Configuration** (via decorator):
- `tiers`: List of tier levels (e.g., `[1, 2, 3, 4]` for all tiers, `[3, 4]` for admin/root only)
- `requires_approval`: Boolean indicating if tool requires approval queue (for future transaction system)
- `crud_type`: String indicating operation type: `"create"`, `"read"`, `"update"`, `"delete"`
- `display_color`: Optional color code for approval interface display (for future transaction system)

**Example Registration**:
```python
@register_mcp_tool(
    tool_name='add_page',
    description='Create a new page...',
    inputSchema={...},
    tiers=[3, 4],  # Admin and root only
    requires_approval=False,  # Currently not used, reserved for future
    crud_type='create',
    display_color=None  # Currently not used, reserved for future
)
def _page_tools_registration():
    """Registration placeholder for page-related MCP tools."""
    pass
```

**Cache Behavior**:
- Cold cache files store only `description` and `inputSchema` (no tier metadata in JSON)
- Cache files auto-rebuild on miss (when tool requested but not found)
- All tier caches rebuilt together when any tier has a miss
- Hot cache (in-memory) persists across rebuilds to match other registry systems

---

## 3. Transaction Structure

### JSON Schema

A transaction is a JSON object with the following structure:

```json
{
    "groups": [
        {
            "operations": [
                {
                    "tool": "add_page",
                    "args": {
                        "target_page": 123,
                        "name": "New Page",
                        "class": "page"
                    },
                    "parallelization_key": "A",
                    "extract": {
                        "id": ["result", "page", "id"],
                        "name": ["result", "page", "name"]
                    }
                },
                {
                    "tool": "add_page",
                    "args": {
                        "target_page": 123,
                        "name": "Another Page",
                        "class": "page"
                    },
                    "parallelization_key": "B",
                    "extract": {
                        "id": ["result", "page", "id"],
                        "name": ["result", "page", "name"]
                    }
                }
            ]
        },
        {
            "operations": [
                {
                    "tool": "modify_text",
                    "args": {
                        "page_id": "register['A'].id",
                        "text": "Content for first page"
                    },
                    "parallelization_key": "A"
                },
                {
                    "tool": "modify_text",
                    "args": {
                        "page_id": "register['B'].id",
                        "text": "Content for second page"
                    },
                    "parallelization_key": "B"
                }
            ]
        }
    ]
}
```

### Structure Components

**Transaction Root**:
- `groups`: Array of serial groups (executed sequentially)

**Serial Group**:
- `operations`: Array of individual operations (executed in parallel)
- No nested serial groups allowed (only top-level serial groups)
- All operations in a group run simultaneously

**Individual Operation**:
- `tool`: MCP tool name (must be in whitelist for requesting tier)
- `args`: Tool arguments (can reference registers using `register[key].bucket` syntax)
- `parallelization_key`: Associative key (string or number) for register access
- `extract`: Optional object specifying what to extract from response (JSON paths)

### Parallelization Keys

- **Associative**: Can be strings ("A", "B", "file1") or numbers (0, 1, 2)
- **Unique within group**: Each operation in a serial group must have unique key
- **Cross-group reference**: Same keys can be used across serial groups to access registers
- **Flexible count**: Different serial groups can have different numbers of operations
- **Key matching**: Operations referencing registers must use keys that exist in previous groups

### Extraction Specification

**Format**: Object mapping bucket names to JSON path arrays

**Example**:
```json
{
    "id": ["result", "page", "id"],
    "name": ["result", "page", "name"],
    "link": ["result", "page", "link"]
}
```

**JSON Path Navigation**:
- Array format: `["result", "page", "id"]` navigates `result.page.id`
- Supports nested structures of arbitrary depth
- Extracts values from tool response JSON
- Stores in register: `register[parallelization_key].bucket_name`

---

## 4. Register System

### Two-Dimensional Associative Arrays

Registers are 2D arrays with:
- **First dimension**: Associative keys (parallelization keys from operations)
- **Second dimension**: Numerical buckets (extracted values: id, name, link, etc.)

**Syntax**: `register[key].bucket`

**Examples**:
- `register["A"].id` - ID extracted from operation with key "A"
- `register[0].name` - Name extracted from operation with key 0
- `register["file1"].link` - Link extracted from operation with key "file1"

### Register Lifecycle

**Initialization**: Empty at transaction start

**Population**:
- Values are not eagerly stored; extraction is evaluated at use-time by consumers
- Producers declare `extract_spec`; consumers navigate producer `result` JSON to obtain values

**Persistence**:
- Effective values are derivable at any time from executed producer results
- Available to all subsequent serial groups via dependency resolution

**Modification**:
- Later serial groups can introduce new buckets in producers’ `extract_spec`
- Example: First group extracts `id` and `name`; second group’s producers may also expose `link`

### Register Reference in Arguments

**Syntax in args**: Use string format `"register[key].bucket"` which gets replaced with actual value

**Example**:
```json
{
    "tool": "modify_text",
    "args": {
        "page_id": "register['A'].id",
        "text": "Updated content"
    }
}
```

**Replacement**: `"register['A'].id"` → actual ID value (e.g., `123`)

**Key Format**: Keys can be strings (use quotes: `register['A']`) or numbers (no quotes: `register[0]`)

---

## 5. Database Schema

### New Table: `mcp_action_requests`

Stores individual MCP action requests with their arguments, dependency metadata, results, and lifecycle state.

**Schema**:
```sql
CREATE TABLE mcp_action_requests (
    page_id INT PRIMARY KEY,               -- 1:1 with mcp_action page

    tool_name VARCHAR(255) NOT NULL,
    arguments JSON NOT NULL,
    extraction_spec JSON,

    status ENUM(
        'pending','approved','dependency_unmet','executing',
        'executed','failed','rejected','cancelled'
    ) DEFAULT 'pending',

    result JSON,

    is_create TINYINT(1) DEFAULT 0,
    is_read   TINYINT(1) DEFAULT 0,
    is_update TINYINT(1) DEFAULT 0,
    is_delete TINYINT(1) DEFAULT 0,

    INDEX idx_status (status),
    INDEX idx_tool (tool_name),
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
);
```

### New Table: `mcp_requests`

Stores aggregate request records and lifecycle state.

**Schema**:
```sql
CREATE TABLE mcp_requests (
    page_id INT PRIMARY KEY,                    -- Links to mcp_request page
    input_request JSON NOT NULL,                -- Original transaction JSON
    output_response JSON,                       -- Final aggregated results

    create_request INT DEFAULT 0,
    read_request   INT DEFAULT 0,
    update_request INT DEFAULT 0,
    delete_request INT DEFAULT 0,

    create_executed INT DEFAULT 0,
    read_executed   INT DEFAULT 0,
    update_executed INT DEFAULT 0,
    delete_executed INT DEFAULT 0,

    status ENUM('pending','approved','executing','completed','failed','cancelled','rolled_back')
           DEFAULT 'pending',

    INDEX idx_status (status)
);
```
### New Page Class Types

Two new page class types extend the base page system; serial groups use the existing `page` class:

#### 1. Individual MCP Action (`mcp_action`)

**Purpose**: Represents a single MCP tool call

**Data**: Links to `mcp_action_requests` table via `page_id`

**Properties**:
- Standard page properties (id, name, parent, etc.)
- Additional data in `mcp_action_requests` table

#### 2. MCP Request (`mcp_request`)

**Purpose**: Final aggregate record of entire transaction

**Data**: Additional table `mcp_requests`

**Schema (see updated schema below)**: Tracks lifecycle and counts for the request

### Page Hierarchy Structure

```
MCP Request (mcp_request page)
    ├─ Group 1 (page)    ← groups sorted by ascending page_id; executed sequentially
    │   ├─ Action (mcp_action)
    │   ├─ Action (mcp_action)
    │   └─ Action (mcp_action)
    └─ Group 2 (page)
        ├─ Action (mcp_action)
        └─ Action (mcp_action)
```

**Notes**:
- Any direct child `page` of an `mcp_request` is a serial group
- Groups execute in ascending `page_id`
- Actions within a group launch in parallel by default (UI displays in `page_id` order)

### Approval Queue Folder

All transaction pages are created under a special folder (e.g., page ID for "approval_queue" or similar) for easy access in web interface.

---

## 6. Approval Workflow

### Request Submission

1. **Agent calls `batch_operations` tool** with transaction JSON
2. **Transaction parser** validates structure and creates database entries
3. **Page creation**:
   - Creates MCP Request page in approval queue folder
   - Creates Group pages (class=`page`) as children (one per serial group)
   - Creates Individual MCP Action pages as children of each group
   - Links each `mcp_action` page to `mcp_action_requests` table
4. **Immediate response**: Returns page ID and link to agent for monitoring

### Human Review Interface

**Access**: Web interface via panel/admin tier (HTTP, not MCP)

**Features**:
- **Hierarchical view**: See transaction structure as page tree
- **Color coding**: Actions colored by CRUD type (green=create, red=delete, blue=update, gray=read)
- **Individual actions**: See tool name, arguments, parallelization key
- **Dependency readiness**: UI computes unmet dependencies and disables Run where appropriate
- **Approval controls**: 
  - Approve/reject individual actions
  - Delete actions from request
  - Approve entire request
  - Run entire request or parts of it

**Dashboard Views** (future enhancements):
- **Table-level view**: Which database tables will be affected
- **Hierarchy view**: Which parts of page tree will be affected
- **CRUD summary**: Counts of create/read/update/delete operations

### Approval Actions

**Individual Action**:
- Approve: Mark action as approved
- Reject: Mark action as rejected (won't execute)
- Delete: Remove action from request entirely
- Edit: Modify arguments (future enhancement)

**Group/Request Level**:
- Approve all: Mark all pending actions as approved
- Run group: Execute all approved actions in a serial group
- Run request: Execute entire transaction (all approved actions)

### Execution Trigger

**Manual**: Human clicks "Run" button on approved request/group

**Automatic**: (Future enhancement) Auto-execute when all actions approved

**Executed-once Rule**: Already executed items are never re-run; running a group/request processes only approved and unexecuted items

---

## 7. Execution Model

### Execution Flow

1. **Validation**: Check actions are approved; skip any already executed (executed-once rule)
2. **Serial group execution**: Process groups sequentially by ascending `page_id`
3. **Within-group execution**: Launch approved, unexecuted actions in parallel
4. **Dependency resolution (use-time)**: For each action just-in-time, resolve any `register[key].bucket` references against prior executed producers
5. **Result storage**: On success, persist `result` JSON and mark `executed`; on failure, rollback DB changes (action remains eligible to re-run)
6. **Failure barrier**: Any failure in a serial group blocks subsequent groups; peers in the same group continue

### Parallel Execution

**Implementation**: 
- Fire off independent gateway subprocess calls for each operation
- Let server handle parallelization (potentially through root MCP)
- All operations in serial group start simultaneously

**Failure Handling**:
- If any operation fails, other parallel operations continue
- After all parallel operations complete, check for failures
- If any failed: Stop execution of remaining serial groups
- Human can review failures, edit request, and retry

### Dependency Resolution (Lazy Extraction)

Resolution happens at the moment a consumer action is about to execute:
1. Scan consumer arguments for `register[key].bucket` patterns
2. Find a prior executed producer with matching `parallelization_key` in earlier groups
3. Confirm producer declares an `extract_spec` for `bucket`
4. Apply the JSON path to the producer’s stored `result` and substitute the concrete value
5. If producer not executed or path missing:
   - Mark consumer `dependency_unmet` and do not execute
   - Surface dependency error in UI; action remains eligible once dependencies are satisfied

### Result Aggregation

**After all serial groups execute**:
1. Collect all operation results
2. Count CRUD operations by type (requested vs. executed)
3. Build `refined_output_json` with all results
4. Update MCP Request record with:
   - `refined_output_json`
   - `executed_create_count`, `executed_read_count`, etc.
   - `executed_at` timestamp
   - `status` = 'completed' or 'failed'

### Cleanup

**After completion**:
- Optionally delete intermediate pages (Serial Step Groups, Parallel Step Groups, Individual MCP Actions)
- Keep MCP Request page with final aggregate record
- Or provide option to keep all pages for audit trail

---

## 8. Extraction System

### JSON Path Navigation

**Format**: Array of strings representing path through JSON object

**Examples**:
- `["result", "page", "id"]` → navigates `result.page.id`
- `["content", 0, "text", "page", "name"]` → navigates `content[0].text.page.name`
- `["data", "items", 2, "value"]` → navigates `data.items[2].value`

### Extraction Specification

**In transaction JSON**:
```json
{
    "extract": {
        "id": ["result", "page", "id"],
        "name": ["result", "page", "name"],
        "link": ["result", "page", "link"]
    }
}
```

**Processing**:
1. Producer action stores its `result` JSON on success
2. Consumer action (at execution time) finds the producer by `parallelization_key`
3. For each referenced bucket:
   - Navigate JSON path on the producer’s stored `result`
   - Extract value and substitute into consumer arguments
4. If extraction fails (missing producer/path): mark consumer `dependency_unmet` and do not execute

### Multiple Extractions

**Unlimited buckets**: Can extract as many values as needed from a single response

**Example**: Extract ID, name, link, parent, class, visibility, etc. from `add_page` response

### Error Handling

**Missing path**: If JSON path doesn't exist in response:
- Set register value to null
- Or mark extraction as failed
- Operation may still succeed, but register value unavailable

**Type mismatches**: Extract value as-is, let subsequent operations handle type conversion

---

## 9. Integration Points

### With MCP System

**New Tool**: `batch_operations` added to whitelist
- Admin tier: Requires approval
- Root tier: Executes immediately (bypasses approval queue)

**Tool Schema**:
```python
"batch_operations": {
    "description": "Execute a batch of MCP operations as a transaction with approval workflow",
    "inputSchema": {
        "type": "object",
        "properties": {
            "transaction": {
                "type": "object",
                "description": "Transaction structure with serial groups and operations"
            }
        },
        "required": ["transaction"]
    },
    "tiers": ["admin", "root"],
    "requires_approval": True,  # Admin tier only
    "crud_type": "mixed"
}
```

### With Gateway System

**Execution**: 
- Individual operations execute via `gateway.dispatch(argv, "mcp")`
- May route through root MCP for parallel execution
- Uses standard Gateway action/backend handlers

**Error Handling**: 
- Gateway errors collected per operation
- Aggregated in final result report

### With Page System

**Page Classes**: 
- New page classes: `mcp_request` and `mcp_action` (serial groups use existing `page` class)
- Use existing page hierarchy, display, and management systems

**Approval Interface**: 
- Uses existing page display system
- Custom rendering for MCP action details
- Integration with existing page CRUD operations

### With Database Connection

**Transaction Safety**: 
- Individual operations use existing `@db_write` decorators
- Serial groups could use database transactions (future enhancement)
- Register system is in-memory (not persisted to database)

---

## 10. Implementation Details

### Transaction Parser

**Location**: New action handler for `batch_operations` tool

**Responsibilities**:
1. Validate transaction JSON structure
2. Validate all tool names are in whitelist for requesting tier
3. Validate parallelization keys are unique within each serial group
4. Create page hierarchy in database
5. Create `mcp_action_requests` records
6. Create `mcp_requests` record
7. Count CRUD operations for `requested_*_count` fields
8. Return page ID and link to agent

### Register System Implementation

**In-Memory Storage**: 
- Registers stored in memory during execution
- Not persisted to database
- Cleared after transaction completes

**Data Structure**:
```python
registers = {
    "A": {
        "id": 123,
        "name": "Page Name",
        "link": "page-name"
    },
    "B": {
        "id": 124,
        "name": "Another Page"
    },
    0: {
        "id": 125,
        "name": "Numeric Key Page"
    }
}
```

**Reference Resolution**:
- Regex pattern: `register\[(['"]?)(\w+)\1\]\.(\w+)`
- Replace with: `registers[key][bucket]`
- Handle both string keys (quoted) and numeric keys (unquoted)

### Execution Engine

**Location**: New execution handler (triggered by approval interface)

**Responsibilities**:
1. Load transaction structure from database
2. Initialize empty registers
3. For each serial group:
   - Resolve register references in arguments
   - Execute all operations in parallel (gateway subprocess calls)
   - Collect results
   - Populate registers from extraction specs
   - Check for failures, stop if any
4. Aggregate final results
5. Update MCP Request record

### Approval Interface

**Location**: Web interface (Flask routes, HTML templates)

**Features**:
- Display transaction as page tree
- Color code actions by CRUD type
- Show tool name, arguments, parallelization key
- Approve/reject/delete controls
- Run button for approved requests/groups

**Integration**:
- Uses existing page display system
- Custom templates for MCP action rendering
- HTTP endpoints for approval actions (not MCP)

### Agent Monitoring

**Agent can**:
- Call `get_page` or `show_page` with returned page ID
- See approval status, execution status
- See final results in MCP Request record
- Monitor progress through transaction lifecycle

**Response Format**:
```json
{
    "page_id": 1234,
    "status": "pending",
    "link": "/page/1234",
    "message": "Transaction queued for approval"
}
```

---

## Design Constraints Summary

1. **Explicit extraction**: Agent must specify extraction paths; no inference
2. **Lazy resolution**: Extraction is evaluated at use-time from producers’ stored results
3. **Associative keys**: Parallelization keys are associative (strings or numbers), not positional
4. **Flexible group sizes**: Serial groups can have different numbers of operations
5. **Key matching**: Consumers must use keys that exist in previous groups
6. **Parallel failure handling**: Parallel peers continue; any failure blocks subsequent groups
7. **No nested serial groups**: Only top-level serial groups allowed
8. **Page-based organization**: Use existing `page` for groups; `mcp_request` and `mcp_action` as root/leaf classes
9. **Ordering**: Groups execute by ascending `page_id`; actions launched in parallel by default
10. **Executed-once**: Executed items are never re-run; subsequent runs operate only on remaining approved/unrun items
11. **Tier-based behavior**: Admin tier requires approval, root tier executes immediately

---

## Future Enhancements

### Short-term
- Color coding in approval interface
- Dashboard views (table-level, hierarchy-level)
- Edit operation arguments in approval interface

### Medium-term
- Database transactions for serial groups (atomicity)
- Automatic execution when all actions approved
- Register persistence for debugging/audit

### Long-term
- Nested serial groups (if needed)
- Conditional execution based on register values
- Template system for common transaction patterns
- Agent learning from approved transactions

---

This document provides comprehensive specification for the transaction/batch system. All implementation should follow these design constraints and architectural patterns.

