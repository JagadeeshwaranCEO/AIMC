"""
ACR Day 1 - Pulse Compiler

Given a per-cell calibration profile (from profiler.py or mock_data.py)
and a current/target normalized conductance, plans a sequence of pulses
that should drive the cell from current_g toward target_g.

This is OPEN-LOOP: it trusts the calibration curve and does not re-read
the real cell between pulses. Closed-loop control (apply one pulse,
re-measure, correct, repeat) is the natural next step and belongs in
its own module later - this file is deliberately just the planner.

No dependency on emulator.py: this only needs a profile dict, so the
dashboard track can build and test it against mock data all day.
"""


def compile_pulse(cell_profile, current_g, target_g, max_pulses=50, tolerance=1e-3):
    """
    Returns a list of {"direction": "SET"|"RESET", "pulse_width": float}.
    """
    g = current_g
    gamma_up = cell_profile["gamma_up_est"]
    gamma_down = cell_profile["gamma_down_est"]
    gain = cell_profile["pulse_gain_est"]

    plan = []
    for _ in range(max_pulses):
        error = target_g - g
        if abs(error) < tolerance:
            break

        if error > 0:
            direction = "SET"
            step = gain * ((1.0 - g) ** gamma_up)
        else:
            direction = "RESET"
            step = gain * (g ** gamma_down)

        if step < 1e-6:
            break  # predicted to be saturated in this direction, stop planning

        pulse_width = min(1.0, abs(error) / step)
        plan.append({"direction": direction, "pulse_width": round(pulse_width, 4)})

        signed_step = step * pulse_width
        g = g + signed_step if direction == "SET" else g - signed_step
        g = max(0.0, min(1.0, g))

    return plan


if __name__ == "__main__":
    demo_profile = {
        "gamma_up_est": 1.1,
        "gamma_down_est": 1.3,
        "pulse_gain_est": 0.05,
    }
    plan = compile_pulse(demo_profile, current_g=0.2, target_g=0.7)
    print(f"{len(plan)} pulses planned:")
    for step in plan:
        print(" ", step)
