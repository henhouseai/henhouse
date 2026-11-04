# agent-info
## description
Comprehensive agent data retrieval with filtering and analysis capabilities.
## summary
The agent information system provides comprehensive data retrieval and analysis capabilities for inspecting agent profiles, work history, and system relationships. It includes advanced filtering options, deep mode analysis for detailed activity tracking, and relationship mapping between agents, work dockets, and system components. The system supports complex queries with pagination, sorting, and detailed reporting through specialized data source scripts. All data is presented through consistent table formatting with proper icons, labels, and dynamic field types based on agent status and context.
## full_text
The agent_info system provides comprehensive agent information retrieval and analysis through a suite of specialized commands that implement the parser system architecture with data source scripts generating JSON and parser modules formatting output using `render_flexible_table()`.

**Core Commands:**
- `agent-list` - List and filter agents with comprehensive search capabilities, deep mode analysis, and pagination support
- `agent-tree` - Get detailed agent information with activity tree, relationships, and comprehensive deep mode analysis

**Database Architecture:** All commands use PyMySQL with DictCursor for database operations, loading connection parameters from `.henhouse.cnf` files. The system implements complex query structures with LEFT JOINs across `agents`, `agent_profiles`, `work_dockets`, and related tables.

**Agent List Implementation:** The main query performs SELECT on `agents` table with LEFT JOINs to `agent_profiles` table using the structure: `SELECT DISTINCT a.id, a.agent_key, a.role, a.status, a.created_at, a.terminated, a.gate_status, a.gate_started_ts, a.session_id, ap.display_name, ap.country, ap.lineage_key, ap.generation FROM agents a LEFT JOIN agent_profiles ap ON a.id = ap.agent_id`.

**Advanced Filtering:** The system builds dynamic WHERE conditions using conditions array and params list. Role filtering uses `a.role = %s`, status filtering uses `a.status = %s` (defaulting to 'active'), and A/T/S relationship filtering uses EXISTS subqueries against `watercooler_messages` and microlog link tables (`wc_microlog_link_ask`, `wc_microlog_link_task`, `wc_microlog_link_step`).

**Deep Mode Architecture:** When `--deep` flag is used, the system creates separate cursor contexts to avoid closure issues and performs additional queries for each agent: watercooler activity query (`SELECT wm.id, wm.kind, wm.content, wm.meta, wm.occurred_ts FROM watercooler_messages wm WHERE wm.from_agent_id = %s ORDER BY wm.occurred_ts DESC LIMIT 10`) and subscription count query using UNION ALL across subscription tables.

**Agent Tree Implementation:** The agent tree query retrieves comprehensive agent data using: `SELECT a.id, a.agent_key, a.role, a.status, a.created_at, a.terminated, a.gate_status, a.gate_started_ts, a.session_id, ap.display_name, ap.persona_json, ap.country, ap.lineage_key, ap.generation FROM agents a LEFT JOIN agent_profiles ap ON a.id = ap.agent_id WHERE a.id = %s`.

**Deep Mode Queries:** Agent tree deep mode performs five additional queries: agent runs history (`SELECT ar.id, ar.session_id, ar.prompt, ar.model, ar.log_path, ar.started_ts, ar.last_heartbeat_ts, ar.status, ar.notes FROM agent_runs ar WHERE ar.agent_id = %s ORDER BY ar.started_ts DESC LIMIT 10`), watercooler activity, subscriptions using UNION ALL across subscription tables, linked A/T/S items via microlog link tables, and agent runtime state from `agent_runtime_state` table.

**Parser Integration:** Both commands use field configurations with dynamic field types for status and role (`role_{status}`, `status_{status}`) and implement the "ONE table" approach with all data in single `render_flexible_table()` calls. The parsers handle datetime serialization, JSON meta parsing, error states with hints, and conditional rendering based on NO_FLAGS configuration.

**Error Handling:** The system includes comprehensive error handling for not found agents (`{"error": "not_found", "hint": f"agent {agent_id}"}`), database connection issues, and JSON serialization problems. Errors are formatted through the parser system with proper icons and styling.

**Pagination Support:** Agent list supports `--limit` parameter applied post-processing using Python list slicing (`result["agents"] = result["agents"][:args.limit]`) after all filtering and sorting operations.

**Output Format:** Both commands return structured JSON with success/error states, data arrays, and metadata. The parsers transform this into formatted tables using the table rendering system with proper icons, labels, and styling through the configuration system (`icon.ini`, `label.ini`, `table.ini`).

**Security and Validation:** All operations include comprehensive identity validation, status checking, and error handling with proper parameterized queries for security and transaction management for data consistency.
---
