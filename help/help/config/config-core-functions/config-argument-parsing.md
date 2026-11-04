# config-argument-parsing
## description
Argument parsing system for --no-* flags that lets parsers suppress parts of their output.
## summary
System that takes a list of flag names from parsers and creates --no-* command line arguments. Uses a global _args variable to store parsed arguments so any function can check if a flag was set. The is_no() function checks flags and logs usage. When you run a parser with --no-header, it won't show table headers. When you run with --no-icon, it won't show emoji icons. The system uses lazy initialization and comprehensive logging to track flag usage patterns.
## full_text
The argument parsing system handles --no-* flags that let users control what parts of parser output to show or hide.

**How it works:**

1. Each parser defines a list of flag names it supports (like `['header', 'icon', 'desc']`)
2. The system creates --no-* command line arguments from these names (--no-header, --no-icon, --no-desc)
3. When you run a parser, it parses the arguments and stores them in a global `_args` variable
4. Any function can call `is_no('header')` to check if --no-header was used
5. If the flag was used, the function skips showing that part of the output

**Global state management:**

The system uses a global `_args` variable to store parsed arguments: `_args: Optional[argparse.Namespace] = None`. This means any function can check flags without having to pass arguments around. The parser is only initialized when first needed through lazy initialization. The global state allows the entire configuration system to access parsed arguments without parameter passing.

**Argument parsing process:**

When `setup_argparse()` is called with `no_flags_config = ['header', 'icon']`, it:
1. Creates an `ArgumentParser` instance
2. Calls `parser.add_argument(f"--no-{flag_name}", action="store_true")` for each flag
3. Parses command line arguments using `parser.parse_args()`
4. Stores the result in the global `_args` variable

**Logging integration:**

Every time `is_no()` is called, it logs which flag was checked and whether it was set using:
- `_touch_timestamp_log('no', f'no_{group}')` - logs timestamp to `tools/log/config.log.no`
- `_increment_count('no', f'no_{group}', present=bool(result))` - logs usage counts to `tools/log/config.log.no.counts.json`

This data goes to log files for tracking usage patterns and helps understand which flags are used most frequently.

**Error handling:**

All logging is wrapped in try-catch blocks. If logging fails, the system keeps working. Missing flags are treated as False (not set) using `getattr(_args, f'no_{group}', False)`.

**Global state and lazy initialization:**

The system uses a global `_args` variable that starts as `None`. When `is_no()` is called for the first time, it automatically calls `setup_argparse()` to initialize the parser. This lazy initialization pattern means:

1. No setup is required - the system initializes itself when first used
2. The global state is shared across all functions in the config module
3. Any function can check flags without needing to pass arguments around
4. The parser is only created when actually needed

**Important:** The global state means that once `setup_argparse()` is called, the same parsed arguments are available to all functions. This is both convenient and potentially problematic if different parts of the system expect different flag configurations.

**Best Practice:** Always call `setup_argparse()` explicitly at the start of your main function rather than relying on lazy initialization, especially when working with multiple parsers or complex applications.

**Integration with configuration system:**

The argument parsing system is tightly integrated with the broader configuration system:
- Uses the same logging infrastructure as other config functions
- Shares global state with icon, label, and table configuration
- Integrates with the `_section_has_output` tracking system
- Works seamlessly with helper functions like `ic()`, `dc()`, and `out()`

# setup-argparse
## description
Creates the argument parser and adds --no-* flags based on what the parser supports.
## summary
Takes a list of flag names and creates --no-* command line arguments for them. Stores the parsed arguments in a global _args variable so other functions can check if flags were used.
## full_text
The setup_argparse() function creates the argument parser and adds --no-* flags.

**Function:**
```python
def setup_argparse(no_flags_config: Optional[List[str]] = None, args: Optional[List[str]] = None) -> argparse.Namespace:
```

