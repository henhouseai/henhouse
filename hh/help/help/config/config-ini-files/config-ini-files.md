# config-ini-files
## description
Four .ini configuration files (parse.ini, icon.ini, label.ini, table.ini) that define parser settings, emoji icons, text labels, and table styling for the entire system.
## summary
Configuration system that manages four .ini files (parse.ini, icon.ini, label.ini, table.ini) through key routing, lazy loading with caching, and integration with parser helper functions. The system routes keys to files based on prefixes, handles errors with fallbacks, and caches files for performance.
## full_text
The config-ini-files system manages four .ini files that control different aspects of the parser system. Each file serves a specific purpose and is loaded by the config system through key routing based on key prefixes.

**Configuration File Architecture:**

The system manages four .ini files that work together to control the entire parser system:

- **parse.ini** - The "control center" that manages parser registration, logging behavior, and system parameters
- **icon.ini** - The "visual elements" containing emoji and symbol definitions for UI elements and status indicators
- **label.ini** - The "text labels" providing user-facing text for UI elements, table headers, and field descriptions
- **table.ini** - The "presentation rules" defining table styling, layout, and formatting for consistent output

**How the Files Work Together:**

The four .ini files work as an integrated system where each file handles a specific aspect of configuration:

- **parse.ini** decides what gets processed and how the system behaves
- **icon.ini** and **label.ini** provide the content elements (visual and text) that make output readable
- **table.ini** defines how everything gets displayed with consistent formatting
- The config system automatically routes keys to the appropriate file based on prefixes

**Key Routing System:**

The `_raw_get()` function automatically routes configuration keys to the correct file:

- **t_* keys** → table.ini (table styling and layout)
- **l_* keys** → label.ini (text labels and descriptions)
- **max_* and config_* keys** → parse.ini (system settings and limits)
- **All other keys** → icon.ini (emoji and symbol definitions)

**File Loading and Caching:**

Files are loaded lazily using `_read_flat_ini()` which wraps content in a [DEFAULT] section for parsing. Global caching uses module-level variables (`_cfg_parse`, `_cfg_icon`, `_cfg_label`, `_cfg_table`) to avoid repeated disk I/O. Files are cached after first load and accessed through `_ensure_loaded()`.

**Helper Functions Integration:**

Configuration files work with parser helper functions to provide a clean API:

- **ic(name: str) -> str** - Gets icons from icon.ini, respects --no-icon flag
- **dc(name: str, add_tc: bool = False) -> str** - Gets labels from label.ini, respects --no-desc flag
- **mc(name: str) -> int** - Gets numeric values from config files
- **tc(repeat: int = 1, mode: Optional[int] = None) -> str** - Generates tab characters
- **out(value: Any) -> str** - Safe string output with display-width awareness

**Error Handling and Reliability:**

The system handles errors gracefully when files are missing or corrupted:

- **Empty string fallbacks** - `fallback=''` parameter in `_raw_get()`
- **Zero fallbacks** - Zero values for invalid numeric entries in `get_int()`
- **Exception handling** - All functions handle exceptions without crashing
- **File existence checks** - `_read_flat_ini()` checks file existence before reading
- **String processing** - Automatic trimming and quote handling

**File Format and Structure:**

All .ini files use a flat structure wrapped in a [DEFAULT] section for parsing through `_read_flat_ini()`. The system supports standard INI format with key-value pairs, automatic string trimming with `.strip('"')`, and quote handling for values containing special characters.

**Performance Optimization:**

The system optimizes performance through several mechanisms:

- **Lazy Loading** - Files loaded only when first accessed through `_ensure_loaded()`
- **Global Caching** - Configuration objects cached in module-level variables after initial load
- **Key Lookup** - Efficient key routing through `_raw_get()`
- **Memory Management** - Shared configuration objects across the system
- **Disk I/O** - Single file read per configuration type through caching

**Maintenance and Updates:**

Configuration files can be updated by modifying the .ini files. Changes are reflected throughout the system without requiring recompilation or code changes. The system supports live updates through lazy loading, making it easy to customize behavior without touching code.

**Integration with Parser System:**

The configuration system integrates seamlessly with the parser architecture, providing consistent access to settings, visual elements, text labels, and table formatting across all parser modules. This creates a unified experience where all parsers use the same configuration system and display consistent output.
---
