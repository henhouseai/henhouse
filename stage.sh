#!/usr/bin/env bash
# Stage bash wrapper script
# Usage: ./stage.sh [command] [args...]

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Run the Python script with all passed arguments
python3 stage.py "$@"

