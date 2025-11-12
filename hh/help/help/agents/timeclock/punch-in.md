# punch-in
## description
Activate an agent session with deterministic persona naming.
## summary
Activates an inactive agent by validating identity with badge timestamp, generating a deterministic persona name, updating the agent profile, and setting status to active. Uses MD5 hash of badge timestamp as seed for consistent persona name generation.
## full_text
The punch-in command implements agent session activation through the parser system architecture. It consists of a data source script (`tools/agents/punch_in.py`) that generates JSON data and a parser module (`tools/agents/parse_timeclock_punch.py`) that formats the output using `render_flexible_table()` with shared logic for both punch operations.

**Database Architecture:** The command performs identity validation against the `agents` table using both `agent_id` and `badge_ts` parameters. It then updates the `agent_profiles` table with deterministic persona information and modifies the `agents` table to set status to 'active' and update the `agent_key` field.

**Identity Validation:** The system validates agent identity using `validate_agent_identity()` which queries `SELECT id, role, badge_ts, status FROM agents WHERE id=%s AND badge_ts=%s`. This ensures only the correct agent with the matching badge timestamp can be activated.

**Deterministic Persona Naming:** The system implements `pick_persona_name_from_badge_ts()` which creates an MD5 hash of the badge timestamp, uses the first 8 hex characters as a random seed, and selects a name from `tools/timeclock/persona_names.txt`. The selected name is combined with the agent's role for uniqueness (e.g., "Alice worker").

**Profile Management:** The system performs an upsert operation on `agent_profiles` table. If a profile exists, it updates the `display_name`. If not, it creates a new profile with `display_name`, `country` (defaults to "US"), `lineage_key` (format: "{role}:{badge_ts[:10]}"), `generation` (defaults to 1), and `persona_json` (JSON-encoded display name).

**Agent Key Update:** The system updates the `agent_key` field in the `agents` table with the newly generated display name using `UPDATE agents SET agent_key=%s WHERE id=%s`. This ensures the agent's identifier reflects the current persona name.

**Status Management:** The command updates the `agents` table by changing `status` from 'inactive' to 'active' using `UPDATE agents SET status='active' WHERE id=%s`. All operations are wrapped in a database transaction with rollback on error.

**Error Handling:** The system includes comprehensive error handling for invalid identity (`{"error": "identity not found"}`), already active agents (`{"error": "agent already active"}`), and database transaction failures. Errors are formatted through the parser system with proper icons and styling.

**Parser Integration:** The parser uses `PUNCH_FIELD_CONFIGS` with dynamic field types for status (`status_{status_value}`). It implements shared logic through `_render_punch_parser()` for both punch-in and punch-out operations, displaying success status, agent name, agent ID, and current status. The parser is located in `tools/agents/parse_timeclock_punch.py` and handles both punch operations with the same formatting logic.

**Transaction Safety:** All database operations are wrapped in a database transaction with `conn.begin()`, `conn.commit()`, and `conn.rollback()` on error. This ensures atomicity and data consistency across profile updates, agent key changes, and status transitions.

**Data Validation:** The system includes comprehensive validation for agent identity (both agent_id and badge_ts must match), status preconditions (agent must be inactive), and database operation success. All validation failures result in structured error responses.

**Output Format:** Returns structured JSON with success/error states, agent information, and status. The parser transforms this into formatted tables using the table rendering system with proper icons, labels, and styling through the configuration system (`icon.ini`, `label.ini`, `table.ini`).
---
# agent-id-parameter
## description
Required agent ID parameter to specify which agent to activate.
## summary
The --agent-id flag specifies the unique identifier of the agent to activate. This must be a valid agent ID that exists in the agents table.
## full_text
The --agent-id flag is implemented as a required argument in the argparse configuration (`parser.add_argument("--agent-id", type=int, required=True, help="Agent ID to activate")`). The parameter is passed to the `cmd_punch_in()` function and used in the identity validation query (`WHERE id=%s AND badge_ts=%s`). The agent ID must exist in the agents table and must be in 'inactive' status to be eligible for punch-in. If the agent ID is not found or doesn't match the badge timestamp, the system returns an identity validation error.
---
# badge-ts-parameter
## description
Required badge timestamp parameter for identity validation.
## summary
The --badge-ts flag provides the badge timestamp used for identity validation and deterministic persona name generation.
## full_text
The --badge-ts flag is implemented as a required argument in the argparse configuration (`parser.add_argument("--badge-ts", required=True, help="Badge timestamp")`). This timestamp serves two critical functions: identity validation (must match the stored badge_ts in the agents table) and deterministic persona name generation. The timestamp is converted to an MD5 hash, with the first 8 hex characters used as a random seed to ensure the same badge timestamp always generates the same persona name. This provides consistency across multiple punch-in operations for the same agent while maintaining uniqueness across different agents.
---
# deterministic-naming
## description
Deterministic persona name generation based on badge timestamp.
## summary
Generates consistent persona names using MD5 hash of badge timestamp as random seed, selecting from predefined name list and combining with agent role.
## full_text
The deterministic naming system ensures that the same badge timestamp always generates the same persona name, providing consistency across multiple punch-in operations. The process involves several steps:

