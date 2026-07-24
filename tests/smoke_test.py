"""
ACR Day 1 - end-to-end smoke test

emulate -> profile -> compile pulses -> verify the cells actually move
toward their targets. This is the one script that proves the two tracks
(emulator/profiler and pulse_compiler) agree on the same contract.

Run from the acr/ directory:
    python3 tests/smoke_test.py
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "runtime"))

from emulator import AnalogCrossbar
from profiler import DeviceProfiler
from pulse_compiler import compile_pulse


def main():
    xbar = AnalogCrossbar(n_cells=6, seed=123)
    profiler = DeviceProfiler(n_characterization_pulses=30)
    profiles = profiler.characterize_crossbar(xbar)

    target_g = 0.5
    errors = []
    print(f"{'cell':>4} {'start':>7} {'final':>7} {'error':>7} {'pulses':>7}")
    for cell, profile in zip(xbar.cells, profiles):
        start_g = cell.read(add_noise=False)
        plan = compile_pulse(profile, start_g, target_g)
        for step in plan:
            cell.apply_pulse(step["direction"], step["pulse_width"])
        final_g = cell.read(add_noise=False)
        err = abs(final_g - target_g)
        errors.append(err)
        print(f"{cell.cell_id:>4} {start_g:>7.3f} {final_g:>7.3f} {err:>7.3f} {len(plan):>7}")

    avg_error = sum(errors) / len(errors)
    print(f"\naverage final error: {avg_error:.4f}")
    assert avg_error < 0.2, "pulse compiler isn't converging well enough - check the fitted profile"
    print("SMOKE TEST PASSED (open-loop; closed-loop control next will tighten this further)")


if __name__ == "__main__":
    main()
