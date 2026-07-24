"""
ACR Day 1 (continued) - Closed-Loop Conductance Control

Wraps the open-loop pulse_compiler with a measure -> correct -> repeat
loop: apply one pulse, re-read the actual cell, and re-plan from
wherever it actually landed - instead of trusting the calibration
curve for a whole multi-pulse sequence like compile_pulse() alone does.

Works against ANY object exposing .read(add_noise) and
.apply_pulse(direction, pulse_width):
  - FakeCell below, for building/testing this today without the emulator
  - a real runtime.emulator.AnalogCell once the two tracks merge

Run from the acr/ directory:
    python3 runtime/closed_loop.py
"""

import random

from pulse_compiler import compile_pulse


def closed_loop_program(cell, profile, target_g, max_pulses=50, tolerance=1e-3):
    """
    Returns a history: one dict per pulse actually applied, plus a
    final summary dict with the converged conductance.
    """
    history = []
    for _ in range(max_pulses):
        current_g = cell.read(add_noise=False)
        if abs(target_g - current_g) < tolerance:
            break

        # ask for exactly the next pulse given where the cell REALLY is,
        # not where an earlier open-loop plan predicted it would be
        next_step = compile_pulse(profile, current_g, target_g, max_pulses=1, tolerance=tolerance)
        if not next_step:
            break

        step = next_step[0]
        cell.apply_pulse(step["direction"], step["pulse_width"])
        history.append({
            "direction": step["direction"],
            "pulse_width": step["pulse_width"],
            "g_before": round(current_g, 5),
            "g_after": round(cell.read(add_noise=False), 5),
        })

    final_g = cell.read(add_noise=False)
    history.append({"final_g": round(final_g, 5), "target_g": target_g, "n_pulses": len(history)})
    return history


class FakeCell:
    """
    Minimal stand-in for runtime.emulator.AnalogCell - same public
    interface (read, apply_pulse) so this module and its tests never
    need the real emulator today. Swap in a real AnalogCell on Day 2;
    closed_loop_program() itself doesn't change at all.
    """

    def __init__(self, g_norm=0.3, gamma_up=1.0, gamma_down=1.0,
                 pulse_gain=0.05, write_noise_std=0.1, seed=0):
        self.g_norm = g_norm
        self.gamma_up = gamma_up
        self.gamma_down = gamma_down
        self.pulse_gain = pulse_gain
        self.write_noise_std = write_noise_std
        self._rng = random.Random(seed)

    def apply_pulse(self, direction, pulse_width=1.0):
        base_step = self.pulse_gain * pulse_width
        if direction == "SET":
            ideal = base_step * ((1.0 - self.g_norm) ** self.gamma_up)
        else:
            ideal = -base_step * (self.g_norm ** self.gamma_down)
        noise = self._rng.gauss(0.0, self.write_noise_std * base_step)
        self.g_norm = max(0.0, min(1.0, self.g_norm + ideal + noise))
        return ideal + noise

    def read(self, add_noise=False):
        val = self.g_norm
        if add_noise:
            val += self._rng.gauss(0.0, 0.01)
        return max(0.0, min(1.0, val))


if __name__ == "__main__":
    # Deliberately WRONG calibration profile (doesn't match the cell's
    # true params) to show closed-loop correcting for it as it goes -
    # this is the realistic case, since profiler.py estimates are
    # always somewhat off from ground truth.
    true_cell_kwargs = dict(gamma_up=1.6, gamma_down=0.7, pulse_gain=0.035,
                             write_noise_std=0.2, seed=9)
    wrong_profile = {"gamma_up_est": 1.0, "gamma_down_est": 1.0, "pulse_gain_est": 0.05}
    target_g, start_g = 0.7, 0.15

    # open-loop: plan the whole sequence up front, trust it blindly
    open_cell = FakeCell(g_norm=start_g, **true_cell_kwargs)
    open_plan = compile_pulse(wrong_profile, start_g, target_g)
    for step in open_plan:
        open_cell.apply_pulse(step["direction"], step["pulse_width"])
    open_final = open_cell.read(add_noise=False)

    # closed-loop: re-measure and re-plan after every single pulse
    closed_cell = FakeCell(g_norm=start_g, **true_cell_kwargs)
    closed_history = closed_loop_program(closed_cell, wrong_profile, target_g)
    closed_summary = closed_history[-1]

    print(f"target: {target_g}\n")
    print(f"open-loop:   final={open_final:.4f}  error={abs(open_final - target_g):.4f}  pulses={len(open_plan)}")
    print(f"closed-loop: final={closed_summary['final_g']:.4f}  "
          f"error={abs(closed_summary['final_g'] - target_g):.4f}  pulses={closed_summary['n_pulses']}")