**Parameters:**
- `no_flags_config`: Optional list of flag names to create --no-* arguments for (e.g., `['header', 'icon', 'desc']`). If None, no --no-* flags are created.
- `args`: Optional pre-split arguments list. If None, uses `sys.argv` automatically. Useful for testing with predefined arguments.

**Implementation:**

1. Creates an `ArgumentParser` instance
2. If `no_flags_config` is provided, iterates through the list (like `['header', 'icon']`)
3. For each flag name, calls `parser.add_argument(f"--no-{flag_name}", action="store_true")`
4. Parses command line arguments using `parser.parse_args(args)` if `args` is provided, otherwise `parser.parse_args()`
5. Stores the result in the global `_args` variable
6. Returns the parsed arguments

**Global state update:**

The function sets the global `_args` variable: `_args = parser.parse_args(args)` if `args` is provided, otherwise `_args = parser.parse_args()`. This allows other functions to access parsed arguments without parameter passing.


**Example usage:**

```python
# Parser defines supported flags
NO_FLAGS = ['header', 'desc', 'icon', 'topic', 'section']

# Set up argument parser
args = setup_argparse(NO_FLAGS)

# Now --no-header, --no-desc, --no-icon, --no-topic, --no-section are available
```

**Example:**

If you call `setup_argparse(['header', 'icon'])`, it creates --no-header and --no-icon arguments. When someone runs the command with --no-header, the `_args` variable will have `no_header=True`.

**Real usage from config.stats.py:**

```python
def main() -> None:
    """Show statistics for all log types."""
    # Setup argparse to handle --no-header flag
    setup_argparse(['header'])
    
    # Later in the code, check the flag
    if tb.has_header and not is_no('header'):
        tb.row(keys=['name', 'total', 'present', 'missing', 'last'], 
               values=['name', 'total', 'present', 'missing', 'last'])
```

**Usage with pre-split arguments:**

```python
# When you have arguments already split (useful for testing)
test_args = ['--no-header', '--no-icon']
setup_argparse(['header', 'icon'], args=test_args)

# This is equivalent to running: python script.py --no-header --no-icon
```

---
# is-no
## description
Checks if a --no-* flag was used and logs the check.
## summary
Takes a flag name and returns True if the --no-* version was used. If the parser hasn't been set up yet, it sets it up automatically. Logs every check for tracking usage.
## full_text
The is_no() function checks if a --no-* flag was used.

**Function:**
```python
def is_no(group: str, no_flags_config: Optional[List[str]] = None) -> bool:
```

**Implementation:**

1. If global `_args` is None, calls `setup_argparse(no_flags_config)` to set up the parser
2. Uses `getattr(_args, f'no_{group}', False)` to safely check if the flag was set
3. Logs the check using `_touch_timestamp_log('no', f'no_{group}')` and `_increment_count('no', f'no_{group}', present=bool(result))`
4. Returns `bool(result)` - True if the flag was used, False otherwise

**Logging details:**

Every call to `is_no()` logs:
- Timestamp to `tools/log/config.log.no`
- Usage count to `tools/log/config.log.no.counts.json`
- Whether the flag was present or missing

**Parameters:**

- `group`: The flag name to check (like 'header' for --no-header)
- `no_flags_config`: Optional list of flag names for parser setup if `_args` is None and setup is needed

**Lazy initialization:**

If the global `_args` variable is None, the function automatically calls `setup_argparse(no_flags_config)` to initialize the argument parser before checking flags. This ensures the parser is set up even if `setup_argparse()` was never called explicitly.

**Safe flag checking:**

Uses `getattr(_args, f'no_{group}', False)` to safely access flag attributes. If the flag doesn't exist, it returns False instead of raising an AttributeError. This handles cases where a flag was checked but not defined in the parser.

**Examples:**

```python
# Check if --no-header was used
if is_no('header'):
    # Skip showing table headers

# Check if --no-icon was used  
if is_no('icon'):
    # Don't show emoji icons

# Check with specific no_flags_config
if is_no('summary', ['header', 'summary', 'icon']):
    # Skip summary section
```

