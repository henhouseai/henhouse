# punch-out
## description
Deactivate an agent session.
## summary
Deactivates an active agent by validating identity with badge timestamp and setting status to inactive. Preserves agent profile data and persona information while making the agent unavailable for operational tasks.
## full_text
The punch-out command implements agent session deactivation through the parser system architecture. It consists of a data source script (`tools/agents/punch_out.py`) that generates JSON data and a parser module (`tools/agents/parse_timeclock_punch.py`) that formats the output using `render_flexible_table()` with shared logic for both punch operations.

**Database Architecture:** The command performs identity validation against the `agents` table using both `agent_id` and `badge_ts` parameters. It then updates the `agents` table to set status to 'inactive' while preserving all agent profile data and persona information.

**Identity Validation:** The system validates agent identity using `validate_agent_identity()` which queries `SELECT id, agent_key, status FROM agents WHERE id=%s AND badge_ts=%s`. This ensures only the correct agent with the matching badge timestamp can be deactivated.

**Status Management:** The command updates the `agents` table by changing `status` from 'active' to 'inactive' using `UPDATE agents SET status='inactive' WHERE id=%s`. Unlike punch-in, punch-out does not modify the `agent_key` or profile data, preserving the agent's persona information.

**Profile Preservation:** The system does not modify the `agent_profiles` table during punch-out, maintaining all persona data, display names, and profile information for potential future punch-in operations.

**Transaction Safety:** All operations are wrapped in a database transaction with rollback on error, ensuring data consistency and proper state management.

**Error Handling:** The system includes comprehensive error handling for invalid identity (`{"error": "identity not found"}`), inactive agents (`{"error": "agent not active"}`), and database transaction failures. Errors are formatted through the parser system with proper icons and styling.

**Parser Integration:** The parser uses `PUNCH_FIELD_CONFIGS` with dynamic field types for status (`status_{status_value}`). It implements shared logic through `_render_punch_parser()` for both punch-in and punch-out operations, displaying success status, agent name, agent ID, and current status. The parser is located in `tools/agents/parse_timeclock_punch.py` and handles both punch operations with the same formatting logic.

**Transaction Safety:** All database operations are wrapped in a database transaction with `conn.begin()`, `conn.commit()`, and `conn.rollback()` on error. This ensures atomicity and data consistency across status transitions.

**Data Validation:** The system includes comprehensive validation for agent identity (both agent_id and badge_ts must match), status preconditions (agent must be active), and database operation success. All validation failures result in structured error responses.

**Profile Preservation:** Unlike punch-in operations, punch-out does not modify the `agent_key` field or any data in the `agent_profiles` table. This preserves the agent's persona information, display name, and profile data for potential future punch-in operations.

**Output Format:** Returns structured JSON with success/error states, agent information, and status. The parser transforms this into formatted tables using the table rendering system with proper icons, labels, and styling through the configuration system (`icon.ini`, `label.ini`, `table.ini`).
---
# agent-id-parameter
## description
Required agent ID parameter to specify which agent to deactivate.
## summary
The --agent-id flag specifies the unique identifier of the agent to deactivate. This must be a valid agent ID that exists in the agents table.
## full_text
The --agent-id flag is implemented as a required argument in the argparse configuration (`parser.add_argument("--agent-id", type=int, required=True, help="Agent ID")`). The parameter is passed to the `cmd_punch_out()` function and used in the identity validation query (`WHERE id=%s AND badge_ts=%s`). The agent ID must exist in the agents table and must be in 'active' status to be eligible for punch-out. If the agent ID is not found or doesn't match the badge timestamp, the system returns an identity validation error.
---
# badge-ts-parameter
## description
Required badge timestamp parameter for identity validation.
## summary
The --badge-ts flag provides the badge timestamp used for identity validation during punch-out operations.
## full_text
The --badge-ts flag is implemented as a required argument in the argparse configuration (`parser.add_argument("--badge-ts", required=True, help="Badge timestamp")`). This timestamp serves as the primary identity validation mechanism, ensuring that only the correct agent with the matching badge timestamp can be deactivated. The timestamp must exactly match the stored `badge_ts` value in the agents table for the specified agent ID. This provides security and prevents unauthorized deactivation of agent sessions.
---
# status-transition
## description
Agent status transition from active to inactive during punch-out.
## summary
Transitions agent status from 'active' to 'inactive' while preserving all agent data and profile information.
## full_text
The status transition system manages the agent's operational state through controlled database updates. The process ensures proper state management while preserving agent data:

