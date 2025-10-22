#!/usr/bin/env python3
"""
main.py
Runs a repeatable stress/rest protocol and records energy using the user's RAPL logger.

- Rest 20s (0% load), then stress 80s at load L in [0, 10, ..., 100]
- Records during BOTH rest and stress phases.
- Uses existing logging start/stop functions from energy_logger.py if present.

Detected in energy_logger.py:
  start logging: NOT FOUND (using fallback)
  stop  logging: NOT FOUND (using fallback)

Usage:
  python3 main.py --cpu 1 --rest 20 --stress 80 --levels 0,10,20,30,40,50,60,70,80,90,100

To Run:
    python3 main.py
"""

import argparse
import subprocess
import sys
import time

# Try to import user's logging functions if available
START_FUNC = None
STOP_FUNC = None

try:
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location("user_main", str(pathlib.Path("energy_logger.py")))
    user_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_main)  # type: ignore
    START_FUNC = getattr(user_main, "None", None)
    STOP_FUNC  = getattr(user_main, "None", None)
except Exception as e:
    print(f"[warn] Could not import energy_logger.py logging functions: {e}", file=sys.stderr)

def default_start_logging():
    print("[info] Starting energy logging (fallback).")
    # TODO: Replace with your actual start logging call if not auto-detected.

def default_stop_logging():
    print("[info] Stopping energy logging (fallback).")
    # TODO: Replace with your actual stop logging call if not auto-detected.

def start_logging():
    if callable(START_FUNC):
        print("[info] Using energy_logger.py start logging")
        return START_FUNC()
    return default_start_logging()

def stop_logging():
    if callable(STOP_FUNC):
        print("[info] Using energy_logger.py stop logging")
        return STOP_FUNC()
    return default_stop_logging()

def run(cmd: str):
    print(f"[run] {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def protocol(levels, cpu, rest_s, stress_s):
    for lvl in levels:
        # Rest phase at 0%
        run(f"stress-ng -l 0 --cpu {cpu} -t {rest_s}s")
        # Stress phase at target %
        run(f"stress-ng -l {lvl} --cpu {cpu} -t {stress_s}s")
        print(f"[ok] Completed level {lvl}% (rest {rest_s}s + stress {stress_s}s)")

def parse_levels(s: str):
    if s.strip().lower() in ("default", "std", "standard"):
        return [0,10,20,30,40,50,60,70,80,90,100]
    # allow ranges like 0:100:10 or comma-separated
    if ":" in s:
        a,b,step = [int(x) for x in s.split(":")]
        return list(range(a, b+1, step))
    return [int(x) for x in s.split(",") if x.strip() != ""]

def main():
    ap = argparse.ArgumentParser(description="Stress/Rest energy logging protocol")
    ap.add_argument("--cpu", type=int, default=1, help="Number of CPU workers to stress (default: 1)")
    ap.add_argument("--rest", type=int, default=20, help="Rest duration in seconds at 0%% load (default: 20)")
    ap.add_argument("--stress", type=int, default=80, help="Stress duration in seconds at target load (default: 80)")
    ap.add_argument("--levels", type=str, default="default",
                    help="Comma list or range (e.g., 0,10,... or 0:100:10). Use 'default' for 0..100 by 10.")
    args = ap.parse_args()

    levels = parse_levels(args.levels)

    print("[info] Starting logging...")
    start_logging()
    try:
        protocol(levels, args.cpu, args.rest, args.stress)
    finally:
        print("[info] Stopping logging...")
        stop_logging()

if __name__ == "__main__":
    main()
