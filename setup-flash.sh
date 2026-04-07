#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Creating local virtualenv in .venv"
    python3 -m venv "$ROOT_DIR/.venv"
fi

echo "Installing/updating mpremote in project-local .venv"
"$VENV_PYTHON" -m pip install --upgrade pip mpremote

echo
echo "Setup complete."
echo "Use ./flash.sh to upload code to the board."
echo "You do not need to activate the virtualenv."
