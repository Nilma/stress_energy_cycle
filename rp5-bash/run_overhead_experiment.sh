#!/usr/bin/env bash
# run_overhead_experiment.sh — orchestrate 7×(81s) forløb, each repeated 3×.
# Forløb definitions:
#   0: none
#   1: every 20s -> 4 markers at 20,40,60,80
#   2: every 10s -> 8 markers at 10,...,80
#   3: every 5s  -> 16 markers at 5,...,80
#   4: every 4s  -> 20 markers at 4,...,80
#   5: every 2s  -> 40 markers at 2,...,80
#   6: every 1s  -> 80 markers at 1,...,80
# Start marker at t=0, end marker at t=81 (by default), independent of periodic series.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/marker_utils.sh"

REPEATS="${REPEATS:-3}"
DURATION="${DURATION:-81}"
COOLDOWN="${COOLDOWN:-10}"
periods=(0 20 10 5 4 2 1)

sleep_until() {
  local start_epoch="$1" target="$2"
  while : ; do
    local now=$(date +%s)
    local remain=$(( target - (now - start_epoch) ))
    (( remain <= 0 )) && break
    if (( remain > 1 )); then sleep $((remain-1)); else sleep "$remain"; fi
  done
}

run_forloeb() {
  local idx="$1" period="$2" rep="$3"

  echo "=== Forløb $idx (period=${period}s) — repeat $rep ==="
  local start_epoch=$(date +%s)

  send_marker "start_f${idx}_r${rep}" "$idx" "$rep" "0"

  if (( period > 0 )); then
    for t in $(seq "$period" "$period" 80); do
      sleep_until "$start_epoch" "$t"
      send_marker "f${idx}_r${rep}_t${t}" "$idx" "$rep" "$t"
    done
  fi

  sleep_until "$start_epoch" "$DURATION"
  send_marker "end_f${idx}_r${rep}" "$idx" "$rep" "$DURATION"
}

for rep in $(seq 1 "$REPEATS"); do
  for idx in $(seq 0 6); do
    run_forloeb "$idx" "${periods[$idx]}" "$rep"
    (( COOLDOWN > 0 )) && echo "Cooldown ${COOLDOWN}s..." && sleep "$COOLDOWN"
  done
done

echo "Done. CSV at: ${MARKER_CSV}"
