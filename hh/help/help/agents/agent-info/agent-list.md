# agent-list
## description
List agents with comprehensive filtering and deep mode options for detailed agent management.
## summary
Lists all agents with advanced filtering capabilities including role, status, work docket, and A/T/S relationships. Deep mode provides extensive additional details like recent activity, subscriptions, and session information. Results are ordered by creation date (newest first) and default to active agents only unless status is explicitly specified. Supports pagination with --limit option.
## full_text
The agent-list command implements comprehensive agent listing through the parser system architecture. It consists of a data source script (`tools/agents/agent_list.py`) that generates JSON data and a parser module (`tools/agents/parse_agent_list.py`) that formats the output using `render_flexible_table()` with the "ONE table" approach.

**Database Architecture:** The main query performs a SELECT on the `agents` table with LEFT JOINs to `agent_profiles` table. The query structure includes DISTINCT selection to handle potential duplicates and supports complex WHERE clause construction based on filter parameters. The base query is: `SELECT DISTINCT a.id, a.agent_key, a.role, a.status, a.created_at, a.terminated, a.gate_status, a.gate_started_ts, a.session_id, ap.display_name, ap.country, ap.lineage_key, ap.generation FROM agents a LEFT JOIN agent_profiles ap ON a.id = ap.agent_id`.

**Filtering Implementation:** The system builds dynamic WHERE conditions using a conditions array and params list. Role filtering uses `a.role = %s`, status filtering uses `a.status = %s` (defaulting to 'active' if not specified), and A/T/S relationship filtering uses EXISTS subqueries against `watercooler_messages` and the respective link tables (`wc_microlog_link_ask`, `wc_microlog_link_task`, `wc_microlog_link_step`). The system supports complex filtering combinations and maintains parameterized query safety.

**Deep Mode Architecture:** When `--deep` flag is used, the system creates a separate cursor context (`with conn.cursor() as deep_cursor:`) to avoid cursor closure issues. It performs two additional queries for each agent: watercooler activity query (`SELECT wm.id, wm.kind, wm.content, wm.meta, wm.occurred_ts FROM watercooler_messages wm WHERE wm.from_agent_id = %s ORDER BY wm.occurred_ts DESC LIMIT 10`) and subscription count query using UNION ALL across `subscription_ask`, `subscription_task`, `subscription_step`, and `subscription_sidecar` tables.

**Parser Integration:** The parser uses `AGENT_LIST_FIELD_CONFIGS` with dynamic field types for status and role (`role_{status}`, `status_{status}`). It implements the "ONE table" approach with all data in a single `render_flexible_table()` call. The parser handles datetime serialization, error states, and conditional rendering based on NO_FLAGS configuration including 'header', 'desc', 'icon', 'agent', 'status', 'role', 'timestamp', 'session', 'activity', 'meta'.

**Error Handling:** The system includes comprehensive error handling for database connection issues, query failures, and JSON serialization problems. Errors are formatted through the parser system with proper icons and styling.

**Pagination Support:** The system supports `--limit` parameter for pagination, applied post-processing using Python list slicing (`result["agents"] = result["agents"][:args.limit]`) after all filtering and sorting operations.

