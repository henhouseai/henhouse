# agents
## description
Comprehensive agent management system for complete lifecycle control, monitoring, and administrative operations.
## summary
The agents system provides complete agent lifecycle management including listing, filtering, detailed analysis, session control, and administrative operations. It implements a parser-based architecture with data sources and formatters for consistent user experience across all agent management operations.
## full_text
The agents system provides comprehensive agent management through a suite of specialized commands and tools. The system implements a parser-based architecture with data sources that generate JSON and parser modules that format output using `render_flexible_table()` for consistent user experience.

**Core Management Commands:**
- `agent-list` - List and filter agents with comprehensive search capabilities, deep mode analysis, and pagination support
- `agent-tree` - Get detailed agent information with activity tree, relationships, and comprehensive deep mode analysis
- `agent-purge` - Archive all agents (excluding operators) and clean operational state with dry-run capabilities
- `punch-in` - Activate agent sessions with deterministic persona naming and profile management
- `punch-out` - Deactivate agent sessions while preserving all profile data and historical information

**System Architecture:** All commands follow the parser system pattern with data source scripts (`tools/agents/*.py`) that generate JSON data and parser modules (`tools/agents/parse_*.py`) that format output using the table rendering system. This ensures consistent formatting, error handling, and user experience across all operations.

**Database Integration:** The system uses PyMySQL with DictCursor for database operations, loading connection parameters from `.henhouse.cnf` files. All operations include proper transaction management with rollback capabilities for data consistency.

**Key Features:**
- **Deterministic Persona Naming:** Consistent agent naming based on MD5 hash of badge timestamps
- **Deep Mode Analysis:** Comprehensive activity tracking, subscription monitoring, and relationship analysis
- **Advanced Filtering:** Filter by role, status, work docket, and A/T/S relationships with complex query support
- **Session Management:** Secure punch-in/punch-out operations with identity validation and profile management
- **Administrative Tools:** Safe purge operations with dry-run capabilities and comprehensive operation reporting
- **Transaction Safety:** All operations use database transactions with proper error handling and rollback capabilities
- **Audit Trails:** Complete operation logging and reporting for compliance and troubleshooting

**Security and Validation:** All operations include comprehensive identity validation, status checking, and error handling. Critical operations like agent-purge require explicit confirmation flags to prevent accidental data loss.

**Parser System Integration:** All commands use the shared parser system with field configurations, dynamic field types, and consistent formatting through the configuration system (`icon.ini`, `label.ini`, `table.ini`).
---
