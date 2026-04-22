#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVICE="auto"
WITH_CONFIG=0
WITH_SCENES=0
WITH_SCHEDULES=0
NO_MONITOR=0
MONITOR_PORT=""

usage() {
    echo "Usage: ./flash.sh [device] [--with-config] [--with-scenes] [--with-schedules] [--no-monitor]"
    echo
    echo "Examples:"
    echo "  ./flash.sh"
    echo "  ./flash.sh --with-config"
    echo "  ./flash.sh --with-scenes --with-schedules"
    echo "  ./flash.sh --no-monitor"
    echo "  ./flash.sh /dev/tty.usbmodem123401"
    echo "  ./flash.sh /dev/tty.usbmodem123401 --with-config --with-scenes --with-schedules"
}

resolve_monitor_port() {
    if [ "$NO_MONITOR" -eq 1 ]; then
        return
    fi

    if [ "$DEVICE" != "auto" ]; then
        MONITOR_PORT="$DEVICE"
        return
    fi

    MONITOR_PORT="$("$MPREMOTE" connect list | awk '$3 != "None" && $3 != "0000:0000" { print $1; exit }')"

    if [ -z "$MONITOR_PORT" ]; then
        echo "Could not determine a serial port for the monitor."
        exit 1
    fi
}

for arg in "$@"; do
    case "$arg" in
        --with-config)
            WITH_CONFIG=1
            ;;
        --with-scenes)
            WITH_SCENES=1
            ;;
        --with-schedules)
            WITH_SCHEDULES=1
            ;;
        --no-monitor)
            NO_MONITOR=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            DEVICE="$arg"
            ;;
    esac
done

if [ -x "$ROOT_DIR/.venv/bin/mpremote" ]; then
    MPREMOTE="$ROOT_DIR/.venv/bin/mpremote"
    MONITOR_PYTHON="$ROOT_DIR/.venv/bin/python"
elif command -v mpremote >/dev/null 2>&1; then
    MPREMOTE="$(command -v mpremote)"
    MONITOR_PYTHON="python3"
else
    echo "mpremote not found."
    echo "Run ./setup-flash.sh once, then re-run ./flash.sh"
    exit 1
fi

resolve_monitor_port

echo "Uploading code to device: $DEVICE"
if [ "$WITH_CONFIG" -eq 1 ]; then
    echo "Including src/config.json in this flash."
else
    echo "Preserving config.json already on the device."
fi
if [ "$WITH_SCENES" -eq 1 ]; then
    echo "Including src/scenes.json in this flash."
else
    echo "Preserving scenes.json already on the device."
fi
if [ "$WITH_SCHEDULES" -eq 1 ]; then
    echo "Including src/schedules.json in this flash."
else
    echo "Preserving schedules.json already on the device."
fi
if [ "$NO_MONITOR" -eq 1 ]; then
    echo "Skipping serial monitor."
else
    echo "Opening serial monitor on: $MONITOR_PORT"
    echo "Press Ctrl-] to exit the monitor when you are done."
fi

CMD=(
    "$MPREMOTE"
    connect "$DEVICE"
    fs cp "$ROOT_DIR"/src/*.py : +
    fs cp "$ROOT_DIR"/src/config_*.json : +
    fs cp "$ROOT_DIR"/src/default_scenes.json :default_scenes.json +
    fs cp -r "$ROOT_DIR"/src/www/* :www +
)

if [ "$WITH_CONFIG" -eq 1 ]; then
    CMD+=(fs cp "$ROOT_DIR"/src/config.json :config.json +)
fi

if [ "$WITH_SCENES" -eq 1 ]; then
    CMD+=(fs cp "$ROOT_DIR"/src/scenes.json :scenes.json +)
fi

if [ "$WITH_SCHEDULES" -eq 1 ]; then
    CMD+=(fs cp "$ROOT_DIR"/src/schedules.json :schedules.json +)
fi

CMD+=(reset)

"${CMD[@]}"

if [ "$NO_MONITOR" -eq 1 ]; then
    exit 0
fi

sleep 2

exec "$MONITOR_PYTHON" -m serial.tools.miniterm "$MONITOR_PORT" 115200
