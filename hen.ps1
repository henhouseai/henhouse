#!/usr/bin/env pwsh
# Henhouse PowerShell wrapper script
# Usage: .\henhouse.ps1 [command] [args...]

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to the script directory
Set-Location $ScriptDir

# Run the Python script with all passed arguments
python hen.py $args
