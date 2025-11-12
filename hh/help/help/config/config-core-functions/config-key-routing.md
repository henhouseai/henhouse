# config-key-routing
## description
Key routing system that routes different key types to appropriate configuration files based on their prefix.
## summary
The key routing system uses the _raw_get() function to route configuration keys to the correct .ini file based on their prefix. Keys starting with 't_' go to table.ini, 'l_' go to label.ini, 'max_' or 'config_' go to parse.ini, and everything else goes to icon.ini. The system loads files lazily through _ensure_loaded() and returns empty strings for missing keys. The routing integrates with logging, argument parsing, and table rendering systems. The system maintains global state through ConfigParser objects and provides comprehensive logging of key usage patterns.
## full_text
The key routing system routes configuration keys to the appropriate .ini file based on their prefix. This happens in the _raw_get() function.

**How it works:**
The _raw_get() function checks the key prefix and routes it to the right file:
- t_* keys → table.ini
- l_* keys → label.ini  
- max_* or config_* keys → parse.ini
- everything else → icon.ini

**File loading:**
Files are loaded lazily when first accessed. The _ensure_loaded() function loads all four .ini files into global ConfigParser objects. The _read_flat_ini() function wraps each .ini file content in a [DEFAULT] section.

**Global state management:**
- _cfg_table: ConfigParser for table.ini
- _cfg_label: ConfigParser for label.ini
- _cfg_parse: ConfigParser for parse.ini
- _cfg_icon: ConfigParser for icon.ini
- _section_has_output: Boolean flag for output tracking
- _logging_enabled: Cached logging state
- _args: Parsed command line arguments

**Integration with other systems:**
The routing system integrates with logging (tracks key usage), argument parsing (--no-* flags), and table rendering (provides configuration values).

**Error handling:**
Missing keys return empty strings. Missing files return empty ConfigParser objects.

---
# routing-implementation
## description
The actual _raw_get() function that does the key routing.
## summary
The _raw_get() function is the core of the routing system. It converts keys to lowercase, checks prefixes in order, and returns values from the appropriate .ini file with quotes stripped.
## full_text
The routing is done by the _raw_get() function in config.py:

```python
def _raw_get(key: str) -> str:
    _ensure_loaded()
    k = key.lower()
    if k.startswith('t_'):
        return _cfg_table.get('DEFAULT', k, fallback='').strip('"')
    if k.startswith('l_'):
        return _cfg_label.get('DEFAULT', k, fallback='').strip('"')
    if k.startswith('max_') or k.startswith('config_'):
        return _cfg_parse.get('DEFAULT', k, fallback='').strip('"')
    return _cfg_icon.get('DEFAULT', k, fallback='').strip('"')
```

**What it does:**
1. Calls _ensure_loaded() to load .ini files if not already loaded
2. Converts key to lowercase
3. Checks prefixes in order: t_, l_, max_/config_, then defaults to icon
4. Gets value from the right ConfigParser object using 'DEFAULT' section
5. Strips quotes from the value
6. Returns empty string if key not found (via fallback parameter)

**Helper functions that use _raw_get():**
```python
def get_str(key: str) -> str:
    return _raw_get(key)

def get_int(key: str) -> int:
    raw = _raw_get(key)
    if raw == '':
        return 0
    try:
        iv = int(raw)
        return iv if iv >= 0 else 0
    except Exception:
        return 0

def conf_str(cls: str, name: str) -> str:
    return get_str(f't_{cls}_{name}')

def conf_int(cls: str, name: str) -> int:
    return get_int(f't_{cls}_{name}')
```

**Global variables:**
- _cfg_table: ConfigParser for table.ini
- _cfg_label: ConfigParser for label.ini  
- _cfg_parse: ConfigParser for parse.ini
- _cfg_icon: ConfigParser for icon.ini

---
# routing-rules
## description
Which keys go to which .ini files.
## summary
Keys starting with 't_' go to table.ini, 'l_' go to label.ini, 'max_' or 'config_' go to parse.ini, and everything else goes to icon.ini. Keys are case-insensitive.
## full_text
The routing rules check the key prefix:

**t_* keys → table.ini**
Examples from table.ini:
- t_standard_has_header = 1
- t_standard_columns = label
- t_standard_padl = 1
- t_standard_top_left = "┌"
- t_standard_v_left = "│"
- t_standard_h_top = "─"
- t_double_has_header = 1
- t_heavy_has_header = 1
- t_ascii_has_header = 1
- t_minimal_has_header = 1
- t_meta_main_has_header = 1

