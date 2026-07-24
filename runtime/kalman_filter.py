"""
AIMC Kalman Filter for Drift Exponent Tracking

Implements a scalar Kalman filter to track the drift exponent nu per tile
using the power-law drift model: G(t) = G0 * (t/t0)^(-nu)

The filter estimates nu from sparse probe observations, predicting when
drift will become critical and enabling proactive compensation.

This is the core of the Compensation Tick's drift tracking capability.
"""

import math
import numpy as np
from typing import Optional, List, Dict
from dataclasses import dataclass, field


@dataclass
class DriftEstimate:
    """A single drift estimate from the Kalman filter."""
    time: float
    nu_hat: float
    residual: float
    covariance: float
    confidence: float


class KalmanDriftTracker:
    """
    Scalar Kalman filter tracking drift exponent nu per tile.

    State model: nu_{k+1} = nu_k + w_k  (random walk)
    Measurement: G_k = G_0 * (t_k/t_0)^(-nu_k) + v_k

    The filter linearizes the nonlinear observation model around the
    current estimate to apply standard Kalman update equations.
    """

    def __init__(self, tile_id: int, initial_nu: float = 0.01,
                 process_noise: float = 1e-6, measurement_noise: float = 0.01):
        """
        Args:
            tile_id: Unique identifier for the tile
            initial_nu: Initial drift exponent estimate
            process_noise: Process noise variance (Q)
            measurement_noise: Measurement noise variance (R)
        """
        self.tile_id = tile_id
        self.nu_hat = initial_nu
        self.P = 0.01
        self.Q = process_noise
        self.R = measurement_noise
        self.G0 = None
        self.t0 = None
        self.initialized = False
        self.history: List[DriftEstimate] = []
        self.update_count = 0

    def predict(self, current_time: float):
        """
        State prediction step.

        For a random walk model, the state doesn't change,
        but uncertainty grows due to process noise.
        """
        self.P += self.Q

    def update(self, measured_G: float, current_time: float) -> float:
        """
        Measurement update using linearized observation model.

        Args:
            measured_G: Observed conductance from sparse probe
            current_time: Current timestamp

        Returns:
            Innovation (measurement residual) for monitoring
        """
        if not self.initialized:
            self.G0 = measured_G
            self.t0 = current_time
            self.initialized = True
            self.history.append(DriftEstimate(
                time=current_time,
                nu_hat=self.nu_hat,
                residual=0.0,
                covariance=self.P,
                confidence=self.get_confidence()
            ))
            return 0.0

        t_ratio = current_time / self.t0
        if t_ratio <= 0 or abs(t_ratio - 1.0) < 1e-10:
            return 0.0

        G_expected = self.G0 * (t_ratio ** (-self.nu_hat))

        y = measured_G - G_expected

        H = -self.G0 * (t_ratio ** (-self.nu_hat)) * math.log(t_ratio)

        S = H * self.P * H + self.R

        K = self.P * H / S if abs(S) > 1e-12 else 0.0

        self.nu_hat += K * y

        self.P = (1.0 - K * H) * self.P

        self.nu_hat = max(0.0001, min(0.5, self.nu_hat))
        self.P = max(1e-10, self.P)

        self.update_count += 1
        self.history.append(DriftEstimate(
            time=current_time,
            nu_hat=self.nu_hat,
            residual=y,
            covariance=self.P,
            confidence=self.get_confidence()
        ))

        return y

    def predict_critical_time(self, threshold: float = 0.1) -> float:
        """
        Predict when conductance will drift beyond threshold fraction.

        Uses the current nu estimate to project when:
        G(t) = G0 * (t/t0)^(-nu) = G0 * (1 - threshold)

        Args:
            threshold: Drift threshold fraction (e.g., 0.1 = 10% drift)

        Returns:
            Predicted time when drift exceeds threshold
        """
        if self.nu_hat <= 0 or self.t0 is None:
            return float('inf')

        return self.t0 * math.exp(-math.log(1 - threshold) / self.nu_hat)

    def get_confidence(self) -> float:
        """
        Return confidence in current estimate (inverse of uncertainty).
        """
        return 1.0 / (1.0 + self.P)

    def get_state(self) -> Dict:
        """Get current filter state as dictionary."""
        return {
            'tile_id': self.tile_id,
            'nu_hat': self.nu_hat,
            'covariance': self.P,
            'confidence': self.get_confidence(),
            'initialized': self.initialized,
            'update_count': self.update_count,
            'critical_time_10pct': self.predict_critical_time(0.1),
            'critical_time_20pct': self.predict_critical_time(0.2),
        }

    def get_history(self) -> List[Dict]:
        """Get filter history as list of dictionaries."""
        return [
            {
                'time': h.time,
                'nu_hat': h.nu_hat,
                'residual': h.residual,
                'covariance': h.covariance,
                'confidence': h.confidence,
            }
            for h in self.history
        ]


