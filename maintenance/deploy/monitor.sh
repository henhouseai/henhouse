#!/bin/bash

# Get site name from command line argument (passed by monitor action)
SITE="${1:-henhouse}"

# Check for -kill flag
if [ "$1" == "-kill" ]; then
    # If second arg is provided, kill specific site session, otherwise kill all maintenance sessions
    if [ -n "$2" ]; then
        tmux kill-session -t "maintenance_$2" 2>/dev/null
    else
        tmux kill-session -t maintenance 2>/dev/null
        # Also try to kill any site-specific sessions
        tmux list-sessions 2>/dev/null | grep -o "maintenance_[^:]*" | xargs -I {} tmux kill-session -t {} 2>/dev/null
    fi
    exit 0
fi

SESSION_NAME="maintenance_${SITE}"

# Kill any pre-existing maintenance session for this site
tmux kill-session -t "$SESSION_NAME" 2>/dev/null

# Create tmux session with panes
echo "Creating tmux session: $SESSION_NAME"

# Start with a basic session
tmux new-session -d -s "$SESSION_NAME"

# Split the window vertically (60/40 - more space for htop)
echo "Splitting window..."
tmux split-window -v -l 60%

# Split the bottom pane horizontally (50/50 for logs/aggregator)
echo "Creating third pane..."
tmux split-window -t "$SESSION_NAME:0.1"

# Send commands to panes
tmux send-keys -t "$SESSION_NAME:0.0" "htop" Enter
tmux send-keys -t "$SESSION_NAME:0.1" "tail -F /srv/${SITE}/logs/maintenance_${SITE}.log" Enter

# Send flask aggregator to bottom pane
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmux send-keys -t "$SESSION_NAME:0.2" "python3 \"${SCRIPT_DIR}/flask_aggregator.py\" ${SITE}" Enter

# Select the flask aggregator pane (bottom)
tmux select-pane -t "$SESSION_NAME:0.2"
echo "Attaching to session..."
tmux attach-session -t "$SESSION_NAME"