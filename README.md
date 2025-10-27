# Stress–Energy Cycle Logger
A Raspberry Pi 5 Power-Measurement Experiment using `vcgencmd` and `stress-ng`

---

## Overview
This project automates energy consumption measurements on a Raspberry Pi 5 during controlled CPU stress and rest cycles.  
It uses:

- [`stress-ng`](https://wiki.ubuntu.com/Kernel/Reference/stress-ng) to apply CPU loads (0–100% in configurable steps)  
- `vcgencmd pmic_read_adc` to measure core voltage and current  
- CSV logging to record voltage, current, power, and timestamps  
- Optional compatibility with external power meters (Siglent) for future expansion

---

## Folder Structure

stress_energy_cycle/
├── energy_logger.py        # Reads voltage/current using vcgencmd
├── main_with_csv.py        # Orchestrates stress/rest cycles and CSV logging
└── README.md               # This file

---

## Features
- Automated stress-and-rest testing sequence  
- Adjustable durations, sampling rate, and load levels  
- Real-time CSV logging with timestamps and power data  
- Works with or without `stress-ng` (simulation mode on macOS)  
- Ready for integration with external instruments (Siglent, etc.)

---

## How It Works
1. The script runs alternating rest (20 s) and stress (80 s) phases.  
2. During each phase, it logs:
   - Timestamp (UTC)
   - CPU load (%)
   - Voltage (V)
   - Current (A)
   - Power (W)
   - Phase marker (REST/STRESS)
3. A CSV file like `energy_cycle_log.csv` is created for post-analysis.

Example CSV headers:

timestamp_iso, epoch_s, load_percent, voltage_v, current_a, power_w, marker

---

## Installation (Raspberry Pi 5)
```bash
sudo apt update
sudo apt install -y stress-ng python3

Clone or copy your files:

git clone https://github.com/<your-user>/stress_energy_cycle.git
cd stress_energy_cycle


⸻

Verification Steps (Before Running)

To ensure your Raspberry Pi can read voltage and current values, test the following command:

vcgencmd pmic_read_adc

Expected output (example):

VDD_CORE_V = 0.8420V
VDD_CORE_A = 0.1530A
VDD_SDCARD_V = 3.3172V
VDD_SDCARD_A = 0.0123A

If you see similar lines containing VDD_CORE_V and VDD_CORE_A, your Pi is ready for measurement.
If the command fails, ensure your user has permission to run vcgencmd without sudo.

⸻

Usage

Run the experiment:

python3 main_with_csv.py

Command-line options

Option	Description	Default
--cpu	Number of CPU workers	1
--rest	Duration (seconds) of rest at 0% load	20
--stress	Duration (seconds) of stress at each load	80
--levels	Load levels (comma-list or range 0:100:10)	0,10,...,100
--interval	Sampling interval for voltage/current readings	0.5 s
--out	Output CSV file name	energy_cycle_log.csv

Example:

python3 main_with_csv.py --rest 20 --stress 80 --levels 0:100:10 --interval 0.25


⸻

macOS / Local Simulation Mode

You can test the script locally before deploying to the Pi.
	•	If stress-ng is not installed, the script automatically simulates the load using sleep.
	•	Voltage/current readings will be blank, but timestamps and phase markers will still be logged.

To install stress-ng on macOS:

brew install stress-ng


⸻

Output Example

After running, a file such as:

energy_cycle_log_20251022_154500.csv

is created with entries like:

timestamp_iso,epoch_s,load_percent,voltage_v,current_a,power_w,marker
2025-10-22T15:45:00.123Z,1732801500.123,0,0.842,0.156,0.131,REST_BEGIN_level_10
2025-10-22T15:45:20.456Z,1732801520.456,10,0.835,0.231,0.193,STRESS_10_BEGIN
...


⸻

Future Expansion

The system is designed for future integration with Siglent power supplies or DMMs via SCPI commands.
Planned extensions:
	•	External logging via LAN/TCP (port 5025)
	•	Real-time graph plotting
	•	Energy comparison between CPU loads

⸻

Notes
	•	The script relies on vcgencmd pmic_read_adc, which is available only on Raspberry Pi boards.
	•	On non-Pi systems, the voltage/current fields remain empty.
	•	Ensure vcgencmd is accessible without sudo.

⸻

Author

Nilma Abbas,
Zealand Institute of Business and Technology

⸻

License

