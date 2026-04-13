#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVICE="${1:-auto}"
MONITOR_PORT=""

usage() {
    echo "Usage: ./monitor.sh [device]"
    echo
    echo "Examples:"
    echo "  ./monitor.sh"
    echo "  ./monitor.sh /dev/tty.usbmodem123401"
}

if [[ "$DEVICE" == "-h" || "$DEVICE" == "--help" ]]; then
    usage
    exit 0
fi

if [ -x "$ROOT_DIR/.venv/bin/mpremote" ]; then
    MPREMOTE="$ROOT_DIR/.venv/bin/mpremote"
    MONITOR_PYTHON="$ROOT_DIR/.venv/bin/python"
elif command -v mpremote >/dev/null 2>&1; then
    MPREMOTE="$(command -v mpremote)"
    MONITOR_PYTHON="python3"
else
    echo "mpremote not found."
    echo "Run ./setup-flash.sh once, then re-run ./monitor.sh"
    exit 1
fi

if [ "$DEVICE" != "auto" ]; then
    MONITOR_PORT="$DEVICE"
else
    MONITOR_PORT="$("$MPREMOTE" connect list | awk '$3 != "None" && $3 != "0000:0000" { print $1; exit }')"
fi

if [ -z "$MONITOR_PORT" ]; then
    echo "Could not determine a serial port for the monitor."
    exit 1
fi

echo "Opening serial monitor on: $MONITOR_PORT"
echo "Press Ctrl-] to exit the monitor when you are done."

exec "$MONITOR_PYTHON" -m serial.tools.miniterm "$MONITOR_PORT" 115200