**l_* keys → label.ini**
Examples from label.ini:
- l_help_topic = "Help:"
- l_agent_name = "Agent:"
- l_message_channel = "Channel:"
- l_timestamp = "Timestamp:"
- l_main_header = "🏠 Henhouse: "
- l_peek_header = "Watercooler Queue Peek"
- l_message = "Message:"
- l_agent_status = "Status:"
- l_success = "Success:"
- l_error = "Error:"
- l_agent_tree = "Agent Tree:"

**max_* or config_* keys → parse.ini**
Examples from parse.ini:
- config_enable_logging = true
- config_enable_decorator_system = true
- config_registered_parsers = watercooler/parse_queue_peek.py, help/parse_help_menu.py, agents/parse_timeclock_punch.py, agents/parse_agent_list.py, agents/parse_agent_purge.py, agents/parse_agent_tree.py
- config_enable_parser_logging = true
- config_parser_log_level = info
- max_json_length = 1000

**Everything else → icon.ini**
Examples from icon.ini:
- agent = "🤖"
- message = "📧"
- active = "🎯"
- tab = "  "
- error = "🚨"
- help_topic = "❓"
- help_section = "🔸"
- timestamp = "🕒"
- channel = "📡"
- blank_emoji = "  "
- docket = "💼"
- ask = "🧩"
- task = "📌"
- step = "📍"
- sort_order = "#"
- todo = "🔲"
- doing = "🔄"
- review = "🔍"
- done = "✅"

**Case insensitive:**
All keys are converted to lowercase before checking, so 'Agent', 'AGENT', and 'agent' all work the same.

---
# file-loading-mechanism
## description
How configuration files are loaded and managed by the system.
## summary
The system uses lazy loading through _ensure_loaded() to load .ini files only when first accessed. Files are wrapped in [DEFAULT] sections and loaded into global ConfigParser objects. Missing files are handled gracefully by returning empty ConfigParser objects.
## full_text
The file loading mechanism uses lazy loading to load .ini files only when first accessed.

**Lazy loading implementation:**
```python
def _ensure_loaded() -> None:
    global _cfg_parse, _cfg_icon, _cfg_label, _cfg_table
    if _cfg_parse is None:
        _cfg_parse = _read_flat_ini(os.path.join(_tools_dir(), 'parse.ini'))
    if _cfg_icon is None:
        _cfg_icon = _read_flat_ini(os.path.join(_tools_dir(), 'icon.ini'))
    if _cfg_label is None:
        _cfg_label = _read_flat_ini(os.path.join(_tools_dir(), 'label.ini'))
    if _cfg_table is None:
        _cfg_table = _read_flat_ini(os.path.join(_tools_dir(), 'table.ini'))
```

**File reading function:**
```python
def _read_flat_ini(path: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if os.path.exists(path):
        with open(path, 'r') as f:
            content = '[DEFAULT]\n' + f.read()
        cfg.read_string(content)
    return cfg
```

**What happens:**
1. Files are loaded only when first accessed via _raw_get()
2. Each file is wrapped in a [DEFAULT] section for consistent access
3. Missing files return empty ConfigParser objects
4. Global variables store the loaded ConfigParser objects
5. Subsequent accesses use the cached objects

**File paths:**
- parse.ini: Parser configuration and settings
- icon.ini: Icons and spacing definitions
- label.ini: Text labels for UI elements
- table.ini: Table styling and layout definitions

**Error handling:**
- Missing files: Returns empty ConfigParser (no crash)
- Malformed .ini: ConfigParser handles gracefully
- Permission errors: Handled by file existence check

---
# global-state-management
## description
How the system manages global state for configuration and logging.
## summary
The system maintains global state through several variables: ConfigParser objects for each .ini file, output tracking flags, logging state, and parsed arguments. State is initialized lazily and cached for performance.
## full_text
The system maintains global state through several variables that are initialized lazily and cached for performance.

**Global state variables:**
```python
_cfg_parse: Optional[configparser.ConfigParser] = None
_cfg_icon: Optional[configparser.ConfigParser] = None
_cfg_label: Optional[configparser.ConfigParser] = None
_cfg_table: Optional[configparser.ConfigParser] = None
_section_has_output: bool = False
_logging_enabled: Optional[bool] = None
_args: Optional[argparse.Namespace] = None
```

**State initialization:**
- ConfigParser objects: Loaded lazily via _ensure_loaded()
- Logging state: Cached after first check via _is_logging_enabled()
- Arguments: Parsed once via setup_argparse()
- Output tracking: Reset per section via break_section()

**State management patterns:**
```python
def _is_logging_enabled() -> bool:
    global _logging_enabled
    if _logging_enabled is None:
        _ensure_loaded()
        _logging_enabled = _cfg_parse.getboolean('DEFAULT', 'config_enable_logging', fallback=False)
    return bool(_logging_enabled)
```

