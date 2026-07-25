"""
ACR Improved Pulse Compiler — Enhanced Accuracy Version

Improvements over basic pulse_compiler.py:
1. Adaptive pulse width scaling
2. Fine-tuning pass for final corrections
3. Better handling of saturation regions
4. Multi-pass approach for higher accuracy

Target: Reduce open-loop error from 3.2% to <2%
"""

import math


def compile_pulse_improved(cell_profile, current_g, target_g, 
                           max_pulses=50, tolerance=1e-3):
    """
    Improved pulse compiler with adaptive scaling.
    
    Returns a list of {"direction": "SET"|"RESET", "pulse_width": float}.
    """
    g = current_g
    gamma_up = cell_profile["gamma_up_est"]
    gamma_down = cell_profile["gamma_down_est"]
    gain = cell_profile["pulse_gain_est"]
    
    plan = []
    
    for pulse_num in range(max_pulses):
        error = target_g - g
        if abs(error) < tolerance:
            break
        
        # Adaptive pulse width: smaller pulses near target
        distance_to_target = abs(error)
        
        if distance_to_target > 0.3:
            # Large error: use bigger pulses
            scale_factor = 1.0
        elif distance_to_target > 0.1:
            # Medium error: moderate pulses
            scale_factor = 0.7
        elif distance_to_target > 0.02:
            # Small error: fine control
            scale_factor = 0.4
        else:
            # Very small error: precision mode
            scale_factor = 0.2
        
        if error > 0:
            direction = "SET"
            step = gain * ((1.0 - g) ** gamma_up)
        else:
            direction = "RESET"
            step = gain * (g ** gamma_down)
        
        if step < 1e-6:
            break
        
        # Calculate pulse width with adaptive scaling
        raw_pulse_width = abs(error) / step
        pulse_width = min(1.0, raw_pulse_width * scale_factor)
        
        # Ensure minimum pulse width for small corrections
        pulse_width = max(0.05, pulse_width)
        
        plan.append({"direction": direction, "pulse_width": round(pulse_width, 4)})
        
        signed_step = step * pulse_width
        g = g + signed_step if direction == "SET" else g - signed_step
        g = max(0.0, min(1.0, g))
    
    return plan


def compile_pulse_two_pass(cell_profile, current_g, target_g, 
                           max_pulses=50, tolerance=1e-3):
    """
    Two-pass approach:
    1. Coarse pass: get close to target
    2. Fine pass: precise adjustment
    """
    # Pass 1: Coarse adjustment
    coarse_plan = compile_pulse_improved(
        cell_profile, current_g, target_g, 
        max_pulses=max_pulses // 2, tolerance=tolerance * 5
    )
    
    # Simulate execution of coarse plan
    g = current_g
    gamma_up = cell_profile["gamma_up_est"]
    gamma_down = cell_profile["gamma_down_est"]
    gain = cell_profile["pulse_gain_est"]
    
    for step in coarse_plan:
        if step["direction"] == "SET":
            s = gain * ((1.0 - g) ** gamma_up) * step["pulse_width"]
            g = min(1.0, g + s)
        else:
            s = gain * (g ** gamma_down) * step["pulse_width"]
            g = max(0.0, g - s)
    
    # Pass 2: Fine adjustment from where we landed
    fine_plan = compile_pulse_improved(
        cell_profile, g, target_g,
        max_pulses=max_pulses // 2, tolerance=tolerance
    )
    
    return coarse_plan + fine_plan


def compile_pulse_adaptive(cell_profile, current_g, target_g,
                           max_pulses=50, tolerance=1e-3):
    """
    Fully adaptive approach that adjusts strategy based on progress.
    """
    g = current_g
    gamma_up = cell_profile["gamma_up_est"]
    gamma_down = cell_profile["gamma_down_est"]
    gain = cell_profile["pulse_gain_est"]
    
    plan = []
    prev_error = abs(target_g - current_g)
    
    for pulse_num in range(max_pulses):
        error = target_g - g
        abs_error = abs(error)
        
        if abs_error < tolerance:
            break
        
        # Check if we're making progress
        progress = prev_error - abs_error
        if pulse_num > 3 and progress < 0.001:
            # Stalled: increase pulse width
            scale_factor = 1.2
        elif abs_error < 0.01:
            # Very close: precision mode
            scale_factor = 0.15
        elif abs_error < 0.05:
            # Close: fine control
            scale_factor = 0.3
        elif abs_error < 0.15:
            # Moderate: balanced
            scale_factor = 0.6
        else:
            # Far: aggressive
            scale_factor = 1.0
        
        if error > 0:
            direction = "SET"
            step = gain * ((1.0 - g) ** gamma_up)
        else:
            direction = "RESET"
            step = gain * (g ** gamma_down)
        
        if step < 1e-6:
            break
        
        raw_pulse_width = abs_error / step
        pulse_width = min(1.0, raw_pulse_width * scale_factor)
        pulse_width = max(0.03, pulse_width)
        
        plan.append({"direction": direction, "pulse_width": round(pulse_width, 4)})
        
        signed_step = step * pulse_width
        g = g + signed_step if direction == "SET" else g - signed_step
        g = max(0.0, min(1.0, g))
        
        prev_error = abs_error
    
    return plan


if __name__ == "__main__":
    # Test all three approaches
    profile = {
        "gamma_up_est": 1.5,
        "gamma_down_est": 0.8,
        "pulse_gain_est": 0.04,
    }
    
    target = 0.7
    start = 0.2
    
    print("Testing improved pulse compilers:")
    print(f"Target: {target}, Start: {start}")
    print()
    
    # Basic
    from pulse_compiler import compile_pulse
    basic_plan = compile_pulse(profile, start, target)
    print(f"Basic: {len(basic_plan)} pulses")
    
    # Improved
    improved_plan = compile_pulse_improved(profile, start, target)
    print(f"Improved: {len(improved_plan)} pulses")
    
    # Two-pass
    two_pass_plan = compile_pulse_two_pass(profile, start, target)
    print(f"Two-pass: {len(two_pass_plan)} pulses")
    
    # Adaptive
    adaptive_plan = compile_pulse_adaptive(profile, start, target)
    print(f"Adaptive: {len(adaptive_plan)} pulses")
