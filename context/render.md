# Henhouse Render System Architecture

This document covers the comprehensive output formatting system that transforms structured data into formatted tables and text output, including the render system, table builder, configuration management, and text processing utilities.

## Table of Contents

1. [Render System](#1-render-system)
2. [Table Builder](#2-table-builder)
3. [Table Configuration](#3-table-configuration)
4. [Table Layout](#4-table-layout)
5. [Table Borders](#5-table-borders)
6. [Table Cells](#6-table-cells)
7. [Table Types](#7-table-types)
8. [Text Tools](#8-text-tools)
9. [Config System](#9-config-system)
10. [INI Configuration Files](#10-ini-configuration-files)

## Agent Quick Reference

- **Render Pipeline**: Data → Field Config → Table Builder → Layout → Borders → Cells → Text Tools → Output
- **Table Creation**: `TableBuilder(table_class)` → `set_columns()` → `row()` → `render()`
- **Field Configuration**: `FieldConfig` class with methods like `add_header()`, `add_simple()`, `add_group()` for building field configurations
- **Text Processing**: `display_width()`, `wrap()`, `pad_*()`, `to_*_case()` for Unicode-aware text manipulation
- **Configuration Access**: `ic()`, `dc()`, `mc()`, `tc()`, `cc()` for icons, labels, table config, parse settings
- **Output Flow**: Table data flows through `render_block()` → `render_flexible_table()` → `TableBuilder.render()`

## Agent Training Notes

### Render System Integration
- **Render Function Usage**: Use `render_block(data, FieldConfig(), table_class, overrides, block_type)` for main table rendering
- **Field Configuration**: Use `FieldConfig` class with methods like `add_header()`, `add_simple()`, `add_group()` to build field configurations inline
- **Meta Rendering**: Use `render_meta_table()` for complex nested data; accepts dicts or JSON strings and auto-sizes nested tables
- **Meta Overrides**: `render_meta_table()` trims margin overrides before recursing, measures nested content with `get_max_width()`, and applies the widest value to `column_widths['value']`
- **Header Rendering**: Use `render_header_block(subheader_key)` with no-flag support for conditional headers
- **Output Finalization**: Header/section blocks call `render_header_block()` → `finalize_output()`; data tables return `TableBuilder.render()` directly
- **Color Integration**: Apply colors using `COLORS` dict with `color_key` in field configurations
- **No-Flag Support**: Use `gateway.is_no(flag_name)` to check conditional display flags

### Table System Usage
- **Table Creation**: Use `TableBuilder(table_class)` to create new table instances
- **Column Setup**: Use `set_columns("col1,col2,col3")` to define column order
- **Configuration**: Use `set_*()` methods to configure margins, padding, borders, and column settings
- **Data Addition**: Use `row(keys=[...], values=[...])` or `cell(column, value)` to add data
- **Overrides**: Use `apply_overrides({"margin_l": 2, "padl": 1})` to override configuration
- **Rendering**: Use `render()` to generate final formatted table output
- **Separators**: Use `sep()` to add horizontal rules between rows

### Text Processing Patterns
- **Display Width**: Use `display_width(text)` to calculate accurate display width for Unicode text
- **Text Wrapping**: Use `wrap(text, width)` for advanced wrapping with color preservation
- **Text Padding**: Use `pad_left()`, `pad_right()`, `pad_center()` for text alignment
- **Case Conversion**: Use `to_snake_case()`, `to_camel_case()`, `to_kebab_case()` for case transformation
- **ANSI Handling**: Use `strip_ansi()` to remove color codes for width calculation
- **Text Slicing**: Use `slice(text, max_width)` for width-aware text truncation
- **Unicode Support**: System handles East Asian characters and special symbols correctly

### Configuration Access
- **Icon Access**: Use `ic(key)` to get icon values from icon.ini
- **Label Access**: Use `dc(key, default)` to get label values from label.ini
- **Table Config**: Use `mc(key)` to get table configuration values
- **Parse Config**: Use `tc(key)` and `cc(key)` for parse configuration
- **Caching**: Configuration data is cached for performance
- **Default Values**: Always provide default values for configuration access

### Common Integration Patterns
- **Render Pipeline**: Data → Field Config → Table Builder → Layout → Borders → Cells → Text Tools → Output
- **Configuration Flow**: INI Files → Config System → Render System → Table System → Text Tools
- **Error Handling**: Use gateway error methods for render failures and configuration issues
- **Performance**: Configuration caching and lazy loading for optimal performance
- **Unicode Support**: Full Unicode support with proper width calculation and text processing

---

## 1. Render System

**File**: `hh/render/render.py`

The comprehensive output formatting system that transforms structured data into formatted tables and text output. It provides sophisticated table formatting, field configuration management, meta rendering for complex nested data structures, color coding, and text utilities.

The render system serves as the central orchestrator for all output formatting in the Henhouse system. It takes structured data from backend modules and transforms it into human-readable formatted output with tables, headers, colors, and proper text processing. The system handles both simple data display and complex nested metadata rendering with automatic width calculation and layout optimization.

### Global Module

#### owned by:
- backend modules : *Used by backend handlers for output formatting*

#### owns:
- render functions : *Core rendering functions (render_block, render_flexible_table, etc.)*
- field configuration system : *Field type and display configuration management*
- meta table rendering : *Recursive metadata rendering for nested data*
- color system : *Color coding and visual styling for output*

#### data managed:
- rendering state (local copy) : *Rendering process state and temporary data*
- field configurations (source of truth) : *Field type and display configuration definitions*
- META_FIELD_CONFIGS (source of truth) : *Metadata field configuration definitions*
- color definitions (source of truth) : *Color codes and names for output styling*

#### calls:
- **render_block()** : *Main table rendering function with field configuration support*
- **render_flexible_table()** : *Flexible table rendering with column auto-detection*
- **render_meta_table()** : *Recursive metadata table rendering for nested data structures*
- **render_header_block()** : *Header block rendering with no-flag support*
- **finalize_output()** : *Output finalization and line filtering*
- **render_dict_contents()** : *Dictionary content rendering with nested structure support*
- **render_list_contents()** : *List content rendering with nested structure support*
- **render_simple_value()** : *Simple value rendering and type conversion*
- **TableBuilder()** : *Creates table builder instances for table construction*
- **config functions (ic, dc, mc, tc, cc)** : *Configuration access calls for icons, labels, and settings*
- **get_max_width()** : *Calculates maximum text width for layout optimization*
- **break_section()** : *Adds section breaks between content blocks*

#### called by:
- backend modules (rendering) : *Backend handlers call render functions for output formatting*
- debug systems (table rendering) : *Debug systems use render functions for formatted output*

#### retrieves from:
- config system (icons, labels, table config) : *Gets configuration data for display elements*
- table system (table formatting) : *Gets table formatting functionality from table modules*
- gateway (no-flag states) : *Gets no-flag configuration for conditional display*
- text system (width calculation) : *Gets text processing utilities for width calculations*

**Gateway no-flags used by render system**
- `main_header`: suppresses the top-level header produced by `render_header_block()`
- `sub_header`: suppresses the subheader branch in `render_header_block()`
- `header`: hides the first data row when `render_block()` treats it as a table header
- `label`: clears the leading label column when formatting table rows
- `meta` / `sub_meta`: skip entire metadata sections or collapse nested structures into summaries

#### provides to:
- backend modules (formatted output) : *Provides formatted output for backend handlers*
- debug systems (formatted tables) : *Provides formatted table output for debug display*
- table system (field configurations) : *Provides field configuration data to table system*

#### configuration dependencies:
- icon.ini : *Icon definitions and mappings for visual elements*
- label.ini : *Label definitions and text for display elements*
- table.ini : *Table formatting configuration settings*
- parse.ini : *Parse configuration settings for text processing*

#### error handling:
- **render_error()** : *Reports rendering errors through gateway error system*
- **warn()** : *Logs warnings for rendering issues*
- **gateway error methods** : *Uses gateway error reporting for render failures*

#### cross-references:
- **[Table Builder](#2-table-builder)**: *Uses TableBuilder for table construction*
- **[Config System](#9-config-system)**: *Accesses configuration data for display elements*
- **[Text Tools](#8-text-tools)**: *Uses text utilities for width calculation and formatting*

---

## 2. Table Builder

**File**: `hh/render/table/table.py`

The table formatting system that transforms structured data into formatted tables through coordinated modules. Acts as the main orchestrator and data collector, managing table construction, column configuration, and cell content assembly.

The TableBuilder serves as the central coordinator for the entire table rendering pipeline. It manages the data collection process, applies configuration settings, and orchestrates the various table modules to produce the final formatted output. The builder pattern allows for fluent configuration and incremental data addition while maintaining clean separation of concerns between data management, layout calculation, border rendering, and cell processing.

### TableBuilder Class

#### owned by:
- render system : *Created by render functions for table construction*

#### owns:
- columns : *Column data storage and content management*
- column_order : *Column ordering and display sequence*
- config : *Table configuration settings and overrides*
- hrules_after_rows : *Horizontal rule positions and separator management*

#### data managed:
- columns (source of truth) : *Table column data and content*
- column_order (source of truth) : *Column display order and sequence*
- config (source of truth) : *Table configuration settings and overrides*
- hrules_after_rows (source of truth) : *Horizontal rule positions and separators*

#### calls:
- **set_columns()** : *Sets column order and configuration from comma-separated string*
- **set_has_header()** : *Configures header display settings*
- **set_rule_header()** : *Configures header rule display*
- **set_rule_every()** : *Configures periodic rule display interval*
- **set_margin_*()** : *Sets margin configurations (left, right, top, bottom)*
- **set_pad*()** : *Sets padding configurations (left, right)*
- **set_*_border()** : *Sets border glyph configurations for all border types*
- **set_column_*()** : *Sets column-specific configurations (width, align, overflow, valign)*
- **apply_overrides()** : *Applies configuration overrides from dictionary*
- **cell()** : *Adds individual cell content to specified column*
- **newline()** : *Adds new row to table structure*
- **row()** : *Adds complete row with keys and values*
- **sep()** : *Adds horizontal separator after current row*
- **render()** : *Renders final table with borders and formatting*

#### called by:
- render system (table creation) : *Render system creates table builders for output*

#### retrieves from:
- table_config (configuration) : *Gets table configuration from table_config module*
- table_layout (column layouts) : *Gets column layout calculations from table_layout module*
- table_borders (border rendering) : *Gets border rendering functions from table_borders module*
- table_cells (cell shaping) : *Gets cell shaping functions from table_cells module*

#### provides to:
- render system (formatted tables) : *Provides rendered table output to render system*

#### configuration dependencies:
- table.ini : *Table formatting configuration settings*

#### error handling:
- **warn()** : *Logs warnings for table construction issues*
- **gateway error methods** : *Uses gateway error reporting for table failures*

#### cross-references:
- **[Table Configuration](#3-table-configuration)**: *Uses table configuration for settings*
- **[Table Layout](#4-table-layout)**: *Uses layout calculations for column dimensions*
- **[Table Borders](#5-table-borders)**: *Uses border rendering for table borders*
- **[Table Cells](#6-table-cells)**: *Uses cell processing for content formatting*

---

## 3. Table Configuration

**File**: `hh/render/table/table_config.py`

The configuration management system that loads and manages table configuration settings from INI files, providing configuration data and override handling for the table system.

The table configuration system provides a clean abstraction layer between the INI file storage and the table rendering system. It handles the loading of configuration data, applies overrides, and manages column-specific settings. The system uses lazy loading and caching to ensure optimal performance while providing a flexible configuration system that can be overridden at runtime.

### Global Module

#### owned by:
- global scope : *Module-level configuration management*

#### owns:
- configuration functions : *Configuration loading and management functions*
- TableConfig class : *Table configuration data structure*

#### data managed:
- table configurations (cached) : *Loaded table configuration data from INI files*

#### calls:
- **load_table_config()** : *Loads table configuration from INI files for specified class*
- **update_column_config()** : *Updates column-specific configuration settings*
- **apply_config_overrides()** : *Applies configuration overrides to existing config*
- **conf_str(), conf_int()** : *Configuration value access functions*

#### called by:
- TableBuilder (configuration loading) : *Table builder loads configuration during initialization*
- render system (configuration access) : *Render system accesses configuration for table settings*

#### retrieves from:
- config system (INI file access) : *Gets configuration from INI files through config system*

#### provides to:
- TableBuilder (configuration data) : *Provides table configuration to table builder*
- render system (configuration functions) : *Provides configuration functions to render system*

#### configuration dependencies:
- table.ini : *Table formatting configuration settings*

#### error handling:
- **warn()** : *Logs warnings for configuration loading issues*

#### cross-references:
- **[Config System](#9-config-system)**: *Uses config system for INI file access*
- **[Table Builder](#2-table-builder)**: *Provides configuration to table builder*

---

## 4. Table Layout

**File**: `hh/render/table/table_layout.py`

The layout calculation system that determines optimal column layouts and dimensions based on content and configuration settings.

The table layout system is responsible for calculating the optimal dimensions and properties for each column in a table. It analyzes the content width, applies configuration constraints, and determines when text wrapping is needed. The system balances natural content width with configured column widths to create an optimal layout that respects both content requirements and user preferences.

### Global Module

#### owned by:
- global scope : *Module-level layout calculation*

#### owns:
- calculate_column_layouts function : *Column layout calculation function*
- ColumnLayout class : *Column layout data structure*

#### data managed:
- column layouts (local copy) : *Calculated column layout data for table rendering*

#### calls:
- **calculate_column_layouts()** : *Calculates optimal column layouts based on content and config*
- **display_width()** : *Calculates text display width for layout calculations*

#### called by:
- TableBuilder (layout calculation) : *Table builder calculates layouts during rendering*

#### retrieves from:
- text tools (width calculation) : *Gets text width calculation from text tools*
- TableConfig (configuration) : *Gets table configuration for layout settings*

#### provides to:
- TableBuilder (column layouts) : *Provides calculated column layouts to table builder*

#### configuration dependencies:
- table.ini : *Table formatting configuration settings*

#### error handling:
- **warn()** : *Logs warnings for layout calculation issues*

#### cross-references:
- **[Text Tools](#8-text-tools)**: *Uses text tools for width calculation*
- **[Table Builder](#2-table-builder)**: *Provides layouts to table builder*

---

## 5. Table Borders

**File**: `hh/render/table/table_borders.py`

The border rendering system that creates table borders and separators using normalized glyphs and layout calculations.

The table borders system handles the complex task of creating consistent and properly aligned table borders. It normalizes glyphs to ensure consistent spacing, builds different types of borders (top, header, mid, bottom), and handles pattern filling for border segments. The system ensures that all border elements are properly aligned regardless of their individual widths.

### Global Module

#### owned by:
- global scope : *Module-level border rendering*

#### owns:
- border functions : *Border rendering functions for all border types*
- glyph normalization : *Glyph alignment and normalization system*

#### data managed:
- glyph data (local copy) : *Normalized glyph data for border rendering*

#### calls:
- **normalize_glyphs()** : *Normalizes and aligns border glyphs for consistent rendering*
- **build_top_border()** : *Builds top table border with proper glyph alignment*
- **build_header_border()** : *Builds header separator border*
- **build_mid_border()** : *Builds mid-row separator border*
- **build_bottom_border()** : *Builds bottom table border*
- **display_width(), pad_center(), pad_left(), pad_right()** : *Text processing utilities for glyph alignment*

#### called by:
- TableBuilder (border rendering) : *Table builder renders borders during table construction*

#### retrieves from:
- text tools (text processing) : *Gets text processing utilities for glyph alignment*
- TableConfig (border configuration) : *Gets border glyph configuration from table config*

#### provides to:
- TableBuilder (border functions) : *Provides border rendering functions to table builder*

#### configuration dependencies:
- table.ini : *Table formatting configuration settings*

#### error handling:
- **warn()** : *Logs warnings for border rendering issues*

#### cross-references:
- **[Text Tools](#8-text-tools)**: *Uses text tools for glyph alignment*
- **[Table Builder](#2-table-builder)**: *Provides border functions to table builder*

---

## 6. Table Cells

**File**: `hh/render/table/table_cells.py`

The cell processing system that handles individual cell content with text shaping, wrapping, and alignment.

The table cells system is responsible for processing individual cell content and ensuring it fits properly within the calculated column dimensions. It handles text wrapping, alignment, overflow handling, and vertical alignment. The system works with the text tools to ensure proper Unicode width calculation and color preservation during text processing.

### Global Module

#### owned by:
- global scope : *Module-level cell processing*

#### owns:
- cell processing functions : *Cell content processing and shaping functions*
- text shaping functions : *Text wrapping and alignment functions*

#### data managed:
- cell data (local copy) : *Processed cell content and shaped text*

#### calls:
- **shape_cell()** : *Shapes individual cell content based on layout settings*
- **align_line()** : *Aligns text within cell based on alignment settings*
- **shape_column()** : *Shapes entire column content with consistent formatting*
- **display_width(), wrap(), ellipsize(), slice()** : *Text processing utilities for cell content*

#### called by:
- TableBuilder (cell processing) : *Table builder processes cells during table construction*

#### retrieves from:
- text tools (text processing) : *Gets text processing utilities for cell content*
- ColumnLayout (layout configuration) : *Gets column layout settings for cell processing*

#### provides to:
- TableBuilder (cell functions) : *Provides cell processing functions to table builder*

#### configuration dependencies:
- table.ini : *Table formatting configuration settings*

#### error handling:
- **warn()** : *Logs warnings for cell processing issues*

#### cross-references:
- **[Text Tools](#8-text-tools)**: *Uses text tools for cell content processing*
- **[Table Builder](#2-table-builder)**: *Provides cell functions to table builder*

---

## 7. Table Types

**File**: `hh/render/table/table_types.py`

The data structure system that provides type definitions and management for the entire table system.

The table types system provides the foundational data structures used throughout the table rendering pipeline. It defines the TableConfig, ColumnLayout, and RenderedRow classes that encapsulate the configuration and state information needed for table rendering. These types ensure type safety and provide clear interfaces between the different table modules.

### Global Module

#### owned by:
- global scope : *Module-level data structures*

#### owns:
- TableConfig class : *Table configuration data structure*
- ColumnLayout class : *Column layout data structure*
- RenderedRow class : *Rendered row data structure*

#### data managed:
- data structure definitions (source of truth) : *Data structure definitions for table system*

#### calls:
- **TableConfig.__post_init__()** : *Initializes table configuration with default values*
- **ColumnLayout.__init__()** : *Initializes column layout with specified parameters*
- **RenderedRow.__init__()** : *Initializes rendered row with lines and types*

#### called by:
- table system (data structures) : *Table system uses data structures for type management*

#### retrieves from:
- none : *Pure data structure definitions*

#### provides to:
- table system (data structures) : *Provides data structure classes to table system*

#### configuration dependencies:
- none : *Pure data structure definitions*

#### error handling:
- **warn()** : *Logs warnings for data structure initialization issues*

#### cross-references:
- **[Table Builder](#2-table-builder)**: *Uses data structures for type management*
- **[Table Configuration](#3-table-configuration)**: *Uses TableConfig for configuration*

---

## 8. Text Tools

**File**: `hh/render/text/text.py`

The comprehensive text processing utility system that provides advanced text manipulation and formatting capabilities with Unicode and ANSI color support.

The text tools system provides the foundational text processing capabilities used throughout the render system. It handles Unicode width calculation, text wrapping with color preservation, padding, alignment, case conversion, and various text manipulation tasks. The system ensures accurate display width calculation for international characters and proper handling of ANSI escape sequences.

### Global Module

#### owned by:
- global utilities : *Module-level text processing*

#### owns:
- text processing functions : *Advanced text manipulation utilities*
- Unicode width calculation : *Unicode character width calculation system*
- ANSI color handling : *ANSI escape sequence processing system*
- case conversion functions : *Text case transformation utilities*

#### data managed:
- Unicode character mappings (source of truth) : *Known single/double wide character sets*
- text processing state (local copy) : *Text processing state and temporary data*

#### calls:
- **display_width()** : *Calculates display width for Unicode text with ANSI filtering*
- **wrap()** : *Advanced text wrapping with color preservation and intelligent word breaking*
- **wrap_simple()** : *Simple text wrapping without color handling*
- **ellipsize()** : *Text ellipsizing with display width awareness*
- **pad(), pad_left(), pad_right(), pad_center()** : *Text padding functions with display width*
- **slice()** : *Text slicing with display width calculation*
- **justify()** : *Text justification with proper spacing*
- **to_snake_case(), to_camel_case(), to_kebab_case()** : *Case conversion functions*
- **clean_whitespace()** : *Whitespace normalization*
- **strip_ansi()** : *ANSI escape sequence removal*
- **indent(), dedent()** : *Text indentation functions*
- **get_max_width()** : *Calculates maximum width from table output*
- **string methods** : *Python string operations*
- **regex operations** : *Regular expression processing*

#### called by:
- render system : *Render system uses text tools for formatting*
- table system : *Table system uses text tools for width calculation*
- config system : *Config system uses text tools for text processing*

#### retrieves from:
- input strings : *Gets text input for processing*
- wcwidth library : *Gets Unicode width calculation (optional fallback)*
- unicodedata : *Gets Unicode character properties*

#### provides to:
- all modules (text processing utilities) : *Provides text processing functionality to all modules*
- table system (width calculations) : *Provides display width calculations to table system*
- render system (text formatting) : *Provides text formatting functions to render system*

#### configuration dependencies:
- none : *Pure utility functions*

#### error handling:
- **warn()** : *Logs warnings for text processing issues*

#### cross-references:
- **[Render System](#1-render-system)**: *Provides text formatting to render system*
- **[Table System](#2-table-builder)**: *Provides width calculation to table system*

---

## 9. Config System

**File**: `hh/render/config/__init__.py`

The comprehensive configuration management system that provides centralized access to all system configuration data through a unified interface.

The config system serves as the central access point for all configuration data in the Henhouse system. It provides a unified API for accessing icons, labels, table configuration, and parse settings through simple function calls. The system implements lazy loading and caching to ensure optimal performance while providing a clean abstraction layer between the INI file storage and the consuming modules.

### Global Module

#### owned by:
- global scope : *Module-level configuration management*

#### owns:
- config functions : *Configuration access functions (ic, dc, mc, tc, cc)*
- cached config data : *Cached configuration data from INI files*

#### data managed:
- icon.ini data (cached) : *Icon configuration data from icon.ini*
- label.ini data (cached) : *Label configuration data from label.ini*
- table.ini data (cached) : *Table configuration data from table.ini*
- parse.ini data (cached) : *Parse configuration data from parse.ini*

#### calls:
- **configparser.ConfigParser()** : *Parses INI files for configuration data*
- **_read_flat_ini()** : *Reads flat INI structure for configuration access*
- **json.load()** : *Loads JSON configuration data*

#### called by:
- render system (ic(), dc(), mc(), tc(), cc()) : *Render system accesses config for display elements*
- all modules (configuration access) : *All modules access configuration through config functions*

#### retrieves from:
- INI files (configuration data) : *Gets configuration from INI files on disk*

#### provides to:
- render system (icons, labels, table config) : *Provides configuration data to render system*
- all modules (configuration values) : *Provides configuration values to all modules*

#### configuration dependencies:
- icon.ini : *Icon definitions and mappings*
- label.ini : *Label definitions and text*
- table.ini : *Table formatting configuration*
- parse.ini : *Parse configuration settings*

#### error handling:
- **warn()** : *Logs warnings for configuration loading issues*

#### cross-references:
- **[INI Configuration Files](#10-ini-configuration-files)**: *Reads configuration from INI files*
- **[Render System](#1-render-system)**: *Provides configuration to render system*

---

## 10. INI Configuration Files

**File**: `hh/render/config/*.ini`

The configuration data storage system that provides all system configuration data through INI files.

The INI configuration files serve as the persistent storage layer for all system configuration data. They provide a human-readable format for storing icons, labels, table formatting settings, and parse configuration. The files are organized by function and provide a clear separation between different types of configuration data.

### Global Module

#### owned by:
- file system : *Configuration files on disk*

#### owns:
- icon.ini : *Icon definitions and mappings for visual elements*
- label.ini : *Label definitions and text for display elements*
- table.ini : *Table formatting configuration settings*
- parse.ini : *Parse configuration settings for text processing*

#### data managed:
- configuration data (source of truth) : *All system configuration data stored in INI files*

#### calls:
- none : *Static configuration files*

#### called by:
- config system (file reading) : *Config system reads INI files for configuration data*

#### retrieves from:
- none : *Static configuration files*

#### provides to:
- config system (configuration data) : *Provides configuration data to config system*

#### configuration dependencies:
- none : *Static configuration files*

#### error handling:
- **file system errors** : *Handles file system errors for configuration file access*

#### cross-references:
- **[Config System](#9-config-system)**: *Provides configuration data to config system*