**Output tracking:**
```python
def break_section(lines: List[str]) -> None:
    global _section_has_output
    if _section_has_output:
        lines.append("")
    _section_has_output = False
```

**Thread safety:**
The global state is not thread-safe. In multi-threaded environments, access should be synchronized or each thread should use its own instance.

---
# integration-patterns
## description
How key routing is used in the actual code.
## summary
The routing system is used through helper functions like ic() and dc(). These functions call get_str() which calls _raw_get() to route keys to the right .ini file. The system also integrates with logging, argument parsing, and table rendering.
## full_text
The routing system is used through helper functions that call get_str().

**Core helper functions:**
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

def dc(name: str, add_tc: bool = False) -> str:
    global _section_has_output
    # Check for --no-desc flag
    if is_no('desc'):
        log_no_flag('desc')
        _touch_timestamp_log('dc', name)
        _increment_count('dc', name, present=False)
        return ''
    result = get_str(name)
    if result:
        _section_has_output = True
        if add_tc:
            result = tc() + result
    _touch_timestamp_log('dc', name)
    _increment_count('dc', name, present=bool(result))
    return result

def mc(name: str) -> int:
    try:
        val = get_int(name)
        result = val if val >= 0 else 0
        present = val is not None and val >= 0
        _touch_timestamp_log('mc', name)
        _increment_count('mc', name, present=present)
        return result
    except Exception:
        _touch_timestamp_log('mc', name)
        _increment_count('mc', name, present=False)
        return 0

def log_no_flag(group: str) -> None:
    """Log usage of --no-* flags"""
    if not _is_logging_enabled():
        return
    flag_name = f'no_{group}'
    _touch_timestamp_log('no', flag_name)
    _increment_count('no', flag_name, present=True)

def tc(repeat: int = 1, mode: Optional[int] = None) -> str:
    base = get_str('tab')
    blank = get_str('blank_emoji')
    if repeat <= 1:
        if not mode:
            return base
        segs: List[str] = []
        if mode in (2, 4):
            segs.append(blank)
        segs.append(base)
        if mode in (3, 4):
            segs.append(blank)
        return ''.join(segs)
    if not mode:
        return base * repeat
    segs: List[str] = []
    if mode in (2, 4):
        segs.append(blank)
    for i in range(repeat):
        segs.append(base)
        if i < repeat - 1 and mode in (1, 2, 3, 4):
            segs.append(blank)
    if mode in (3, 4):
        segs.append(blank)
    return ''.join(segs)

def out(value: Any) -> str:
    global _section_has_output
    s = safe_str(value)
    if s != "":
        _section_has_output = True
    return s

def break_section(lines: List[str]) -> None:
    global _section_has_output
    if _section_has_output:
        lines.append("")
    _section_has_output = False
```

**Argument parsing integration:**
```python
def setup_argparse(no_flags_config: Optional[List[str]] = None, args: Optional[List[str]] = None) -> argparse.Namespace:
    global _args
    parser = argparse.ArgumentParser()
    if no_flags_config:
        for flag_name in no_flags_config:
            parser.add_argument(f"--no-{flag_name}", action="store_true")
    if args is not None:
        _args = parser.parse_args(args)
    else:
        _args = parser.parse_args()
    return _args

def is_no(group: str, no_flags_config: Optional[List[str]] = None) -> bool:
    global _args
    if _args is None:
        setup_argparse(no_flags_config)
    result = getattr(_args, f'no_{group}', False)
    # Log the is_no usage
    try:
        _touch_timestamp_log('no', f'no_{group}')
        _increment_count('no', f'no_{group}', present=bool(result))
    except Exception:
        pass  # Don't break if logging fails
    return bool(result)
```

**Logging system integration:**
```python
def _touch_timestamp_log(log_type: str, name: str) -> None:
    """Maintain legacy-style timestamp logs: config.log.<type> lines of name:timestamp, sorted."""
    if not _is_logging_enabled():
        return
    log_file = os.path.join(_tools_dir(), 'log', f'config.log.{log_type}')
    entries: List[str] = []
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            entries = [line.rstrip('\n') for line in f if line.strip()]
    # Replace or insert sorted
    found = False
    for i, line in enumerate(entries):
        if ':' in line:
            k, _ = line.split(':', 1)
            if k == name:
                entries[i] = f"{name}:{_now_iso()}"
                found = True
                break
            if k > name:
                entries.insert(i, f"{name}:{_now_iso()}")
                found = True
                break
    if not found:
        entries.append(f"{name}:{_now_iso()}")
        entries.sort(key=lambda s: s.split(':', 1)[0])
    with open(log_file, 'w') as f:
        for line in entries:
            f.write(line + '\n')

