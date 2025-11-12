# config-maintenance
## description
Log cleanup tools and maintenance procedures for the config system. Includes config.clean.py for removing log files and procedures for managing disk space and system maintenance.
## summary
Two maintenance tools provide complete configuration system upkeep: config.clean.py for log file cleanup and config.stats.py for usage statistics analysis. Both tools operate on the four log types (ic, dc, mc, no) and provide safe maintenance without affecting active configuration operations.
## full_text
The config-maintenance system provides two essential utilities for maintaining the Henhouse configuration system: log file cleanup and usage statistics analysis.

**Available Maintenance Tools:**
- **config.clean.py** - Removes all configuration log files (timestamp and count files)
- **config.stats.py** - Analyzes usage statistics from count files and displays formatted tables

**Log Types Maintained:**
Both tools operate on the same four log types:
- `ic` - Icon access logs from `ic()` function calls (tracks icon usage with `--no-icon` flag handling)
- `dc` - Label access logs from `dc()` function calls (tracks label usage with `--no-desc` flag handling)
- `mc` - Margin/config access logs from `mc()` function calls (tracks margin and config value access)
- `no` - Flag usage logs from `is_no()` function calls (tracks `--no-*` flag usage patterns)

**File Structure:**
Maintenance tools operate on files in `tools/log/` directory:
- **Timestamp files**: `config.log.{type}` - Contains `name:timestamp` entries, sorted alphabetically by name
- **Count files**: `config.log.{type}.counts.json` - Contains JSON usage statistics with total, present, missing counts and last timestamp

**Tool Integration:**
Both tools import config and table modules but operate independently:
- Safe to run while configuration system is active
- No interference with active parser operations
- Only affects log files, not configuration data
- Logging resumes automatically after cleanup

**Maintenance Procedures:**
1. **Regular Cleanup**: Use `config.clean.py` to remove old log files
2. **Usage Analysis**: Use `config.stats.py` to analyze usage patterns
3. **Performance Monitoring**: Monitor log file sizes and cleanup frequency
4. **System Optimization**: Clean logs before major operations

**Command Usage:**
```bash
# Clean all log files
python3 tools/config.clean.py

# Analyze usage statistics
python3 tools/config.stats.py

# Analyze statistics without headers
python3 tools/config.stats.py --no-header
```

**Safety Considerations:**
- Both tools are safe to run during active system operation
- No risk of corrupting configuration data or active state
- Log files are recreated automatically as needed
- No backup mechanism - deleted data cannot be recovered
- Uses `os.path.exists()` checks before file operations
- Handles missing files gracefully with appropriate status messages

---
