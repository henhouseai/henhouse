# config-log-cleanup
## description
Standalone Python script that removes configuration system log files to free up disk space and reset usage statistics.
## summary
Python script (config.clean.py) that deletes configuration logging files including timestamp logs (config.log.*) and JSON count files (config.log.*.counts.json) for four log types: ic, dc, mc, and no. The script provides status output for each deletion operation and handles missing files gracefully using os.path.exists() checks.
## full_text
The config-log-cleanup system is implemented as a standalone Python script that removes all configuration logging files to free up disk space and reset usage statistics.

**Script Implementation:**
The cleanup utility is located at `tools/config.clean.py` and consists of a `_tools_dir()` helper function and a `main()` function that iterates through four log types and deletes both timestamp and count files for each type.

**Log Types Handled:**
The script processes four specific log types defined in the `kinds` list:
- `'ic'` - Icon function call logs (tracks `ic()` function usage with `--no-icon` flag handling)
- `'dc'` - Label/description function call logs (tracks `dc()` function usage with `--no-desc` flag handling)
- `'mc'` - Margin/config function call logs (tracks `mc()` function usage)
- `'no'` - Flag usage logs (tracks `is_no()` function calls and `--no-*` flag usage)

**File Deletion Process:**
For each log type, the script attempts to delete two files:
1. **Timestamp file**: `tools/log/config.log.{type}` - Contains sorted `name:timestamp` entries (one per line)
2. **Count file**: `tools/log/config.log.{type}.counts.json` - Contains JSON usage statistics with total, present, missing counts and last timestamp

**Status Output:**
The script provides clear status messages for each file operation:
- `"Deleted        : {file_path}"` - File was successfully removed
- `"Already clean  : {file_path}"` - File didn't exist (no action needed)

**Error Handling:**
The script handles missing files gracefully:
- Uses `os.path.exists()` to check file existence before deletion
- Uses `os.remove()` to delete existing files
- No exception handling - relies on OS-level file operations
- Continues processing even if individual file deletions fail

**Command Line Usage:**
```bash
python3 tools/config.clean.py
```

**Expected Output:**
```
Deleted        : tools/log/config.log.ic
Already clean  : tools/log/config.log.ic.counts.json
Deleted        : tools/log/config.log.dc
Already clean  : tools/log/config.log.dc.counts.json
Deleted        : tools/log/config.log.mc
Already clean  : tools/log/config.log.mc.counts.json
Deleted        : tools/log/config.log.no
Already clean  : tools/log/config.log.no.counts.json
```

**Integration with Config System:**
The cleanup script imports config and table modules for compatibility but doesn't use them:
- Imports `config` and `table` modules with try/except fallback pattern
- No actual usage of imported functions in the cleanup logic
- Safe to run while other processes are using the config system
- Only affects log files, not configuration data or active system state

**File Structure:**
The script expects log files to be located in `tools/log/` directory:
```
tools/log/
├── config.log.ic
├── config.log.ic.counts.json
├── config.log.dc
├── config.log.dc.counts.json
├── config.log.mc
├── config.log.mc.counts.json
├── config.log.no
└── config.log.no.counts.json
```

**File Format Details:**
- **Timestamp files**: Each line contains `name:timestamp` format, sorted alphabetically by name
- **Count files**: JSON format with structure `{"name": {"total": int, "present": int, "missing": int, "last_ts": "ISO_timestamp"}}`

**When to Use:**
- Before system maintenance or updates
- When log files become too large
- To reset usage statistics
- During system cleanup procedures
- When disk space is needed

**Safety Considerations:**
- Deletes all configuration logging data permanently
- No backup or recovery mechanism
- Safe to run multiple times (handles missing files with os.path.exists() checks)
- Does not affect configuration files (icon.ini, label.ini, table.ini, parse.ini) or system operation
- Logging will resume automatically after cleanup with fresh statistics

**Performance Impact:**
- Minimal performance impact during execution
- No impact on running config system operations
- Fast execution (simple file existence checks and deletion operations)
- No memory usage for large log files (streaming file operations)

