# config-parse-ini
## description
Parser registration settings, logging configuration, and system parameters for the Henhouse architecture.
## summary
The parse.ini file contains configuration for parser registration, logging behavior, and system parameters that control the Henhouse parser architecture including which parsers are loaded, logging verbosity, and operational limits.
## full_text
The parse.ini file serves as the central configuration file for parser-specific settings, logging configuration, and system parameters. It contains settings that control parser registration, logging behavior, and system-wide operational limits.

**Parser Registration Settings:**
The file includes settings that control which parsers are loaded and how the decorator system operates:
- `config_enable_decorator_system` - Controls the @register_parser decorator functionality (default: true)
- `config_registered_parsers` - Comma-separated list of parser module file paths

**Parser Logging Settings:**
The file contains settings that control parser-specific logging output:
- `config_enable_parser_logging` - Enables parser-specific logging output (default: true)
- `config_parser_log_level` - Sets the verbosity level for parser logging (default: info)

**System Parameters:**
The file defines system-wide limits and operational parameters:
- `config_enable_logging` - Master switch for all configuration usage logging (default: true)
- `max_json_length` - Maximum length for JSON output processing (default: 1000)

**Error Handling:**
The system handles missing or malformed configuration values by providing empty string fallbacks and maintaining system stability.
---
# parser-registration
## description
Parser registration and discovery configuration settings.
## summary
Controls which parsers are loaded and how the @register_parser decorator system operates throughout the Henhouse architecture.
## full_text
The parser registration section controls which parser modules are loaded and how the decorator system functions.

**Key Settings:**
- `config_enable_decorator_system` - Enables/disables the @register_parser decorator functionality (default: true)
- `config_registered_parsers` - Comma-separated list of parser module file paths that are loaded at startup
- `config_enable_parser_logging` - Controls parser-specific logging output (default: true)
- `config_parser_log_level` - Sets the verbosity level for parser logging (default: info)

**Registered Parsers:**
The current registered parser list includes:
- watercooler/parse_queue_peek.py
- help/parse_help_menu.py
- agents/parse_timeclock_punch.py
- agents/parse_agent_list.py
- agents/parse_agent_purge.py
- agents/parse_agent_tree.py

**Parser Discovery:**
The system loads registered parsers by importing the specified modules and collecting their @register_parser decorators. This enables dynamic parser loading based on the configuration.

**Integration:**
Parser registration integrates with the main parse.py engine to provide parser discovery and execution based on user commands.
---
# logging-configuration
## description
Logging and analytics configuration settings for the parser system.
## summary
Controls logging behavior, statistics collection, and analytics tracking throughout the configuration and parser systems.
## full_text
The logging configuration section controls how the system tracks usage patterns and collects analytics data.

**Logging Settings:**
- `config_enable_logging` - Master switch for all configuration usage logging (default: true)
- `config_enable_parser_logging` - Controls parser-specific logging output (default: true)
- `config_parser_log_level` - Sets logging verbosity level (default: info)

**Integration:**
Logging configuration integrates with the parser system to provide usage tracking and system optimization insights.
---
# system-parameters
## description
System-wide configuration parameters and performance settings.
## summary
Controls global system behavior, performance limits, and operational parameters throughout the Henhouse architecture.
## full_text
The system parameters section defines global settings that affect overall system behavior and performance.

**System Parameters:**
- `max_json_length` - Maximum length for JSON output processing to prevent memory issues (default: 1000)

**Integration:**
These parameters integrate with the core config system to provide consistent behavior across all parser modules and system components.
---
