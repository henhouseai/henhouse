#!/usr/bin/env python3

import os
import sys
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

# Site colors - can be extended for different sites
SITE_COLOR_MAP = {
    'henhouse': 'bright_blue',
    'foxhouse': 'bright_cyan',
    'global': 'cyan'
}

def build_log_config(site_name):
    """Build log configuration dynamically by scanning the log directory"""
    site_color = SITE_COLOR_MAP.get(site_name, 'bright_blue')
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
        
        flask_logs.append({
            "name": log_name,
            "path": str(log_file),
            "color": site_color
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

def get_site_from_log_name(log_name):
    """Extract site identifier from log name"""
    # Extract site name (everything before the first underscore)
    parts = log_name.split('_', 1)
    if len(parts) > 0:
        return parts[0]
    return 'global'  # default

def colorize_left_half(line, log_name):
    """Color the left half (metadata) of the log line"""
    import re
    
    # Get colors
    site = get_site_from_log_name(log_name)
    site_color = get_color_code(SITE_COLOR_MAP.get(site, 'white'))
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
                    # Add our timestamp prefix with log source (colored by site)
                    site = get_site_from_log_name(log_name)
                    site_color = get_color_code(SITE_COLOR_MAP.get(site, 'white'))
                    reset_color = get_color_code('reset')
                    timestamp_color = get_color_code('red')
                    
                    colored_timestamp = f"{timestamp_color}[{timestamp}]{reset_color}"
                    colored_log_name = f"{site_color}[{log_name}]{reset_color}"
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

