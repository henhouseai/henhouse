# config-log-analysis
## description
Log analysis features and interpretation of usage statistics from JSON log files.
## summary
The log analysis system provides tools for interpreting usage statistics from JSON log files. It helps identify unused config options, problem configurations, and usage patterns through analysis of total, present, missing, and timestamp data. The system processes four types of logs (ic, dc, mc, no) and provides insights for configuration optimization.
## full_text
The log analysis system provides tools for interpreting usage statistics from JSON log files created by the config system.

**Analysis Capabilities:**

The system analyzes four types of log files:

- `tools/log/config.log.ic.counts.json` - Icon usage analysis
- `tools/log/config.log.dc.counts.json` - Label usage analysis  
- `tools/log/config.log.mc.counts.json` - Margin usage analysis
- `tools/log/config.log.no.counts.json` - Flag usage analysis

**Data Interpretation:**

Each log file contains JSON data with usage statistics:

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

**Usage Pattern Analysis:**

**High total, high present:**
- Config option is used frequently and usually works
- Example: `"agent": {"total": 30, "present": 18, "missing": 12}`

**High total, high missing:**
- Config option is accessed often but often returns empty
- Might indicate a problem or unused config
- Example: `"indent": {"total": 24, "present": 0, "missing": 24}`

**Low total:**
- Config option is rarely used
- Might be unused and could be removed
- Example: `"info": {"total": 2, "present": 2, "missing": 0}`

**Zero present:**
- Config option is never found/always missing
- Definitely unused or misconfigured
- Example: `"indent": {"total": 24, "present": 0, "missing": 24}`

**What to look for:**

- **Unused configs**: Low total or zero present
- **Problem configs**: High missing ratio
- **Popular configs**: High total with good present ratio
- **Old configs**: Very old last_ts timestamp

**Running Analysis:**

```bash
python3 tools/config.stats.py
python3 tools/config.stats.py --no-header
```

**Output Interpretation:**

The analysis tool shows tables with columns:
- `name`: Configuration key name
- `total`: Total accesses
- `present`: Successful lookups  
- `missing`: Failed lookups
- `last`: Last access timestamp

**Maintenance Actions:**

Based on analysis results:
- Remove configs with zero present values
- Investigate configs with high missing ratios
- Keep popular configs with good present ratios
- Consider removing old, unused configs

---
# config-stats-tool
## description
The config.stats.py script that displays usage statistics from JSON log files.
## summary
Simple Python script that reads config.log.*.counts.json files and displays the data in tables. Shows usage counts sorted by frequency and supports --no-header flag.
## full_text
The config.stats.py script is the tool for analyzing config usage logs.

**What it does:**

1. Reads 4 types of log files: `ic`, `dc`, `mc`, `no`
2. Loads JSON data from each file
3. Sorts by total usage (descending)
4. Displays in tables with columns: name, total, present, missing, last using TableBuilder with 'standard' class
5. Falls back to simple text if table rendering fails

**Code structure:**

```python
def main() -> None:
    """Show statistics for all log types."""
    # Setup argparse to handle --no-header flag
    setup_argparse(['header'])
    
    kinds = ['ic', 'dc', 'mc', 'no']
    
    for k in kinds:
        path = os.path.join(_tools_dir(), 'log', f'config.log.{k}.counts.json')
        print(f"\n=== {k} ===")
        if not os.path.exists(path):
            print("(no data)")
            continue
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except Exception:
            print("(corrupt data)")
            continue
        # Sort by total desc, build table with TableBuilder
        items = sorted(data.items(), key=lambda kv: int(kv[1].get('total', 0)), reverse=True)
        try:
            tb = TableBuilder('standard')
            tb.set_columns('name,total,present,missing,last')
            tb.set_column_align('total', 'center')
            tb.set_column_align('present', 'center')
            tb.set_column_align('missing', 'center')
            if tb.has_header and not is_no('header'):
                tb.row(keys=['name', 'total', 'present', 'missing', 'last'], values=['name', 'total', 'present', 'missing', 'last'])
            for name, rec in items:
                tb.row(keys=['name', 'total', 'present', 'missing', 'last'], values=[
                    name,
                    str(rec.get('total', 0)),
                    str(rec.get('present', 0)),
                    str(rec.get('missing', 0)),
                    rec.get('last_ts', ''),
                ])
            print(tb.render())
        except Exception:
            # Fallback to simple text output if table rendering fails
            for name, rec in items:
                print(f"{name}: total={rec.get('total', 0)}, present={rec.get('present', 0)}, missing={rec.get('missing', 0)}, last={rec.get('last_ts', '')}")
```

**Error handling:**

- If file doesn't exist: shows "(no data)"
- If JSON is corrupt: shows "(corrupt data)"
- If table rendering fails: falls back to simple text output

**Usage:**

```bash
python3 tools/config.stats.py
python3 tools/config.stats.py --no-header
```

---
# log-data-structure
## description
Structure of the JSON log files that store usage statistics for config options.
## summary
JSON files with usage counts for each config option. Each entry has total, present, missing counts and last timestamp.
## full_text
The log files store usage statistics in JSON format, created by the config system's logging functions.

**File locations:**