---
# script-implementation
## description
Core implementation details of the config.clean.py cleanup script.
## summary
Standalone Python script with single main() function that iterates through four log types and deletes both timestamp and count files for each type using os.path.exists() and os.remove().
## full_text
The cleanup script is implemented as a simple Python module with minimal dependencies and straightforward file deletion logic.

**Script Structure:**
The script consists of:
- Import statements for `os` and `sys` modules
- Try/except block importing `config` and `table` modules (imported but unused)
- `_tools_dir()` helper function to get script directory path
- `main()` function containing all cleanup logic
- `if __name__ == '__main__':` guard for direct execution

**Core Algorithm:**
1. Define `kinds` list with four log types: ['ic', 'dc', 'mc', 'no']
2. Iterate through each log type in the list
3. For each type, construct two file paths using `os.path.join()`:
   - `tools/log/config.log.{type}` (timestamp file)
   - `tools/log/config.log.{type}.counts.json` (count file)
4. Check if each file exists using `os.path.exists(path)`
5. If exists: delete using `os.remove(path)` and print "Deleted" message
6. If not exists: print "Already clean" message
7. Continue to next file regardless of success/failure

**File Path Construction:**
Uses `os.path.join(_tools_dir(), 'log', f'config.log.{k}')` and `os.path.join(_tools_dir(), 'log', f'config.log.{k}.counts.json')` to build file paths relative to the script location, ensuring portability across different directory structures.

**Error Handling Strategy:**
The script uses a "fail silently" approach:
- No try/catch blocks around file operations
- Relies on OS-level error handling for file deletion
- Continues processing even if individual deletions fail
- Uses `os.path.exists()` to avoid errors on missing files
- No exception handling around path construction or file operations

**Dependencies:**
External dependencies:
- `os` module for file operations (`os.path.exists()`, `os.remove()`)
- `sys` module for path manipulation (sys.path.append fallback)
- `config` and `table` modules imported but not used (compatibility imports)
- Try/except fallback for import failures (graceful degradation)

---
# file-deletion-process
## description
Detailed process for deleting timestamp and count files for each log type.
## summary
For each of the four log types (ic, dc, mc, no), the script attempts to delete both the timestamp file (config.log.{type}) and the count file (config.log.{type}.counts.json), providing status output for each operation.
## full_text
The file deletion process is the core functionality of the cleanup script, handling both timestamp and count files for each log type.

**Log Types Processed:**
The script handles four specific log types defined in the `kinds` list:
- `'ic'` - Icon function call logs from `ic()` function calls (tracks icon usage with `--no-icon` flag handling)
- `'dc'` - Label/description function call logs from `dc()` function calls (tracks label usage with `--no-desc` flag handling)
- `'mc'` - Margin/config function call logs from `mc()` function calls (tracks margin and config value access)
- `'no'` - Flag usage logs from `is_no()` function calls (tracks `--no-*` flag usage patterns)

**File Types Deleted:**
For each log type, two files are targeted for deletion:
1. **Timestamp file**: `tools/log/config.log.{type}`
   - Contains `name:timestamp` entries
   - One entry per line, sorted alphabetically by name
   - Example: `agent:2025-09-28T20:19:13.158881`
   - Maintained by `_touch_timestamp_log()` function in config.py
2. **Count file**: `tools/log/config.log.{type}.counts.json`
   - Contains usage statistics in JSON format
   - Tracks total, present, missing counts and last timestamp
   - Example: `{"agent": {"total": 30, "present": 18, "missing": 12, "last_ts": "2025-09-28T20:19:13.159662"}}`
   - Maintained by `_increment_count()` function in config.py

**Deletion Logic:**
For each file path:
1. Check if file exists using `os.path.exists(path)`
2. If exists: delete using `os.remove(path)` and print "Deleted" message
3. If not exists: print "Already clean" message
4. Continue to next file regardless of success/failure
5. No exception handling around file operations

**Status Output Format:**
Each file operation produces one of two status messages:
- `"Deleted        : {file_path}"` - File was successfully removed
- `"Already clean  : {file_path}"` - File didn't exist (no action needed)

