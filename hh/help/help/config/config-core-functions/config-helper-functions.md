# config-helper-functions
## description
Core helper functions for getting configuration values, checking flags, logging usage, and formatting output in the parser system.
## summary
Twelve helper functions that provide the main interface to the configuration system. Functions get values from .ini files (icon.ini, label.ini, table.ini, parse.ini), check --no-* flags, log usage statistics, and format output. The system uses intelligent file routing where t_* keys go to table.ini, l_* keys to label.ini, max_*/config_* keys to parse.ini, and everything else to icon.ini. All functions include comprehensive logging and error handling.
## full_text
The helper functions are the primary interface for accessing configuration values and formatting output in the parser system. They provide a consistent API for getting values from multiple .ini files, checking command-line flags, logging usage statistics, and managing output formatting.

**Configuration File Routing:**
The system automatically routes configuration keys to the correct .ini file:
- `t_*` keys → `table.ini` (table styling and layout)
- `l_*` keys → `label.ini` (text labels for UI elements)  
- `max_*` or `config_*` keys → `parse.ini` (parser settings and limits)
- All other keys → `icon.ini` (emoji and symbol definitions)

**Core Functions:**
- `get_str(key)` - Gets string values from any config file
- `get_int(key)` - Gets integer values with validation and error handling
- `ic(name)` - Gets icons from icon.ini with --no-icon flag support
- `dc(name, add_tc=False)` - Gets labels from label.ini with --no-desc flag support
- `mc(name)` - Gets integer values with error handling and logging
- `tc(repeat=1, mode=None)` - Creates tab characters with spacing modes
- `out(value)` - Converts any value to safe string and tracks output
- `break_section(lines)` - Adds spacing between output sections

**Table Configuration Functions:**
- `conf_str(cls, name)` - Gets table configuration string values
- `conf_int(cls, name)` - Gets table configuration integer values

**Flag and Argument Functions:**
- `setup_argparse(no_flags_config, args)` - Sets up argument parsing for --no-* flags
- `is_no(group, no_flags_config)` - Checks if --no-* flags are set
- `log_no_flag(group)` - Logs usage of --no-* flags

**Logging System:**
Every function call logs to timestamp files (`config.log.<type>`) and count files (`config.log.<type>.counts.json`) for comprehensive usage tracking and statistics.

**Section Output Tracking:**
Functions that produce output (`ic()`, `dc()`, `out()`) set `_section_has_output = True` when they return non-empty values. This is used by `break_section()` to add appropriate spacing between different sections of parser output.

# get-str-function
## description
Gets string values from configuration files using intelligent file routing.
## summary
get_str() function is the core function for retrieving string values from .ini files. It automatically routes keys to the correct configuration file based on key prefixes and strips quotes from values.
## full_text
The get_str() function is the fundamental way to retrieve string values from configuration files.

**Function:**
```python
def get_str(key: str) -> str:
```

**What it does:**
1. Calls `_raw_get(key)` to get the raw value from the appropriate .ini file
2. Returns the string value with quotes stripped

**File Routing:**
The underlying `_raw_get()` function automatically routes keys:
- `t_*` keys → `table.ini` (table styling and layout)
- `l_*` keys → `label.ini` (text labels for UI elements)
- `max_*` or `config_*` keys → `parse.ini` (parser settings and limits)
- All other keys → `icon.ini` (emoji and symbol definitions)

**Quote Handling:**
All values are automatically stripped of surrounding quotes using `.strip('"')`.

**Example:**
```python
icon = get_str('agent')  # Returns "🤖" from icon.ini
label = get_str('l_agent_id')  # Returns "Agent ID:" from label.ini
table_style = get_str('t_standard_has_header')  # Returns "1" from table.ini
```

**Error Handling:**
Returns empty string if key is not found or file cannot be read.

---

# get-int-function
## description
Gets integer values from configuration files with validation and error handling.
## summary
get_int() function retrieves integer values from configuration files, validates they are non-negative, and handles errors gracefully by returning 0 for invalid values.
## full_text
The get_int() function retrieves and validates integer values from configuration files.

**Function:**
```python
def get_int(key: str) -> int:
```

**What it does:**
1. Calls `_raw_get(key)` to get the raw value from the appropriate .ini file
2. If value is empty: returns 0
3. Attempts to convert value to integer
4. If conversion fails: returns 0
5. If value is negative: returns 0
6. Returns the integer value

**Validation Rules:**
- Empty values return 0
- Invalid values (non-numeric) return 0
- Negative values return 0
- Only non-negative integers are returned

**Example:**
```python
margin = get_int('t_standard_padl')  # Returns 1 from table.ini
max_length = get_int('max_json_length')  # Returns 1000 from parse.ini
invalid = get_int('nonexistent')  # Returns 0
```