- `tools/log/config.log.ic.counts.json` - Icon usage stats
- `tools/log/config.log.dc.counts.json` - Description usage stats  
- `tools/log/config.log.mc.counts.json` - Margin usage stats
- `tools/log/config.log.no.counts.json` - Flag usage stats

**Logging mechanism:**

The config system automatically logs usage via two functions in `tools/config.py`:
- `_touch_timestamp_log(log_type, name)` - Maintains timestamp logs in `config.log.{type}` files
- `_increment_count(log_type, name, present=bool)` - Maintains usage counts in `config.log.{type}.counts.json` files

Logging is controlled by the `config_enable_logging` setting in `parse.ini`.

**JSON structure:**

```json
{
  "config_name": {
    "total": 9,
    "present": 2,
    "missing": 7,
    "last_ts": "2025-09-26T19:20:12.867406"
  }
}
```

**Field meanings:**

- `total`: Total number of times this config was accessed
- `present`: How many times it returned a non-empty value
- `missing`: How many times it returned empty/missing
- `last_ts`: ISO timestamp of last access

**Real example from ic.counts.json:**

```json
{
  "agent": {
    "total": 30,
    "present": 18,
    "missing": 12,
    "last_ts": "2025-09-28T20:19:13.159662"
  }
}
```

This means the "agent" icon was accessed 30 times, returned a value 18 times, was missing 12 times, and was last used on 2025-09-28.

---
# usage-interpretation
## description
How to understand what the usage statistics mean and what they tell you about the system.
## summary
Guide to interpreting the usage data to identify unused config options, frequently used items, and potential issues.
## full_text
The usage statistics tell you different things depending on the numbers.

**High total, high present:**
- Config option is used frequently and usually works
- Example: `"agent": {"total": 30, "present": 18, "missing": 12}`

**High total, high missing:**
- Config option is accessed often but often returns empty
- Might indicate a problem or unused config
- Example: `"indent": {"total": 24, "present": 0, "missing": 24}`

**Low total:**
- Config option is rarely used
- Might be unused and could be removed
- Example: `"info": {"total": 2, "present": 2, "missing": 0}`

**Zero present:**
- Config option is never found/always missing
- Definitely unused or misconfigured
- Example: `"indent": {"total": 24, "present": 0, "missing": 24}`

**What to look for:**

- **Unused configs**: Low total or zero present
- **Problem configs**: High missing ratio
- **Popular configs**: High total with good present ratio
- **Old configs**: Very old last_ts timestamp

**Example analysis:**

From the ic.counts.json data:
- `"agent"` is used frequently (30 times) and usually works (18/30)
- `"indent"` is accessed often (24 times) but never found (0/24) - probably unused
- `"info"` is rarely used (2 times) but always works (2/2)

---
# log-types
## description
The four types of logs that config.stats.py reads and what each one tracks.
## summary
Four log types: ic (icons), dc (descriptions), mc (margins), no (flags). Each tracks different aspects of config usage.
## full_text
The config system tracks usage in four different log types.

**ic (Icons):**
- Tracks when `ic()` function is called
- Logs icon name and whether it returned a value
- Examples: "agent", "message", "channel", "timestamp"

**dc (Descriptions):**
- Tracks when `dc()` function is called  
- Logs description key and whether it returned a value
- Examples: "l_agent_id", "l_message", "l_timestamp"

**mc (Margins):**
- Tracks when `mc()` function is called
- Logs margin key and whether it returned a value
- Examples: margin settings and counts

**no (Flags):**
- Tracks when `is_no()` function is called
- Logs flag name and whether it was set
- Examples: "no_icon", "no_desc", "no_header"

**When each gets logged:**

- `ic()` calls log to ic logs via `_touch_timestamp_log('ic', name)` and `_increment_count('ic', name, present=bool(result))`
- `dc()` calls log to dc logs via `_touch_timestamp_log('dc', name)` and `_increment_count('dc', name, present=bool(result))`
- `mc()` calls log to mc logs via `_touch_timestamp_log('mc', name)` and `_increment_count('mc', name, present=present)`
- `is_no()` calls log to no logs via `_touch_timestamp_log('no', f'no_{group}')` and `_increment_count('no', f'no_{group}', present=bool(result))`

**File naming:**

Each type has two files:
- `config.log.{type}` - Timestamp logs
- `config.log.{type}.counts.json` - Usage statistics

The stats tool only reads the .counts.json files.

---
# running-analysis
## description
How to run the log analysis and what the output looks like.
## summary
Simple command that shows usage statistics in tables. Supports --no-header flag and handles missing/corrupt files gracefully.
## full_text
Running the log analysis is simple.

**Basic usage:**

```bash
python3 tools/config.stats.py
```

**With options:**

```bash
python3 tools/config.stats.py --no-header
```

**What you get:**

The tool shows a table for each log type (ic, dc, mc, no) with columns:
- name: Config option name
- total: Total accesses
- present: Successful accesses  
- missing: Failed accesses
- last: Last access timestamp

**Example output:**

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

**Error handling:**

- Missing file: shows "(no data)"
- Corrupt JSON: shows "(corrupt data)"  
- Table rendering fails: shows simple text output

**What to do with the results:**

- Look for high missing ratios (problem configs)
- Look for low totals (unused configs)
- Check timestamps for old/unused items
- Use this to clean up unused config options

---