**Pre-conditions:** The agent must be in 'active' status to be eligible for punch-out. The system validates this condition before proceeding with the deactivation process.

**Status Deactivation:** The agent status is changed from 'active' to 'inactive' using `UPDATE agents SET status='inactive' WHERE id=%s`. This transition makes the agent unavailable for operational tasks and system interactions.

**Data Preservation:** Unlike punch-in, punch-out does not modify the `agent_key` field or any data in the `agent_profiles` table. This preserves the agent's persona information, display name, and profile data for potential future punch-in operations.

**Transaction Management:** The status change is performed within a database transaction, ensuring atomicity. If the operation fails, the transaction is rolled back to maintain data consistency.

**Validation:** The system includes validation to prevent punch-out of inactive agents, returning an error if the agent is not in the expected 'active' state.
---
# profile-preservation
## description
Preservation of agent profile data during punch-out operations.
## summary
Maintains all agent profile information including display name, persona data, and profile metadata without modification during deactivation.
## full_text
The profile preservation system ensures that agent profile data remains intact during punch-out operations, allowing for seamless reactivation in future punch-in operations:

**No Profile Modifications:** Unlike punch-in operations, punch-out does not perform any updates to the `agent_profiles` table. This preserves all existing profile data including display names, persona information, and metadata.

**Data Retention:** All profile fields are maintained: `display_name` (current persona name), `country`, `lineage_key`, `generation`, and `persona_json`. This ensures that when the agent punches in again, their previous persona information is preserved.

**Consistent Identity:** The `agent_key` field in the `agents` table is not modified during punch-out, maintaining the agent's current persona name and identity across the deactivation process.

**Future Reactivation:** The preserved profile data allows for consistent persona naming when the agent punches in again, as the deterministic naming system will generate the same persona name based on the badge timestamp.

**Data Integrity:** The preservation approach ensures that agent history, persona evolution, and profile metadata remain consistent across multiple punch-in/punch-out cycles.
---
# error-handling
## description
Comprehensive error handling for punch-out operations.
## summary
Handles identity validation errors, status conflicts, and database transaction failures with structured error responses.
## full_text
The punch-out command implements comprehensive error handling through structured error responses and transaction management:

**Identity Validation Errors:** When an agent ID and badge timestamp combination is not found, the system returns `{"error": "identity not found"}`. This occurs when the agent doesn't exist or the badge timestamp doesn't match the stored value.

**Status Conflict Errors:** If an agent is not active, the system returns `{"error": "agent not active"}`. This prevents deactivation of already inactive agents and ensures proper state management.

**Database Transaction Errors:** All database operations are wrapped in try-catch blocks with automatic rollback on error. If any database operation fails, the transaction is rolled back using `conn.rollback()` and an error response is returned with the exception details.

**Parser Integration:** The parser processes error responses using `render_flexible_table()` with error field configurations, displaying user-friendly error messages with proper icons and styling.

**Consistent Formatting:** All errors are formatted consistently through the parser system architecture, ensuring uniform error presentation across all punch operations.
---
# session-lifecycle
## description
Agent session lifecycle management through punch-in/punch-out operations.
## summary
Manages complete agent session lifecycle from activation through deactivation with proper state transitions and data management.
## full_text
The session lifecycle management system provides complete agent session control through coordinated punch-in and punch-out operations:

**Session Activation:** Punch-in operations activate agents by validating identity, generating deterministic persona names, updating profiles, and setting status to 'active'. This makes agents available for operational tasks and system interactions.

**Session Deactivation:** Punch-out operations deactivate agents by validating identity and setting status to 'inactive'. This preserves all agent data while making agents unavailable for operational tasks.

**State Consistency:** The system ensures consistent state management by validating agent status before operations (inactive for punch-in, active for punch-out) and maintaining proper state transitions.

**Data Persistence:** Agent profile data, persona information, and identity details are preserved across the entire session lifecycle, allowing for consistent agent behavior and identity management.

**Transaction Safety:** All operations are wrapped in database transactions with rollback capabilities, ensuring data integrity and consistent state management across the session lifecycle.

**Error Recovery:** Comprehensive error handling ensures that failed operations do not leave the system in an inconsistent state, with automatic rollback and clear error reporting.
---
