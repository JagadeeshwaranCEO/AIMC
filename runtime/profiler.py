"""
ACR Day 1 - Device Profiler

Exercises each analog cell with known pulse sequences and fits a
simplified device model to the observed responses, without ever
touching the cell's true (hidden) parameters. Produces device_profile.json,
matching schemas/device_profile.schema.json.

Run from the acr/ directory:
    python3 runtime/profiler.py
"""

import json
import math
import statistics

from emulator import AnalogCrossbar


def _fit_power_law(xs, ys):
    """
    Fit y = a * x^gamma via log-linear regression.
    Falls back to (mean(ys), 1.0) if there isn't enough usable data.
    """
    pts = [(math.log(x), math.log(y)) for x, y in zip(xs, ys) if x > 1e-6 and y > 1e-6]
    if len(pts) < 3:
        return (statistics.mean(ys) if ys else 0.0, 1.0)

    n = len(pts)
    mean_x = sum(p[0] for p in pts) / n
    mean_y = sum(p[1] for p in pts) / n
    num = sum((px - mean_x) * (py - mean_y) for px, py in pts)
    den = sum((px - mean_x) ** 2 for px, _ in pts)
    gamma = num / den if den > 1e-12 else 1.0
    log_a = mean_y - gamma * mean_x
    return (math.exp(log_a), gamma)


class DeviceProfiler:
    def __init__(self, n_characterization_pulses=30, drift_probe_dt=150):
        self.n_pulses = n_characterization_pulses
        self.drift_probe_dt = drift_probe_dt

    def characterize_cell(self, cell):
        set_xs, set_ys = [], []
        for _ in range(self.n_pulses):
            g_before = cell.read(add_noise=False)
            delta = cell.apply_pulse("SET")
            set_xs.append(1.0 - g_before)
            set_ys.append(max(delta, 1e-6))

        reset_xs, reset_ys = [], []
        for _ in range(self.n_pulses):
            g_before = cell.read(add_noise=False)
            delta = cell.apply_pulse("RESET")
            reset_xs.append(g_before)
            reset_ys.append(max(-delta, 1e-6))

        pulse_gain_up, gamma_up = _fit_power_law(set_xs, set_ys)
        pulse_gain_down, gamma_down = _fit_power_law(reset_xs, reset_ys)
        pulse_gain_est = (pulse_gain_up + pulse_gain_down) / 2.0

        resid = []
        for x, y in zip(set_xs, set_ys):
            pred = pulse_gain_up * (x ** gamma_up) if x > 0 else pulse_gain_up
            resid.append(y - pred)
        write_noise_std_est = statistics.pstdev(resid) if len(resid) > 1 else 0.0

        reads = [cell.read(add_noise=True) for _ in range(20)]
        read_noise_std_est = statistics.pstdev(reads)

        g_before_drift = cell.read(add_noise=False)
        cell.step_time(self.drift_probe_dt)
        g_after_drift = cell.read(add_noise=False)
        drift_rate_est = (g_after_drift - g_before_drift) / self.drift_probe_dt

        return {
            "cell_id": cell.cell_id,
            "gamma_up_est": round(gamma_up, 4),
            "gamma_down_est": round(gamma_down, 4),
            "pulse_gain_est": round(pulse_gain_est, 5),
            "write_noise_std_est": round(write_noise_std_est, 5),
            "read_noise_std_est": round(read_noise_std_est, 5),
            "drift_rate_est": round(drift_rate_est, 8),
            "g_min_phys": cell.g_min_phys,
            "g_max_phys": cell.g_max_phys,
            "n_pulses_used": self.n_pulses,
        }

    def characterize_crossbar(self, xbar):
        return [self.characterize_cell(c) for c in xbar.cells]


if __name__ == "__main__":
    xbar = AnalogCrossbar(n_cells=16, seed=7)
    profiler = DeviceProfiler(n_characterization_pulses=30)
    profiles = profiler.characterize_crossbar(xbar)

    with open("device_profile.json", "w") as f:
        json.dump({"cells": profiles}, f, indent=2)

    print(f"profiled {len(profiles)} cells -> device_profile.json\n")
    header = f"{'id':>3} {'g_up':>6} {'g_down':>7} {'gain':>8} {'w_noise':>8} {'r_noise':>8} {'drift':>10}"
    print(header)
    for p in profiles:
        print(f"{p['cell_id']:>3} {p['gamma_up_est']:>6.2f} {p['gamma_down_est']:>7.2f} "
              f"{p['pulse_gain_est']:>8.4f} {p['write_noise_std_est']:>8.4f} "
              f"{p['read_noise_std_est']:>8.4f} {p['drift_rate_est']:>10.6f}")
