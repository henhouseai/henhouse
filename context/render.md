# Henhouse Render System Architecture

This document covers the comprehensive output formatting system that transforms structured data into formatted tables and text output, including the render system, table builder, configuration management, and text processing utilities.

## Table of Contents

1. [Render System](#1-render-system)
1.5. [Render Parser Module](#15-render-parser-module)
1.6. [Render HTTP Module](#16-render-http-module)
2. [Table Builder](#2-table-builder)
3. [Table Configuration](#3-table-configuration)
4. [Table Layout](#4-table-layout)
5. [Table Borders](#5-table-borders)
6. [Table Cells](#6-table-cells)
7. [Table Types](#7-table-types)
8. [Text Tools](#8-text-tools)
9. [Config System](#9-config-system)
10. [Config Registry System](#10-config-registry-system)
11. [INI Configuration Files](#11-ini-configuration-files)

## Agent Quick Reference

- **Render Pipeline**: `TableData.add_row()` → `render_block()` → backend router → `render_flexible_table()` → `TableBuilder` → Layout → Borders → Cells → Text Tools → Output
- **Table Data Collection**: `TableData()` → `add_row(field_type, **columns)` → `render_block(table_data, field_configs)`
- **Field Configuration**: `FieldConfig()` → `add_header()` / `add_simple()` / `add_simple_color()` → matches row `field_type` to apply icons, labels, colors
- **Row Generation**: Each row must have `field_type` identifier; additional columns passed as keyword arguments to `add_row()`
- **Field Matching**: `render_flexible_table()` matches each row's `field_type` to FieldConfig items to determine styling
- **Table Creation**: `TableBuilder(class_name, table_id)` → `set_columns()` → `row()` → `render()`
- **Text Processing**: `display_width()`, `wrap()`, `pad_*()`, `to_*_case()` for Unicode-aware text manipulation
- **Configuration Access**: `ic()`, `dc()`, `mc()`, `tc()`, `cc()`, `out()` for icons, labels, table config, parse settings
- **Output Flow**: `TableData` → `render_block()` → backend router → `render_flexible_table()` (parser) or `render_html_table()` (HTTP) → `TableBuilder.render()`

## Agent Training Notes

### Render System Integration
- **Table Data Collection**: Create `TableData()` instance, call `add_row(field_type, **columns)` for each row. The `field_type` parameter is required and identifies the row type for FieldConfig matching. Additional columns are passed as keyword arguments (e.g., `name='Item 1', status='active'`).
- **Render Function Usage**: Use `render_block(table_data, FieldConfig(), table_class, overrides, block_type, table_id)` for main table rendering. The function routes to backend-specific renderers automatically.
- **Field Configuration**: Use `FieldConfig` class with methods like `add_header()`, `add_simple()`, `add_group()`, `add_simple_color()` to build field configurations inline. Each configuration maps a `field_type` string to styling rules (icon, label, color, no-flag).
- **Field Type Matching**: Each row's `field_type` (set in `add_row()`) is matched against FieldConfig items. The first matching config is used. If no match, row renders without icon/label styling.
- **Row Processing**: `render_flexible_table()` processes rows by: (1) matching `field_type` to FieldConfig, (2) checking no-flags and conditions, (3) applying icon/label/color from matched config, (4) adding row to TableBuilder.
- **Column Auto-Detection**: Columns are automatically detected from the first row's keys (excluding `field_type`). If `gateway.is_no('label')` is true, the first column is removed.
- **Meta Rendering**: Use `render_block()` with `block_type='meta'` for complex nested data; delegates to `render_meta_table()` which accepts dicts or JSON strings and auto-sizes nested tables
- **Meta Overrides**: `render_meta_table()` trims margin overrides before recursing, measures nested content with `get_max_width()`, and applies the widest value to `column_widths['value']`
- **Header Rendering**: Use `render_header_block(subheader_key, header_id)` with no-flag support for conditional headers
- **Output Finalization**: Header/section blocks call `render_header_block()` → `finalize_output()`; data tables return `TableBuilder.render()` directly
- **Color Integration**: Apply colors using `color_key` in field configurations (calls `apply_color()` from text.color module). Colors are only applied to label text, not data columns.
- **No-Flag Support**: Use `gateway.is_no(flag_name)` to check conditional display flags. FieldConfig items can specify `no_flag` to conditionally hide rows.
- **Backend Routing**: `render_block()` and `render_header_block()` automatically route to parser (CLI) or HTTP (HTML) renderers based on `gateway.backend`

### Table System Usage
- **Table Creation**: Use `TableBuilder(class_name, table_id)` to create new table instances
- **Column Setup**: Use `set_columns("col1,col2,col3")` to define column order
- **Configuration**: Use `set_*()` methods to configure margins, padding, borders, and column settings
- **Data Addition**: Use `row(keys=[...], values=[...])` or `row(pairs=[...])` or `cell(column, value)` to add data
- **Overrides**: Use `apply_overrides({"margin_l": 2, "padl": 1})` to override configuration
- **Rendering**: Use `render()` to generate final formatted table output
- **Separators**: Use `sep(kind='h')` to add horizontal rules between rows

### Text Processing Patterns
- **Display Width**: Use `display_width(text)` to calculate accurate display width for Unicode text
- **Text Wrapping**: Use `wrap(text, width)` for advanced wrapping with color preservation
- **Text Padding**: Use `pad_left()`, `pad_right()`, `pad_center()` for text alignment
- **Case Conversion**: Use `to_snake_case()`, `to_camel_case()`, `to_kebab_case()` for case transformation
- **ANSI Handling**: Use `strip_ansi()` to remove color codes for width calculation
- **Text Slicing**: Use `slice(text, max_width)` for width-aware text truncation
- **Unicode Support**: System handles East Asian characters and special symbols correctly

### Configuration Access
- **Icon Access**: Use `ic(key)` to get icon values from the decorator-based registry system
- **Label Access**: Use `dc(key, default)` to get label values from the decorator-based registry system
- **Table Config**: Use `mc(key)` to get table configuration values from table.ini
- **Parse Config**: Use `tc(key)` and `cc(key)` for parse configuration from parse.ini
- **Caching**: Configuration data is cached for performance (hot cache in-memory, cold cache JSON)
- **Default Values**: Always provide default values for configuration access

### Common Integration Patterns
- **Render Pipeline**: Data → Field Config → Table Builder → Layout → Borders → Cells → Text Tools → Output
- **Configuration Flow**: Decorator Registry (icons/labels) / INI Files (table/parse) → Config System → Render System → Table System → Text Tools
- **Error Handling**: Use gateway error methods for render failures and configuration issues
- **Performance**: Configuration caching and lazy loading for optimal performance
- **Unicode Support**: Full Unicode support with proper width calculation and text processing

---

## 1. Render System

**File**: `hh/render/render.py`

The comprehensive output formatting system that transforms structured data into formatted tables and text output. It provides field configuration management, table data structures, header rendering, and output finalization.

The render system serves as the central orchestrator for all output formatting in the Henhouse system. It provides the core data structures (TableData, FieldConfig) and main entry points (render_block, render_header_block) that delegate to backend-specific renderers (render_parser.py for CLI, render_http.py for HTML).

### Global Module

#### owned by:
- backend modules : *Used by backend handlers for output formatting*

#### owns:
- render functions : *Core rendering functions (render_block, render_header_block, finalize_output)*
- TableData class : *Table data structure for collecting rows*
- FieldConfig class : *Field configuration builder for styling rules*

#### data managed:
- rendering state (local copy) : *Rendering process state and temporary data*
- field configurations (source of truth) : *Field type and display configuration definitions (FieldConfig class)*
- color definitions (source of truth) : *Color codes and names for output styling*

#### calls:
- **render_block()** : *Main table rendering function with field configuration support*
- **render_header_block()** : *Header block rendering with no-flag support*
- **finalize_output()** : *Output finalization and line filtering*
- **TableData()** : *Creates table data instances for data collection*
- **FieldConfig()** : *Creates field configuration instances*
- **config functions (ic, dc, mc, tc, cc)** : *Configuration access calls for icons, labels, and settings*
- **break_section()** : *Adds section breaks between content blocks*

#### called by:
- backend modules (rendering) : *Backend handlers call render functions for output formatting*
- debug systems (table rendering) : *Debug systems use render functions for formatted output*

#### retrieves from:
- config registry (icons, labels) : *Gets icon and label data from decorator-based registry*
- config system (table config, parse config) : *Gets table and parse configuration data from INI files*
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
- config registry : *Icon and label definitions via @register_label decorator system*
- table.ini : *Table formatting configuration settings*
- parse.ini : *Parse configuration settings for text processing*

#### error handling:
- **warn()** : *Logs warnings for rendering issues*
- **gateway error methods** : *Uses gateway error reporting for render failures*

#### cross-references:
- **[Table Builder](#2-table-builder)**: *Uses TableBuilder for table construction*
- **[Config System](#9-config-system)**: *Accesses configuration data for display elements*
- **[Text Tools](#8-text-tools)**: *Uses text utilities for width calculation and formatting*
- **render_parser.py**: *Contains render_flexible_table, render_meta_table, render_dict_contents, render_list_contents, render_simple_value for CLI/parser backend*
- **render_http.py**: *Contains render_html_table, render_html_header for HTTP backend*

---

### TableData Class

**Location**: `hh/render/render.py`

The `TableData` class is the primary data structure for collecting table rows before rendering. It stores row data with field types and optional metadata.

#### Constructor
- **`TableData()`**: Creates a new empty table data instance

#### Methods

- **`add_row(field_type: str, **extra_cols) -> TableData`**: Adds a row to the table data
  - `field_type`: Required field type identifier (e.g., 'header', 'item', 'active_item', 'error_item')
  - `**extra_cols`: Any additional column data as keyword arguments (e.g., `name="Item 1", status="active"`)
  - Returns `self` for method chaining
  - Example: `table_data.add_row('item', name='Item 1', status='active', count=5)`

- **`add_page_link_to_column(column_name: str, page_id: int) -> TableData`**: Adds page link metadata to the most recently added row
  - `column_name`: Name of the column to link
  - `page_id`: Page ID to link to
  - Stores link in `_links` metadata on the row
  - Returns `self` for method chaining

- **`add_image_link_to_column(column_name: str, image_id: int) -> TableData`**: Adds image link metadata to the most recently added row
  - `column_name`: Name of the column to link
  - `image_id`: Image ID to link to
  - Returns `self` for method chaining

- **`add_image_file_link_to_column(column_name: str, src_path: str) -> TableData`**: Adds image file link metadata to the most recently added row
  - `column_name`: Name of the column to link
  - `src_path`: Source path to the image file
  - Returns `self` for method chaining

- **`add_file_link_to_column(column_name: str, src_path: str) -> TableData`**: Adds file link metadata to the most recently added row
  - `column_name`: Name of the column to link
  - `src_path`: Source path to the file
  - Returns `self` for method chaining

- **`num_rows() -> int`**: Returns the number of rows, accounting for no-flag 'header' filtering
  - If `gateway.is_no('header')` is true and there are multiple rows, excludes the first row (header)
  - Otherwise returns total row count

- **`get_rows() -> List[TableRow]`**: Returns the list of rows, accounting for no-flag 'header' filtering
  - If `gateway.is_no('header')` is true and there are multiple rows, returns rows starting from index 1
  - Otherwise returns all rows
  - Used by render functions to get filtered row data

#### Row Structure

Each row is a dictionary with:
- **`field_type`** (required): String identifier for the row's field type (e.g., 'header', 'item', 'active_item')
  - Used to match against FieldConfig items for styling
  - If no FieldConfig match found, row renders without icon/label styling
- **`label`** (optional): Custom label text for the first column
  - **Overrides FieldConfig**: If provided and not empty, completely overrides icon+label from FieldConfig
  - **Color Note**: Custom labels do NOT receive color styling from FieldConfig `color_key` (only FieldConfig-generated labels get colors)
  - Example: `table_data.add_row('item', label='Custom Label', name='Item 1')`
- **Additional columns**: Any extra keyword arguments passed to `add_row()` become column data
  - Column names are auto-detected from first row's keys (excluding `field_type`)
  - Example: `table_data.add_row('item', name='Item 1', status='active', count=5)` creates columns: `name`, `status`, `count`
- **`_links`** (optional): Dictionary of link metadata keyed by column name, containing:
  - `{'type': 'page', 'id': page_id}`
  - `{'type': 'image', 'id': image_id}`
  - `{'type': 'image_file', 'src_path': src_path}`
  - `{'type': 'file', 'src_path': src_path}`
  - Added via `add_*_link_to_column()` methods after adding a row

#### Link Metadata

Rows can include link metadata for HTML rendering. Use the `add_*_link_to_column()` methods after adding a row:

```python
table_data.add_row('item', name='Page Name', page_id=123)
table_data.add_page_link_to_column('name', 123)  # Links 'name' column to page 123

table_data.add_row('item', image_name='Image')
table_data.add_image_link_to_column('image_name', 456)  # Links to image 456
```

Link metadata is stored in `_links` dictionary on the row and is used by HTML renderers to create clickable links.

#### Usage Pattern

```python
table_data = TableData()
table_data.add_row('header', name='Name', status='Status')  # Header row
table_data.add_row('item', name='Item 1', status='active')  # Data row
table_data.add_row('error_item', name='Item 2', status='error')  # Data row with different field_type
```

---

### FieldConfig Class

**Location**: `hh/render/render.py`

The `FieldConfig` class builds field configuration rules that determine how rows are styled, labeled, and displayed based on their `field_type`. It uses a builder pattern to chain configuration methods.

#### Constructor
- **`FieldConfig()`**: Creates a new empty field configuration instance

#### Methods

- **`add_header(header_name: str) -> FieldConfig`**: Adds a header field configuration
  - `header_name`: Field type name for header rows
  - Configures: `field_type=header_name`, `label_key=f'l_{header_name}'`, `icon_key=header_name`, `no_flag='header'`
  - Returns `self` for method chaining

- **`add_headers(header_names: List[str]) -> FieldConfig`**: Adds multiple header field configurations
  - `header_names`: List of header field type names
  - Calls `add_header()` for each name
  - Returns `self` for method chaining

- **`add_simple(field_names: List[str]) -> FieldConfig`**: Adds simple field configurations (no color)
  - `field_names`: List of field type names
  - For each name, configures: `field_type=name`, `label_key=f'l_{name}'`, `icon_key=name`, `no_flag=name`
  - Returns `self` for method chaining
  - Example: `.add_simple(['item', 'active_item', 'error_item'])`

- **`add_group(field_names: List[str], shared_no_flag: str) -> FieldConfig`**: Adds field configurations with a shared no-flag
  - `field_names`: List of field type names
  - `shared_no_flag`: Single no-flag name shared by all fields in the group
  - Useful for grouping related fields that should be hidden together
  - Returns `self` for method chaining

- **`addGroup(field_names: List[str], shared_no_flag: str) -> FieldConfig`**: Alias for `add_group()`

- **`add_simple_color(field_name: str, color: str) -> FieldConfig`**: Adds a field configuration with color styling
  - `field_name`: Field type name
  - `color`: Color name (e.g., 'red', 'green', 'yellow')
  - Configures: `field_type=field_name`, `label_key=f'l_{field_name}'`, `icon_key=field_name`, `color_key=color`, `no_flag=field_name`
  - Returns `self` for method chaining
  - Example: `.add_simple_color('error_item', 'red')`

- **`get_configs() -> List[FieldConfigItem]`**: Returns the list of field configuration items
  - Used internally by render functions to access configurations

#### Field Configuration Item Structure

Each configuration item is a dictionary with:
- **`field_type`** (required): String identifier that matches row `field_type` values
- **`label_key`** (optional): Label lookup key (e.g., `'l_item'` for `dc('l_item')`)
- **`icon_key`** (optional): Icon lookup key (e.g., `'item'` for `ic('item')`)
- **`no_flag`** (optional): No-flag name for conditional display (e.g., `'header'`, `'item'`)
- **`color_key`** (optional): Color name for applying color styling (e.g., `'red'`, `'green'`)
- **`condition`** (optional): Callable function for conditional row display

#### Field Matching Process

When rendering, `render_flexible_table()` matches each row's `field_type` to a FieldConfig item:
1. Iterates through rows from `TableData.get_rows()`
2. For each row, extracts `field_type` from `row_data.get('field_type')`
3. Searches FieldConfig items for matching `field_type`
4. If match found, applies that configuration (icon, label, color, no-flag check)
5. If no match found, renders row without icon/label (plain data only)

#### Usage Pattern

```python
FieldConfig()
    .add_header('header')  # Header row styling
    .add_simple(['item', 'active_item'])  # Default styling for multiple field types
    .add_simple_color('error_item', 'red')  # Colored styling for error items
```

---

### render_block() Function

**Location**: `hh/render/render.py`

The main entry point for rendering table data. Routes to backend-specific renderers and handles special cases like meta tables.

#### Signature
```python
render_block(
    table_data: TableData, 
    field_configs: FieldConfig = None, 
    table_class: str = 'standard',
    table_overrides: Dict[str, Union[str, int, bool]] = None,
    block_type: str = None,
    table_id: str = None
) -> str
```

#### Parameters
- **`table_data`**: `TableData` instance containing rows to render
- **`field_configs`**: `FieldConfig` instance (optional, defaults to empty `FieldConfig()`)
- **`table_class`**: Table class name for styling (e.g., 'standard', 'div', 'double')
- **`table_overrides`**: Dictionary of table configuration overrides (e.g., `{'margin_l': 4, 'padl': 2}`)
- **`block_type`**: Optional block type identifier (e.g., 'meta', 'maintenance')
  - If `'meta'`, uses special meta table rendering
  - Also checked against no-flags (if `gateway.is_no(block_type)` is true, returns empty string)
- **`table_id`**: Optional table ID string (used for HTML rendering, stored but not used in CLI)

#### Behavior

1. **Gateway Check**: Returns empty string if no gateway available
2. **Block Type No-Flag Check**: If `block_type` is provided and `gateway.is_no(block_type)` is true, returns empty string
3. **Empty Data Check**: If `table_data.num_rows() == 0`, returns empty string
4. **Meta Table Handling**: If `block_type == 'meta'`:
   - Imports `render_meta_table` from `render_parser`
   - Creates default FieldConfig with `add_header('meta_header')` and `add_simple(['meta', 'sub_meta'])`
   - Applies default meta overrides: `{'padl': 2, 'padr': 2, 'column_align': {'label': 'right'}}`
   - Merges with provided `table_overrides`
   - Calls `render_meta_table()` with `table_class='div'`
5. **Backend Routing**:
   - If `gateway.backend == "http"`: Imports `render_html_table` from `render_http` and calls it
   - Otherwise: Imports `render_flexible_table` from `render_parser` and calls it
6. **Returns**: Formatted table string (CLI text or HTML)

#### Usage Pattern

```python
result = render_block(
    table_data,
    FieldConfig()
        .add_header('header')
        .add_simple(['item', 'active_item'])
        .add_simple_color('error_item', 'red'),
    table_class='standard',
    table_overrides={'margin_l': 4},
    block_type='maintenance',
    table_id='maintenance_table'
)
```

---

### render_flexible_table() Function

**Location**: `hh/render/render_parser.py`

The parser/CLI-specific table renderer that processes `TableData` rows, matches them to `FieldConfig` rules, and builds formatted tables using `TableBuilder`.

#### Signature
```python
render_flexible_table(
    table_data: TableData, 
    table_id: str, 
    field_configs: FieldConfig = None, 
    table_class: str = 'standard', 
    table_overrides: Dict[str, Union[str, int, bool]] = None
) -> str
```

#### Processing Flow

1. **Get Rows**: Calls `table_data.get_rows()` to get filtered row list (respects no-flag 'header')
2. **Column Auto-Detection**: 
   - Extracts column names from first row's keys
   - Excludes `'field_type'` key
   - If `gateway.is_no('label')` is true, removes first column (label column)
3. **TableBuilder Setup**:
   - Creates `TableBuilder(table_class, table_id)`
   - Sets columns with `tb.set_columns(','.join(columns))`
   - If multiple columns, sets final column width to `mc('config_trim_width')` and overflow to `'wrap'`
   - Applies `table_overrides` if provided
4. **Row Processing Loop**:
   - For each row in data:
     - **Field Matching**: Searches `field_configs` for matching `field_type`
     - **No Match**: If no matching config found, renders row with plain data (no icon/label)
     - **Match Found**: 
       - Checks `no_flag`: If `matching_field_config.get('no_flag')` and `gateway.is_no(no_flag)` is true, skips row
       - Checks `condition`: If `matching_field_config.get('condition')` exists and returns false, skips row
       - **Label Column Processing** (if `!gateway.is_no('label')`):
         - **Custom Label Override**: If `row_data['label']` exists and is not empty, uses that directly (overrides FieldConfig icon/label)
         - **FieldConfig Label**: Otherwise, gets icon: `ic(matching_field_config['icon_key'])` if `icon_key` exists, and gets label: `dc(matching_field_config['label_key'], True)` if `label_key` exists
         - **Color Application**: If `color_key` exists in matching config, wraps label text with `apply_color(label_text, color_name)` (only applies if using FieldConfig label, not custom label)
         - Final label column content: custom `row_data['label']` if present, otherwise `icon + label_text` from FieldConfig
       - **Data Columns**: Processes remaining columns with `out(safe_str(row_data[col]))`
     - Adds row to TableBuilder with `tb.row(keys=columns, values=row_values)`
5. **Render**: Calls `tb.render()` and returns formatted table string

#### Field Config Matching Details

- Matching is done by comparing `row_data.get('field_type')` to `field_config.get('field_type')`
- First matching config is used (stops at first match)
- If no match, row is rendered without icon/label styling
- Field configs are accessed via `field_configs.get_configs()` which returns list of config dictionaries

#### Color Application

- Colors are applied via `apply_color()` from `hh.render.text.color` module
- Only applied to label text when `color_key` is present in matching field config
- Color is applied after label text is retrieved but before being placed in row

#### Usage Example

```python
# In render_block(), this calls render_flexible_table():
table_data = TableData()
table_data.add_row('header', name='Name', status='Status')
table_data.add_row('item', name='Item 1', status='active')
table_data.add_row('error_item', name='Item 2', status='error')

field_configs = FieldConfig()
    .add_header('header')
    .add_simple(['item'])
    .add_simple_color('error_item', 'red')

result = render_flexible_table(table_data, '', field_configs, 'standard', None)
# Result: Formatted table with header row, plain item row, and red-colored error item row
```

---

## 1.5. Render Parser Module

**File**: `hh/render/render_parser.py`

The parser/CLI-specific rendering module that handles table and metadata rendering for command-line output.

### Key Functions

- **`render_flexible_table(table_data, table_id, field_configs, table_class, table_overrides)`**: Renders tables for CLI output with column auto-detection
  - Takes TableData and FieldConfig instances
  - Auto-detects columns from first row
  - Creates TableBuilder instance with `TableBuilder(table_class, table_id)`
  - Applies field configurations for labels, icons, and colors
  - Returns formatted table string

- **`render_meta_table(table_data, table_id, field_configs, table_class, table_overrides, block_type)`**: Recursive metadata table rendering for nested data structures
  - Handles dict and list nesting
  - Auto-sizes nested tables using `get_max_width()`
  - Trims margin overrides before recursing
  - Applies widest nested width to `column_widths['value']`

- **`render_dict_contents(value_dict, table_id, field_configs, table_class, table_overrides, block_type)`**: Renders dictionary content with nested structure support
  - Recursively processes nested dicts and lists
  - Returns formatted table string

- **`render_list_contents(value_list, table_id, field_configs, table_class, table_overrides, block_type)`**: Renders list content with nested structure support
  - Recursively processes nested dicts and lists
  - Returns formatted table string

- **`render_simple_value(value)`**: Simple value rendering and type conversion
  - Converts value to string using `safe_str()`
  - Returns formatted string

- **`render_parser_header(subheader_key, header_id)`**: Parser/CLI header renderer
  - Renders headers as plain text for CLI output
  - Uses `dc()` for label lookup
  - Returns formatted header string

### Cross-references
- **render.py**: Imports TableData and FieldConfig from render module
- **Table Builder**: Uses TableBuilder for table construction
- **Text Tools**: Uses get_max_width() for nested table sizing

---

## 1.6. Render HTTP Module

**File**: `hh/render/render_http.py`

The HTTP/HTML-specific rendering module that handles table and header rendering for web output.

### Key Functions

- **`render_html_table(table_data, table_id, field_configs, table_class, table_overrides)`**: HTML renderer for tables
  - Delegates to `render_html_flexible_table()` from html/html_flexible.py
  - Returns HTML table string

- **`render_html_header(subheader_key, header_id)`**: HTML renderer for headers
  - Renders headers as HTML content
  - Uses `dc()` for label lookup
  - Returns HTML header string (no wrapper div - response object handles wrapping)

### Cross-references
- **render.py**: Imports TableData and FieldConfig from render module
- **html/html_flexible.py**: Contains actual HTML table rendering implementation

---

## 2. Table Builder

**File**: `hh/render/table/table.py`

The table formatting system that transforms structured data into formatted tables through coordinated modules. Acts as the main orchestrator and data collector, managing table construction, column configuration, and cell content assembly.

The TableBuilder serves as the central coordinator for the entire table rendering pipeline. It manages the data collection process, applies configuration settings, and orchestrates the various table modules to produce the final formatted output. The builder pattern allows for fluent configuration and incremental data addition while maintaining clean separation of concerns between data management, layout calculation, border rendering, and cell processing.

### TableBuilder Class

#### owned by:
- render system : *Created by render functions for table construction*

#### constructor:
- **`TableBuilder(class_name: str, table_id: str)`**: Creates new table builder instance
  - `class_name`: Table class name for configuration lookup (e.g., 'standard', 'div', 'double')
  - `table_id`: Table ID string (stored but not used in CLI output, available for HTML rendering)

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
- **render(class_name=None)** : *Renders final table with borders and formatting (uses self.class_name if class_name not provided)*

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
- **load_table_config(class_name)** : *Loads table configuration from INI files for specified class*
- **update_column_config(config, columns)** : *Updates column-specific configuration settings*
- **apply_config_overrides(config, overrides)** : *Applies configuration overrides to existing config*
- **conf_str(cls, name), conf_int(cls, name)** : *Configuration value access functions*

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
- **calculate_column_layouts(config, columns, table_data)** : *Calculates optimal column layouts based on content and config*
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
- **normalize_glyphs(config)** : *Normalizes and aligns border glyphs for consistent rendering*
- **build_top_border(glyphs, column_layouts, column_order)** : *Builds top table border with proper glyph alignment*
- **build_header_border(glyphs, column_layouts, column_order)** : *Builds header separator border*
- **build_mid_border(glyphs, column_layouts, column_order)** : *Builds mid-row separator border*
- **build_bottom_border(glyphs, column_layouts, column_order)** : *Builds bottom table border*
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
- **shape_cell(layout, text)** : *Shapes individual cell content based on layout settings*
- **align_line(layout, line)** : *Aligns text within cell based on alignment settings*
- **shape_column(column_name, rows, layout)** : *Shapes entire column content with consistent formatting*
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
- **display_width(s)** : *Calculates display width for Unicode text with ANSI filtering*
- **wrap(text, width)** : *Advanced text wrapping with color preservation and intelligent word breaking*
- **wrap_simple(text, width, indent='', pad_all_lines=False, first_line_extra_indent='')** : *Simple text wrapping without color handling*
- **ellipsize(text, width, glyph='…')** : *Text ellipsizing with display width awareness*
- **ellipsize_simple(text, width, glyph='…')** : *Simple text ellipsizing without display width*
- **pad(text, target)** : *Text padding with display width*
- **pad_simple(text, target)** : *Simple text padding without display width*
- **pad_left(text, width, char=' ')** : *Left padding with display width*
- **pad_left_simple(text, width, char=' ')** : *Simple left padding without display width*
- **pad_right(text, width, char=' ')** : *Right padding with display width*
- **pad_right_simple(text, width, char=' ')** : *Simple right padding without display width*
- **pad_center(text, width, char=' ')** : *Center padding with display width*
- **pad_center_simple(text, width, char=' ')** : *Simple center padding without display width*
- **slice(text, maxw)** : *Text slicing with display width calculation*
- **slice_simple(text, maxw)** : *Simple text slicing without display width*
- **justify(text, width)** : *Text justification with proper spacing*
- **justify_simple(text, width)** : *Simple text justification*
- **to_snake_case(text)** : *Converts text to snake_case*
- **to_camel_case(text)** : *Converts text to camelCase*
- **to_kebab_case(text)** : *Converts text to kebab-case*
- **to_title_case(text)** : *Converts text to Title Case*
- **clean_whitespace(text)** : *Whitespace normalization*
- **clean_whitespace_simple(text)** : *Simple whitespace normalization*
- **strip_ansi()** : *ANSI escape sequence removal (from text.color module)*
- **strip_ansi_simple(text)** : *Simple ANSI removal*
- **indent(text, prefix='  ', skip_first=False)** : *Text indentation*
- **indent_simple(text, prefix='  ', skip_first=False)** : *Simple text indentation*
- **dedent(text)** : *Text dedentation*
- **dedent_simple(text)** : *Simple text dedentation*
- **normalize_line_endings(text)** : *Normalizes line endings to \n*
- **normalize_line_endings_simple(text)** : *Simple line ending normalization*
- **repeat_pattern(pattern, width)** : *Repeats pattern to fill width*
- **repeat_pattern_simple(pattern, width)** : *Simple pattern repetition*
- **get_max_width(table_output)** : *Calculates maximum width from table output*
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

The config system serves as the central access point for all configuration data in the Henhouse system. It provides a unified API for accessing icons (from decorator-based registry), labels (from decorator-based registry), table configuration (from table.ini), and parse settings (from parse.ini) through simple function calls. The system implements lazy loading and caching to ensure optimal performance while providing a clean abstraction layer between the registry/INI file storage and the consuming modules.

### Global Module

#### owned by:
- global scope : *Module-level configuration management*

#### owns:
- config functions : *Configuration access functions (ic, dc, mc, tc, cc, out)*
- cached config data : *Cached configuration data from registry (icons/labels) and INI files (table/parse)*

#### data managed:
- icon registry (hot/cold cache) : *Icon configuration data from @register_label decorator system*
- label registry (hot/cold cache) : *Label configuration data from @register_label decorator system*
- table.ini data (cached) : *Table configuration data from table.ini*
- parse.ini data (cached) : *Parse configuration data from parse.ini*

#### calls:
- **ic(name)** : *Gets icon value from decorator-based registry (checks hot cache, then cold cache, then rebuilds) with no-flag support*
- **dc(name, add_tc=False)** : *Gets label/description value from decorator-based registry (checks hot cache, then cold cache, then rebuilds) with no-flag support*
- **mc(name)** : *Gets integer configuration value from parse.ini*
- **tc(repeat=1, mode=None)** : *Gets tab character with optional repeat and mode*
- **cc(name)** : *Gets string configuration value from parse.ini*
- **out(value)** : *Converts value to string and marks section as having output*
- **get_str(key, caller_file=None)** : *Gets string configuration value with hierarchical lookup (registry for icons/labels, INI for table/parse)*
- **get_int(key, caller_file=None)** : *Gets integer configuration value with hierarchical lookup*
- **conf_str(cls, name, caller_file=None)** : *Gets table configuration string value from table.ini*
- **conf_int(cls, name, caller_file=None)** : *Gets table configuration integer value from table.ini*
- **safe_str(value, max_length=1000)** : *Safely converts value to string*
- **break_section(lines)** : *Adds section break if section has output*
- **configparser.ConfigParser()** : *Parses INI files for table/parse configuration data*
- **_read_flat_ini()** : *Reads flat INI structure for configuration access*
- **get_icon(name)** : *Gets icon from config_registry (from hh.render.config.config_registry)*
- **get_label(name)** : *Gets label from config_registry (from hh.render.config.config_registry)*

#### called by:
- render system (ic(), dc(), mc(), tc(), cc()) : *Render system accesses config for display elements*
- all modules (configuration access) : *All modules access configuration through config functions*

#### retrieves from:
- config registry (icons, labels) : *Gets icon and label data from decorator-based registry system (config_registry.py)*
- INI files (table, parse) : *Gets table and parse configuration from table.ini and parse.ini files on disk*

#### provides to:
- render system (icons, labels, table config) : *Provides configuration data to render system*
- all modules (configuration values) : *Provides configuration values to all modules*

#### configuration dependencies:
- config registry : *Icon and label definitions via @register_label decorator system (config_registry.py)*
- table.ini : *Table formatting configuration*
- parse.ini : *Parse configuration settings*

#### error handling:
- **warn()** : *Logs warnings for configuration loading issues*

#### cross-references:
- **config_registry.py**: *Icon and label registry system with @register_label decorator and hot/cold cache*
- **[INI Configuration Files](#10-ini-configuration-files)**: *Reads table and parse configuration from INI files*
- **[Render System](#1-render-system)**: *Provides configuration to render system*

---

## 10. Config Registry System

**File**: `hh/render/config/config_registry.py`

The decorator-based registration system for icons and labels that replaces the old .ini file system.

The config registry system provides a Python-based registration mechanism for icons and labels using the `@register_label` decorator. Icons and labels are registered in `config_labels.py` files throughout the codebase. The system uses a hot cache (in-memory registry) and cold cache (JSON file) for fast lookups. The registry automatically scans for `@register_label` decorators and builds a cache of all registered icons and labels.

### Global Module

#### owned by:
- global scope : *Module-level registry management*

#### owns:
- registry functions : *Icon and label registration and lookup functions*
- hot cache : *In-memory registry (_icon_registry, _label_registry)*
- cold cache : *JSON cache file (config-registry.json)*

#### data managed:
- icon registry (hot/cold cache) : *Icon definitions registered via @register_label decorator*
- label registry (hot/cold cache) : *Label definitions registered via @register_label decorator*

#### calls:
- **register_label(name, label_value, icon_value=None)** : *Decorator for registering a label and optionally an icon*
- **get_icon(name)** : *Gets icon from registry (checks hot cache, then cold cache, then rebuilds)*
- **get_label(name)** : *Gets label from registry (checks hot cache, then cold cache, then rebuilds)*
- **discover_config_registrations(force_regenerate=False)** : *Discovers all icon and label registrations and builds cache*
- **_scan_for_config_registrations()** : *Scans hh folder tree for files containing @register_label decorators*
- **_import_modules(module_paths)** : *Imports modules containing @register_label decorators*

#### called by:
- config system (icon/label lookup) : *Config system calls get_icon() and get_label() for icon/label access*

#### retrieves from:
- Python modules : *Scans Python modules for @register_label decorators*
- cache file : *Reads cached registry data from JSON file*

#### provides to:
- config system (icons, labels) : *Provides icon and label data to config system*

#### configuration dependencies:
- none : *Registry system is self-contained*

#### error handling:
- **warn()** : *Logs warnings for duplicate registrations and import errors*

#### cross-references:
- **[Config System](#9-config-system)**: *Provides icon and label data to config system*
- **config_labels.py files**: *Files throughout codebase that register icons and labels using @register_label decorator*

---

## 11. INI Configuration Files

**File**: `hh/render/config/table.ini`, `hh/render/config/parse.ini`

The configuration data storage system that provides table and parse configuration data through INI files.

The INI configuration files serve as the persistent storage layer for table formatting settings and parse configuration. Icons and labels are no longer stored in .ini files; they use the decorator-based registry system (see [Config Registry System](#10-config-registry-system)). The remaining INI files provide a human-readable format for storing table formatting settings and parse configuration.

### Global Module

#### owned by:
- file system : *Configuration files on disk*

#### owns:
- table.ini : *Table formatting configuration settings*
- parse.ini : *Parse configuration settings for text processing*

#### data managed:
- table configuration data (source of truth) : *Table formatting configuration stored in table.ini*
- parse configuration data (source of truth) : *Parse configuration stored in parse.ini*

#### calls:
- none : *Static configuration files*

#### called by:
- config system (file reading) : *Config system reads INI files for table and parse configuration data*

#### retrieves from:
- none : *Static configuration files*

#### provides to:
- config system (configuration data) : *Provides table and parse configuration data to config system*

#### configuration dependencies:
- none : *Static configuration files*

#### error handling:
- **file system errors** : *Handles file system errors for configuration file access*

#### cross-references:
- **[Config System](#9-config-system)**: *Provides table and parse configuration data to config system*
- **[Config Registry System](#10-config-registry-system)**: *Icons and labels use registry system instead of .ini files*