def _increment_count(log_type: str, name: str, *, present: bool) -> None:
    """Maintain counts in JSON file: config.log.<type>.counts.json.
    Structure: { name: { total, present, missing, last_ts } }
    """
    if not _is_logging_enabled():
        return
    path = os.path.join(_tools_dir(), 'log', f'config.log.{log_type}.counts.json')
    data: Dict[str, Dict[str, Any]] = {}
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
        except Exception:
            data = {}
    rec = data.get(name, {"total": 0, "present": 0, "missing": 0, "last_ts": None})
    rec["total"] = int(rec.get("total", 0)) + 1
    rec["present"] = int(rec.get("present", 0)) + (1 if present else 0)
    rec["missing"] = int(rec.get("missing", 0)) + (0 if present else 1)
    rec["last_ts"] = _now_iso()
    data[name] = rec
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

**Real usage examples:**
From parse_help_menu.py:
```python
'label': dc('l_help_topic', True),  # Routes to label.ini
'label': dc('l_help_child', True),  # Routes to label.ini
'label': dc('l_help_file', True),   # Routes to label.ini
```

**How it works:**
1. Parser calls dc('l_help_topic', True)
2. dc() calls get_str('l_help_topic')
3. get_str() calls _raw_get('l_help_topic')
4. _raw_get() sees 'l_' prefix and routes to label.ini
5. Returns "Help:" from label.ini

---
# error-handling
## description
How the system handles missing keys and files.
## summary
Missing keys return empty strings. Missing files are handled by returning empty ConfigParser objects. The system doesn't crash on configuration errors.
## full_text
The error handling returns empty strings for missing keys and empty ConfigParser objects for missing files.

**Missing keys:**
```python
def _raw_get(key: str) -> str:
    # ... routing logic ...
    return _cfg_table.get('DEFAULT', k, fallback='').strip('"')
    #                                    ^^^^^^^^^ fallback value
```
The `fallback=''` parameter means missing keys return empty strings instead of crashing.

**Missing files:**
```python
def _read_flat_ini(path: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if os.path.exists(path):
        with open(path, 'r') as f:
            content = '[DEFAULT]\n' + f.read()
        cfg.read_string(content)
    return cfg  # Returns empty ConfigParser if file missing
```
If a file doesn't exist, it returns an empty ConfigParser object that returns empty strings for all keys.

**Lazy loading error handling:**
```python
def _ensure_loaded() -> None:
    global _cfg_parse, _cfg_icon, _cfg_label, _cfg_table
    if _cfg_parse is None:
        _cfg_parse = _read_flat_ini(os.path.join(_tools_dir(), 'parse.ini'))
    if _cfg_icon is None:
        _cfg_icon = _read_flat_ini(os.path.join(_tools_dir(), 'icon.ini'))
    if _cfg_label is None:
        _cfg_label = _read_flat_ini(os.path.join(_tools_dir(), 'label.ini'))
    if _cfg_table is None:
        _cfg_table = _read_flat_ini(os.path.join(_tools_dir(), 'table.ini'))
```
Each file is loaded independently, so if one file is missing, the others still work.

**Quote stripping:**
The `.strip('"')` operation is safe - it just removes quotes from values if they exist.

**What happens:**
- Missing key → empty string (via fallback parameter)
- Missing file → empty string for all keys from that file (empty ConfigParser)
- Malformed .ini → ConfigParser handles it, skips bad lines
- Invalid integer conversion → returns 0 (get_int function)
- Logging errors → silently ignored (try/except blocks)
- No crashes, system keeps running

**Specific error handling examples:**
```python
# Missing key handling
def _raw_get(key: str) -> str:
    return _cfg_table.get('DEFAULT', k, fallback='').strip('"')
    #                                    ^^^^^^^^^ fallback value

# Missing file handling
def _read_flat_ini(path: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if os.path.exists(path):  # Check before reading
        with open(path, 'r') as f:
            content = '[DEFAULT]\n' + f.read()
        cfg.read_string(content)
    return cfg  # Returns empty ConfigParser if file missing

# Integer conversion error handling
def get_int(key: str) -> int:
    raw = _raw_get(key)
    if raw == '':
        return 0
    try:
        iv = int(raw)
        return iv if iv >= 0 else 0
    except Exception:
        return 0  # Returns 0 on any conversion error
```

**Logging system resilience:**
The logging functions (_touch_timestamp_log, _increment_count) are wrapped in try/except blocks to ensure configuration errors don't break the main functionality. If logging fails, the system continues to work normally.

---
