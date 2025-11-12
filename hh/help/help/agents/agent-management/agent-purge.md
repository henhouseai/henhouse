# agent-purge
## description
Archive all agents from the active system and clean operational state.
## summary
Archives all active agents (excluding operators) by setting them to inactive and terminated status, while cleaning operational state including subscriptions and watercooler activity. Preserves all historical data but prevents agent re-spawning. Supports dry-run mode for safe preview of operations.
## full_text
The agent-purge command implements comprehensive agent archival through the parser system architecture. It consists of a data source script (`tools/agents/agent_purge.py`) that generates JSON data and a parser module (`tools/agents/parse_agent_purge.py`) that formats the output using `render_flexible_table()` with detailed operation reporting.

**Database Architecture:** The command performs a multi-step archival process across multiple tables. It first queries active agents using `SELECT a.id, a.agent_key, a.role, a.status, a.created_at, ap.display_name FROM agents a LEFT JOIN agent_profiles ap ON a.id = ap.agent_id WHERE a.status = 'active' AND a.role != 'operator' ORDER BY a.created_at DESC`.

**Agent Archival Process:** The system updates all active agents (excluding operators) using `UPDATE agents SET status='inactive', \`terminated\`=1 WHERE status='active' AND role != 'operator'`. This dual update ensures agents are both deactivated and marked as terminated to prevent re-spawning.

**Subscription Cleanup:** The system performs comprehensive subscription cleanup across eight subscription tables: `subscription_ask`, `subscription_task`, `subscription_step`, `subscription_sidecar`, `subscription_keyword`, `subscription_docket`, `subscription_agent`, and `subscription_operator`. Each table is completely cleared using `DELETE FROM {table}` operations.

**Watercooler State Cleanup:** The system cleans operational watercooler state using `DELETE FROM watercooler_last_seen` to remove all last-seen tracking data while preserving historical watercooler messages.

**Transaction Management:** All operations are wrapped in a database transaction with `conn.begin()`, `conn.commit()`, and `conn.rollback()` on error. This ensures atomicity and data consistency across the entire archival process.

**Dry Run Mode:** The system supports comprehensive dry-run functionality that previews all operations without making changes. It counts affected rows in each table and provides detailed operation descriptions for safe review before execution.

**Safety Mechanisms:** The command requires explicit `--confirm` flag for actual purge operations (not dry runs) and provides clear error messages when confirmation is missing. This prevents accidental data loss.

**Parser Integration:** The parser uses `AGENT_PURGE_FIELD_CONFIGS` with field types for success, message, agents_affected, dry_run, operation, affected_rows, and description. It renders header information followed by detailed operation breakdowns with proper icons and styling.

**Output Format:** Returns structured JSON with success/error states, operation details, affected row counts, and comprehensive operation descriptions. The parser transforms this into formatted tables using the table rendering system with proper icons, labels, and styling through the configuration system (`icon.ini`, `label.ini`, `table.ini`).
---
# dry-run-mode
## description
Preview mode that shows what would be purged without making actual changes.
## summary
The --dry-run flag enables safe preview of all purge operations, showing affected agents and subscription counts without modifying any data.
## full_text
The dry-run mode provides comprehensive preview functionality for safe operation planning and verification. The system implements several key features:

**Agent Preview:** The system queries and displays all active agents that would be affected, including their ID, agent_key, role, status, creation date, and display name. This provides complete visibility into which agents will be archived.

**Operation Simulation:** The system simulates all database operations without executing them, providing detailed descriptions of what would be performed. This includes the main agent archival query and all subscription cleanup operations.

**Count Analysis:** For each subscription table, the system executes `SELECT COUNT(*) as count FROM {table}` to determine how many records would be affected. This provides precise impact assessment before execution.

**Operation Details:** Each simulated operation includes the exact SQL query, affected row count, and human-readable description. This allows operators to understand the full scope of the purge operation.

