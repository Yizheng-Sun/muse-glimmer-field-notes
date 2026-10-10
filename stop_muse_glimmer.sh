#!/usr/bin/env bash
set -euo pipefail

PID_FILE="${PID_FILE:-/workspace/muse-glimmer-field-notes/.logs/muse-glimmer.pid}"

if [ ! -f "$PID_FILE" ]; then
  echo "No PID file found at $PID_FILE"
  exit 1
fi

PID="$(cat "$PID_FILE" 2>/dev/null || true)"
if [ -z "${PID:-}" ] || ! kill -0 "$PID" 2>/dev/null; then
  echo "Muse Glimmer server is not running."
  exit 1
fi

kill "$PID"
for _ in $(seq 1 20); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Stopped Muse Glimmer server (PID $PID)"
    rm -f "$PID_FILE"
    exit 0
  fi
  sleep 0.25
done

kill -9 "$PID"
rm -f "$PID_FILE"
echo "Force-stopped Muse Glimmer server (PID $PID)"