**Logging:**

Every call logs which flag was checked and whether it was set. If logging fails, the function still works due to try-catch blocks around logging calls.

**Logging system integration:**

The `is_no()` function integrates with the comprehensive logging system:

```python
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

This creates detailed usage statistics in:
- `tools/log/config.log.no` - timestamp logs
- `tools/log/config.log.no.counts.json` - usage counts and statistics

---
# log-no-flag
## description
Logs when a --no-* flag is used for tracking purposes.
## summary
Function that logs flag usage to the logging system. Only logs if logging is enabled. Used by helper functions when they detect flag usage.
## full_text
The log_no_flag() function logs when a --no-* flag is used.

**Function:**
```python
def log_no_flag(group: str) -> None:
```

**Implementation:**

1. Checks if logging is enabled using `_is_logging_enabled()`
2. If enabled, constructs `flag_name` as `f'no_{group}'`
3. Calls `_touch_timestamp_log('no', flag_name)` to log timestamp
4. Calls `_increment_count('no', flag_name, present=True)` to log usage count
5. Does nothing if logging is disabled

**When it's used:**

Helper functions like `ic()` and `dc()` call this when they detect that their output is being suppressed by --no-* flags. This provides a way to log flag usage even when the flag check happens in helper functions rather than directly in `is_no()`. It ensures consistent logging across all flag usage patterns.

**Logging details:**

- `flag_name` is constructed as `f'no_{group}'` (e.g., 'no_icon' for group 'icon')
- Timestamp logs go to `tools/log/config.log.no`
- Count logs go to `tools/log/config.log.no.counts.json`
- Only logs if `config_enable_logging` is true in `parse.ini`

**Example:**

```python
def ic(name: str) -> str:
    if is_no('icon'):
        log_no_flag('icon')  # Log that icon was suppressed
        _touch_timestamp_log('ic', name)
        _increment_count('ic', name, present=False)
        return ''  # Don't show icon
    result = get_str(name)
    if result:
        _section_has_output = True
    _touch_timestamp_log('ic', name)
    _increment_count('ic', name, present=bool(result))
    return result
```

---
# integration-patterns
## description
How the argument parsing system works with parsers, tables, and helper functions.
## summary
Shows how parsers register their flags, how tables check for --no-header, and how helper functions like ic() and dc() check for --no-icon and --no-desc flags.
## full_text
The argument parsing system works with different parts of the parser system to control what gets shown.

**Parser Registration:**

When a parser registers, it lists what flags it supports:

```python
NO_FLAGS = ['header', 'desc', 'icon', 'topic', 'section']
@register_parser('help_menu', NO_FLAGS, 'tools/help/help_menu.py')
def render_help_parser(data: Dict[str, Any]) -> str:
    # Parser code here
```

This creates --no-header, --no-desc, --no-icon, --no-topic, --no-section arguments.

**Table Rendering:**

Tables check for --no-header to decide whether to show headers:

```python
if has_header and num_rows > 0 and not is_no('header'):
    # Show table headers
```

**Helper Functions:**

Helper functions check flags to decide what to show:

```python
def ic(name: str) -> str:
    global _section_has_output
    if is_no('icon'):
        log_no_flag('icon')
        _touch_timestamp_log('ic', name)
        _increment_count('ic', name, present=False)
        return ''  # Don't show icon
    result = get_str(name)
    if result:
        _section_has_output = True
    _touch_timestamp_log('ic', name)
    _increment_count('ic', name, present=bool(result))
    return result

def dc(name: str, add_tc: bool = False) -> str:
    global _section_has_output
    if is_no('desc'):
        log_no_flag('desc')
        _touch_timestamp_log('dc', name)
        _increment_count('dc', name, present=False)
        return ''  # Don't show description
    result = get_str(name)
    if result:
        _section_has_output = True
        if add_tc:
            result = tc() + result
    _touch_timestamp_log('dc', name)
    _increment_count('dc', name, present=bool(result))
    return result
