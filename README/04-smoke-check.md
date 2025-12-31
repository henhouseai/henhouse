# Chapter 4: Smoke Check

## Overview

Smoke checking is the process of verifying that your Henhouse installation works correctly before deploying to production. This process is **box-agnostic** - the same concepts apply whether you're testing on your developer box or your deployment box.

## What is Smoke Checking?

Smoke checking involves:
1. Running the Python code directly (without installing it as a package)
2. Using built-in tools to probe the system and discover what it finds
3. Verifying dependencies are installed correctly
4. Testing database connections
5. Using the debugger to identify issues

**Key Principle**: Smoke checking is about using the basic tools Henhouse provides to verify your setup, then using an AI agent to help troubleshoot if something isn't working.

## Prerequisites

Before smoke checking, you should have:
- Python 3.x installed
- Project code cloned or copied to your test environment
- Database configured (if testing database connections)
- Dependencies installed (see below)

## Dependency Checking

### Running Dependency List

The `dependency-list` command shows what Python packages Henhouse expects:

```bash
python -m hh.gateway.main dependency-list
```

Or if you have the entry script:
```bash
hen dependency-list
```

This command:
- Lists all required Python packages
- Shows which are installed and which are missing
- Helps identify dependency issues before running other commands

### Installing Dependencies

**On Ubuntu/Debian deployment boxes** (recommended):
Install all dependencies via apt:

```bash
sudo apt install python3-flask python3-pymysql python3-psutil python3-mutagen python3-pil ffmpeg -y
```

This installs:
- `python3-flask` - Flask web framework
- `python3-pymysql` - MySQL connector
- `python3-psutil` - System utilities
- `python3-mutagen` - Audio metadata
- `python3-pil` - Image processing (Pillow)
- `ffmpeg` - Audio/video processing (includes ffprobe)

**On developer boxes or other systems**:
If apt packages aren't available, use pip:

```bash
pip install -r requirements.txt
pip install pillow  # Pillow not in requirements.txt but required
```

**Note**: Using apt packages is preferred on deployment boxes because:
- Packages are managed by the system package manager
- Lower risk of conflicts with system Python
- Easier to update with `apt upgrade`
- No need for `--break-system-packages` flag

## System Probing

### Using Built-in Discovery Tools

Henhouse includes several commands that probe the system and show what it discovers:

**Command List**:
```bash
hen command-list
```
Shows all available commands and their status.

**Backend List**:
```bash
hen backend-list
```
Shows all registered backend modules.

**Parser List**:
```bash
hen parser-list
```
Shows all registered parser modules.

**Registry List**:
```bash
hen registry-list
```
Shows registry contents and status.

### What These Tools Reveal

These discovery tools help you understand:
- What commands are available
- What modules are loaded
- What extensions are detected (from `ext/` folder)
- What the system can see and access
- Potential integration issues

## Database Connection Testing

### Testing Database Connections

If you have database credentials configured, test the connection:

```bash
hen check-db -root
```

This command:
- Attempts to connect to the database
- Shows table information if connection succeeds
- Reports connection errors if it fails

**Common Issues**:
- SSL certificate paths incorrect
- Database host unreachable
- Credentials incorrect
- MySQL user permissions insufficient

### Debugging Database Issues

If database connections fail:
1. Check your config file (`~/.{project}.cnf`) for correct values
2. Verify SSL certificate paths exist and are readable
3. Test MySQL connection directly: `mysql -h db.example.com -u user -p`
4. Check MySQL user permissions and grants

## Using the Debugger

### Running the Debugger

The debugger provides detailed system information:

```bash
hen debugger
```

Or:
```bash
python -m hh.gateway.main debugger
```

### What the Debugger Shows

The debugger output includes:
- System information (OS, Python version, paths)
- Gateway initialization status
- Database connection status
- Registry contents
- Module loading status
- Configuration file locations
- Error messages and warnings

## Technical Details: Discovery Tools Implementation

The discovery tools use the Gateway and Registry systems to probe the system:

**Command List** (`command-list`):
- Scans command registry for all registered commands
- Shows command status and availability
- Uses `hh.gateway.registry.registry` to discover commands

**Backend List** (`backend-list`):
- Scans backend registry for all registered backends
- Shows backend modules and their status
- Uses `hh.gateway.registry.backend` to discover backends

**Parser List** (`parser-list`):
- Scans parser registry for all registered parsers
- Shows parser modules and their status
- Uses `hh.gateway.registry.parser` to discover parsers

**Registry List** (`registry-list`):
- Shows complete registry contents
- Displays all registered handlers, commands, and modules
- Shows extension detection from `ext/` folder
- Uses registry scanning to discover all registered components

These tools help identify what the system can see and access, and reveal potential integration issues or missing components.

### Copying Debugger Output

**Important**: You can copy the debugger output from your deployment box and paste it into an AI agent chat window on your developer box to get help troubleshooting issues.

The debugger output is designed to be:
- Self-contained (includes all relevant information)
- Machine-readable (structured format)
- Human-readable (formatted for easy reading)

## Smoke Check Workflow

### Step 1: Dependency Check

```bash
hen dependency-list
```

Verify all required packages are installed. Install missing dependencies.

### Step 2: Basic Command Test

```bash
hen command-list
```

Verify the command system is working and commands are registered.

### Step 3: System Discovery

```bash
hen backend-list
hen parser-list
hen registry-list
```

Verify modules are loading correctly and extensions are detected.

### Step 4: Database Test (if configured)

```bash
hen check-db -root
```

Verify database connections work (requires SSL certificates and credentials).

### Step 5: Debugger Run

```bash
hen debugger
```

Review the debugger output for any warnings or errors.

### Step 6: Troubleshooting

If any step fails:
1. Review the error message
2. Run the debugger and review its output
3. Copy debugger output to an AI agent for help
4. Check relevant documentation (this guide, error messages, etc.)

## Deployment Box vs. Developer Box

### Deployment Box Smoke Check

The **deployment box smoke check is more important** because:
- It's the actual production environment
- It has the real database connections
- It has the actual file permissions and paths
- It reflects the real deployment state

### Developer Box Smoke Check

Developer box smoke checking is useful for:
- Testing code changes before deployment
- Verifying dependencies locally
- Testing command syntax
- Debugging code issues

**Note**: Developer box may not have database access or may use different credentials.

## Common Issues and Solutions

### Missing Dependencies

**Problem**: Commands fail with import errors

**Solution**:
1. Run `dependency-list` to see what's missing
2. Install via pip: `pip install package-name`
3. If pip fails, check for system package requirements
4. Install system packages: `sudo apt install package-name`

### Database Connection Failures

**Problem**: Database commands fail with connection errors

**Solution**:
1. Verify config file exists and has correct values
2. Check SSL certificate paths are correct and files exist
3. Test MySQL connection directly
4. Verify MySQL user has correct permissions
5. Check firewall rules allow connections

### Module Loading Issues

**Problem**: Commands not found or modules not loading

**Solution**:
1. Run `debugger` to see module loading status
2. Check for Python path issues
3. Verify project structure is correct
4. Check for circular import issues
5. Review error messages in debugger output

### Permission Issues

**Problem**: Commands fail with permission errors

**Solution**:
1. Verify file permissions on project directory
2. Check user has access to required files
3. Verify group memberships are correct
4. Check `/srv/` directory permissions if testing deployment paths

## Getting Help

### Using AI Agents

When smoke checking reveals issues:
1. Run the debugger: `hen debugger`
2. Copy the entire debugger output
3. Paste it into your AI agent chat window
4. Describe the issue you're seeing
5. The agent can help interpret the output and suggest fixes

### Debugger Output Format

The debugger output is structured to be:
- **Complete**: Includes all relevant system information
- **Structured**: Organized by category (system, gateway, database, etc.)
- **Actionable**: Shows specific paths, errors, and status information

## Next Steps

After successful smoke checking:
1. Proceed with installation (Chapter 5)
2. Or continue development if testing on developer box
3. Use smoke check process regularly to verify system health

