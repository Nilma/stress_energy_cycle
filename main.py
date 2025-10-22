#!/usr/bin/env python3
"""
main_with_csv.py
----------------------------
Runs a repeatable stress/rest protocol while sampling voltage/current on a Raspberry Pi
and writes a CSV log with timestamps, load percentage, voltage, current, power, and markers.

Key ideas:
- A background thread ("Sampler") polls voltage/current at a fixed interval and writes rows to CSV.
- The main thread orchestrates the experiment: for each load level, it runs a 20s rest at 0% and 80s stress at the target %.
- Phase "markers" are injected into the CSV so it's easy to segment data during analysis.
- If stress-ng is not installed (e.g., on macOS), the script simulates duration using sleep so you can test logging.
"""

import argparse
import csv
import subprocess
import threading
import time
from datetime import datetime, timezone
import importlib.util
import pathlib
import sys
import shutil

# -------------------------
# Import energy_logger.py
# -------------------------
# We import energy_logger.py from the same folder. That file must provide
# a function `read_voltage_current()` that returns (voltage_v, current_a).
# On Raspberry Pi, it's typically implemented using `vcgencmd pmic_read_adc`.
THIS_DIR = pathlib.Path(__file__).resolve().parent
EL_PATH = THIS_DIR / "energy_logger.py"
spec = importlib.util.spec_from_file_location("energy_logger", str(EL_PATH))
energy_logger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(energy_logger)  # type: ignore

def has_stress_ng() -> bool:
    """
    Return True if the 'stress-ng' binary is available on PATH.
    On macOS (or any system without stress-ng), we fall back to simulation.
    """
    return shutil.which("stress-ng") is not None


class Sampler(threading.Thread):
    """
    Background sampler that periodically reads voltage/current and writes CSV rows.
    - Runs as a daemon thread so it won't block interpreter shutdown in hard failures.
    - Writes the header once, then a row at every interval.
    - Also supports writing "marker" rows to record phase transitions.
    """
    def __init__(self, csv_path: str, interval: float = 0.5):
        super().__init__(daemon=True)
        # Minimum interval guard to prevent extremely fast polling
        self.interval = max(0.05, float(interval))
        self.csv_path = csv_path

        # Thread-safe controls
        self.stop_event = threading.Event()   # signal to stop the thread
        self._lock = threading.Lock()         # protect shared state like _load
        self._load = 0                        # current target load (%) to log with samples

        # Open CSV for writing and emit header
        self._fh = open(self.csv_path, "w", newline="")
        self._csv = csv.writer(self._fh)
        self._csv.writerow(["timestamp_iso", "epoch_s", "load_percent", "voltage_v", "current_a", "power_w", "marker"])

    def set_load(self, pct: int) -> None:
        """
        Update the 'load percent' value that will be recorded with each sample row.
        Called by the main thread when switching phases (rest/stress).
        """
        with self._lock:
            self._load = int(pct)

    def mark(self, text: str) -> None:
        """
        Write a special "marker" row into the CSV.
        Marker rows help you align the CSV with phase transitions (e.g., REST_BEGIN, STRESS_60_BEGIN).
        """
        now = time.time()
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        # For marker rows we leave the numeric columns empty
        self._csv.writerow([ts, f"{now:.3f}", "", "", "", "", text])
        self._fh.flush()

    def run(self) -> None:
        """
        Main loop of the sampler thread:
        - At each interval, read (V, I) via energy_logger.read_voltage_current()
        - Compute power (P = V * I) if both are available
        - Write a CSV row with current load and measurements
        """
        next_t = time.time()
        while not self.stop_event.is_set():
            # Pace the loop to fire exactly at the desired cadence
            now = time.time()
            if now < next_t:
                time.sleep(next_t - now)

            ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

            # Read the current target load safely
            with self._lock:
                load = self._load

            # Collect voltage/current from the energy logger
            try:
                v, i = energy_logger.read_voltage_current()
            except Exception:
                # If the logger raises for any reason, record empty values for this tick
                v, i = None, None

            # Compute power if possible
            p = v * i if (v is not None and i is not None) else None

            # Write the data row
            self._csv.writerow([
                ts,
                f"{now:.3f}",
                load,
                v if v is not None else "",
                i if i is not None else "",
                p if p is not None else "",
                ""
            ])

            # Schedule the next tick
            next_t += self.interval

        # Clean shutdown: flush and close file handle
        self._fh.flush()
        self._fh.close()

    def stop(self) -> None:
        """
        Signal the sampler to stop and wait briefly for the thread to exit.
        """
        self.stop_event.set()
        self.join(timeout=2)


