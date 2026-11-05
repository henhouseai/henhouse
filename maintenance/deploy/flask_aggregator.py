#!/usr/bin/env python3

import os
import sys
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

# Add project root to Python path so we can import hh modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from hh.deploy.deploy_utils import detect_project_context
from hh.deploy.conf.user_account_suffixes import HENHOUSE_TIERS

# Tier colors - dynamically built based on project and tiers
TIER_COLOR_MAP: dict[str, str] = {}

def initialize_tier_colors():
    """Initialize tier color mapping based on current project and configured tiers."""
    global TIER_COLOR_MAP

    # Get project name
    project_name, _ = detect_project_context()

    # Define tier colors (includes media tier and default)
    tier_colors = {
        'guest': 'white',      # White for guest tier
        'verified': 'magenta', # Magenta for verified users
        'admin': 'yellow',     # Yellow for admins
        'root': 'green',       # Green for highest tier
        'media': 'cyan',       # Cyan for media server tier
        'errors': 'red',       # Red for error logs
        'other': 'blue',       # Blue for other unmatched logs
    }

    # Build the mapping: {project}_{tier} -> color
    TIER_COLOR_MAP = {}
    for tier in HENHOUSE_TIERS:
        tier_key = f"{project_name}_{tier}"
        TIER_COLOR_MAP[tier_key] = tier_colors.get(tier, tier_colors['other'])

    # Add media, errors, and other tiers
    TIER_COLOR_MAP[f"{project_name}_media"] = tier_colors['media']
    TIER_COLOR_MAP['errors'] = tier_colors['errors']
    TIER_COLOR_MAP['other'] = tier_colors['other']

def build_log_config(site_name):
    """Build log configuration dynamically by scanning the log directory"""
    flask_logs = []
    
    log_dir = Path(f"/srv/{site_name}/logs")
    
    if not log_dir.exists():
        return {"flask_logs": []}
    
    # Find all log files matching pattern *_{site}*.log (includes flask and migration logs)
    pattern = f"*_{site_name}*.log"
    for log_file in log_dir.glob(pattern):
        # Exclude maintenance log and rotated logs (.1, .2, etc.)
        if "maintenance" in log_file.name or log_file.suffixes and len(log_file.suffixes) > 1:
            continue
        
        # Extract name from filename
        # For flask_{site}_{tier}.log -> {site}_{tier}
        # For migration_{site}.log -> migration_{site}
        log_name = log_file.stem
        if log_name.startswith("flask_"):
            log_name = log_name.replace("flask_", "", 1)

        # Determine tier-based color for this log
        tier = get_tier_from_log_name(log_name)
        log_color = TIER_COLOR_MAP.get(tier, 'bright_blue')

        flask_logs.append({
            "name": log_name,
            "path": str(log_file),
            "color": log_color
        })
    
    # Sort by name for consistent ordering
    flask_logs.sort(key=lambda x: x["name"])
    
    return {"flask_logs": flask_logs}

# ANSI color codes
COLORS = {
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'white': '\033[37m',
    'bright_red': '\033[91m',
    'bright_green': '\033[92m',
    'bright_yellow': '\033[93m',
    'bright_blue': '\033[94m',
    'bright_magenta': '\033[95m',
    'bright_cyan': '\033[96m',
    'bright_white': '\033[97m',
    'reset': '\033[0m'
}

# Log type colors
LOG_TYPE_COLORS = {
    'access': 'white',
    'error': 'red', 
    'traffic': 'cyan',
    'debug': 'yellow'
}

# Site colors (now using SITE_COLOR_MAP defined above)

def expand_path(path):
    """Expand ~ and relative paths to absolute paths"""
    return os.path.expanduser(os.path.expandvars(path))

def get_color_code(color_name):
    """Get ANSI color code for the given color name"""
    return COLORS.get(color_name, COLORS['white'])

def get_log_type(log_name):
    """Determine log type from log name"""
    if 'access' in log_name:
        return 'access'
    elif 'error' in log_name:
        return 'error'
    elif 'traffic' in log_name:
        return 'traffic'
    elif 'debug' in log_name:
        return 'debug'
    else:
        return 'access'  # default

def get_tier_from_log_name(log_name):
    """Extract tier identifier from log name (e.g., foxhouse_guest -> foxhouse_guest)"""
    # Special case: errors logs are always red
    if log_name.startswith('errors_'):
        return 'errors'

    # Look for tier suffixes in the log name
    project_name, _ = detect_project_context()

    # Check all known tiers (including media which is not in HENHOUSE_TIERS config)
    all_tiers = HENHOUSE_TIERS + ['media']

    for tier in all_tiers:
        tier_suffix = f"_{tier}"
        if tier_suffix in log_name:
            return f"{project_name}_{tier}"

    # If no tier found, check if it's a migration or other special log
    if 'migration' in log_name:
        return f"{project_name}_admin"  # Migration logs typically admin level

    return 'other'  # fallback for unmatched logs

