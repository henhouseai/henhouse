#!/usr/bin/env pwsh
# Stage PowerShell wrapper script
# Usage: .\stage.ps1 [command] [args...]

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to the script directory
Set-Location $ScriptDir

# Run the Python script with all passed arguments
python stage.py $args
