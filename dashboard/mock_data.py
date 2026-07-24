"""
ACR Day 1 - Mock device profile generator

Produces a device_profile.json with the exact schema the real profiler
(runtime/profiler.py) produces, so the dashboard can be built and tested
without waiting on the emulator/profiler to be finished. On Day 2, swap
this file's output for the real one - the dashboard doesn't need to change.

Run from the acr/ directory:
    python3 dashboard/mock_data.py
"""

import json
import random


def generate_mock_profile(n_cells=16, seed=1):
    rng = random.Random(seed)
    cells = []
    for i in range(n_cells):
        cells.append({
            "cell_id": i,
            "gamma_up_est": round(rng.uniform(0.6, 1.8), 4),
            "gamma_down_est": round(rng.uniform(0.6, 1.8), 4),
            "pulse_gain_est": round(rng.uniform(0.03, 0.09), 5),
            "write_noise_std_est": round(rng.uniform(0.002, 0.02), 5),
            "read_noise_std_est": round(rng.uniform(0.002, 0.01), 5),
            "drift_rate_est": round(rng.uniform(-0.001, 0.001), 8),
            "g_min_phys": 1.0,
            "g_max_phys": 25.0,
            "n_pulses_used": 30,
        })
    return {"cells": cells}


if __name__ == "__main__":
    data = generate_mock_profile()
    with open("mock_device_profile.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote mock_device_profile.json with {len(data['cells'])} cells")