**File Path Construction:**
Uses `os.path.join()` to build paths:
- Base directory: `_tools_dir()` (script directory)
- Subdirectory: `'log'`
- Filename: `f'config.log.{k}'` (timestamp file) or `f'config.log.{k}.counts.json'` (count file)

**Error Handling:**
- No exception handling around file operations
- Relies on OS-level error handling for file deletion
- Continues processing even if individual deletions fail
- Uses existence check to avoid errors on missing files
- No error recovery or retry mechanisms

---
# status-output
## description
Status messages and output format provided by the cleanup script.
## summary
Clear status messages for each file operation showing whether files were deleted or already clean, with consistent formatting and complete coverage of all eight target files.
## full_text
The cleanup script provides clear, consistent status output for each file operation, making it easy to understand what actions were taken.

**Output Format:**
Each file operation produces exactly one status message with consistent formatting:
- **Deleted files**: `"Deleted        : {file_path}"`
- **Missing files**: `"Already clean  : {file_path}"`

**Message Structure:**
- Fixed-width action indicator (12 characters)
- Colon separator with single space
- Full file path from script directory

**Complete Output Example:**
```
Deleted        : tools/log/config.log.ic
Already clean  : tools/log/config.log.ic.counts.json
Deleted        : tools/log/config.log.dc
Already clean  : tools/log/config.log.dc.counts.json
Deleted        : tools/log/config.log.mc
Already clean  : tools/log/config.log.mc.counts.json
Deleted        : tools/log/config.log.no
Already clean  : tools/log/config.log.no.counts.json
```

**Output Characteristics:**
- One line per file processed (8 total lines)
- Consistent indentation and spacing
- Clear distinction between deleted and already-clean files
- Full file paths for easy verification
- No additional formatting or headers

**Use Cases:**
- Verification that cleanup completed successfully
- Identification of which files existed before cleanup
- Confirmation that all target files were processed
- Debugging file system issues

**Error Scenarios:**
- If file deletion fails: OS error may be printed to stderr
- If path construction fails: Python error may be printed to stderr
- Script continues processing regardless of individual failures
- No error recovery or retry mechanisms implemented

---
# integration-safety
## description
How the cleanup script integrates with the config system and safety considerations.
## summary
The cleanup script imports config and table modules but doesn't use them, making it safe to run while other processes are using the configuration system.
## full_text
The cleanup script is designed to operate safely alongside the active configuration system without causing conflicts or data corruption.

**Import Behavior:**
The script imports config and table modules for compatibility but doesn't use them:
- Imports `config` and `table` modules with try/except fallback pattern
- No actual usage of imported functions in cleanup logic
- No interaction with active configuration loading or cached state
- No interference with running parser processes or logging operations

**Safe Execution:**
The script can be run safely while the config system is active:
- Only affects log files, not configuration data or active system state
- No locking or synchronization with config operations
- No risk of corrupting active configuration state or cached values
- Logging will resume automatically after cleanup with fresh statistics

**File System Safety:**
The script uses safe file operations:
- Checks file existence before deletion using `os.path.exists()`
- Uses standard `os.remove()` for file deletion
- No risk of deleting non-target files
- No recursive directory operations

**Data Impact:**
The cleanup only affects logging data:
- **Configuration files**: Not touched (icon.ini, label.ini, table.ini, parse.ini)
- **Active state**: Not affected (global variables, cached configs, _cfg_* variables)
- **Parser operation**: Not interrupted (no impact on running parsers)
- **Logging data**: Permanently deleted (timestamp and count files)
- **Logging functions**: Will resume automatically (_touch_timestamp_log, _increment_count)

**Recovery Considerations:**
- No backup mechanism provided
- Deleted logging data cannot be recovered
- Usage statistics will restart from zero (fresh counts)
- Timestamp logs will be recreated as needed by logging functions
- No impact on system functionality or configuration loading

**Performance Impact:**
- Minimal CPU usage (simple file existence checks and deletion operations)
- No memory usage for large log files (streaming file operations)
- Fast execution (typically < 1 second for all eight files)
- No impact on running config operations or parser execution

**Best Practices:**
- Run during low-activity periods if possible
- Verify system stability before cleanup
- Consider backing up important log data first
- Monitor system performance during execution

---