**Safety Validation:** Dry-run mode requires no confirmation flags and can be executed safely by any user. It provides complete transparency into the purge process without risk of data modification.

**Output Formatting:** The parser renders dry-run results with clear "DRY RUN - No changes made" indicators and detailed operation breakdowns, making it easy to review and understand the planned operations.
---
# confirmation-requirement
## description
Safety mechanism requiring explicit confirmation for actual purge operations.
## summary
The --confirm flag is required for actual purge operations to prevent accidental data loss, with clear error messages when confirmation is missing.
## full_text
The confirmation requirement system implements critical safety mechanisms to prevent accidental agent archival and data loss:

**Mandatory Confirmation:** The system requires the `--confirm` flag for all actual purge operations (excluding dry runs). This prevents accidental execution of destructive operations.

**Error Handling:** When confirmation is missing, the system outputs clear error messages: "Error: Purge operation requires --confirm flag for safety" and "Use --dry-run to see what would be affected first". This guides users to the safe preview mode.

**Dry Run Exception:** Dry-run operations do not require confirmation, allowing safe exploration and planning without risk of data modification.

**Argument Validation:** The confirmation check is implemented in the main function with `if not args.dry_run and not args.confirm:` logic, ensuring both flags are properly validated before execution.

**User Guidance:** The error messages provide clear guidance on using `--dry-run` first to understand the impact before proceeding with the actual purge operation.

**Safety Culture:** This mechanism enforces a safety-first approach to destructive operations, requiring deliberate confirmation rather than accidental execution.
---
# agent-archival
## description
Process of archiving active agents by setting them to inactive and terminated status.
## summary
Archives all active agents (excluding operators) by updating their status to inactive and setting terminated flag to prevent re-spawning.
## full_text
The agent archival process implements comprehensive agent deactivation with permanent termination marking:

**Agent Selection:** The system identifies all active agents using `SELECT a.id, a.agent_key, a.role, a.status, a.created_at, ap.display_name FROM agents a LEFT JOIN agent_profiles ap ON a.id = ap.agent_id WHERE a.status = 'active' AND a.role != 'operator' ORDER BY a.created_at DESC`.

**Dual Status Update:** The archival process performs a single update operation: `UPDATE agents SET status='inactive', \`terminated\`=1 WHERE status='active' AND role != 'operator'`. This sets both the operational status and termination flag.

**Operator Exclusion:** The system explicitly excludes operators from archival using `role != 'operator'` condition. This ensures system administrators and operators remain active during the purge process.

**Termination Flag:** The `terminated` flag is set to 1 to prevent agent re-spawning. This ensures that archived agents cannot be automatically reactivated by the system.

**Row Count Tracking:** The system tracks the number of affected agents using `cursor.rowcount` and includes this information in the operation details for audit purposes.

**Transaction Safety:** The archival operation is performed within a database transaction, ensuring atomicity. If any subsequent operation fails, the agent archival can be rolled back.

**Historical Preservation:** The archival process preserves all historical data including agent profiles, watercooler messages, and work docket assignments. Only operational state is modified.
---
# subscription-cleanup
## description
Comprehensive cleanup of all subscription tables to remove operational state.
## summary
Clears all subscription tables including ask, task, step, sidecar, keyword, docket, agent, and operator subscriptions to remove operational state.
## full_text
The subscription cleanup process removes all operational subscription data across eight subscription tables:

**Subscription Tables:** The system cleans the following tables: `subscription_ask`, `subscription_task`, `subscription_step`, `subscription_sidecar`, `subscription_keyword`, `subscription_docket`, `subscription_agent`, and `subscription_operator`.

**Complete Cleanup:** Each table is completely cleared using `DELETE FROM {table}` operations. This removes all subscription data regardless of agent or work docket associations.

**Row Count Tracking:** The system tracks affected rows for each table using `cursor.rowcount` and only reports operations that affected data (rows_deleted > 0).

**Operation Documentation:** Each cleanup operation is documented with the exact SQL query, affected row count, and human-readable description for audit purposes.

