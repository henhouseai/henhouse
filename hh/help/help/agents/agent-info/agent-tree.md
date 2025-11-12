# agent-tree
## description
Get comprehensive agent information with activity tree and relationship data for detailed agent analysis.
## summary
Retrieves detailed information about a specific agent including basic profile data, work docket assignment, and optional deep mode for comprehensive activity logs, subscriptions, linked items, and runtime state. Results are formatted in a single table with proper icons and styling using dynamic field types based on agent status. Deep mode provides extensive additional data through five additional database queries.
## full_text
The agent-tree command implements comprehensive agent information retrieval through the parser system architecture. It consists of a data source script (`tools/agents/agent_tree.py`) that generates JSON data and a parser module (`tools/agents/parse_agent_tree.py`) that formats the output using `render_flexible_table()` with the "ONE table" approach.

**Database Architecture:** The main query performs a SELECT on the `agents` table with LEFT JOINs to `agent_profiles` table. The query structure includes comprehensive agent data: `a.id, a.agent_key, a.role, a.status, a.created_at, a.terminated, a.gate_status, a.gate_started_ts, a.session_id` from agents, and `ap.display_name, ap.persona_json, ap.country, ap.lineage_key, ap.generation` from agent_profiles. The query is: `SELECT a.id, a.agent_key, a.role, a.status, a.created_at, a.terminated, a.gate_status, a.gate_started_ts, a.session_id, ap.display_name, ap.persona_json, ap.country, ap.lineage_key, ap.generation FROM agents a LEFT JOIN agent_profiles ap ON a.id = ap.agent_id WHERE a.id = %s`.

**Deep Mode Implementation:** When `--deep` flag is used, the system performs five additional queries within the same cursor context: agent runs history (`SELECT ar.id, ar.session_id, ar.prompt, ar.model, ar.log_path, ar.started_ts, ar.last_heartbeat_ts, ar.status, ar.notes FROM agent_runs ar WHERE ar.agent_id = %s ORDER BY ar.started_ts DESC LIMIT 10`), watercooler activity (`SELECT wm.id, wm.kind, wm.content, wm.meta, wm.occurred_ts FROM watercooler_messages wm WHERE wm.from_agent_id = %s ORDER BY wm.occurred_ts DESC LIMIT 50`), subscriptions using UNION ALL across all subscription tables, linked A/T/S items via microlog link tables, and agent runtime state from `agent_runtime_state` table.

**Parser Integration:** The parser uses `AGENT_TREE_FIELD_CONFIGS` with dynamic field types for status and role (`role_{status}`, `status_{status}`). It implements the "ONE table" approach with all data in a single `render_flexible_table()` call. The parser handles datetime serialization, JSON meta parsing, error states with hints, and conditional rendering based on NO_FLAGS configuration including 'header', 'desc', 'icon', 'agent', 'status', 'role', 'timestamp', 'session', 'activity', 'meta', 'state', 'runs'.

**Error Handling:** The system includes comprehensive error handling for not found agents (`{"error": "not_found", "hint": f"agent {agent_id}"}`), database connection issues, and JSON serialization problems. Errors are formatted through the parser system with proper icons and styling.

**Data Processing:** The system includes automatic datetime serialization for JSON output, JSON meta parsing for watercooler messages, and comprehensive data validation. All datetime objects are converted to ISO format strings for proper JSON serialization.

**Output Format:** Returns structured JSON with success/error states, agent object, deep_mode flag, and optional deep mode data arrays. The parser transforms this into formatted tables using the table rendering system with proper icons, labels, and styling through the configuration system (`icon.ini`, `label.ini`, `table.ini`).
---
# agent-id-parameter
## description
Required agent ID parameter to specify which agent to retrieve.
## summary
The --agent-id flag specifies the unique identifier of the agent to retrieve comprehensive information for. This must be a valid agent ID that exists in the agents table.
## full_text
The --agent-id flag is implemented as a required argument in the argparse configuration (`parser.add_argument("--agent-id", type=int, required=True, help="Agent ID to retrieve")`).

**Parameter Processing:** The parameter is passed to the `op_tree()` function and used in the main agent query (`WHERE a.id = %s`).

**Error Handling:** If the agent ID is not found, the system returns a structured error response (`{"error": "not_found", "hint": f"agent {agent_id}"}`) which is then processed by the parser to display a user-friendly error message with the specific agent ID that was not found.
---
# deep-mode
## description
Include comprehensive activity logs, subscriptions, and relationship data.
## summary
Adds extensive additional data including agent runs, watercooler activity, subscriptions, linked items, and runtime state through five additional database queries.
## full_text
Deep mode implements comprehensive data retrieval through five additional queries executed within the same cursor context.

**Agent Runs Query:** The agent runs query (`SELECT ar.id, ar.session_id, ar.prompt, ar.model, ar.log_path, ar.started_ts, ar.last_heartbeat_ts, ar.status, ar.notes FROM agent_runs ar WHERE ar.agent_id = %s ORDER BY ar.started_ts DESC LIMIT 10`) retrieves execution history.

**Watercooler Activity Query:** The watercooler activity query joins `watercooler_messages` with `work_dockets` to get the last 50 messages with full content and metadata.

**Subscriptions Query:** The subscriptions query uses UNION ALL across `subscription_ask`, `subscription_task`, `subscription_step`, and `subscription_sidecar` tables.