def colorize_left_half(line, log_name):
    """Color the left half (metadata) of the log line"""
    import re

    # Get colors
    tier = get_tier_from_log_name(log_name)
    tier_color = get_color_code(TIER_COLOR_MAP.get(tier, 'bright_blue'))
    timestamp_color = get_color_code('red')
    reset_color = get_color_code('reset')
    
    # Colorize timestamps (anything in square brackets) in RED
    colored_line = re.sub(r'(\[[^\]]*\])', f'{timestamp_color}\\1{reset_color}', line)
    
    # Colorize all IP addresses in RED
    colored_line = re.sub(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', 
                        f'{timestamp_color}\\1{reset_color}', 
                        colored_line)
    
    return colored_line

def colorize_right_half(line, log_name):
    """Color the right half (message) of the log line"""
    # Get colors
    log_type = get_log_type(log_name)
    log_type_color = get_color_code(LOG_TYPE_COLORS.get(log_type, 'white'))
    reset_color = get_color_code('reset')
    
    # Color the entire message with log type color
    return f'{log_type_color}{line}{reset_color}'

def tail_log_file(log_config, output_queue):
    """Tail a single log file and put new lines in the output queue"""
    log_path = expand_path(log_config['path'])
    log_name = log_config['name']
    color_code = get_color_code(log_config['color'])
    
    while True:
        # Wait for file to exist if it doesn't (handles redeploy scenarios)
        if not os.path.exists(log_path):
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] [INFO] Waiting for {log_name} to appear at {log_path}...")
            time.sleep(2)
            continue
        
        try:
            # Use tail -F to follow the file by name (handles log rotation and file recreation)
            process = subprocess.Popen(
                ['tail', '-F', log_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            while True:
                line = process.stdout.readline()
                if line:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    # Split the line at the last ]
                    line_stripped = line.rstrip()
                    last_bracket = line_stripped.rfind(']')
                    if last_bracket != -1:
                        # Split into left and right halves
                        left_half = line_stripped[:last_bracket + 1]
                        right_half = line_stripped[last_bracket + 1:]
                        
                        # Color each half independently
                        colored_left = colorize_left_half(left_half, log_name)
                        colored_right = colorize_right_half(right_half, log_name)
                        
                        # Combine them
                        split_line = colored_left + colored_right
                    else:
                        split_line = line_stripped
                    # Add our timestamp prefix with log source (colored by tier)
                    tier = get_tier_from_log_name(log_name)
                    tier_color = get_color_code(TIER_COLOR_MAP.get(tier, 'bright_blue'))
                    reset_color = get_color_code('reset')
                    timestamp_color = get_color_code('red')

                    colored_timestamp = f"{timestamp_color}[{timestamp}]{reset_color}"
                    colored_log_name = f"{tier_color}[{log_name}]{reset_color}"
                    output = f"{colored_timestamp} {colored_log_name} {split_line}"
                    output_queue.put(output)
                elif process.poll() is not None:
                    # Process exited, break inner loop to restart
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{timestamp}] [INFO] Tail process for {log_name} exited, restarting...")
                    break
                    
        except Exception as e:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] [ERROR] Failed to tail {log_name}: {e}, retrying in 2 seconds...")
            time.sleep(2)

def main():
    """Main function to start Flask log monitoring"""
    # Initialize tier colors based on current project
    initialize_tier_colors()

    # Get site name from command line argument, default to henhouse
    site_name = sys.argv[1] if len(sys.argv) > 1 else 'henhouse'
    
    # Build log configuration dynamically based on site
    config = build_log_config(site_name)
    
    # Collect Flask logs to monitor
    logs_to_monitor = config.get('flask_logs', [])
    
    if not logs_to_monitor:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] No Flask logs configured to monitor for site: {site_name}")
        return
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [INFO] Starting Flask log monitor for site '{site_name}' with {len(logs_to_monitor)} log files")
    
    # Create output queue for thread-safe printing
    import queue
    output_queue = queue.Queue()
    
    # Start tailing threads for each log file
    threads = []
    for log_config in logs_to_monitor:
        thread = threading.Thread(target=tail_log_file, args=(log_config, output_queue))
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    # Print output from the queue
    try:
        while True:
            try:
                # Get output with timeout to allow for graceful shutdown
                output = output_queue.get(timeout=1)
                print(output)
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [INFO] Shutting down Flask log monitor...")
        return

if __name__ == '__main__':
    main()