```

**Global state tracking:**

Helper functions use the global `_section_has_output` variable to track whether any output was generated in the current section. This is used by `break_section()` to determine if blank lines should be added between sections. The variable is reset to False by `break_section()` after adding spacing.

**Real Examples:**

From the watercooler parser:
```python
# Check summary flag with specific config
if not is_no('summary', no_flags_config):
    # Show summary section

# Check timestamps flag with specific config
if message.get('queued_ts') and not is_no('timestamps', no_flags_config):
    # Show timestamp info
```

From the help parser:
```python
# Check header flag
if tb.has_header and not is_no('header'):
    # Show table headers

# Check icon flag
if not is_no('icon'):
    # Show emoji icons
```

From config.stats.py:
```python
# Setup argparse with specific flags
setup_argparse(['header'])

# Check header flag in table rendering
if tb.has_header and not is_no('header'):
    tb.row(keys=['name', 'total', 'present', 'missing', 'last'], 
           values=['name', 'total', 'present', 'missing', 'last'])
```

---
# error-handling
## description
How the system handles errors and what happens when things go wrong.
## summary
Error handling that keeps the system working even when logging fails or flags are missing. Uses try-catch blocks and safe defaults.
## full_text
The argument parsing system handles errors by keeping things simple and not breaking when something goes wrong.

**Logging Errors:**

All logging is wrapped in try-catch blocks:

```python
try:
    _touch_timestamp_log('no', f'no_{group}')
    _increment_count('no', f'no_{group}', present=bool(result))
except Exception:
    pass  # Don't break if logging fails
```

If logging fails, the system keeps working. This pattern is used in `is_no()` function.

**Missing Flags:**

When checking flags, the system uses safe defaults:

```python
result = getattr(_args, f'no_{group}', False)
```

If a flag doesn't exist, it returns False (not set) instead of crashing. This is used in `is_no()` function.

**Missing Parser:**

If `_args` is None, `is_no()` automatically calls `setup_argparse(no_flags_config)` to set up the parser before checking flags.

**Invalid Arguments:**

If `argparse` encounters invalid arguments, it raises `SystemExit` and shows error messages. This is handled by the calling code.

**SystemExit Handling:**

When `argparse` encounters invalid arguments (like unknown flags), it:
1. Prints an error message to stderr
2. Raises `SystemExit` with exit code 2
3. Terminates the program unless caught by calling code

**Example of invalid argument handling:**
```python
# If user runs: python script.py --invalid-flag
# argparse will print: error: unrecognized arguments: --invalid-flag
# and exit with code 2
```

**What happens when things go wrong:**

- Logging fails: System keeps working, just no logs
- Flag doesn't exist: Treated as False (not set) using `getattr(_args, f'no_{group}', False)`
- Parser not set up: Automatically sets it up via lazy initialization
- Invalid arguments: argparse handles this and shows error messages
- Missing configuration: Uses empty list as default for `no_flags_config`
- Global `_args` is None: `is_no()` automatically calls `setup_argparse()`

**Error handling in helper functions:**

Helper functions like `ic()` and `dc()` also use try-catch blocks around their logging calls to ensure they continue working even if logging fails.

**Actual error handling implementation:**

The error handling is implemented with comprehensive try-catch blocks:

```python
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

**Error handling in helper functions:**

Helper functions like `ic()` and `dc()` also use try-catch blocks around their logging calls to ensure they continue working even if logging fails.

The system is designed to fail gracefully and keep working.

---
# troubleshooting
## description
Common issues users might encounter when using the argument parsing system.
## summary
Troubleshooting guide for common problems with --no-* flags, parser setup, and integration issues.
## full_text
Common issues and solutions when working with the argument parsing system.

