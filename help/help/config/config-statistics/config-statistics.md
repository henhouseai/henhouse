# config-statistics
## description
Usage tracking and analytics for config system. Includes timestamp logs, JSON count files, and config.stats.py for displaying usage statistics in formatted tables with access counts and timing data.
## summary
The config-statistics system provides comprehensive configuration usage tracking and analysis tools. It consists of two main tools: config.stats.py for displaying usage statistics and config.clean.py for log maintenance. The system automatically logs configuration access via four function types (ic, dc, mc, no) and stores data in both timestamp logs and JSON count files. The stats tool reads JSON files and displays usage counts in formatted tables using TableBuilder, showing total accesses, successful lookups, failed lookups, and last access time for each configuration key. The clean tool removes all log files when maintenance is needed. The system integrates with the broader config architecture and provides complete end-to-end workflows for usage tracking, analysis, and maintenance.
## full_text
The config-statistics system provides comprehensive configuration usage tracking and analysis capabilities through a dual-tool architecture.

**System Architecture:**

The system consists of two main tools working together:

**1. config.stats.py (70 lines)**
- Displays usage statistics from JSON log files
- Processes four types of log files (ic, dc, mc, no)
- Uses TableBuilder with 'standard' class for formatted output
- Handles errors gracefully with fallback mechanisms

**2. config.clean.py (44 lines)**
- Removes all log files for maintenance
- Cleans both timestamp logs and JSON count files
- Provides deletion feedback and status reporting
- Resets system for fresh logging

**Logging Integration:**

The system automatically logs configuration access via four function types:

```python
def main() -> None:
    setup_argparse(['header'])
    kinds = ['ic', 'dc', 'mc', 'no']
    
    for k in kinds:
        path = os.path.join(_tools_dir(), 'log', f'config.log.{k}.counts.json')
        # Load JSON, sort by total, display in table
```

**Complete Workflows:**

**Data Collection Workflow:**
1. Config functions called (ic, dc, mc, is_no)
2. Logging functions update both timestamp and JSON files
3. Data stored in `tools/log/` directory
4. Controlled by `config_enable_logging` setting in parse.ini

**Statistics Display Workflow:**
1. `config.stats.py` reads JSON count files
2. Sorts by usage frequency (descending)
3. Renders formatted tables with TableBuilder
4. Handles errors gracefully with fallbacks

**Maintenance Workflow:**
1. `config.clean.py` removes all log files
2. Cleans both timestamp and JSON files
3. Provides deletion feedback
4. Resets system for fresh logging

**File System Architecture:**

The system maintains dual file types for each log category:

**JSON Count Files (used by stats tool):**
- `config.log.ic.counts.json` - Icon usage statistics from `ic()` function calls
- `config.log.dc.counts.json` - Label usage statistics from `dc()` function calls  
- `config.log.mc.counts.json` - Margin usage statistics from `mc()` function calls
- `config.log.no.counts.json` - Flag usage statistics from `is_no()` function calls

**Timestamp Log Files (maintained by config system):**
- `config.log.ic` - Icon access timestamps (name:timestamp format)
- `config.log.dc` - Label access timestamps (name:timestamp format)
- `config.log.mc` - Margin access timestamps (name:timestamp format)
- `config.log.no` - Flag usage timestamps (name:timestamp format)

**JSON Data Structure:**

Each log file contains JSON data with the following structure:

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
- `total`: Total number of times this configuration key was accessed
- `present`: Number of times the key returned a non-empty value
- `missing`: Number of times the key returned empty/missing
- `last_ts`: ISO timestamp of the last access

**Table Rendering System:**

The statistics are displayed using TableBuilder with the 'standard' table class:

```python
tb = TableBuilder('standard')
tb.set_columns('name,total,present,missing,last')
tb.set_column_align('total', 'center')
tb.set_column_align('present', 'center')
tb.set_column_align('missing', 'center')
```

**Column Configuration:**
- `name`: Configuration key name (left-aligned)
- `total`: Total usage count (center-aligned)
- `present`: Successful lookups (center-aligned)
- `missing`: Failed lookups (center-aligned)
- `last`: Last access timestamp (left-aligned)

**Data Processing:**

The system sorts entries by total usage count in descending order:

```python
items = sorted(data.items(), key=lambda kv: int(kv[1].get('total', 0)), reverse=True)
```

**Error Handling:**

The system handles errors gracefully without crashing:

- **Missing files**: Shows "(no data)" and continues to next log type
- **Corrupt JSON**: Shows "(corrupt data)" and continues to next log type
- **Table rendering failure**: Falls back to simple text output

**Command Line Usage:**

```bash
python3 config.stats.py
python3 config.stats.py --no-header
```

**Output Format:**

Each log type gets its own section with a clear header:

```
=== ic ===
┌─────────────┬───────┬────────┬─────────┬─────────────────────────┐
│ name        │ total │ present│ missing │ last                    │
├─────────────┼───────┼────────┼─────────┼─────────────────────────┤
│ agent       │    30 │     18 │      12 │ 2025-09-28T20:19:13.159 │
│ message     │    35 │     23 │      12 │ 2025-09-26T19:20:12.900 │
│ timestamp   │    50 │     34 │      16 │ 2025-09-28T20:19:13.180 │
└─────────────┴───────┴────────┴─────────┴─────────────────────────┘
```

**How data gets collected:**

The config system automatically logs usage when these functions are called:
- `ic()` function calls log to ic logs
- `dc()` function calls log to dc logs  
- `mc()` function calls log to mc logs
- `is_no()` function calls log to no logs

**What the numbers mean:**

- **High total, high present**: Config is used frequently and usually works
- **High total, high missing**: Config is accessed often but often returns empty (might be unused)
- **Low total**: Config is rarely used (might be unused)
- **Zero present**: Config is never found (definitely unused)

**Integration Patterns:**

**Config System Integration:**
- Logging functions integrate with core config functions (ic, dc, mc, is_no)
- Automatic logging controlled by `config_enable_logging` setting
- Uses internal functions: `_touch_timestamp_log()`, `_increment_count()`, `_is_logging_enabled()`

**Table Rendering Integration:**
- Uses TableBuilder with 'standard' table class from table.ini
- Supports --no-header flag for conditional display
- Provides fallback to plain text if table rendering fails

**File System Integration:**
- Stores logs in `tools/log/` directory
- Maintains both timestamp and JSON file formats
- Integrates with broader config architecture

**Configuration Dependencies:**
- `tools/parse.ini` - Contains `config_enable_logging` setting
- `tools/table.ini` - Contains 'standard' table class definition
- `tools/log/` directory - Where all log files are stored

**Error Handling:**
- Missing files: Shows "(no data)" and continues
- Corrupt JSON: Shows "(corrupt data)" and continues
- Table rendering failure: Falls back to plain text output
- Graceful degradation across all components

**Usage Patterns:**
- `python3 config.stats.py` - Display statistics with headers
- `python3 config.stats.py --no-header` - Display statistics without headers
- `python3 config.clean.py` - Remove all log files for maintenance

**Data Interpretation:**
- High total, high present: Config used frequently and works well
- High total, high missing: Config accessed often but often returns empty (possibly unused)
- Low total: Config rarely used (possibly unused)
- Zero present: Config never found (definitely unused)

---
