"""
ACR Day 1 (continued) - tests for runtime/pulse_compiler.py

This file belongs to the dashboard/Windows track - it never touches
the emulator, only the pulse compiler's contract.

Run from the acr/ directory:
    python3 tests/test_pulse_compiler.py
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "runtime"))
from pulse_compiler import compile_pulse


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    assert condition, name


def main():
    normal_profile = {"gamma_up_est": 1.1, "gamma_down_est": 1.2, "pulse_gain_est": 0.05}

    plan = compile_pulse(normal_profile, current_g=0.5, target_g=0.5005)
    check("already-at-target needs no pulses", len(plan) == 0)

    plan = compile_pulse(normal_profile, current_g=0.2, target_g=0.8)
    check("SET-only plan when target is above current", all(s["direction"] == "SET" for s in plan))
    check("SET plan is non-empty", len(plan) > 0)

    plan = compile_pulse(normal_profile, current_g=0.8, target_g=0.2)
    check("RESET-only plan when target is below current", all(s["direction"] == "RESET" for s in plan))

    tiny_gain_profile = {"gamma_up_est": 1.0, "gamma_down_est": 1.0, "pulse_gain_est": 0.0001}
    plan = compile_pulse(tiny_gain_profile, current_g=0.1, target_g=0.9, max_pulses=20)
    check("tiny gain respects the max_pulses cap (no runaway loop)", len(plan) <= 20)

    plan = compile_pulse(normal_profile, current_g=0.1, target_g=0.95)
    check("pulse widths always stay in (0, 1]", all(0 < s["pulse_width"] <= 1.0 for s in plan))

    extreme_profile = {"gamma_up_est": 5.0, "gamma_down_est": 0.3, "pulse_gain_est": 0.02}
    plan = compile_pulse(extreme_profile, current_g=0.05, target_g=0.95)
    check("extreme gamma values still return a plan without crashing", isinstance(plan, list))

    print("\nALL PULSE COMPILER TESTS PASSED")


if __name__ == "__main__":
    main()
