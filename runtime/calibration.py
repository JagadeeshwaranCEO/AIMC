"""
ACR Calibration Engine — Fits power laws, estimates noise, and extracts device parameters.
"""
import math
import statistics


def fit_power_law(xs, ys):
    """Fit y = a * x^gamma via log-linear regression."""
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




def fit_cell_profile(cell_id, set_xs, set_ys, reset_xs, reset_ys, read_samples, drift_delta, dt):
    """Translates raw pulse measurement series into a structured profile dict."""
    pulse_gain_up, gamma_up = fit_power_law(set_xs, set_ys)
    pulse_gain_down, gamma_down = fit_power_law(reset_xs, reset_ys)
    pulse_gain_est = (pulse_gain_up + pulse_gain_down) / 2.0


    resid = []
    for x, y in zip(set_xs, set_ys):
        pred = pulse_gain_up * (x ** gamma_up) if x > 0 else pulse_gain_up
        resid.append(y - pred)
    write_noise_std_est = statistics.pstdev(resid) if len(resid) > 1 else 0.0
    read_noise_std_est = statistics.pstdev(read_samples)
    drift_rate_est = drift_delta / dt if dt > 0 else 0.0


    return {
        "cell_id": cell_id,
        "gamma_up_est": round(gamma_up, 4),
        "gamma_down_est": round(gamma_down, 4),
        "pulse_gain_est": round(pulse_gain_est, 5),
        "write_noise_std_est": round(write_noise_std_est, 5),
        "read_noise_std_est": round(read_noise_std_est, 5),
        "drift_rate_est": round(drift_rate_est, 8),
    }
