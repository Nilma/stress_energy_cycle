#!/usr/bin/env bash
# wrap_with_markers.sh — run an arbitrary workload with injected sigmarkeringer
#
# Examples:
#   ./wrap_with_markers.sh --interval 4 --tag myrun -- python3 script.py
#   ./wrap_with_markers.sh --tag build -- make -j4
#
# Options:
#   --interval N   periodic marker every N seconds (optional)
#   --tag NAME     base tag (default: run)
#   --no-startend  skip start/end markers

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/marker_utils.sh"

INTERVAL=""
TAG="run"
SEND_STARTEND=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interval) INTERVAL="$2"; shift 2 ;;
    --tag) TAG="$2"; shift 2 ;;
    --no-startend) SEND_STARTEND=0; shift ;;
    --) shift; break ;;
    *) break ;;
  esac
done

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 [--interval N] [--tag NAME] [--no-startend] -- <command...>" >&2
  exit 1
fi

CMD=( "$@" )

start_epoch=$(date +%s)
(( SEND_STARTEND == 1 )) && send_marker "${TAG}_start" "" "" "0"

set +e
"${CMD[@]}" &
WORK_PID=$!
set -e

if [[ -n "${INTERVAL}" ]]; then
  next="${INTERVAL}"
  while kill -0 "$WORK_PID" 2>/dev/null; do
    now=$(date +%s)
    elapsed=$(( now - start_epoch ))
    remain=$(( next - elapsed ))
    (( remain > 0 )) && sleep "$remain"
    kill -0 "$WORK_PID" 2>/dev/null && send_marker "${TAG}_t${next}" "" "" "$next"
    next=$(( next + INTERVAL ))
  done
fi

wait "$WORK_PID" || true

if (( SEND_STARTEND == 1 )); then
  total=$(( $(date +%s) - start_epoch ))
  send_marker "${TAG}_end" "" "" "$total"
fi
