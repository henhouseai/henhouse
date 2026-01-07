#!/bin/bash

# Get site name from argument, default to henhouse
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

# Create new tmux session with unique name
tmux new-session -d -s "$SESSION_NAME" -x "$(tput cols)" -y "$(tput lines)"

# Split first pane: top 50%, bottom 50%
tmux split-window -t "${SESSION_NAME}:0.0" -v -p 50

# Split the bottom pane 33/67 (maintenance log gets 1/3, flask aggregator gets 2/3)
tmux split-window -t "${SESSION_NAME}:0.1" -v -p 67

# Select the top pane and launch htop
tmux send-keys -t "${SESSION_NAME}:0.0" "htop" Enter

# Select the middle pane and tail the maintenance log
tmux send-keys -t "${SESSION_NAME}:0.1" "tail -F /srv/${SITE}/logs/maintenance_${SITE}.log" Enter

# Select the bottom pane and launch the flask aggregator
tmux send-keys -t "${SESSION_NAME}:0.2" "python3 hh/deploy/maintenance/flask_aggregator.py ${SITE}" Enter

# Focus on the bottom pane (flask aggregator) and attach session
tmux select-pane -t "${SESSION_NAME}:0.2"
tmux -2 attach-session -t "$SESSION_NAME"