**Problem: Parser not recognizing --no-* flags**

**Symptoms:** Flags are ignored, no error messages
**Cause:** `setup_argparse()` wasn't called or called with wrong flag names
**Solution:** Ensure `setup_argparse(['flag_name'])` is called before using `is_no()`. The lazy initialization in `is_no()` will work, but explicit setup is more reliable.

```python
# Wrong - flags won't work
if is_no('header'):  # This will always return False

# Right - set up parser first
setup_argparse(['header', 'icon'])
if is_no('header'):  # This will work correctly
```

**Problem: Global state issues**

**Symptoms:** Flags work sometimes but not others, inconsistent behavior
**Cause:** Global `_args` variable not properly initialized or different parsers using different flag configurations
**Solution:** Always call `setup_argparse()` before first `is_no()` call. Each parser should call it with its own flag list.

```python
# Wrong - relying on lazy initialization in different contexts
def function_a():
    if is_no('header'):  # Might work

def function_b():
    if is_no('header'):  # Might not work if called first

# Right - explicit initialization
def main():
    setup_argparse(['header', 'icon'])
    function_a()  # Will work
    function_b()  # Will work
```

**Problem: Flags not working in helper functions**

**Symptoms:** `ic()` and `dc()` functions ignore --no-icon and --no-desc flags
**Cause:** Helper functions check flags internally, but parser wasn't set up with the right flags
**Solution:** Ensure `setup_argparse(['icon', 'desc'])` is called before using helper functions. The helper functions will work with lazy initialization, but explicit setup is more reliable.

```python
# Wrong - helper functions won't respect flags
ic('help_topic')  # Will always show icon

# Right - set up parser first
setup_argparse(['icon', 'desc'])
ic('help_topic')  # Will respect --no-icon flag
```

**Problem: Testing with pre-split arguments**

**Symptoms:** Tests fail because flags don't work as expected
**Cause:** Using `sys.argv` instead of pre-split arguments in tests
**Solution:** Use the `args` parameter for testing. This allows you to test with specific arguments without modifying `sys.argv`.

```python
# Wrong - uses sys.argv which might not have test flags
setup_argparse(['header'])

# Right - use pre-split arguments for testing
test_args = ['--no-header']
setup_argparse(['header'], args=test_args)
```

**Problem: Logging not working**

**Symptoms:** No log files created, no usage tracking
**Cause:** Logging disabled in configuration
**Solution:** Check `config_enable_logging` setting in `parse.ini`

```ini
# In parse.ini
config_enable_logging = true
```

**Problem: Flag names with underscores**

**Symptoms:** Flags not recognized, attribute errors
**Cause:** Flag names with underscores create invalid attribute names
**Solution:** Use simple flag names without special characters

```python
# Wrong - underscores can cause issues
setup_argparse(['no_header', 'my-flag'])

# Right - use simple names
setup_argparse(['header', 'icon'])
```

**Problem: Multiple parsers with different flags**

**Symptoms:** Flags from one parser affect another
**Cause:** Global state shared between parsers - the `_args` variable is global
**Solution:** Each parser should call `setup_argparse()` with its own flag list. The last parser to call `setup_argparse()` will override the global state.

```python
# Parser A
setup_argparse(['header', 'icon'])

# Parser B  
setup_argparse(['summary', 'timestamps'])
```

**Debugging Tips:**

1. **Check if parser was set up:** `print(_args)` should not be None
2. **Verify flag names:** Use simple names without special characters (no underscores, hyphens)
3. **Test with explicit args:** Use `args` parameter for reliable testing
4. **Check logging:** Ensure `config_enable_logging = true` in `parse.ini`
5. **Verify flag usage:** Check log files in `tools/log/` directory
6. **Check flag values:** Use `getattr(_args, 'no_header', 'NOT_SET')` to see actual flag values
7. **Test lazy initialization:** Call `is_no()` without calling `setup_argparse()` first

---
