# config-log-files
## description
Log file structure and format documentation for configuration system maintenance.
## summary
Configuration logging system tracks when configuration values are accessed through four log types using timestamp files and JSON count files.
## full_text
The configuration logging system tracks when configuration values are accessed through four log types.

**Logging System:**
- config.log.* files - track when config values are accessed (icons, labels, margins, flags)

**File Structure:**
Each log type uses two file types:
- Timestamp files: `name:timestamp` format, sorted alphabetically
- Count files: JSON format with access counts

**File Locations:**
All log files are stored in `tools/log/` directory.

**Log Types:**
- config logs: ic, dc, mc, no

**Logging Control:**
Logging is controlled by `config_enable_logging` setting in `parse.ini` (defaults to true).

---
# config-log-files
## description
Configuration usage tracking log files for icons, labels, margins, and flags.
## summary
config.log.* files track when configuration values are accessed, with timestamp files showing last access time and JSON count files showing access counts.
## full_text
The config logging system tracks when configuration values are accessed through four log types.

**Log Types:**
- config.log.ic - icon access timestamps
- config.log.ic.counts.json - icon access counts
- config.log.dc - label access timestamps  
- config.log.dc.counts.json - label access counts
- config.log.mc - margin/config access timestamps
- config.log.mc.counts.json - margin/config access counts
- config.log.no - flag usage timestamps
- config.log.no.counts.json - flag usage counts

**Timestamp File Format:**
```
name:timestamp
```
Example:
```
agent:2025-09-28T20:19:13.158881
channel:2025-09-26T19:20:12.902476
```

**Count File Format (JSON):**
```json
{
  "name": {
    "total": 30,
    "present": 18,
    "missing": 12,
    "last_ts": "2025-09-28T20:19:13.159662"
  }
}
```

**What Triggers Logging:**
- ic() function calls log to config.log.ic
- dc() function calls log to config.log.dc
- mc() function calls log to config.log.mc
- --no-* flag usage logs to config.log.no

**Logging Functions:**
- `_touch_timestamp_log(log_type, name)` - updates timestamp files
- `_increment_count(log_type, name, present)` - updates count files
- `_is_logging_enabled()` - checks if logging is enabled
- `_now_iso()` - generates ISO format timestamps

---
# statistics-tool
## description
Tool for viewing configuration log statistics and usage patterns.
## summary
config.stats.py displays statistics for all config log types showing access counts, success rates, and last access times.
## full_text
The statistics tool provides analysis of configuration log usage patterns.

**Tool Location:**
`tools/config.stats.py`

**Usage:**
```bash
python3 tools/config.stats.py
```

**Output:**
Displays tables for each log type (ic, dc, mc, no) showing:
- name: configuration item name
- total: total number of accesses
- present: number of successful retrievals
- missing: number of failed retrievals
- last: timestamp of last access

**Flags:**
- `--no-header` - suppress table headers

**Table Format:**
Uses standard table class with columns: name, total, present, missing, last

---
# cleanup-tool
## description
Tool for cleaning configuration log files and removing accumulated data.
## summary
config.clean.py removes all config log files to reset logging data and free disk space.
## full_text
The cleanup tool removes all configuration log files.

**Tool Location:**
`tools/config.clean.py`

**Usage:**
```bash
python3 tools/config.clean.py
```

**Files Removed:**
- config.log.ic
- config.log.ic.counts.json
- config.log.dc
- config.log.dc.counts.json
- config.log.mc
- config.log.mc.counts.json
- config.log.no
- config.log.no.counts.json

**Output:**
Shows status for each file:
- "Deleted: {filename}" - file was removed
- "Already clean: {filename}" - file didn't exist

**Safety:**
- Only removes log files, no other data
- No confirmation prompt
- Files are recreated automatically when logging resumes

---
# timestamp-format
## description
Timestamp file format and maintenance for configuration logging system.
## summary
Timestamp files use name:timestamp format, are sorted alphabetically, and are updated by replacing existing entries or inserting new ones.
## full_text
Timestamp files track when specific configuration values were last accessed.

**File Format:**
- One entry per line
- Format: `name:timestamp`
- Timestamp: ISO format with microseconds
- Sorted alphabetically by name

**Example:**
```
active:2025-09-28T20:19:13.173089
agent:2025-09-28T20:19:13.158881
help_topic:2025-09-28T20:19:12.653005
```

**Update Behavior:**
- If name exists: replace timestamp
- If name doesn't exist: insert in alphabetical order
- Files are rewritten completely on each update
- Only updates if logging is enabled

**Maintenance:**
- Files are created automatically when first entry is added
- No automatic cleanup or rotation
- Use `config.clean.py` for manual cleanup

---
# count-format
## description
JSON count file format and structure for configuration access count tracking.
## summary
Count files use JSON format to track total accesses, successful retrievals, missing values, and last access timestamp for each configuration item.
## full_text
Count files track configuration access counts in JSON format.

**File Format:**
```json
{
  "item_name": {
    "total": 30,
    "present": 18,
    "missing": 12,
    "last_ts": "2025-09-28T20:19:13.159662"
  }
}
```

**Field Meanings:**
- total: total number of accesses
- present: number of successful retrievals
- missing: number of failed retrievals
- last_ts: ISO timestamp of last access

**Update Behavior:**
- Files are read, updated, and written back on each access
- New items are added with default values
- Existing items have counts incremented
- Only updates if logging is enabled

**Error Handling:**
- If file doesn't exist: creates new file
- If JSON is invalid: starts with empty data
- If write fails: data is lost

---
# logging-functions
## description
Functions that create and maintain configuration log files.
## summary
Two main logging functions handle timestamp and count file updates: _touch_timestamp_log and _increment_count.
## full_text
The configuration logging system uses two main functions to maintain log files.

**Logging Functions:**
- `_touch_timestamp_log(log_type, name)` - updates config.log.{type} files
- `_increment_count(log_type, name, present)` - updates config.log.{type}.counts.json files

**Function Behavior:**
- Check if logging is enabled before proceeding
- Read existing file content
- Update or insert entry
- Write file back to disk
- Handle errors gracefully

**Log Type Parameters:**
- config: 'ic', 'dc', 'mc', 'no'

**Helper Functions:**
- `_is_logging_enabled()` - checks config_enable_logging setting
- `_now_iso()` - generates ISO format timestamps

---
# file-locations
## description
Where configuration log files are stored and how they are organized.
## summary
All configuration log files are stored in tools/log/ directory with consistent naming patterns for easy identification and maintenance.
## full_text
Configuration log files are stored in a single directory with consistent naming.

**Directory:**
`tools/log/`

**File Naming Pattern:**
- Timestamp files: `config.log.{type}`
- Count files: `config.log.{type}.counts.json`

**Complete File List:**
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

**File Creation:**
- Files are created automatically when first entry is logged
- No pre-existing files required
- Directory must exist for logging to work
- Files are only created if logging is enabled

---
