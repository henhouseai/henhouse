# config-table-rendering
## description
TableBuilder implementation for displaying config statistics from JSON log files.
## summary
The config statistics system uses TableBuilder with the 'standard' table class to display usage data from JSON log files. It shows 5 columns (name, total, present, missing, last) with numeric columns centered, sorts by usage count, and has fallback error handling.
## full_text
The table rendering system displays configuration usage statistics from JSON log files using TableBuilder.

**TableBuilder Configuration:**

The system uses TableBuilder with the 'standard' table class:

```python
tb = TableBuilder('standard')
tb.set_columns('name,total,present,missing,last')
tb.set_column_align('total', 'center')
tb.set_column_align('present', 'center')
tb.set_column_align('missing', 'center')
```

The 'standard' table class provides bordered table formatting with headers and proper column alignment.

**Column Setup:**

- `name`: Configuration key name (left-aligned)
- `total`: Total usage count (center-aligned)
- `present`: Successful lookups (center-aligned)
- `missing`: Failed lookups (center-aligned)
- `last`: Last access timestamp (left-aligned)

**Data Processing:**

Entries are sorted by total usage count in descending order:

```python
items = sorted(data.items(), key=lambda kv: int(kv[1].get('total', 0)), reverse=True)
```

**Row Building:**

```python
for name, rec in items:
    tb.row(keys=['name', 'total', 'present', 'missing', 'last'], values=[
        name,
        str(rec.get('total', 0)),
        str(rec.get('present', 0)),
        str(rec.get('missing', 0)),
        rec.get('last_ts', ''),
    ])
```

**Header Handling:**

```python
if tb.has_header and not is_no('header'):
    tb.row(keys=['name', 'total', 'present', 'missing', 'last'], 
           values=['name', 'total', 'present', 'missing', 'last'])
```

The header is only displayed if the table has headers enabled and the `--no-header` flag is not set.

**Error Handling:**

If TableBuilder fails, falls back to simple text output:

```python
try:
    # Table building code
    print(tb.render())
except Exception:
    # Fallback to simple text output if table rendering fails
    for name, rec in items:
        print(f"{name}: total={rec.get('total', 0)}, present={rec.get('present', 0)}, missing={rec.get('missing', 0)}, last={rec.get('last_ts', '')}")
```

This ensures the statistics are always displayed even if table rendering fails.

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

---
# table-setup
## description
How the TableBuilder is configured for statistics display.
## summary
Uses the 'standard' table class with 5 custom columns (name, total, present, missing, last) and centers the numeric columns. Handles headers with the --no-header flag.
## full_text
The table setup is done in config.stats.py using TableBuilder with the 'standard' table class.

**TableBuilder setup:**
```python
tb = TableBuilder('standard')
tb.set_columns('name,total,present,missing,last')
tb.set_column_align('total', 'center')
tb.set_column_align('present', 'center')
tb.set_column_align('missing', 'center')
```

**Rendering:**
```python
print(tb.render())
```

Uses the 'standard' table class which provides bordered formatting with proper column alignment.

**Column configuration:**
- name: Configuration key name (left-aligned)
- total: Total usage count (center-aligned)
- present: Times key was found (center-aligned)
- missing: Times key was missing (center-aligned)
- last: Last timestamp (left-aligned)

**Header handling:**
```python
if tb.has_header and not is_no('header'):
    tb.row(keys=['name', 'total', 'present', 'missing', 'last'], 
           values=['name', 'total', 'present', 'missing', 'last'])
```

The header is only shown if the table has headers enabled and the `--no-header` flag is not set.

---
# data-processing
## description
How JSON log data is processed and sorted for display.
## summary
Reads JSON files from config.log.{type}.counts.json, sorts by total count descending, and handles missing/corrupt files gracefully.
## full_text
The data processing reads JSON log files and prepares them for table display.

**File reading:**
```python
path = os.path.join(_tools_dir(), 'log', f'config.log.{k}.counts.json')
if not os.path.exists(path):
    print("(no data)")
    continue
try:
    with open(path, 'r') as f:
        data = json.load(f)
except Exception:
    print("(corrupt data)")
    continue
```

