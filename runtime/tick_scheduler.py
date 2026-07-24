"""
AIMC Closed-Loop Tick Scheduler

Implements adaptive tick frequency scheduling for the Compensation Tick
coprocessor. The key insight: tick frequency should adapt to the measured
drift rate of each tile.

High-drift tiles (like PCM) need more frequent ticks.
Stable tiles (like FeFET) need fewer ticks.
Uncertainty triggers more frequent ticks to maintain accuracy.

This is the "closed-loop control" aspect of the Aegis-AIMC architecture.
"""

import math
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class TileSchedule:
    """Schedule state for a single tile."""
    tile_id: int
    next_tick_time: float = 0.0
    current_interval: float = 10.0
    base_interval: float = 10.0
    drift_rate_estimate: float = 0.01
    consecutive_stable_ticks: int = 0
    tick_count: int = 0
    min_interval: float = 1.0
    max_interval: float = 1000.0


class TickScheduler:
    """
    Closed-loop adaptive tick scheduling.

    Adapts tick frequency based on measured drift rate:
    - High-drift tiles tick more frequently
    - Stable tiles tick rarely
    - Uncertainty triggers more frequent ticks

    The scheduler uses a combination of:
    1. Drift-based adaptation: interval proportional to 1/nu
    2. Uncertainty penalty: high prediction error -> shorter interval
    3. Stability bonus: consecutive stable ticks -> longer interval
    """

    def __init__(self, tile_ids: List[int], base_interval: float = 10.0,
                 min_interval: float = 1.0, max_interval: float = 1000.0):
        """
        Args:
            tile_ids: List of tile IDs to schedule
            base_interval: Default tick interval
            min_interval: Minimum allowed interval
            max_interval: Maximum allowed interval
        """
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval

        self.tile_schedules: Dict[int, TileSchedule] = {}
        for tid in tile_ids:
            self.tile_schedules[tid] = TileSchedule(
                tile_id=tid,
                next_tick_time=0.0,
                current_interval=base_interval,
                base_interval=base_interval,
                min_interval=min_interval,
                max_interval=max_interval,
            )

    def compute_next_interval(self, tile_id: int, measured_nu: float,
                              prediction_residual: float) -> float:
        """
        Adapt tick interval based on measured drift exponent and prediction error.

        High nu (fast drift) -> shorter interval (more frequent ticks)
        Low nu (stable) -> longer interval (less frequent ticks)
        High prediction error -> shorter interval (model is uncertain)

        Args:
            tile_id: Tile identifier
            measured_nu: Current drift exponent estimate from Kalman filter
            prediction_residual: Innovation from Kalman filter update

        Returns:
            New tick interval for this tile
        """
        schedule = self.tile_schedules[tile_id]

        drift_factor = self.base_interval / (measured_nu * 100 + 0.1)

        uncertainty_factor = 1.0 / (1.0 + abs(prediction_residual) * 10)

        if abs(prediction_residual) < 0.01:
            schedule.consecutive_stable_ticks += 1
        else:
            schedule.consecutive_stable_ticks = 0

        stability_factor = 1.0 + min(schedule.consecutive_stable_ticks * 0.1, 2.0)

        new_interval = drift_factor * uncertainty_factor * stability_factor
        new_interval = max(self.min_interval, min(self.max_interval, new_interval))

        alpha = 0.3
        schedule.current_interval = (
            alpha * new_interval + (1 - alpha) * schedule.current_interval
        )

        schedule.drift_rate_estimate = measured_nu

        return schedule.current_interval

    def should_tick(self, tile_id: int, current_time: float) -> bool:
        """
        Check if a tile is due for a Compensation Tick.

        Args:
            tile_id: Tile identifier
            current_time: Current simulation time

        Returns:
            True if tile is due for a tick
        """
        if tile_id not in self.tile_schedules:
            return True

        schedule = self.tile_schedules[tile_id]
        return current_time >= schedule.next_tick_time

    def mark_ticked(self, tile_id: int, current_time: float):
        """
        Record that a tick just occurred and schedule the next one.

        Args:
            tile_id: Tile identifier
            current_time: Current simulation time
        """
        if tile_id not in self.tile_schedules:
            return

        schedule = self.tile_schedules[tile_id]
        schedule.tick_count += 1
        schedule.next_tick_time = current_time + schedule.current_interval

    def get_interval(self, tile_id: int) -> float:
        """Get current tick interval for a tile."""
        if tile_id not in self.tile_schedules:
            return self.base_interval
        return self.tile_schedules[tile_id].current_interval

    def get_tick_count(self, tile_id: int) -> int:
        """Get total tick count for a tile."""
        if tile_id not in self.tile_schedules:
            return 0
        return self.tile_schedules[tile_id].tick_count

    def get_drift_rate(self, tile_id: int) -> float:
        """Get estimated drift rate for a tile."""
        if tile_id not in self.tile_schedules:
            return 0.01
        return self.tile_schedules[tile_id].drift_rate_estimate

    def get_stability_score(self, tile_id: int) -> float:
        """
        Get stability score for a tile (0-1).
        Higher score means more stable (fewer ticks needed).
        """
        if tile_id not in self.tile_schedules:
            return 0.5

        schedule = self.tile_schedules[tile_id]
        stability = min(schedule.consecutive_stable_ticks / 10.0, 1.0)
        return stability

    def get_all_states(self) -> Dict[int, Dict]:
        """Get states of all schedules."""
        return {
            tid: {
                'tile_id': schedule.tile_id,
                'current_interval': schedule.current_interval,
                'tick_count': schedule.tick_count,
                'drift_rate': schedule.drift_rate_estimate,
                'stability_score': self.get_stability_score(tid),
                'next_tick_time': schedule.next_tick_time,
            }
            for tid, schedule in self.tile_schedules.items()
        }

    def force_tick(self, tile_id: int, current_time: float):
        """Force an immediate tick for a tile (for testing/debugging)."""
        if tile_id in self.tile_schedules:
            self.tile_schedules[tile_id].next_tick_time = current_time

    def set_interval(self, tile_id: int, interval: float):
        """Manually set tick interval for a tile."""
        if tile_id in self.tile_schedules:
            self.tile_schedules[tile_id].current_interval = max(
                self.min_interval,
                min(self.max_interval, interval)
            )


