#!/usr/bin/env bash
# marker_utils.sh — Zealands Raspberry Pi marker utilities (HTTP JSON for Siglent logger).
# Usage:
#   source ./marker_utils.sh
#   send_marker "tag" [scenario] [repeat] [t_rel_sec]
#
# Marker transports:
#   http_json  -> POST JSON {"message": "...", "channelId": "CH1"} to http://REMOTE_ADDRESS/api/log
#   sigmark_sh -> call an external sigmark.sh helper script with (REMOTE_ADDRESS CHANNEL MESSAGE)
#   file       -> append a line to MARKER_LOG
#
# Environment (with safe defaults):
#   REMOTE_ADDRESS  default: 192.168.50.2:8000   # << your logger
#   MARKER_CHANNEL  default: CH1                 # or CH2
#   MARKER_METHOD   default: http_json
#   MARKER_LOG      default: ./markers.log
#   MARKER_CSV      default: ./markers_log.csv
#   SIGMARK_PATH    default: ./sigmark.sh (only used with MARKER_METHOD=sigmark_sh)
#
# This script also writes CSV rows for each emitted marker:
#   ts_iso,epoch_ms,tag,scenario,repeat,t_rel_sec

set -euo pipefail

REMOTE_ADDRESS="${REMOTE_ADDRESS:-192.168.50.2:8000}"
MARKER_CHANNEL="${MARKER_CHANNEL:-CH1}"
MARKER_METHOD="${MARKER_METHOD:-http_json}"
MARKER_LOG="${MARKER_LOG:-./markers.log}"
MARKER_CSV="${MARKER_CSV:-./markers_log.csv}"
SIGMARK_PATH="${SIGMARK_PATH:-./sigmark.sh}"

ensure_csv_header() {
  if [[ ! -f "$MARKER_CSV" ]]; then
    echo "ts_iso,epoch_ms,tag,scenario,repeat,t_rel_sec" >> "$MARKER_CSV"
  fi
}

now_epoch_ms() { date +%s%3N; }
now_iso() { date -u +"%Y-%m-%dT%H:%M:%S.%3NZ"; }

log_marker_csv() {
  local tag="$1" scenario="${2:-}" repeat="${3:-}" t_rel="${4:-}"
  ensure_csv_header
  echo "$(now_iso),$(now_epoch_ms),${tag},${scenario},${repeat},${t_rel}" >> "$MARKER_CSV"
}

_send_http_json() {
  # POST to http://REMOTE_ADDRESS/api/log with JSON body
  local msg="$1"
  curl -fsS -m 2 -H "Content-Type: application/json" \
    -X POST "http://${REMOTE_ADDRESS}/api/log" \
    -d "{\"message\":\"${msg}\",\"channelId\":\"${MARKER_CHANNEL}\"}" >/dev/null || true
}

_send_sigmark_sh() {
  local msg="$1"
  if [[ ! -x "$SIGMARK_PATH" ]]; then
    echo "WARN: SIGMARK_PATH '$SIGMARK_PATH' not found or not executable; falling back to http_json" >&2
    _send_http_json "$msg"
    return
  fi
  "$SIGMARK_PATH" "${REMOTE_ADDRESS}" "${MARKER_CHANNEL}" "${msg}" || true
}

_send_file() {
  local msg="$1"
  echo "$(now_iso) ${MARKER_CHANNEL} tag=${msg}" >> "$MARKER_LOG"
}

# Public API
send_marker() {
  local tag="$1"
  local scenario="${2:-}"
  local repeat="${3:-}"
  local t_rel="${4:-}"

  case "$MARKER_METHOD" in
    http_json) _send_http_json "$tag" ;;
    sigmark_sh) _send_sigmark_sh "$tag" ;;
    file) _send_file "$tag" ;;
    *) echo "ERROR: Unknown MARKER_METHOD: $MARKER_METHOD" >&2 ; exit 1 ;;
  esac

  log_marker_csv "$tag" "$scenario" "$repeat" "$t_rel"
}