**Transaction Safety:** All subscription cleanup operations are performed within the same database transaction as agent archival, ensuring atomicity.

**No Work Docket Scoping:** Unlike some other operations, subscription cleanup is not scoped to specific work dockets. It removes all subscription data for all agents, providing complete operational state reset.

**Audit Trail:** The system maintains detailed audit information for each subscription table cleanup, including operation details and affected row counts.
---
# watercooler-cleanup
## description
Cleanup of operational watercooler state while preserving historical messages.
## summary
Removes all watercooler_last_seen records to clean operational state while preserving historical watercooler messages.
## full_text
The watercooler cleanup process removes operational tracking data while preserving historical communication records:

**Targeted Cleanup:** The system specifically targets the `watercooler_last_seen` table using `DELETE FROM watercooler_last_seen` to remove all last-seen tracking data.

**Historical Preservation:** The cleanup process does not affect the `watercooler_messages` table, preserving all historical communication and activity logs.

**Operational State Reset:** By removing last-seen data, the system resets the operational state of all agents in the watercooler system, effectively clearing their online status.

**Row Count Tracking:** The system tracks affected rows using `cursor.rowcount` and includes this information in operation details for audit purposes.

**Transaction Safety:** The watercooler cleanup is performed within the same database transaction as other purge operations, ensuring atomicity.

**Complete Reset:** The cleanup removes all watercooler_last_seen records regardless of agent or work docket associations, providing complete operational state reset.

**Audit Documentation:** The operation is documented with the exact SQL query, affected row count, and human-readable description for audit purposes.
---
# transaction-safety
## description
Database transaction management ensuring atomicity and data consistency.
## summary
All purge operations are wrapped in database transactions with rollback on error to ensure atomicity and data consistency.
## full_text
The transaction safety system ensures data integrity and consistency across all purge operations:

**Transaction Management:** The system uses `conn.begin()` to start a transaction before performing any database operations, ensuring all changes are atomic.

**Rollback on Error:** If any operation fails, the system executes `conn.rollback()` to undo all changes made within the transaction, maintaining data consistency.

**Commit on Success:** Only when all operations complete successfully does the system execute `conn.commit()` to permanently apply all changes.

**Exception Handling:** The system wraps all database operations in try-catch blocks, ensuring that any exception triggers automatic rollback.

**Atomicity Guarantee:** The transaction ensures that either all operations succeed (agent archival, subscription cleanup, watercooler cleanup) or none of them are applied.

**Data Consistency:** This approach prevents partial updates that could leave the system in an inconsistent state, such as archived agents with remaining subscriptions.

**Error Recovery:** If any operation fails, the system can be safely retried without concern for partial state corruption.
---
# operation-reporting
## description
Detailed reporting of all database operations performed during the purge process.
## summary
Comprehensive reporting of all database operations including SQL queries, affected row counts, and human-readable descriptions.
## full_text
The operation reporting system provides detailed audit information for all database operations performed during the purge process:

**Operation Structure:** Each operation is documented with three key pieces of information: the exact SQL query, affected row count, and human-readable description.

**SQL Query Recording:** The system records the exact SQL query executed, including table names and WHERE conditions, for complete auditability.

**Row Count Tracking:** Each operation tracks the number of affected rows using `cursor.rowcount`, providing precise impact measurement.

**Description Generation:** The system generates human-readable descriptions for each operation, such as "Archived 5 active agents (excluding operators)" or "Cleaned 23 subscription_ask records for all agents".

**Operation Ordering:** Operations are reported in the order they were executed, providing a clear sequence of database changes.

**Conditional Reporting:** Only operations that affected data (rows_deleted > 0) are included in the report, avoiding clutter from empty operations.

**Parser Integration:** The parser renders each operation as a separate table with proper formatting, icons, and styling for easy reading.

**Audit Trail:** This comprehensive reporting provides complete audit trail for compliance and troubleshooting purposes.
---
