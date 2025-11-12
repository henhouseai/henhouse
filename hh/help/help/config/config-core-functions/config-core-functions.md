# config-core-functions
## description
Core helper functions for configuration access, argument parsing, UI elements, and output control. Includes get_str/get_int for values, ic/dc/mc/tc for UI elements, setup_argparse for CLI handling, and break_section for output formatting.
## summary
The config-core-functions system is the central configuration management hub for the parser system. It provides intelligent key routing to multiple .ini files, comprehensive argument parsing for --no-* flags, extensive logging and usage tracking, lazy file loading with global caching, and seamless integration with table rendering and parser output. The system includes value retrieval functions, argument parsing system, helper functions for UI elements, comprehensive logging system, file loading mechanism, error handling, and section output tracking. All functions are designed to work together seamlessly with automatic logging, flag checking, and graceful error handling throughout.
## full_text
The config-core-functions system provides comprehensive configuration management for the entire parser system, handling everything from basic value retrieval to complex argument parsing and usage tracking.

**Core Architecture:**

The system is built around intelligent key routing that automatically directs configuration requests to the appropriate .ini file based on key prefixes. It maintains global state for parsed arguments, loaded configuration files, and output tracking, with comprehensive logging integrated throughout all functions.

**Value Retrieval System:**

The foundation of the system provides three core functions for accessing configuration values:
- **`_raw_get(key: str) -> str`** - Core routing function that directs keys to appropriate .ini files
- **`get_str(key: str) -> str`** - Gets string values with automatic quote stripping
- **`get_int(key: str) -> int`** - Gets integer values with validation and zero fallback

**Intelligent Key Routing:**

Keys are automatically routed to the correct configuration file:
- **t_* keys** → table.ini (table styling, borders, layout settings)
- **l_* keys** → label.ini (text labels for UI elements)
- **max_* and config_* keys** → parse.ini (parser settings and limits)
- **All other keys** → icon.ini (emoji icons and symbols)

**Argument Parsing System:**

Comprehensive --no-* flag handling with global state management:
- **`setup_argparse(no_flags_config, args)`** - Creates argument parser with --no-* flags
- **`is_no(group, no_flags_config)`** - Checks if --no-* flag was used with automatic logging
- **`log_no_flag(group)`** - Logs flag usage for tracking and statistics
- **Global State Management** - Uses `_args` global variable for system-wide flag access

**Helper Functions for UI Elements:**

Specialized functions for common UI elements with built-in flag checking:
- **`ic(name: str) -> str`** - Gets icons from icon.ini, respects --no-icon flag
- **`dc(name: str, add_tc: bool = False) -> str`** - Gets labels from label.ini, respects --no-desc flag
- **`mc(name: str) -> int`** - Gets numeric values with error handling and logging
- **`tc(repeat: int = 1, mode: Optional[int] = None) -> str`** - Generates tab characters with spacing modes
- **`out(value: Any) -> str`** - Safe string output with display-width awareness

**Utility Functions:**

System integration and output control functions:
- **`break_section(lines: List[str]) -> None`** - Adds spacing between output sections
- **`conf_str(cls: str, name: str) -> str`** - Gets table configuration string values
- **`conf_int(cls: str, name: str) -> int`** - Gets table configuration integer values
- **`_tools_dir() -> str`** - Gets tools directory path for file operations

**Comprehensive Logging System:**

Extensive usage tracking with timestamp and count files:
- **`_touch_timestamp_log(log_type, name)`** - Writes timestamps to `config.log.<type>` files
- **`_increment_count(log_type, name, present)`** - Updates usage counters in JSON files
- **`_is_logging_enabled()`** - Checks if logging is enabled via parse.ini configuration
- **`_now_iso()`** - Returns current timestamp as ISO string
- **Automatic Integration** - All functions automatically log their usage

**File Loading System:**

Lazy loading with global caching for performance:
- **`_ensure_loaded()`** - Loads all .ini files into global ConfigParser objects
- **`_read_flat_ini(path)`** - Wraps .ini content in [DEFAULT] section for consistent access
- **Global Caching** - `_cfg_parse`, `_cfg_icon`, `_cfg_label`, `_cfg_table` cache loaded files
- **Performance Optimization** - Files loaded once and cached for subsequent access

**Error Handling:**

Comprehensive graceful handling of missing files and invalid data:
- **Empty string fallbacks** - `fallback=''` parameter in `_raw_get()` for missing keys
- **Zero fallbacks** - Zero values for invalid numeric entries in `get_int()`
- **Exception handling** - All functions wrapped in try-catch blocks for silent failure
- **File existence checks** - `_read_flat_ini()` checks file existence before reading
- **String processing** - Automatic trimming and quote handling throughout

**Section Output Tracking:**

The `_section_has_output` global variable tracks whether any content has been generated in the current section. It's set by `ic()`, `dc()`, and `out()` functions when they return non-empty values, enabling `break_section()` to add appropriate spacing between output sections.

**System Integration:**

The config-core-functions system integrates seamlessly with all parts of the parser system:
- **Parser Registration** - Parsers define NO_FLAGS lists for automatic argument generation
- **Table Rendering** - Tables check --no-header flag before showing headers
- **Helper Function Usage** - All helper functions automatically log usage and check flags
- **Configuration Access** - All configuration access goes through the intelligent routing system
- **Logging Integration** - Every function call is automatically logged for usage tracking

**Global State Management:**

The system maintains several global variables for state management:
- **`_cfg_parse`, `_cfg_icon`, `_cfg_label`, `_cfg_table`** - Cached ConfigParser objects
- **`_section_has_output`** - Tracks output generation for section breaks
- **`_logging_enabled`** - Cached logging state for performance
- **`_args`** - Parsed command line arguments for flag checking

**SPECIAL FILE - ONLY ONE SECTION ALLOWED**
This file provides overview of the entire config-core-functions folder. NO individual aspect sections.

---