**Output Format:** Returns structured JSON with success/error states, agents array, count, filters object, and deep_mode flag. The parser transforms this into formatted tables using the table rendering system with proper icons, labels, and styling through the configuration system (`icon.ini`, `label.ini`, `table.ini`).
---
# role-filter
## description
Filter agents by their assigned role.
## summary
Shows only agents with the specified role (apprentice, worker, reworker, architect, librarian, operator). This filter is applied as a WHERE clause in the SQL query.
## full_text
The --role flag implements role-based filtering through dynamic WHERE clause construction. The system adds `a.role = %s` to the conditions array and appends the role parameter to the params list. This filter is applied directly to the main agents query, ensuring only agents with the specified role are returned. Common role values include 'apprentice', 'worker', 'reworker', 'architect', 'librarian', and 'operator'. The filter integrates with the existing query structure and works in combination with other filters like status and A/T/S relationships.
---
# status-filter
## description
Filter agents by their current operational status.
## summary
Shows only agents with the specified status (active or inactive). By default, only active agents are shown unless this flag is explicitly used.
## full_text
The --status flag implements status-based filtering with a default behavior. When no status is specified, the system automatically adds `a.status = 'active'` to the WHERE clause. When explicitly provided, it adds `a.status = %s` with the specified status value. This ensures backward compatibility while allowing explicit inactive agent queries. The status values are validated against the database schema and the filter integrates with the dynamic WHERE clause construction system.
---
# work-docket-filter
## description
Show agents who have logged to a specific work docket.
## summary
Filters to show only agents who have posted watercooler messages to the specified work docket using an EXISTS subquery.
## full_text
The filtering system uses EXISTS subqueries against microlog link tables to find agents who have logged activity to specific work items. This approach ensures only agents who have actually posted messages to the specified work items are included, providing activity-based filtering rather than just assignment-based filtering.
---
# ask-filter
## description
Show agents who have logged to a specific ask.
## summary
Filters to show only agents who have posted micrologs linked to the specified ask via the microlog linking system.
## full_text
The --ask-id flag implements ask-based filtering through an EXISTS subquery that joins `watercooler_messages` with `wc_microlog_link_ask`. The query structure is `EXISTS (SELECT 1 FROM wc_microlog_link_ask wla WHERE wla.watercooler_message_id = wm.id AND wla.target_id = %s)`. This ensures only agents who have posted messages specifically linked to the target ask are included. The filter leverages the microlog linking system architecture and integrates with the dynamic WHERE clause construction, allowing for precise activity-based filtering across the A/T/S hierarchy.
---
# task-filter
## description
Show agents who have logged to a specific task.
## summary
Filters to show only agents who have posted micrologs linked to the specified task via the microlog linking system.
## full_text
The --task-id flag implements task-based filtering through an EXISTS subquery that joins `watercooler_messages` with `wc_microlog_link_task`. The query structure is `EXISTS (SELECT 1 FROM wc_microlog_link_task wlt WHERE wlt.watercooler_message_id = wm.id AND wlt.target_id = %s)`. This ensures only agents who have posted messages specifically linked to the target task are included. The filter leverages the microlog linking system architecture and integrates with the dynamic WHERE clause construction, allowing for precise activity-based filtering across the A/T/S hierarchy.
---
# step-filter
## description
Show agents who have logged to a specific step.
## summary
Filters to show only agents who have posted micrologs linked to the specified step via the microlog linking system.
## full_text
The --step-id flag implements step-based filtering through an EXISTS subquery that joins `watercooler_messages` with `wc_microlog_link_step`. The query structure is `EXISTS (SELECT 1 FROM wc_microlog_link_step wls WHERE wls.watercooler_message_id = wm.id AND wls.target_id = %s)`. This ensures only agents who have posted messages specifically linked to the target step are included. The filter leverages the microlog linking system architecture and integrates with the dynamic WHERE clause construction, allowing for precise activity-based filtering across the A/T/S hierarchy.
---
# deep-mode
## description
Include comprehensive activity and subscription details.
## summary
Adds recent watercooler activity, subscription counts, and session information to each agent through additional database queries.
## full_text
Deep mode implements a separate cursor context (`with conn.cursor() as deep_cursor:`) to avoid cursor closure issues. It performs two additional queries per agent: watercooler activity query (`SELECT wm.id, wm.kind, wm.content, wm.meta, wm.occurred_ts FROM watercooler_messages wm WHERE wm.from_agent_id = %s ORDER BY wm.occurred_ts DESC LIMIT 10`) and subscription count query using UNION ALL across all 8 subscription tables. The results are added to each agent object as `recent_activity` and `subscription_count` fields, which are then processed by the parser to display activity summaries and subscription counts in the formatted output.
---
# limit-option
## description
Limit the number of results returned.
## summary
Restricts the output to the specified number of agents after all filtering and sorting operations.
## full_text
The --limit flag is applied post-processing in the main function after the database query execution and before JSON output. It uses Python list slicing (`result["agents"] = result["agents"][:args.limit]`) to truncate the agents array and updates the count field accordingly. This approach ensures the limit is applied after all filtering, sorting, and data processing, making it useful for pagination or performance optimization when only a subset of matching agents is needed. The limit is applied to the final result set, not individual queries.
---
