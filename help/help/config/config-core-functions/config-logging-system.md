# config-logging-system
## description
Logging system that tracks configuration key access by writing timestamp entries to text files and usage counts to JSON files, with automatic integration into all configuration functions.
## summary
Logging system that records when configuration keys are accessed by writing timestamp entries to text files and usage counts to JSON files. The system tracks four types of access: icon lookups (ic), label lookups (dc), margin lookups (mc), and flag checks (no). Each access writes a timestamp to a text file and increments counters in a JSON file. The system is controlled by `config_enable_logging` in parse.ini, can be disabled completely, and fails silently if files can't be written. It automatically integrates with all configuration functions and maintains a global `_section_has_output` flag to track whether any output has been generated in the current section.
## full_text
The logging system provides tracking of configuration key access by writing simple text files and JSON files. It's controlled by `config_enable_logging` in parse.ini and can be turned off completely.

**How it works:**
When you call `ic('some_key')`, it writes a timestamp to `tools/log/config.log.ic` and updates counters in `tools/log/config.log.ic.counts.json`. Same for `dc()`, `mc()`, and `is_no()` functions. The system also maintains a global `_section_has_output` flag that tracks whether any output has been generated in the current section.

**File format:**
- Timestamp files: `key:timestamp` format (one per line, sorted alphabetically by key name)
- Count files: JSON with `{"key": {"total": 5, "present": 3, "missing": 2, "last_ts": "2025-01-01T12:00:00.123456"}}`

**Logging Functions:**
- `_touch_timestamp_log(log_type: str, name: str) -> None` - writes timestamp to text file with alphabetical sorting
- `_increment_count(log_type: str, name: str, *, present: bool) -> None` - updates JSON counters with present/missing tracking
- `_is_logging_enabled() -> bool` - checks if logging is turned on via config
- `_now_iso() -> str` - returns current timestamp as ISO string
- `log_no_flag(group: str) -> None` - specifically logs --no-* flag usage

**Configuration:**
- `config_enable_logging` in parse.ini controls whether logging is active
- When disabled, all logging functions return immediately without writing files
- Default state is loaded once and cached globally

**Error handling:**
If files can't be read/written, it just continues without crashing. Missing files get created automatically. Corrupted JSON files are handled gracefully by starting with empty data.

**Integration:**
Every call to `ic()`, `dc()`, `mc()`, or `is_no()` automatically logs the access. The `_section_has_output` global variable is updated when any configuration function returns non-empty values.

**Output tracking mechanism:**
The `_section_has_output` global variable tracks whether any output has been generated in the current section. It's set to `True` whenever any configuration function (`ic()`, `dc()`, `out()`) returns a non-empty value. The variable is reset to `False` after each `break_section()` call.

**Error handling patterns:**
The logging system uses a comprehensive silent failure pattern. If any file operation fails (read, write, JSON parsing), the system continues without crashing. Corrupted JSON files are handled by starting with empty data structures. Missing log files are created automatically on first access. All logging functions are wrapped in try-catch blocks that suppress exceptions to ensure the main application flow continues uninterrupted.

---
# timestamp-logging
## description
Writes timestamps to text files when configuration keys are accessed, maintaining alphabetical sorting.
## summary
System that writes `key:timestamp` entries to text files in `tools/log/config.log.<type>`. Files are kept sorted alphabetically by key name. If a key already exists, it updates the timestamp. If not, it inserts it in the correct alphabetical position and maintains the sorted order. The system handles file creation, reading, modification, and writing with proper error handling.
## full_text
The `_touch_timestamp_log(log_type: str, name: str) -> None` function writes timestamps to text files with intelligent sorting.

**How it works:**
1. Opens `tools/log/config.log.<log_type>` (creates if missing)
2. Reads all existing entries into a list
3. Searches for the key in the existing entries
4. If found: updates the timestamp for that key
5. If not found: inserts the new entry in alphabetical order
6. Sorts the entire list by key name to maintain order
7. Writes the sorted list back to the file

**File format:**
Each line is `key:timestamp` like `agent:2025-01-01T12:00:00.123456`

**Sorting algorithm:**
- Keys are sorted alphabetically by name
- When inserting a new key, it finds the correct position
- The entire file is re-sorted after each modification
- This ensures consistent ordering even with concurrent access

**Error handling:**
The function uses comprehensive error handling to ensure silent failure:
- File read errors: starts with empty entries list and continues
- File write errors: catches exceptions and returns without crashing
- Missing files: created automatically on first write attempt
- Permission errors: handled gracefully with silent failure
- All exceptions are caught and suppressed to avoid disrupting main application flow

**Performance:**
It reads the whole file, modifies it in memory, and writes it back. Not optimized for large files with thousands of entries, but suitable for typical configuration key usage patterns.

---
# count-tracking
## description
Tracks how many times configuration keys are accessed and whether they succeed or fail using JSON files.
## summary
System that maintains JSON files with usage counts. Tracks total accesses, successful lookups (present), failed lookups (missing), and last access time for each key. Uses a boolean parameter to determine whether to increment present or missing counts, with automatic timestamp updates and robust error handling for corrupted JSON files.
## full_text
The `_increment_count(log_type: str, name: str, *, present: bool) -> None` function updates JSON counters with detailed tracking.