**Error Handling:**
All errors (missing keys, invalid values, negative numbers) result in returning 0, ensuring the system continues to function.

---

# icon-functions
## description
Gets icons from icon.ini file with --no-icon flag support and comprehensive logging.
## summary
ic() function gets icon values from icon.ini, checks --no-icon flag, logs usage statistics, and tracks output for section breaks. Includes global state management for output tracking.
## full_text
The ic() function gets icon values from the icon.ini configuration file with flag checking and logging.

**Function:**
```python
def ic(name: str) -> str:
```

**What it does:**
1. Checks if --no-icon flag is set using `is_no('icon')`
2. If flag is set: calls `log_no_flag('icon')`, logs icon access as present=False, returns ""
3. If flag not set: gets value from icon.ini using `get_str(name)`
4. If value exists: sets global `_section_has_output = True`
5. Logs the access with timestamp and count using `_touch_timestamp_log()` and `_increment_count()`
6. Returns the icon value or ""

**Global State:**
Uses global `_section_has_output` flag to track whether any content has been output in the current section. This is used by `break_section()` to add appropriate spacing.

**Logging:**
- Logs to `config.log.ic` timestamp file
- Logs to `config.log.ic.counts.json` with usage statistics
- Tracks both present and missing icon accesses

**Example:**
```python
icon = ic('agent')  # Returns "🤖" or "" if --no-icon
icon = ic('help_topic')  # Returns "❓" or "" if --no-icon
icon = ic('nonexistent')  # Returns "" and logs as missing
```

**Integration:**
Used throughout the parser system for consistent icon display. Works with the table rendering system to provide visual indicators for different data types.

---
# label-functions
## description
Gets labels from label.ini file with --no-desc flag support, optional tab character, and comprehensive logging.
## summary
dc() function gets label values from label.ini, checks --no-desc flag, can add tab character using tc(), logs usage statistics, and tracks output for section breaks.
## full_text
The dc() function gets label values from the label.ini configuration file with flag checking and optional formatting.

**Function:**
```python
def dc(name: str, add_tc: bool = False) -> str:
```

**What it does:**
1. Checks if --no-desc flag is set using `is_no('desc')`
2. If flag is set: calls `log_no_flag('desc')`, logs label access as present=False, returns ""
3. If flag not set: gets value from label.ini using `get_str(name)`
4. If value exists: sets global `_section_has_output = True`
5. If add_tc=True: prepends tab character using `tc()` function
6. Logs the access with timestamp and count using `_touch_timestamp_log()` and `_increment_count()`
7. Returns the label value or ""

**Tab Character Integration:**
When `add_tc=True`, calls `tc()` to prepend the appropriate tab character. This is commonly used for indented labels in table output.

**Global State:**
Uses global `_section_has_output` flag to track whether any content has been output in the current section.

**Logging:**
- Logs to `config.log.dc` timestamp file
- Logs to `config.log.dc.counts.json` with usage statistics
- Tracks both present and missing label accesses

**Example:**
```python
label = dc('l_agent_id')  # Returns "Agent ID:" or "" if --no-desc
label = dc('l_agent_id', True)  # Returns "  Agent ID:" or "" if --no-desc
label = dc('l_help_topic')  # Returns "Help:" or "" if --no-desc
```

**Integration:**
Used throughout the parser system for consistent label display. Works with the table rendering system to provide descriptive labels for data fields.

---
# margin-functions
## description
Gets integer values from configuration files with error handling and comprehensive logging.
## summary
mc() function gets integer values from config files, validates they're non-negative, handles errors gracefully, and logs usage statistics for tracking.
## full_text
The mc() function gets integer values from configuration files with validation and logging.

**Function:**
```python
def mc(name: str) -> int:
```

**What it does:**
1. Calls `get_int(name)` to get integer value from config file
2. Validates the value is non-negative (>= 0)
3. If value is negative: converts to 0
4. If any error occurs: returns 0
5. Logs the access with timestamp and count using `_touch_timestamp_log()` and `_increment_count()`
6. Returns the integer value or 0

**Validation:**
- Uses `get_int()` which already handles missing keys and invalid values
- Additional validation ensures only non-negative integers are returned
- All errors result in returning 0

**Logging:**
- Logs to `config.log.mc` timestamp file
- Logs to `config.log.mc.counts.json` with usage statistics
- Tracks both present and missing margin accesses

**Example:**
```python
margin = mc('t_standard_padl')  # Returns 1 from table.ini
margin = mc('t_standard_margin_l')  # Returns 0 from table.ini
margin = mc('nonexistent')  # Returns 0 and logs as missing
```

**Integration:**
Used for getting margin, padding, and other numeric configuration values. Commonly used with table styling and layout settings.

