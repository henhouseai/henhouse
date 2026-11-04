# config-usage-tracking
## description
Usage tracking system that logs and displays configuration access statistics.
## summary
The usage tracking system logs statistics when configuration functions are called and stores them in JSON log files. The config.stats.py script reads these files and displays usage statistics in formatted tables, showing total accesses, successful lookups, failed lookups, and last access time for each configuration key.
## full_text
The usage tracking system logs statistics when configuration functions are called and stores them in JSON log files.

**Data Collection:**

The system logs usage when these functions are called:

- `ic(name: str) -> str` - logs icon lookups to ic logs
- `dc(name: str, add_tc: bool = False) -> str` - logs label lookups to dc logs  
- `mc(name: str) -> int` - logs margin count lookups to mc logs
- `is_no(group: str, no_flags_config: Optional[List[str]] = None) -> bool` - logs flag usage to no logs

**Data Storage:**

Statistics are stored in two types of files in `tools/log/`:

**JSON Count Files:**
- `config.log.ic.counts.json` - Icon usage statistics
- `config.log.dc.counts.json` - Label usage statistics  
- `config.log.mc.counts.json` - Margin count usage statistics
- `config.log.no.counts.json` - Flag usage statistics

**Timestamp Log Files:**
- `config.log.ic` - Icon access timestamps (name:timestamp format)
- `config.log.dc` - Label access timestamps (name:timestamp format)
- `config.log.mc` - Margin count access timestamps (name:timestamp format)
- `config.log.no` - Flag usage timestamps (name:timestamp format)

**Logging Control:**

Logging is controlled by the `config_enable_logging` setting in `parse.ini`:
```ini
config_enable_logging = true
```

When disabled, no statistics are collected or stored.

**JSON Data Structure:**

Each log file contains usage statistics:

```json
{
  "config_key_name": {
    "total": 30,
    "present": 18,
    "missing": 12,
    "last_ts": "2025-09-28T20:19:13.159662"
  }
}
```

**Field Meanings:**
- `total`: Total number of times this key was accessed
- `present`: Number of successful lookups (key found)
- `missing`: Number of failed lookups (key not found)
- `last_ts`: ISO timestamp of last access

**Statistics Display:**

The `config.stats.py` script reads these files and displays statistics:

```bash
python3 config.stats.py
python3 config.stats.py --no-header
```

**Output Format:**

Each log type gets its own section with formatted table:

```
=== ic ===
┌─────────────┬───────┬────────┬─────────┬─────────────────────────┐
│ name        │ total │ present│ missing │ last                    │
├─────────────┼───────┼────────┼─────────┼─────────────────────────┤
│ agent       │    30 │     18 │      12 │ 2025-09-28T20:19:13.159 │
│ message     │    35 │     23 │      12 │ 2025-09-26T19:20:12.900 │
└─────────────┴───────┴────────┴─────────┴─────────────────────────┘
```

**Error Handling:**

- Missing files: shows "(no data)" and continues
- Corrupt JSON: shows "(corrupt data)" and continues  
- Table rendering failure: falls back to simple text output

**Integration:**

The tracking system integrates with the core config functions in `config.py`:

```python
def ic(name: str) -> str:
    global _section_has_output
    # Check for --no-icon flag
    if is_no('icon'):
        log_no_flag('icon')
        _touch_timestamp_log('ic', name)
        _increment_count('ic', name, present=False)
        return ''
    result = get_str(name)
    if result:
        _section_has_output = True
    _touch_timestamp_log('ic', name)
    _increment_count('ic', name, present=bool(result))
    return result
```

**Logging Functions:**

- `_touch_timestamp_log(log_type: str, name: str)` - Updates timestamp logs with name:timestamp entries, sorted alphabetically
- `_increment_count(log_type: str, name: str, *, present: bool)` - Updates count statistics in JSON files
- `_is_logging_enabled() -> bool` - Checks if logging is enabled via config_enable_logging setting
- `_now_iso() -> str` - Returns current timestamp in ISO format (YYYY-MM-DDTHH:MM:SS.ffffff)
- `log_no_flag(group: str)` - Logs usage of --no-* flags to no logs

**Maintenance:**

Use `config.clean.py` to delete log files when needed:

```bash
python3 config.clean.py
```

This removes all log files:
- `config.log.ic` and `config.log.ic.counts.json`
- `config.log.dc` and `config.log.dc.counts.json`
- `config.log.mc` and `config.log.mc.counts.json`
- `config.log.no` and `config.log.no.counts.json`

The clean script removes both timestamp files and JSON count files for all log types.

---
# statistics-display
## description
Displays usage statistics in formatted tables with sorting and alignment.
## summary
Table rendering system that reads JSON count files and displays them using TableBuilder. Sorts entries by total usage count in descending order. Handles missing files and corrupt data gracefully with fallback to plain text output.
## full_text
The statistics display system uses TableBuilder to render usage data in formatted tables.

**Table configuration:**
- Uses 'standard' table class from table.ini configuration
- Columns: name, total, present, missing, last
- Numeric columns (total, present, missing) are center-aligned
- String columns (name, last) are left-aligned
- Headers can be hidden with `--no-header` flag
- Table styling defined in `tools/table.ini` with Unicode box-drawing characters

**Sorting logic:**
Entries are sorted by total count in descending order using:
```python
items = sorted(data.items(), key=lambda kv: int(kv[1].get('total', 0)), reverse=True)
```