class AdaptiveTickController:
    """
    High-level controller that manages tick scheduling across all tiles.

    Provides a unified interface for the Compensation Tick coprocessor
    to interact with the scheduler.
    """

    def __init__(self, base_interval: float = 10.0,
                 min_interval: float = 1.0,
                 max_interval: float = 1000.0):
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.scheduler: Optional[TickScheduler] = None
        self.tile_nu_history: Dict[int, List[float]] = {}

    def initialize(self, tile_ids: List[int]):
        """Initialize scheduler for a set of tiles."""
        self.scheduler = TickScheduler(
            tile_ids=tile_ids,
            base_interval=self.base_interval,
            min_interval=self.min_interval,
            max_interval=self.max_interval,
        )
        for tid in tile_ids:
            self.tile_nu_history[tid] = []

    def should_tick(self, tile_id: int, current_time: float) -> bool:
        """Check if a tile should be ticked."""
        if self.scheduler is None:
            return True
        return self.scheduler.should_tick(tile_id, current_time)

    def update(self, tile_id: int, measured_nu: float,
               prediction_residual: float, current_time: float):
        """
        Update scheduler with new drift measurement.

        Args:
            tile_id: Tile identifier
            measured_nu: Current drift exponent from Kalman filter
            prediction_residual: Kalman innovation
            current_time: Current simulation time
        """
        if self.scheduler is None:
            return

        self.tile_nu_history.setdefault(tile_id, []).append(measured_nu)

        self.scheduler.compute_next_interval(tile_id, measured_nu, prediction_residual)
        self.scheduler.mark_ticked(tile_id, current_time)

    def get_tick_frequency_summary(self) -> Dict[int, Dict]:
        """
        Get summary of tick frequencies across all tiles.
        """
        if self.scheduler is None:
            return {}

        summary = {}
        for tid, schedule in self.scheduler.tile_schedules.items():
            nu_history = self.tile_nu_history.get(tid, [])
            avg_nu = sum(nu_history) / len(nu_history) if nu_history else 0.01

            summary[tid] = {
                'avg_drift_exponent': avg_nu,
                'current_interval': schedule.current_interval,
                'total_ticks': schedule.tick_count,
                'stability_score': self.scheduler.get_stability_score(tid),
            }

        return summary
