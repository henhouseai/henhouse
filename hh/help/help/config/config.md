# config
## description
Central configuration management system that provides icons, labels, table styles, parser settings, and usage analytics for the entire Henhouse parser architecture.
## summary
The config system is the foundational configuration management hub for the Henhouse parser architecture, providing centralized control over visual elements, text labels, table styling, parser behavior, and comprehensive usage tracking. The system consists of four .ini configuration files (parse.ini, icon.ini, label.ini, table.ini) managed through intelligent key routing, a sophisticated logging and analytics system, and maintenance utilities. It provides 12 core helper functions for value retrieval, argument parsing, UI element handling, and output formatting, all with automatic logging and --no-* flag support. The system includes comprehensive usage tracking with timestamp logs and JSON count files, statistics analysis tools, and maintenance utilities for log cleanup. All components integrate seamlessly with the parser system to provide consistent styling, labeling, and formatting across all parser modules while maintaining detailed usage analytics for system optimization.
## full_text
The config system serves as the central configuration management hub for the entire Henhouse parser architecture, providing unified control over visual elements, text labels, table styling, parser behavior, and comprehensive usage tracking.

**System Architecture:**
The config system operates through four .ini configuration files managed by intelligent key routing that automatically directs different key types to appropriate files. The system uses lazy loading with global caching for performance and provides a comprehensive logging system that tracks all configuration access patterns. The architecture maintains global state through ConfigParser objects, output tracking flags, and parsed arguments, ensuring consistent behavior across all parser modules.

**Configuration Files:**
- **parse.ini** - Parser registration settings, logging configuration, and system parameters. Contains config_enable_logging, config_registered_parsers list, and max_json_length limits. Controls the decorator system and parser discovery mechanisms.

- **icon.ini** - 45 emoji and symbol definitions for UI elements and status indicators. Includes status indicators (active, inactive, todo, doing, review, done), content markers (message, channel, agent, help_topic), formatting elements (tab, blank_emoji, meta), and system elements (error, success, info, timestamp).

- **label.ini** - Text labels for UI elements, table headers, and user-facing text. Contains table headers (l_agent_id, l_message_channel), field descriptions (l_agent_status, l_success), status messages (l_no_messages, l_remaining), and help text (l_help_topic, l_help_section).

- **table.ini** - Table styling definitions with multiple classes and layout options. Defines table classes (standard, double, heavy, ascii, minimal, meta_main, meta_sub) with configuration for borders, padding, alignment, text handling, and rendering behavior.

**Core Functions:**
The system provides 12 core helper functions including value retrieval (get_str, get_int), UI elements (ic, dc, mc, tc, out), argument parsing (setup_argparse, is_no), and output control (break_section). All functions include comprehensive logging, --no-* flag support, and error handling. Functions automatically track usage through timestamp logs and JSON count files, with global state management for output tracking and section breaks.

**Key Routing System:**
Intelligent routing automatically directs keys to appropriate files: t_* keys to table.ini, l_* keys to label.ini, max_*/config_* keys to parse.ini, and everything else to icon.ini. The system handles missing keys gracefully by returning empty strings, missing files by returning empty ConfigParser objects, and provides comprehensive error handling to ensure system stability.

**Logging and Analytics:**
Comprehensive usage tracking through timestamp logs and JSON count files for four log types (ic, dc, mc, no). The system includes statistics analysis tools (config.stats.py) that display usage statistics in formatted tables showing total accesses, successful lookups, failed lookups, and last access times. Maintenance utilities (config.clean.py) remove all log files for cleanup and disk space management.

**Integration:**
The config system integrates seamlessly with all parser modules, providing consistent styling, labeling, and formatting across the entire architecture while maintaining detailed usage analytics for system optimization and maintenance. The system supports --no-* flags for conditional output rendering and provides global state management for consistent behavior across all components.

---