**How it works:**
1. Opens `tools/log/config.log.<log_type>.counts.json` (creates if missing)
2. Loads the JSON data (starts with empty dict if file is corrupted)
3. Finds or creates the key entry with default values
4. Increments total count by 1
5. If present=True: increments present count by 1
6. If present=False: increments missing count by 1
7. Updates last_ts timestamp to current ISO time
8. Writes JSON back to file with proper formatting

**JSON format:**
```json
{
  "key_name": {
    "total": 5,
    "present": 3, 
    "missing": 2,
    "last_ts": "2025-01-01T12:00:00.123456"
  }
}
```

**Key tracking:**
- `total`: Total number of times the key was accessed
- `present`: Number of times the key was found (successful lookup)
- `missing`: Number of times the key was not found (failed lookup)
- `last_ts`: ISO timestamp of the most recent access

**Error handling:**
The function implements robust error handling for all failure scenarios:
- JSON read errors: starts with empty dictionary and continues
- JSON parse errors: catches JSONDecodeError and starts with empty data
- File write errors: catches all exceptions and returns silently
- Missing files: created automatically on first write attempt
- Permission errors: handled gracefully with silent failure
- All exceptions are caught and suppressed to ensure main application continues uninterrupted

**Performance:**
Reads entire JSON file, modifies in memory, writes back. Not optimized for large files with thousands of entries, but suitable for typical configuration key usage patterns.

---
# log-no-flag
## description
Specifically logs usage of --no-* flags for tracking flag behavior patterns.
## summary
Dedicated function for logging --no-* flag usage that writes timestamps and updates counters specifically for flag tracking. This function is called when --no-* flags are used to suppress output, providing detailed tracking of flag usage patterns and helping identify which flags are most commonly used.
## full_text
The `log_no_flag(group: str) -> None` function provides specialized logging for --no-* flag usage.

**How it works:**
1. Checks if logging is enabled via `_is_logging_enabled()`
2. If disabled, returns immediately without logging
3. Constructs flag name as `no_{group}` (e.g., "no_icon" for group "icon")
4. Calls `_touch_timestamp_log('no', flag_name)` to record timestamp
5. Calls `_increment_count('no', flag_name, present=True)` to update counters

**Usage pattern:**
This function is called by the `is_no()` function when --no-* flags are detected, providing automatic tracking of flag usage without requiring manual calls.

**Integration:**
- Called automatically by `is_no()` function
- Logs to `tools/log/config.log.no` timestamp file
- Updates `tools/log/config.log.no.counts.json` counter file
- Tracks which --no-* flags are most commonly used

**Error handling:**
If logging fails, it continues silently without disrupting the main application flow.

---
# logging-control
## description
Functions that control logging behavior and provide timestamp generation.
## summary
Control functions that determine whether logging is enabled and generate ISO timestamps. These functions are used internally by the logging system to check configuration settings and create consistent timestamp formats across all logging operations.
## full_text
The logging control functions manage the overall logging behavior and provide timestamp generation.

**`_is_logging_enabled() -> bool`:**
- Checks if logging is enabled via `config_enable_logging` in parse.ini
- Caches the result globally to avoid repeated file reads
- Returns False if the setting is not found or disabled
- Used by all logging functions to determine whether to proceed

**`_now_iso() -> str`:**
- Returns current timestamp in ISO format: `2025-01-01T12:00:00.123456`
- Uses `datetime.now().isoformat()` for consistent formatting
- Used by all logging functions for timestamp generation
- Provides microsecond precision for accurate tracking

**Configuration loading:**
- Settings are loaded once and cached globally
- Changes to parse.ini require application restart to take effect
- Default behavior is logging enabled if not specified

**Error handling:**
Both functions are designed to be robust and fail gracefully if configuration files can't be read.

---
# integration-patterns
## description
How the logging system integrates with configuration functions and output tracking.
## summary
Detailed explanation of how the logging system automatically integrates with all configuration functions (`ic()`, `dc()`, `mc()`, `is_no()`) and maintains the global `_section_has_output` flag for section-aware output tracking. Shows the complete integration pattern and how logging happens transparently without requiring additional code.
## full_text
The logging system provides seamless integration with all configuration functions and output tracking.

**Automatic integration:**
Every call to configuration functions automatically triggers logging:
- `ic(name)` → logs to `config.log.ic` and `config.log.ic.counts.json`
- `dc(name)` → logs to `config.log.dc` and `config.log.dc.counts.json`
- `mc(name)` → logs to `config.log.mc` and `config.log.mc.counts.json`
- `is_no(group)` → logs to `config.log.no` and `config.log.no.counts.json`

**Output tracking:**
The global `_section_has_output` variable tracks whether any output has been generated:
- Set to True when any configuration function returns non-empty values


**Logging flow:**
1. Configuration function is called
2. Logging functions are called automatically
3. Timestamp and count are updated
4. `_section_has_output` is updated if value is non-empty
5. Original function returns its value

**Error resilience:**
- Logging failures don't affect configuration function behavior
- Silent failure ensures main application continues normally
- Missing log files are created automatically
- Corrupted files are handled gracefully

**Performance impact:**
- Minimal overhead when logging is disabled
- File I/O only occurs when logging is enabled
- Cached configuration settings reduce repeated file reads

---