**Header handling:**
- Shows column headers by default
- Can be hidden with `--no-header` flag
- Headers are: name, total, present, missing, last
- Header display controlled by `tb.has_header` and `is_no('header')` check

**Fallback output:**
If table rendering fails, falls back to simple text format:
```
key_name: total=5, present=3, missing=2, last=2025-01-01T12:00:00.123456
```

**Error handling:**
- Missing files: shows "(no data)" and skips to next log type
- Corrupt JSON: shows "(corrupt data)" and skips to next log type
- Table rendering errors: falls back to plain text output

---
# data-file-structure
## description
JSON file format and structure for storing usage statistics.
## summary
Documents the actual JSON schema used in count files, including field meanings and data types. Explains how the files are organized and what each field represents.
## full_text
The statistics system reads JSON files with a specific structure for storing usage counts.

**File locations:**
- `tools/log/config.log.ic.counts.json` - icon usage counts
- `tools/log/config.log.dc.counts.json` - label usage counts  
- `tools/log/config.log.mc.counts.json` - margin usage counts
- `tools/log/config.log.no.counts.json` - flag usage counts

**Timestamp files:**
- `tools/log/config.log.ic` - icon access timestamps
- `tools/log/config.log.dc` - label access timestamps
- `tools/log/config.log.mc` - margin access timestamps
- `tools/log/config.log.no` - flag usage timestamps

**JSON structure:**
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

**Field meanings:**
- `total`: Total number of times this key was accessed
- `present`: Number of successful lookups (key found)
- `missing`: Number of failed lookups (key not found)
- `last_ts`: ISO timestamp of last access

**Data collection process:**
1. Function is called (ic, dc, mc, or is_no)
2. `_touch_timestamp_log()` updates timestamp file with name:timestamp entry
3. `_increment_count()` updates JSON count file with usage statistics
4. Both operations check `_is_logging_enabled()` first
5. Timestamp files are sorted alphabetically by key name
6. JSON files are created with pretty-printed formatting

**Data types:**
- `total`, `present`, `missing`: integers
- `last_ts`: ISO format timestamp string
- Keys are configuration key names as strings

**File format:**
- UTF-8 encoded JSON
- Pretty-printed with 2-space indentation
- Created and maintained by `_increment_count()` function in config.py
- Uses `json.dump(data, f, ensure_ascii=False, indent=2)` for formatting

---
# error-handling
## description
Basic error handling for missing files and corrupt data.
## summary
Simple error handling that shows "(no data)" for missing files and "(corrupt data)" for unparseable JSON. Falls back to plain text output if table rendering fails.
## full_text
The statistics script handles errors gracefully without crashing.

**Missing files:**
```python
if not os.path.exists(path):
    print("(no data)")
    continue
```
Shows "(no data)" and continues to next log type.

**Corrupt JSON:**
```python
try:
    with open(path, 'r') as f:
        data = json.load(f)
except Exception:
    print("(corrupt data)")
    continue
```
Shows "(corrupt data)" and continues to next log type.

**Table rendering failure:**
```python
try:
    # Table building code
    print(tb.render())
except Exception:
    # Fallback to simple text output
    for name, rec in items:
        print(f"{name}: total={rec.get('total', 0)}, present={rec.get('present', 0)}, missing={rec.get('missing', 0)}, last={rec.get('last_ts', '')}")
```
Falls back to plain text if TableBuilder fails.

**No crash behavior:**
The script never crashes - it always continues processing other log types even if one fails.

**Log types processed:**
The script processes these log types in order:
```python
kinds = ['ic', 'dc', 'mc', 'no']
```

---
# command-line-usage
## description
How to run the statistics script and available options.
## summary
Simple command-line tool that displays statistics for all log types (ic, dc, mc, no). Supports --no-header flag to hide table headers.
## full_text
The statistics script is run from the command line with optional flags.

**Basic usage:**
```bash
python3 config.stats.py
```

**With no headers:**
```bash
python3 config.stats.py --no-header
```

**What it does:**
1. Sets up argparse to handle --no-header flag using `setup_argparse(['header'])`
2. Loops through log types: ic, dc, mc, no
3. For each type, reads the corresponding JSON file from `tools/log/config.log.{k}.counts.json`
4. Displays statistics in formatted tables using TableBuilder
5. Shows "(no data)" for missing files
6. Shows "(corrupt data)" for unparseable JSON
7. Falls back to plain text if table rendering fails

**Output format:**
- Each log type gets its own section with "=== type ===" header
- Tables show: name, total, present, missing, last
- Sorted by total count (highest first)
- Numeric columns are center-aligned

**Arguments:**
- `--no-header`: Hides table column headers
- No other arguments supported

**Implementation details:**
- Uses `TableBuilder('standard')` for table rendering
- Sets columns to 'name,total,present,missing,last'
- Center-aligns numeric columns (total, present, missing)
- Sorts by total count in descending order
- Table configuration loaded from `tools/table.ini`
- Uses Unicode box-drawing characters for borders

**Dependencies:**
- Requires config.py for `_touch_timestamp_log`, `_increment_count`, `_is_logging_enabled`, `_now_iso`, `setup_argparse`, `is_no`
- Requires table.py for TableBuilder
- Requires JSON log files in tools/log/ directory
- Uses argparse for command-line argument handling

---