---
# tab-functions
## description
Creates tab characters with different spacing modes using configuration values.
## summary
tc() function creates tab characters with repeat and spacing options using tab and blank_emoji values from icon.ini configuration file.
## full_text
The tc() function creates tab characters with different spacing modes and repeat patterns.

**Function:**
```python
def tc(repeat: int = 1, mode: Optional[int] = None) -> str:
```

**What it does:**
1. Gets base tab character from icon.ini using `get_str('tab')` (usually "  ")
2. Gets blank_emoji from icon.ini using `get_str('blank_emoji')` for spacing
3. If repeat <= 1 and no mode: returns base tab
4. If repeat <= 1 with mode: adds blank_emoji before/after tab based on mode
5. If repeat > 1: repeats tabs with spacing based on mode
6. Returns the constructed tab string

**Spacing Modes:**
- Mode 1: Add blanks between tabs when repeating
- Mode 2: Add blanks before tabs
- Mode 3: Add blanks after tabs  
- Mode 4: Add blanks before and after tabs
- None: No additional spacing

**Configuration Values:**
- `tab` from icon.ini: Base tab character (default "  ")
- `blank_emoji` from icon.ini: Spacing character (default "  ")

**Example:**
```python
tab = tc()  # Returns "  " (base tab)
tabs = tc(3)  # Returns "      " (6 spaces)
tabs = tc(3, 1)  # Returns "  ·  ·  " (with blank emoji between)
tabs = tc(2, 2)  # Returns "·  ·  " (blank before each tab)
tabs = tc(2, 4)  # Returns "·  ·  ·" (blank before and after)
```

**Integration:**
Used by `dc()` function when `add_tc=True` to create indented labels. Also used directly in parsers for consistent indentation.

---
# output-functions
## description
Converts any value to safe string and tracks output for section breaks.
## summary
out() function converts any value to string using safe_str(), tracks output for section breaks, and manages global output state.
## full_text
The out() function converts any value to a safe string and tracks output state.

**Function:**
```python
def out(value: Any) -> str:
```

**What it does:**
1. Calls `safe_str(value)` to convert value to string safely
2. If result is not empty: sets global `_section_has_output = True`
3. Returns the string

**Safe String Conversion:**
Uses `safe_str()` from the text module which handles:
- Unicode characters and emoji
- Display-width aware processing
- Error handling for non-string values
- Proper encoding

**Global State:**
Uses global `_section_has_output` flag to track whether any content has been output in the current section. This is used by `break_section()` to add appropriate spacing.

**Example:**
```python
output = out(agent_id)  # Returns string representation
output = out({'id': 123})  # Returns JSON string
output = out("Hello 🌍")  # Returns safe Unicode string
output = out(None)  # Returns empty string
```

**Integration:**
Used throughout the parser system for safe value conversion. Works with the section tracking system to manage output spacing.

---
# break-section
## description
Adds spacing between output sections based on whether content was output.
## summary
break_section() function checks if any content was output and adds a blank line if needed. Used to control spacing between different sections of parser output.
## full_text
The break_section() function adds spacing between output sections.

**Function:**
```python
def break_section(lines: List[str]) -> None:
```

**What it does:**
1. Checks if global `_section_has_output` is True
2. If True: adds a blank line to the lines list
3. Resets global `_section_has_output` to False
4. Does nothing if no content was output

**Global State Management:**
Uses global `_section_has_output` flag which is set by:
- `ic()` when returning non-empty icon values
- `dc()` when returning non-empty label values  
- `out()` when returning non-empty string values

**Usage:**
```python
lines = []
# Add some content
lines.append("Some output")
break_section(lines)  # Adds blank line if content was output
# Add more content
lines.append("More output")
```

**Integration:**
Used by parsers to control spacing between different sections of output. Ensures clean separation between logical sections without unnecessary blank lines when no content was produced.

---

# conf-str-function
## description
Gets table configuration string values using class and name parameters.
## summary
conf_str() function gets table configuration string values by constructing t_<class>_<name> keys and routing them to table.ini configuration file.
## full_text
The conf_str() function gets table configuration string values using class and name parameters.

**Function:**
```python
def conf_str(cls: str, name: str) -> str:
```

**What it does:**
1. Constructs key as `t_{cls}_{name}`
2. Calls `get_str()` to get value from table.ini
3. Returns the string value

**Key Construction:**
- `cls` parameter becomes the table class name
- `name` parameter becomes the specific setting name
- Combined as `t_<class>_<name>` for table.ini lookup

**Example:**
```python
style = conf_str('standard', 'has_header')  # Gets t_standard_has_header
columns = conf_str('minimal', 'columns')  # Gets t_minimal_columns
border = conf_str('double', 'top_left')  # Gets t_double_top_left
```

**Integration:**
Used by table rendering system to get table-specific configuration values. Provides a clean API for accessing table styling and layout settings.

---

