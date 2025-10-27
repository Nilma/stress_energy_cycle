#!/usr/bin/env bash
# marker_utils.sh — send markers via your existing sigmark.sh
# No local logging. Uses: sh sigmark.sh <ip:port> <CH1|CH2> "<message>"

set -euo pipefail

# --- CONFIG (override with env vars if needed) ---
SIGMARK_PATH="${SIGMARK_PATH:-./sigmark.sh}"         # path to your script
REMOTE_ADDRESS="${REMOTE_ADDRESS:-192.168.50.2:8000}" # ip:port of your Mac/PC
MARKER_CHANNEL="${MARKER_CHANNEL:-CH1}"               # CH1 or CH2
# --------------------------------------------------

send_marker_raw() {
  # $1 = message string (e.g. "stop,sigmark,0")
  # Never writes local logs; only sends to remote via sigmark.sh
  sh "$SIGMARK_PATH" "$REMOTE_ADDRESS" "$MARKER_CHANNEL" "$1" || {
    echo "WARN: failed to send marker: $1" >&2
    return 0  # don't kill the run if a single marker fails
  }
}

# Convenience helpers using your 3-field CSV message convention
send_start()  { send_marker_raw "start,sigmark,0"; }
send_stop()   { send_marker_raw "stop,sigmark,0"; }
send_tick()   { # $1 = elapsed seconds (integer)
  local t="$1"
  send_marker_raw "sigmark,${t},0"
}

