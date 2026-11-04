# timeclock
## description
Agent session management with punch-in/punch-out operations and profile management.
## summary
The timeclock system manages agent work sessions through secure punch-in and punch-out operations with deterministic persona naming based on badge timestamps. It provides comprehensive profile management, identity validation, and session tracking with full audit trails. The system integrates with the database to maintain agent status, work history, and activity logs while ensuring data consistency through transaction management. All operations include proper error handling and security controls to prevent unauthorized access and maintain system integrity.
## full_text
The timeclock system provides comprehensive time tracking and attendance management capabilities for monitoring agent work hours and activity through specialized commands that implement the parser system architecture with data source scripts generating JSON and parser modules formatting output using `render_flexible_table()`.

**Core Commands:**
- `punch-in` - Activate agent sessions with deterministic persona naming and profile management
- `punch-out` - Deactivate agent sessions while preserving all profile data and historical information

**Database Architecture:** All commands use PyMySQL with DictCursor for database operations, loading connection parameters from `.henhouse.cnf` files. The system implements comprehensive identity validation and profile management with proper transaction handling for data consistency.

**Punch-In Implementation:** The punch-in operation activates agent sessions with deterministic persona naming based on badge timestamps. The system loads persona names from `tools/timeclock/persona_names.txt` and uses MD5 hash of badge timestamps as deterministic seed for persona selection using: `hashlib.md5(f"{badge_ts}_{role}".encode()).hexdigest()`.

**Deterministic Persona Naming:** The system implements consistent agent naming based on MD5 hash of badge timestamps combined with role information. This ensures the same badge timestamp always produces the same persona name, providing deterministic behavior across system restarts and operations.

**Identity Validation:** All operations include comprehensive identity validation using badge timestamps. The validation query uses: `SELECT id, agent_key, status FROM agents WHERE id=%s AND badge_ts=%s` to ensure only valid agents with correct badge timestamps can perform operations.

**Profile Management:** The punch-in operation creates or updates agent profiles with deterministic persona names, role information, and metadata. The system handles profile creation, updates, and maintenance while preserving historical data and maintaining data integrity.

**Punch-Out Implementation:** The punch-out operation deactivates agent sessions while preserving all profile data and historical information. The system updates agent status and session information while maintaining complete audit trails and historical records.

**Session Control:** The system provides secure session management with proper activation and deactivation procedures. All session operations include comprehensive validation, status checking, and error handling to ensure system integrity and prevent unauthorized access.

**Error Handling:** The system includes comprehensive error handling for invalid agent identities, database connection issues, and profile management problems. Errors are formatted through the parser system with proper icons and styling, providing clear feedback about operation status.

**Security and Validation:** All operations include comprehensive identity validation, status checking, and error handling. The system implements proper security controls to ensure only authorized agents can perform timeclock operations and maintains data integrity throughout all operations.

**Parser Integration:** Both commands use field configurations and implement the "ONE table" approach with all data in single `render_flexible_table()` calls. The parsers handle datetime serialization, error states, and conditional rendering based on NO_FLAGS configuration.

**Output Format:** Both commands return structured JSON with success/error states, operation details, and session information. The parsers transform this into formatted tables using the table rendering system with proper icons, labels, and styling through the configuration system (`icon.ini`, `label.ini`, `table.ini`).

**System Integration:** The timeclock system integrates with the broader agent ecosystem, providing session management capabilities that complement the information and management systems while maintaining data integrity and system consistency.
---