# conf-int-function
## description
Gets table configuration integer values using class and name parameters.
## summary
conf_int() function gets table configuration integer values by constructing t_<class>_<name> keys and routing them to table.ini configuration file.
## full_text
The conf_int() function gets table configuration integer values using class and name parameters.

**Function:**
```python
def conf_int(cls: str, name: str) -> int:
```

**What it does:**
1. Constructs key as `t_{cls}_{name}`
2. Calls `get_int()` to get value from table.ini
3. Returns the integer value

**Key Construction:**
- `cls` parameter becomes the table class name
- `name` parameter becomes the specific setting name
- Combined as `t_<class>_<name>` for table.ini lookup

**Example:**
```python
padding = conf_int('standard', 'padl')  # Gets t_standard_padl
margin = conf_int('minimal', 'margin_l')  # Gets t_minimal_margin_l
width = conf_int('double', 'width_label')  # Gets t_double_width_label
```

**Integration:**
Used by table rendering system to get table-specific numeric configuration values. Provides a clean API for accessing table styling and layout settings.

---

# setup-argparse-function
## description
Sets up argument parsing for --no-* flags used throughout the parser system.
## summary
setup_argparse() function configures argparse to handle --no-* flags based on the provided no_flags_config list and parses command line arguments.
## full_text
The setup_argparse() function sets up argument parsing for --no-* flags used throughout the parser system.

**Function:**
```python
def setup_argparse(no_flags_config: Optional[List[str]] = None, args: Optional[List[str]] = None) -> argparse.Namespace:
```

**What it does:**
1. Creates an ArgumentParser instance
2. If no_flags_config provided: adds --no-<flag> arguments for each flag
3. Parses arguments from args list or sys.argv
4. Stores parsed arguments in global _args variable
5. Returns the parsed arguments namespace

**Flag Configuration:**
- `no_flags_config`: List of flag names to create --no-* arguments for
- Each flag becomes a `--no-<flag>` boolean argument
- Flags are used by `is_no()` function to check if they're set

**Global State:**
Sets global `_args` variable which is used by `is_no()` function to check flag states.

**Example:**
```python
# Setup with specific flags
setup_argparse(['icon', 'desc', 'header'])
# Now --no-icon, --no-desc, --no-header are available

# Parse specific arguments
args = setup_argparse(['icon'], ['--no-icon'])
# args.no_icon will be True
```

**Integration:**
Used by parser modules to set up command-line argument parsing. Must be called before using `is_no()` function.

---

# is-no-function
## description
Checks if --no-* flags are set using the global arguments state.
## summary
is_no() function checks if a specific --no-* flag is set by examining the global _args variable and logging the flag usage.
## full_text
The is_no() function checks if --no-* flags are set and logs their usage.

**Function:**
```python
def is_no(group: str, no_flags_config: Optional[List[str]] = None) -> bool:
```

**What it does:**
1. Checks if global `_args` is set, calls `setup_argparse()` if not
2. Gets the flag value from `_args.no_{group}`
3. Logs the flag usage with timestamp and count
4. Returns True if flag is set, False otherwise

**Flag Checking:**
- Looks for `no_{group}` attribute on the arguments namespace
- Returns False if attribute doesn't exist
- Converts result to boolean

**Logging:**
- Logs to `config.log.no` timestamp file
- Logs to `config.log.no.counts.json` with usage statistics
- Tracks both present and missing flag checks

**Example:**
```python
# After setup_argparse(['icon', 'desc'])
if is_no('icon'):  # Checks --no-icon flag
    print("Icons disabled")
if is_no('desc'):  # Checks --no-desc flag
    print("Descriptions disabled")
```

**Integration:**
Used by `ic()` and `dc()` functions to check their respective --no-* flags. Essential for conditional output based on user preferences.

---

# log-no-flag-function
## description
Logs usage of --no-* flags for statistics and tracking.
## summary
log_no_flag() function logs when --no-* flags are used, recording timestamps and usage counts for analysis.
## full_text
The log_no_flag() function logs usage of --no-* flags for statistics and tracking.

**Function:**
```python
def log_no_flag(group: str) -> None:
```

**What it does:**
1. Constructs flag name as `no_{group}`
2. Logs timestamp using `_touch_timestamp_log('no', flag_name)`
3. Logs usage count using `_increment_count('no', flag_name, present=True)`
4. Does nothing if logging is disabled

**Logging Details:**
- Logs to `config.log.no` timestamp file
- Logs to `config.log.no.counts.json` with usage statistics
- Records that the flag was present (used)

**Example:**
```python
# Called internally by ic() and dc() functions
log_no_flag('icon')  # Logs usage of --no-icon flag
log_no_flag('desc')  # Logs usage of --no-desc flag
```

**Integration:**
Called internally by `ic()` and `dc()` functions when their respective --no-* flags are detected. Part of the comprehensive logging system.

---