def run_cmd(cmd: str) -> None:
    """
    Run a shell command. If 'stress-ng' is available, execute it for real.
    If not, parse the requested duration (-t <Ns>) and just sleep that long.
    This lets you test the sampling/CSV pipeline without stress-ng.
    """
    print(f"[run] {cmd}")
    if has_stress_ng():
        subprocess.run(cmd, shell=True, check=True)
    else:
        import re
        m = re.search(r"-t\s*(\d+)s", cmd)
        dur = int(m.group(1)) if m else 1
        print(f"[warn] stress-ng not found; simulating load for {dur}s")
        time.sleep(dur)


def parse_levels(s: str):
    """
    Parse --levels input.
    Accepts:
      - 'default' / 'std' / 'standard'  -> [0,10,20,...,100]
      - range 'A:B:S' (inclusive)       -> list(range(A, B+1, S))
      - comma-separated list             -> e.g. '0,25,50,75,100'
    """
    s = s.strip().lower()
    if s in ("default", "std", "standard"):
        return [0,10,20,30,40,50,60,70,80,90,100]
    if ":" in s:
        parts = [int(x) for x in s.split(":")]
        if len(parts) == 3:
            a,b,step = parts
            return list(range(a, b+1, step))
    return [int(x) for x in s.split(",") if x.strip() != ""]


def main():
    """
    Entry point.
    - Starts the Sampler thread to collect measurements at a fixed interval.
    - Iterates over load levels and for each:
        * Records a 0% "rest" period (default 20s)
        * Records a "stress" period at the target load (default 80s)
    - Injects markers around each phase for easier segmentation during analysis.
    - Stops the sampler and prints the CSV path when done.
    """
    ap = argparse.ArgumentParser(description="Stress/Rest energy CSV logger (internal V/I)")
    ap.add_argument("--cpu", type=int, default=1, help="Number of CPU workers for stress-ng")
    ap.add_argument("--rest", type=int, default=20, help="Rest duration seconds at 0%")
    ap.add_argument("--stress", type=int, default=80, help="Stress duration seconds at target load")
    ap.add_argument("--levels", type=str, default="default", help="Comma list or range 0:100:10")
    ap.add_argument("--interval", type=float, default=0.5, help="Sampling interval seconds")
    ap.add_argument("--out", type=str, default="energy_cycle_log.csv", help="CSV output path")
    args = ap.parse_args()

    # Resolve levels to a list of ints (e.g., [0,10,...,100])
    levels = parse_levels(args.levels)

    # Start background sampling
    sampler = Sampler(args.out, interval=args.interval)
    sampler.start()
    sampler.mark("START_PROTOCOL")

    try:
        # For each load level, run a rest phase followed by a stress phase
        for lvl in levels:
            # Rest at 0% before stressing at this level
            sampler.set_load(0)
            sampler.mark(f"REST_BEGIN_level_{lvl}")
            run_cmd(f"stress-ng -l 0 --cpu {args.cpu} -t {args.rest}s")
            sampler.mark(f"REST_END_level_{lvl}")

            # Stress at the specified level
            sampler.set_load(lvl)
            sampler.mark(f"STRESS_{lvl}_BEGIN")
            run_cmd(f"stress-ng -l {lvl} --cpu {args.cpu} -t {args.stress}s")
            sampler.mark(f"STRESS_{lvl}_END")

        # All levels complete
        sampler.mark("END_PROTOCOL")
    finally:
        # Ensure the sampler thread is stopped even if an exception occurs
        sampler.stop()
        print(f"[ok] CSV written to {args.out}")


if __name__ == "__main__":
    main()