**Linked Items Query:** The linked items query joins microlog link tables (`wc_microlog_link_ask`, `wc_microlog_link_task`, `wc_microlog_link_step`) with `watercooler_messages` to get the last 30 linked A/T/S items.

**Agent State Query:** The agent state query retrieves runtime state from `agent_runtime_state` table.

All results are added to the response object and processed by the parser to display summary counts and indicators.
---
# agent-runs
## description
Agent execution history and session details.
## summary
Shows recent agent runs with session information, prompts, models, and execution status from the agent_runs table.
## full_text
Agent runs represent individual execution sessions stored in the `agent_runs` table.

**Query Details:** The deep mode query retrieves the last 10 runs ordered by `started_ts DESC` with fields including `ar.id, ar.session_id, ar.prompt, ar.model, ar.log_path, ar.started_ts, ar.last_heartbeat_ts, ar.status, ar.notes`.

**Data Processing:** The results are stored in the `agent_runs` array and processed by the parser to display a summary count (e.g., "5 recent runs").

**Use Cases:** This provides insight into the agent's execution patterns, model usage, and session management across different runs.
---
# watercooler-activity
## description
Recent watercooler messages and communication activity.
## summary
Shows the last 50 watercooler messages posted by the agent with content and metadata from the watercooler_messages table.
## full_text
Watercooler activity is retrieved through a query against the `watercooler_messages` table.

**Query Structure:** `SELECT wm.id, wm.kind, wm.content, wm.meta, wm.occurred_ts FROM watercooler_messages wm WHERE wm.from_agent_id = %s ORDER BY wm.occurred_ts DESC LIMIT 50`

**Data Included:** The query includes message content, metadata (parsed as JSON), and timestamps.

**Processing:** The results are stored in the `activities` array and processed by the parser to display a summary count (e.g., "25 recent activities").

**Use Cases:** This provides comprehensive insight into the agent's communication patterns and logging activity.
---
# subscriptions
## description
Active subscriptions to asks, tasks, steps, and sidecar files.
## summary
Shows all active subscriptions across different subscription tables using UNION ALL queries.
## full_text
Subscriptions are retrieved through a complex UNION ALL query across four subscription tables: `subscription_ask`, `subscription_task`, `subscription_step`, and `subscription_sidecar`.

**Table Joins:** Each subquery joins with its respective target table (asks, tasks, steps, sidecar_files) to get target titles and statuses.

**Query Structure:** The query structure includes `'ask' as type, sa.ask_id as target_id, sa.active, sa.last_seen_ts, a.title as target_title, a.status as target_status` for each subscription type.

**Data Processing:** Results are ordered by `last_seen_ts DESC` and stored in the `subscriptions` array.

**Display:** The parser processes this to display a summary count (e.g., "12 active subscriptions") and provides insight into what the agent is actively monitoring across the A/T/S hierarchy.
---
# linked-items
## description
A/T/S items that the agent has logged watercooler messages to.
## summary
Shows asks, tasks, and steps that the agent has posted linked micrologs about via the microlog linking system.
## full_text
Linked items are retrieved through a UNION ALL query that joins microlog link tables (`wc_microlog_link_ask`, `wc_microlog_link_task`, `wc_microlog_link_step`) with `watercooler_messages` and their respective target tables.

**Query Structure:** The query structure includes `'ask' as type, wla.ask_id as target_id, a.title as target_title, a.status as target_status, wm.occurred_ts, wm.content, wm.meta` for each item type.

**Data Processing:** Results are ordered by `occurred_ts DESC` and limited to 30 items.

**Use Cases:** The query provides insight into what work items the agent has been actively engaged with by showing the actual messages and metadata associated with each linked A/T/S item.

**Display:** The parser displays a summary count (e.g., "8 linked items") representing the agent's work engagement patterns.
---
# agent-state
## description
Runtime state information if available.
## summary
Shows current runtime state including mode, latch status, fail count, and validation info from the agent_runtime_state table.
## full_text
Agent state is retrieved from the `agent_runtime_state` table using the query `SELECT mode, latch, fail_count, last_cycle_ts, last_validation FROM agent_runtime_state WHERE agent_id = %s`.

**Data Content:** This table contains runtime operational data including the agent's current mode, latch status, failure count, last cycle timestamp, and last validation information.

**Query Behavior:** The query is optional and only returns data if the agent has runtime state records.

**Processing:** The results are stored in the `agent_state` object and processed by the parser to display a simple indicator (e.g., "Runtime state available") when state data is present.

**Use Cases:** This provides insight into the agent's current operational status and health metrics.
---
# error-handling
## description
Comprehensive error handling for invalid agent IDs and database issues.
## summary
Returns clear error messages for not found agents and database connection issues through structured error responses.
## full_text
The agent-tree command implements comprehensive error handling through structured error responses.

**Not Found Errors:** When an agent ID is not found, the system returns `{"error": "not_found", "hint": f"agent {agent_id}"}` which includes both the error type and the specific agent ID that was not found.

**Database Errors:** Database connection issues are handled through try-catch blocks around the database operations.

**Parser Integration:** The parser processes these error responses using the `render_flexible_table()` function with error field configurations, displaying user-friendly error messages with proper icons and styling.

**Additional Error Handling:** The error handling includes JSON serialization error handling for metadata parsing and datetime conversion error handling for timestamp processing.

**Consistent Formatting:** All errors are formatted consistently through the parser system architecture.
---