class MultiTileKalmanManager:
    """
    Manages Kalman filters across multiple tiles.

    Provides centralized drift tracking and prediction for the
    Compensation Tick coprocessor.
    """

    def __init__(self, initial_nu: float = 0.01,
                 process_noise: float = 1e-6,
                 measurement_noise: float = 0.01):
        self.initial_nu = initial_nu
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.trackers: Dict[int, KalmanDriftTracker] = {}

    def initialize_tile(self, tile_id: int) -> KalmanDriftTracker:
        """Initialize a Kalman tracker for a tile."""
        tracker = KalmanDriftTracker(
            tile_id=tile_id,
            initial_nu=self.initial_nu,
            process_noise=self.process_noise,
            measurement_noise=self.measurement_noise
        )
        self.trackers[tile_id] = tracker
        return tracker

    def predict(self, tile_id: int, current_time: float):
        """Run prediction step for a tile."""
        if tile_id in self.trackers:
            self.trackers[tile_id].predict(current_time)

    def update(self, tile_id: int, measured_G: float, current_time: float) -> float:
        """Run measurement update for a tile."""
        if tile_id not in self.trackers:
            return 0.0
        return self.trackers[tile_id].update(measured_G, current_time)

    def get_nu(self, tile_id: int) -> float:
        """Get current drift exponent estimate for a tile."""
        if tile_id not in self.trackers:
            return self.initial_nu
        return self.trackers[tile_id].nu_hat

    def get_critical_time(self, tile_id: int, threshold: float = 0.1) -> float:
        """Get predicted critical time for a tile."""
        if tile_id not in self.trackers:
            return float('inf')
        return self.trackers[tile_id].predict_critical_time(threshold)

    def get_all_states(self) -> Dict[int, Dict]:
        """Get states of all trackers."""
        return {tid: tracker.get_state()
                for tid, tracker in self.trackers.items()}

    def get_drift_ranking(self) -> List[int]:
        """Get tile IDs ranked by drift exponent (highest first)."""
        return sorted(
            self.trackers.keys(),
            key=lambda tid: self.trackers[tid].nu_hat,
            reverse=True
        )


def estimate_drift_exponent_simple(readings_history: List[float],
                                   times: List[float]) -> float:
    """
    Simple drift exponent estimation from conductance time-series.

    Fits power-law model G(t) = G0 * (t/t0)^(-nu) using log-linear regression.

    Args:
        readings_history: Conductance readings over time
        times: Corresponding timestamps

    Returns:
        Estimated drift exponent nu
    """
    if len(readings_history) < 3 or len(times) < 3:
        return 0.01

    readings = np.array(readings_history, dtype=np.float64)
    time_arr = np.array(times, dtype=np.float64)

    time_arr = np.maximum(time_arr, 1e-10)
    readings = np.maximum(readings, 1e-10)

    log_t = np.log(time_arr / time_arr[0])
    log_g = np.log(readings / readings[0])

    mask = np.abs(log_t) > 1e-10
    if np.sum(mask) < 2:
        return 0.01

    log_t_masked = log_t[mask]
    log_g_masked = log_g[mask]

    nu = -np.polyfit(log_t_masked, log_g_masked, 1)[0]

    return max(0.0001, min(0.5, nu))
