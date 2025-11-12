# agent-management
## summary
The agent management system provides comprehensive administrative tools for managing the complete agent lifecycle from creation to archival. It includes safe purge operations with dry-run capabilities, data cleanup procedures, and system maintenance functions. All operations are designed with transaction safety and rollback capabilities to prevent data loss. The system provides detailed operation reporting, audit trails, and comprehensive error handling to ensure system integrity and compliance. Critical operations require explicit confirmation flags to prevent accidental data loss while maintaining full operational transparency.
## description
Administrative operations for agent archival, data cleanup, and system maintenance.
## full_text
The agent_management system provides comprehensive administrative tools for managing the agent lifecycle and maintaining system integrity through specialized commands that implement the parser system architecture with data source scripts generating JSON and parser modules formatting output using `render_flexible_table()`.

**Core Commands:**
- `agent-purge` - Archive all agents (excluding operators) and clean operational state with dry-run capabilities and comprehensive operation reporting

**Database Architecture:** All commands use PyMySQL with DictCursor for database operations, loading connection parameters from `.henhouse.cnf` files. The system implements comprehensive transaction management with rollback capabilities for data consistency and safety.

**Agent Purge Implementation:** The purge operation performs comprehensive archival of all active agents while preserving historical data. The main query retrieves active agents using: `SELECT id, agent_key, role, status, created_at, terminated, gate_status, gate_started_ts, session_id FROM agents WHERE status = 'active' AND role != 'operator' ORDER BY created_at DESC`.

**Data Preservation Strategy:** The system preserves all historical data including agents, profiles, sessions, watercooler_messages, and related records while cleaning operational state. This includes removing entries from `watercooler_last_seen` and active docket subscriptions to prevent re-spawning while maintaining complete audit trails.

**Transaction Safety:** All operations use database transactions with comprehensive error handling and rollback capabilities. The system implements proper transaction management to ensure data consistency and prevent partial operations that could leave the system in an inconsistent state.

**Dry-Run Capabilities:** The purge operation includes comprehensive dry-run functionality that simulates the entire operation without making changes. This provides detailed reporting of what would be affected, including agent counts, data preservation details, and cleanup operations.

**Comprehensive Reporting:** The system provides detailed operation reporting including agent counts, data preservation statistics, cleanup operations performed, and transaction status. All operations are logged with timestamps and detailed information for audit and troubleshooting purposes.

**Error Handling:** The system includes comprehensive error handling for database connection issues, transaction failures, and data integrity problems. Errors are formatted through the parser system with proper icons and styling, providing clear feedback about operation status and any issues encountered.

**Security and Validation:** All operations include comprehensive validation and safety checks. Critical operations like agent-purge require explicit confirmation flags to prevent accidental data loss and include multiple validation steps to ensure system integrity.

**Parser Integration:** The purge command uses field configurations and implements the "ONE table" approach with all data in single `render_flexible_table()` calls. The parser handles datetime serialization, error states, and conditional rendering based on NO_FLAGS configuration.

**Output Format:** The command returns structured JSON with success/error states, operation details, and comprehensive reporting data. The parser transforms this into formatted tables using the table rendering system with proper icons, labels, and styling through the configuration system (`icon.ini`, `label.ini`, `table.ini`).

**System Integration:** The management system integrates with the broader agent ecosystem, providing administrative capabilities that complement the information and timeclock systems while maintaining data integrity and system consistency.
---