**Hash Generation:** The badge timestamp is converted to an MD5 hash using `hashlib.md5(badge_ts.encode()).hexdigest()`.

**Seed Creation:** The first 8 hex characters of the hash are converted to an integer and used as a random seed with `random.seed(int(seed[:8], 16))`.

**Name Selection:** The system loads persona names from `tools/timeclock/persona_names.txt` (with fallback to default names: Alice, Bob, Charlie, Diana, Eve, Frank, Grace, Henry) and uses the seeded random number generator to select one name.

**Role Combination:** The selected name is combined with the agent's role (e.g., "Alice worker", "Bob apprentice") to ensure uniqueness across different agent types.

**Consistency Guarantee:** The same badge timestamp will always produce the same persona name, while different timestamps will produce different names, providing both consistency and uniqueness.
---
# profile-management
## description
Agent profile creation and update during punch-in process.
## summary
Manages agent profile data including display name, country, lineage key, generation, and persona JSON through upsert operations.
## full_text
The profile management system handles agent profile data through database upsert operations on the `agent_profiles` table. The process includes several key components:

**Profile Existence Check:** The system queries `SELECT 1 FROM agent_profiles WHERE agent_id=%s` to determine if a profile already exists for the agent.

**Update Operation:** If a profile exists, it updates the `display_name` field with the newly generated deterministic name using `UPDATE agent_profiles SET display_name=%s WHERE agent_id=%s`.

**Insert Operation:** If no profile exists, it creates a new profile with comprehensive data: `INSERT INTO agent_profiles (agent_id, display_name, country, lineage_key, generation, persona_json) VALUES (%s,%s,%s,%s,%s,%s)`.

**Data Fields:** The profile includes `display_name` (deterministic persona name), `country` (defaults to "US"), `lineage_key` (format: "{role}:{badge_ts[:10]}"), `generation` (defaults to 1), and `persona_json` (JSON-encoded display name for additional metadata).

**Transaction Safety:** All profile operations are wrapped in database transactions with automatic rollback on error, ensuring data consistency.
---
# status-transition
## description
Agent status transition from inactive to active during punch-in.
## summary
Transitions agent status from 'inactive' to 'active' and updates agent_key with the generated display name.
## full_text
The status transition system manages the agent's operational state through controlled database updates. The process ensures proper state management and data consistency:

**Pre-conditions:** The agent must be in 'inactive' status to be eligible for punch-in. The system validates this condition before proceeding with the activation process.

**Agent Key Update:** The system updates the `agent_key` field in the `agents` table with the newly generated display name using `UPDATE agents SET agent_key=%s WHERE id=%s`. This ensures the agent's identifier reflects the current persona name.

**Status Activation:** The agent status is changed from 'inactive' to 'active' using `UPDATE agents SET status='active' WHERE id=%s`. This transition makes the agent available for operational tasks and system interactions.

**Transaction Management:** Both the agent_key update and status change are performed within the same database transaction, ensuring atomicity. If any operation fails, the entire transaction is rolled back to maintain data consistency.

**Validation:** The system includes validation to prevent punch-in of already active agents, returning an error if the agent is not in the expected 'inactive' state.
---
# error-handling
## description
Comprehensive error handling for punch-in operations.
## summary
Handles identity validation errors, status conflicts, and database transaction failures with structured error responses.
## full_text
The punch-in command implements comprehensive error handling through structured error responses and transaction management:

**Identity Validation Errors:** When an agent ID and badge timestamp combination is not found, the system returns `{"error": "identity not found"}`. This occurs when the agent doesn't exist or the badge timestamp doesn't match the stored value.

**Status Conflict Errors:** If an agent is already active, the system returns `{"error": "agent already active"}`. This prevents duplicate activations and ensures proper state management.

**Database Transaction Errors:** All database operations are wrapped in try-catch blocks with automatic rollback on error. If any database operation fails, the transaction is rolled back using `conn.rollback()` and an error response is returned with the exception details.

**Parser Integration:** The parser processes error responses using `render_flexible_table()` with error field configurations, displaying user-friendly error messages with proper icons and styling.

**Consistent Formatting:** All errors are formatted consistently through the parser system architecture, ensuring uniform error presentation across all punch operations.
---
