#!/bin/bash

# Reset problematic environment variables
unset PYTHONHOME
unset PYTHONPATH

# Create logs directory
mkdir -p "$(dirname "$0")/logs"

# Log environment for debugging
echo "Running with clean environment" >&2
echo "PATH: $PATH" >&2
echo "PWD: $PWD" >&2

# Create virtual environment if it doesn't exist
VENV_DIR="$(dirname "$0")/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..." >&2
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing dependencies..." >&2
pip install -r "$(dirname "$0")/requirements.txt" >&2

# Run the script
exec python "$(dirname "$0")/simple_jdbc.py" "$@" 