**Data structure:**
The JSON files contain data like this:
```json
{
  "main_header": {
    "total": 9,
    "present": 2,
    "missing": 7,
    "last_ts": "2025-09-26T19:20:12.867406"
  },
  "agent": {
    "total": 30,
    "present": 18,
    "missing": 12,
    "last_ts": "2025-09-28T20:19:13.159662"
  }
}
```

**Sorting:**
```python
items = sorted(data.items(), key=lambda kv: int(kv[1].get('total', 0)), reverse=True)
```
Sorts by total count in descending order (highest usage first).

**Error handling:**
- Missing files: prints "(no data)" and continues
- Corrupt JSON: prints "(corrupt data)" and continues
- Missing keys: uses 0 as default value

---
# column-formatting
## description
How data is formatted and aligned in each column.
## summary
Numeric columns (total, present, missing) are center-aligned, text columns (name, last) are left-aligned. Data is converted to strings and formatted appropriately.
## full_text
The column formatting handles different data types and alignment for the statistics table.

**Row building:**
```python
for name, rec in items:
    tb.row(keys=['name', 'total', 'present', 'missing', 'last'], values=[
        name,
        str(rec.get('total', 0)),
        str(rec.get('present', 0)),
        str(rec.get('missing', 0)),
        rec.get('last_ts', ''),
    ])
```

**Column formatting:**
- **name**: Configuration key name (string, left-aligned)
- **total**: Total usage count (converted to string, center-aligned)
- **present**: Times key was found (converted to string, center-aligned)
- **missing**: Times key was missing (converted to string, center-aligned)
- **last**: Last timestamp (string, left-aligned)

**Data conversion:**
All numeric values are converted to strings using `str()` before being added to the table. Timestamps are used as-is from the JSON data.

**Alignment:**
- Numeric columns (total, present, missing): center-aligned
- Text columns (name, last): left-aligned (default)
- Alignment is set during table setup with `tb.set_column_align()`

---
# error-handling
## description
Fallback mechanisms when table rendering fails.
## summary
If TableBuilder fails, the system falls back to simple text output. Also handles missing files and corrupt JSON data gracefully.
## full_text
The error handling provides fallback mechanisms when table rendering fails.

**Table rendering fallback:**
```python
try:
    tb = TableBuilder('standard')
    # ... table setup and rendering ...
    print(tb.render())
except Exception:
    # Fallback to simple text output if table rendering fails
    for name, rec in items:
        print(f"{name}: total={rec.get('total', 0)}, present={rec.get('present', 0)}, missing={rec.get('missing', 0)}, last={rec.get('last_ts', '')}")
```

This ensures statistics are always displayed even if table rendering fails.

**File error handling:**
- Missing files: prints "(no data)" and continues to next log type
- Corrupt JSON: prints "(corrupt data)" and continues to next log type
- Missing keys: uses default values (0 for numbers, empty string for text)

**What happens:**
- If TableBuilder fails: falls back to simple print statements
- If file is missing: shows "(no data)" message
- If JSON is corrupt: shows "(corrupt data)" message
- System continues running even if some log types fail

---
# log-types
## description
The four types of log files processed by the statistics system.
## summary
Processes ic, dc, mc, and no log types (icon, label, margin, and flag usage) with consistent table formatting for each type.
## full_text
The statistics system processes four types of log files, each with its own counts.json file.

**Log types processed:**
```python
kinds = ['ic', 'dc', 'mc', 'no']
```

**File paths:**
- `config.log.ic.counts.json` - Icon usage statistics
- `config.log.dc.counts.json` - Label (description) usage statistics  
- `config.log.mc.counts.json` - Margin configuration usage statistics
- `config.log.no.counts.json` - Flag usage statistics

**Processing:**
Each log type is processed identically:
1. Check if file exists
2. Load JSON data
3. Sort by total count
4. Display in table format
5. Show section header (e.g., "=== ic ===")

**Section headers:**
```python
for k in kinds:
    print(f"\n=== {k} ===")
```
Each log type gets its own section with a clear header.

**What each type tracks:**
- **ic**: Icon usage (from `ic()` function calls)
- **dc**: Label usage (from `dc()` function calls)
- **mc**: Margin config usage (from `mc()` function calls)
- **no**: Flag usage (from `is_no()` function calls)

---
